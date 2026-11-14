#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["python-pptx", "pdfplumber", "lxml"]
# ///
"""Extract page-level context from PPTX, PDF, HTML, or strategy brief files.

This script is intentionally conservative: it extracts text, tables, speaker
notes, and image hints, then marks low-confidence pages for review instead of
guessing their content.

With --assets-dir it also exports embedded images (PPTX pictures, local HTML
<img> files, data URIs) so a multimodal agent can read them directly. Embedded
image bytes are always fingerprinted into content_hash for drift detection,
whether or not they are exported.

Run with `uv run extract_slides_context.py ...` if dependencies are missing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from xml.etree import ElementTree as ET


PAGE_STATUS_EXTRACTED = "extracted"
PAGE_STATUS_PARTIAL = "partial"
PAGE_STATUS_IMAGE_ONLY = "image_only"
PAGE_STATUS_NEEDS_REVIEW = "needs_review"
PAGE_STATUS_NEEDS_OCR = "needs_ocr"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_lines(values: Iterable[Any]) -> List[str]:
    seen = set()
    lines: List[str] = []
    for value in values:
        text = clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        lines.append(text)
    return lines


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def short_bytes_hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()[:16]


def table_text(tables: List[Dict[str, Any]]) -> str:
    chunks: List[str] = []
    for table in tables:
        for row in table.get("rows", []):
            chunks.append(" | ".join(clean_text(cell) for cell in row))
    return "\n".join(chunks)


def page_fingerprints(
    title: str,
    text_blocks: List[str],
    tables: List[Dict[str, Any]],
    speaker_notes: List[str],
    image_hints: List[str],
    image_digests: Optional[List[str]] = None,
) -> Dict[str, str]:
    # Speaker notes are intentionally excluded from the drift fingerprint.
    # Assist output may add managed notes blocks, and those should not make
    # repeated safe writes look like the visible slides changed.
    _ = speaker_notes
    content = "\n".join(
        [
            clean_text(title),
            "\n".join(text_blocks),
            table_text(tables),
            "\n".join(image_hints),
            "\n".join(image_digests or []),
        ]
    )
    return {
        "title_hash": short_hash(clean_text(title)),
        "content_hash": short_hash(clean_text(content)),
    }


def numeric_suffix(path: str) -> int:
    match = re.search(r"(\d+)(?=\.[^.]+$)", path)
    return int(match.group(1)) if match else 0


def infer_status(
    text_blocks: List[str],
    tables: List[Dict[str, Any]],
    speaker_notes: List[str],
    image_hints: List[str],
    warnings: List[str],
    *,
    source_type: str,
) -> str:
    has_text = bool(text_blocks or tables or speaker_notes)
    if has_text and warnings:
        return PAGE_STATUS_PARTIAL
    if has_text:
        return PAGE_STATUS_EXTRACTED
    if image_hints:
        return PAGE_STATUS_IMAGE_ONLY
    if source_type == "pdf":
        return PAGE_STATUS_NEEDS_OCR
    return PAGE_STATUS_NEEDS_REVIEW


def extract_text_from_xml(xml_bytes: bytes) -> List[str]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    texts: List[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") or node.tag == "t":
            if node.text:
                texts.append(node.text)
    return clean_lines(texts)


def read_pptx_notes(pptx_path: Path) -> Dict[int, List[str]]:
    notes_by_slide: Dict[int, List[str]] = {}
    try:
        with zipfile.ZipFile(pptx_path) as archive:
            slide_paths = sorted(
                [
                    name
                    for name in archive.namelist()
                    if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
                ],
                key=numeric_suffix,
            )
            for slide_path in slide_paths:
                slide_num = numeric_suffix(slide_path)
                rels_path = (
                    "ppt/slides/_rels/"
                    + posixpath.basename(slide_path)
                    + ".rels"
                )
                note_path: Optional[str] = None
                if rels_path in archive.namelist():
                    rel_root = ET.fromstring(archive.read(rels_path))
                    for rel in rel_root:
                        rel_type = rel.attrib.get("Type", "")
                        target = rel.attrib.get("Target", "")
                        if "notesSlide" in rel_type or "notesSlides" in target:
                            note_path = posixpath.normpath(
                                posixpath.join(posixpath.dirname(slide_path), target)
                            )
                            break
                fallback = f"ppt/notesSlides/notesSlide{slide_num}.xml"
                if not note_path and fallback in archive.namelist():
                    note_path = fallback
                if note_path and note_path in archive.namelist():
                    notes = extract_text_from_xml(archive.read(note_path))
                    if notes:
                        notes_by_slide[slide_num] = notes
    except Exception:
        return notes_by_slide
    return notes_by_slide


def shape_text(shape: Any) -> str:
    try:
        if getattr(shape, "has_text_frame", False):
            return clean_text(shape.text)
    except Exception:
        return ""
    return ""


def shape_alt_text(shape: Any) -> str:
    try:
        return clean_text(shape._element._nvXxPr.cNvPr.attrib.get("descr", ""))
    except Exception:
        return ""


IMAGE_EXT_BY_CONTENT_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
    "image/tiff": ".tiff",
    "image/svg+xml": ".svg",
}


def save_asset(assets_dir: Optional[Path], page: int, seq: int, ext: str, blob: bytes) -> Optional[str]:
    if assets_dir is None:
        return None
    assets_dir.mkdir(parents=True, exist_ok=True)
    target = assets_dir / f"page-{page:03d}-img-{seq:02d}{ext}"
    target.write_bytes(blob)
    return str(target)


def extract_pptx(path: Path, assets_dir: Optional[Path] = None) -> Dict[str, Any]:
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "python-pptx is required to extract PPTX files. "
            f"Import failed: {exc}"
        ) from exc

    prs = Presentation(str(path))
    notes_by_slide = read_pptx_notes(path)
    pages: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for index, slide in enumerate(prs.slides, start=1):
        page_warnings: List[str] = []
        title = ""
        text_blocks: List[str] = []
        tables: List[Dict[str, Any]] = []
        image_hints: List[str] = []
        image_digests: List[str] = []
        embedded_images: List[str] = []
        image_seq = 0

        try:
            if slide.shapes.title is not None:
                title = clean_text(slide.shapes.title.text)
        except Exception:
            title = ""

        for shape in slide.shapes:
            try:
                if getattr(shape, "has_table", False):
                    rows: List[List[str]] = []
                    for row in shape.table.rows:
                        rows.append([clean_text(cell.text) for cell in row.cells])
                    nonempty = [
                        row for row in rows if any(cell for cell in row)
                    ]
                    if nonempty:
                        tables.append({"rows": nonempty})
            except Exception as exc:
                page_warnings.append(f"Could not extract a table: {exc}")

            text = shape_text(shape)
            if text:
                text_blocks.append(text)

            try:
                if getattr(shape, "has_chart", False):
                    chart_type = ""
                    try:
                        chart_type = str(shape.chart.chart_type)
                    except Exception:
                        pass
                    hint = "native chart" + (f": {chart_type}" if chart_type else "")
                    image_hints.append(hint)
                    page_warnings.append(
                        "Slide has a native chart that text extraction cannot capture; "
                        "use a rendered page image to read it."
                    )
                    continue
            except Exception:
                pass

            try:
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    alt = shape_alt_text(shape)
                    name = clean_text(getattr(shape, "name", "picture"))
                    hint = f"picture: {name or 'picture'}"
                    if alt:
                        hint += f" (alt: {alt})"
                    image_hints.append(hint)
                    try:
                        image = shape.image
                        image_digests.append(short_hash(image.sha1))
                        ext = IMAGE_EXT_BY_CONTENT_TYPE.get(
                            image.content_type, "." + (image.ext or "bin")
                        )
                        image_seq += 1
                        saved = save_asset(assets_dir, index, image_seq, ext, image.blob)
                        if saved:
                            embedded_images.append(saved)
                    except Exception as exc:
                        page_warnings.append(f"Could not export picture bytes: {exc}")
            except Exception:
                pass

        text_blocks = clean_lines(text_blocks)
        if title and title not in text_blocks:
            text_blocks.insert(0, title)
        notes = notes_by_slide.get(index, [])
        status = infer_status(
            text_blocks,
            tables,
            notes,
            image_hints,
            page_warnings,
            source_type="pptx",
        )
        if status in {PAGE_STATUS_IMAGE_ONLY, PAGE_STATUS_NEEDS_REVIEW}:
            page_warnings.append("No extractable text found on this slide.")
        clean_image_hints = clean_lines(image_hints)
        page_title = title or f"Slide {index}"
        slide_id = getattr(slide, "slide_id", None)
        fingerprints = page_fingerprints(
            page_title,
            text_blocks,
            tables,
            notes,
            clean_image_hints,
            sorted(image_digests),
        )
        pages.append(
            {
                "page": index,
                "title": page_title,
                "source_page_id": f"pptx:{slide_id or index}",
                "slide_id": slide_id,
                **fingerprints,
                "text_blocks": text_blocks,
                "tables": tables,
                "speaker_notes": notes,
                "image_hints": clean_image_hints,
                "embedded_images": embedded_images,
                "status": status,
                "warnings": page_warnings,
            }
        )

    return {
        "source_type": "pptx",
        "source_path": str(path),
        "page_count": len(pages),
        "pages": pages,
        "warnings": warnings,
    }


def extract_pdf(path: Path) -> Dict[str, Any]:
    try:
        import pdfplumber
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "pdfplumber is required to extract PDF files. "
            f"Import failed: {exc}"
        ) from exc

    pages: List[Dict[str, Any]] = []
    warnings: List[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            page_warnings: List[str] = []
            text = clean_text(page.extract_text() or "")
            text_blocks = clean_lines(text.splitlines() if text else [])
            tables: List[Dict[str, Any]] = []
            try:
                for table in page.extract_tables() or []:
                    rows = [
                        [clean_text(cell) for cell in row]
                        for row in table
                        if any(clean_text(cell) for cell in row)
                    ]
                    if rows:
                        tables.append({"rows": rows})
            except Exception as exc:
                page_warnings.append(f"Could not extract tables: {exc}")

            image_hints = []
            image_count = len(getattr(page, "images", []) or [])
            if image_count:
                image_hints.append(f"{image_count} image object(s) detected")

            if not text_blocks and not tables:
                if image_count:
                    page_warnings.append(
                        "Page appears image-heavy or scanned; OCR/manual review may be needed."
                    )
                else:
                    page_warnings.append("No extractable text found on this page.")

            title = text_blocks[0] if text_blocks else f"Page {index}"
            status = infer_status(
                text_blocks,
                tables,
                [],
                image_hints,
                page_warnings,
                source_type="pdf",
            )
            fingerprints = page_fingerprints(
                title,
                text_blocks,
                tables,
                [],
                image_hints,
            )
            pages.append(
                {
                    "page": index,
                    "title": title,
                    "source_page_id": f"pdf:{index}",
                    **fingerprints,
                    "text_blocks": text_blocks,
                    "tables": tables,
                    "speaker_notes": [],
                    "image_hints": image_hints,
                    "embedded_images": [],
                    "status": status,
                    "warnings": page_warnings,
                }
            )

    return {
        "source_type": "pdf",
        "source_path": str(path),
        "page_count": len(pages),
        "pages": pages,
        "warnings": warnings,
    }


def html_text_content(node: Any) -> str:
    try:
        return clean_text(" ".join(node.itertext()))
    except Exception:
        return ""


def extract_html(path: Path, assets_dir: Optional[Path] = None) -> Dict[str, Any]:
    try:
        from lxml import html
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "lxml is required to extract HTML slides. "
            f"Import failed: {exc}"
        ) from exc

    raw = path.read_text(encoding="utf-8", errors="replace")
    doc = html.fromstring(raw)
    for bad in doc.xpath("//script|//style|//nav|//noscript"):
        parent = bad.getparent()
        if parent is not None:
            parent.remove(bad)

    candidates = doc.xpath(
        "//*[self::section or contains(concat(' ', normalize-space(@class), ' '), ' slide ') or @data-slide or @data-slide-index or @data-page]"
    )
    if not candidates:
        candidates = doc.xpath("//article")
    if not candidates:
        candidates = [doc]

    pages: List[Dict[str, Any]] = []
    for index, node in enumerate(candidates, start=1):
        page_warnings: List[str] = []
        headings = node.xpath(".//*[self::h1 or self::h2 or self::h3]")
        title = clean_text(headings[0].text_content()) if headings else f"Slide {index}"

        text_blocks: List[str] = []
        for element in node.xpath(
            ".//*[self::h1 or self::h2 or self::h3 or self::h4 or self::p or self::li or self::blockquote or self::figcaption]"
        ):
            text = clean_text(element.text_content())
            if text:
                text_blocks.append(text)

        tables: List[Dict[str, Any]] = []
        for table in node.xpath(".//table"):
            rows: List[List[str]] = []
            for row in table.xpath(".//tr"):
                cells = [
                    clean_text(cell.text_content())
                    for cell in row.xpath("./th|./td")
                ]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append({"rows": rows})

        image_hints: List[str] = []
        image_digests: List[str] = []
        embedded_images: List[str] = []
        image_seq = 0
        for img in node.xpath(".//img"):
            alt = clean_text(img.get("alt") or "")
            src = clean_text(img.get("src") or "")
            if alt:
                image_hints.append(f"image alt: {alt}")
            elif src:
                image_hints.append(f"image src: {src[:120]}")
            else:
                image_hints.append("image")

            blob: Optional[bytes] = None
            ext = ".png"
            if src.startswith("data:image/"):
                try:
                    import base64

                    header, _, data = src.partition(",")
                    mime = header[5:].split(";")[0]
                    ext = IMAGE_EXT_BY_CONTENT_TYPE.get(mime, ".png")
                    blob = base64.b64decode(data) if ";base64" in header else data.encode("utf-8")
                except Exception:
                    page_warnings.append("Could not decode a data-URI image.")
            elif src and not re.match(r"^[a-z]+:", src):
                local = (path.parent / src.split("?")[0].split("#")[0]).resolve()
                if local.is_file():
                    blob = local.read_bytes()
                    ext = local.suffix or ".png"
                    embedded_images.append(str(local))

            if blob is not None:
                image_digests.append(short_bytes_hash(blob))
                if src.startswith("data:image/"):
                    image_seq += 1
                    saved = save_asset(assets_dir, index, image_seq, ext, blob)
                    if saved:
                        embedded_images.append(saved)

        has_canvas_or_svg_chart = bool(node.xpath(".//canvas")) or bool(
            node.xpath(".//svg[.//path or .//rect or .//circle]")
        )
        if has_canvas_or_svg_chart:
            image_hints.append("canvas/svg drawing present")
            page_warnings.append(
                "Slide contains canvas/SVG-drawn content; read the markup or take a "
                "rendered screenshot to understand it."
            )

        if not text_blocks and tables:
            text_blocks = []
        elif not text_blocks:
            fallback_text = html_text_content(node)
            if fallback_text:
                text_blocks = [fallback_text]

        text_blocks = clean_lines(text_blocks)
        if not text_blocks and not tables:
            page_warnings.append("No extractable slide text found.")
        status = infer_status(
            text_blocks,
            tables,
            [],
            image_hints,
            page_warnings,
            source_type="html",
        )
        clean_image_hints = clean_lines(image_hints)
        html_locator = (
            f"#{node.get('id')}"
            if node.get("id")
            else node.get("data-slide")
            or node.get("data-slide-index")
            or node.get("data-page")
            or f"psc-page-{index}"
        )
        fingerprints = page_fingerprints(
            title,
            text_blocks,
            tables,
            [],
            clean_image_hints,
            sorted(image_digests),
        )
        pages.append(
            {
                "page": index,
                "title": title,
                "source_page_id": f"html:{html_locator}",
                "html_locator": html_locator,
                **fingerprints,
                "text_blocks": text_blocks,
                "tables": tables,
                "speaker_notes": [],
                "image_hints": clean_image_hints,
                "embedded_images": embedded_images,
                "status": status,
                "warnings": page_warnings,
            }
        )

    return {
        "source_type": "html",
        "source_path": str(path),
        "page_count": len(pages),
        "pages": pages,
        "warnings": [],
    }


def extract_strategy_brief(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks = re.split(r"(?m)^#{1,3}\s+", text)
    headings = re.findall(r"(?m)^#{1,3}\s+(.+)$", text)
    pages: List[Dict[str, Any]] = []
    if headings and len(chunks) > 1:
        for index, (heading, body) in enumerate(zip(headings, chunks[1:]), start=1):
            lines = clean_lines(body.splitlines())
            title = clean_text(heading)
            pages.append(
                {
                    "page": index,
                    "title": title,
                    "source_page_id": f"strategy_brief:{index}",
                    **page_fingerprints(title, lines[:20], [], [], []),
                    "text_blocks": lines[:20],
                    "tables": [],
                    "speaker_notes": [],
                    "image_hints": [],
                    "status": PAGE_STATUS_EXTRACTED if lines else PAGE_STATUS_PARTIAL,
                    "warnings": [] if lines else ["Heading has no extractable body text."],
                }
            )
    else:
        lines = clean_lines(text.splitlines())
        pages.append(
            {
                "page": 1,
                "title": path.stem,
                "source_page_id": "strategy_brief:1",
                **page_fingerprints(path.stem, lines, [], [], []),
                "text_blocks": lines,
                "tables": [],
                "speaker_notes": [],
                "image_hints": [],
                "status": PAGE_STATUS_EXTRACTED if lines else PAGE_STATUS_NEEDS_REVIEW,
                "warnings": [] if lines else ["No extractable text found."],
            }
        )
    return {
        "source_type": "strategy_brief",
        "source_path": str(path),
        "page_count": len(pages),
        "pages": pages,
        "warnings": [],
    }


def extract(path: Path, assets_dir: Optional[Path] = None) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".pptx":
        return extract_pptx(path, assets_dir)
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix in {".html", ".htm"}:
        return extract_html(path, assets_dir)
    if suffix in {".md", ".markdown", ".txt", ".yaml", ".yml"}:
        return extract_strategy_brief(path)
    raise ValueError(
        f"Unsupported file type '{suffix}'. Supported: .pptx, .pdf, .html, .htm, .md, .txt, .yaml, .yml"
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract page-level text, tables, speaker notes, and image hints from a presentation source."
    )
    parser.add_argument("input", help="Path to a PPTX, PDF, HTML, or strategy brief file.")
    parser.add_argument("--out", help="Write JSON output to this path instead of stdout.")
    parser.add_argument(
        "--assets-dir",
        help="Export embedded images (PPTX pictures, HTML data-URIs) into this directory "
        "so a multimodal agent can read them.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON without indentation.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    source = Path(args.input).expanduser().resolve()
    if not source.exists():
        print(f"Input file does not exist: {source}", file=sys.stderr)
        return 2
    if not source.is_file():
        print(f"Input path is not a file: {source}", file=sys.stderr)
        return 2

    try:
        assets_dir = Path(args.assets_dir).expanduser().resolve() if args.assets_dir else None
        result = extract(source, assets_dir)
    except Exception as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 1

    json_text = json.dumps(
        result,
        ensure_ascii=False,
        indent=None if args.compact else 2,
    )
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_text + "\n", encoding="utf-8")
    else:
        print(json_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
