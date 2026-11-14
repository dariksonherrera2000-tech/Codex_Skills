#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pymupdf"]
# ///
"""Render presentation pages to PNG images for multimodal visual reading.

This is the fallback/high-fidelity visual channel. Prefer the cheapest reliable
channel first (see SKILL.md "Visual Access Strategy"):
- pdf: many harnesses can read the PDF pages directly; render only if not.
- pptx: must be converted (soffice -> pdf -> png); native charts/vector shapes
  are invisible to text extraction and embedded-image export.
- html: the agent can usually read the markup + local <img> assets directly;
  render only when content is canvas/JS-drawn or layout fidelity matters.

Backends tried in order:
- pdf:  PyMuPDF (fitz) -> pdftoppm (poppler) -> pdfplumber(+pypdfium2)
- pptx: LibreOffice soffice --convert-to pdf, then the pdf pipeline
- html: playwright chromium (Reveal.js aware, best-effort otherwise)

Writes page-NNN.png files plus a manifest.json into --out-dir.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def parse_page_spec(spec: Optional[str]) -> Optional[Set[int]]:
    if not spec:
        return None
    pages: Set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            pages.update(range(int(start), int(end) + 1))
        else:
            pages.add(int(chunk))
    return pages


def wanted(page: int, pages: Optional[Set[int]]) -> bool:
    return pages is None or page in pages


def page_name(index: int) -> str:
    return f"page-{index:03d}.png"


# --- PDF backends -----------------------------------------------------------


def render_pdf_fitz(pdf: Path, out_dir: Path, dpi: int, pages: Optional[Set[int]]) -> List[Dict[str, Any]]:
    import fitz  # PyMuPDF

    rendered: List[Dict[str, Any]] = []
    zoom = dpi / 72.0
    with fitz.open(str(pdf)) as doc:
        for index in range(doc.page_count):
            number = index + 1
            if not wanted(number, pages):
                continue
            pix = doc.load_page(index).get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            target = out_dir / page_name(number)
            pix.save(str(target))
            rendered.append({"page": number, "image": str(target)})
    return rendered


def render_pdf_pdftoppm(pdf: Path, out_dir: Path, dpi: int, pages: Optional[Set[int]]) -> List[Dict[str, Any]]:
    if not shutil.which("pdftoppm"):
        raise RuntimeError("pdftoppm not found on PATH")
    prefix = out_dir / "ppm-page"
    cmd = ["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(prefix)]
    subprocess.run(cmd, check=True, capture_output=True)
    rendered: List[Dict[str, Any]] = []
    for produced in sorted(out_dir.glob("ppm-page-*.png")):
        number = int(produced.stem.rsplit("-", 1)[-1])
        if not wanted(number, pages):
            produced.unlink()
            continue
        target = out_dir / page_name(number)
        produced.rename(target)
        rendered.append({"page": number, "image": str(target)})
    return rendered


def render_pdf_pdfplumber(pdf: Path, out_dir: Path, dpi: int, pages: Optional[Set[int]]) -> List[Dict[str, Any]]:
    import pdfplumber

    rendered: List[Dict[str, Any]] = []
    with pdfplumber.open(str(pdf)) as doc:
        for index, page in enumerate(doc.pages, start=1):
            if not wanted(index, pages):
                continue
            target = out_dir / page_name(index)
            page.to_image(resolution=dpi).save(str(target))
            rendered.append({"page": index, "image": str(target)})
    return rendered


def render_pdf(pdf: Path, out_dir: Path, dpi: int, pages: Optional[Set[int]], warnings: List[str]) -> tuple:
    backends = (
        ("pymupdf", render_pdf_fitz),
        ("pdftoppm", render_pdf_pdftoppm),
        ("pdfplumber", render_pdf_pdfplumber),
    )
    last_error: Optional[Exception] = None
    for name, backend in backends:
        try:
            return backend(pdf, out_dir, dpi, pages), name
        except Exception as exc:
            last_error = exc
            warnings.append(f"pdf backend {name} unavailable/failed: {exc}")
    raise RuntimeError(
        "No PDF rendering backend worked. Install one of: pymupdf (pip), "
        f"poppler (brew install poppler), pdfplumber. Last error: {last_error}"
    )


# --- PPTX -> PDF ------------------------------------------------------------


def find_soffice() -> Optional[str]:
    for candidate in ("soffice", "libreoffice"):
        found = shutil.which(candidate)
        if found:
            return found
    mac_default = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if Path(mac_default).exists():
        return mac_default
    return None


def pptx_to_pdf(pptx: Path, work_dir: Path) -> Path:
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice (soffice) not found, so PPTX pages cannot be rendered. "
            "Install it (brew install --cask libreoffice) or fall back to "
            "embedded-image export from extract_slides_context.py --assets-dir. "
            "Note: native charts/diagrams drawn as shapes will be missing from "
            "that fallback; mark such pages needs_visual_render."
        )
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(work_dir), str(pptx)],
        check=True,
        capture_output=True,
        timeout=300,
    )
    produced = work_dir / (pptx.stem + ".pdf")
    if not produced.exists():
        candidates = list(work_dir.glob("*.pdf"))
        if not candidates:
            raise RuntimeError("soffice reported success but produced no PDF")
        produced = candidates[0]
    return produced


# --- HTML via playwright ----------------------------------------------------


def render_html(source: Path, out_dir: Path, pages: Optional[Set[int]], warnings: List[str]) -> List[Dict[str, Any]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(
            "playwright is required to screenshot HTML slides "
            f"(import failed: {exc}). Alternatives that need no rendering: "
            "read the HTML source directly (markup/SVG are model-readable) and "
            "read local <img> assets; only canvas/JS-drawn charts truly need "
            "screenshots. To enable: pip install playwright && playwright install chromium"
        ) from exc

    rendered: List[Dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        page.goto(source.resolve().as_uri())
        page.wait_for_timeout(1200)

        is_reveal = page.evaluate("() => !!(window.Reveal && typeof window.Reveal.next === 'function')")
        if is_reveal:
            total = page.evaluate(
                "() => (typeof Reveal.getTotalSlides === 'function') ? Reveal.getTotalSlides() : document.querySelectorAll('.slides section:not(.stack)').length"
            )
            page.evaluate("() => { if (typeof Reveal.slide === 'function') Reveal.slide(0, 0); }")
            page.wait_for_timeout(300)
            for number in range(1, int(total) + 1):
                if wanted(number, pages):
                    target = out_dir / page_name(number)
                    page.screenshot(path=str(target))
                    rendered.append({"page": number, "image": str(target)})
                page.evaluate("() => Reveal.next()")
                page.wait_for_timeout(250)
        else:
            selector = "section, .slide, [data-slide], [data-slide-index], [data-page]"
            count = page.locator(selector).count()
            if count == 0:
                target = out_dir / page_name(1)
                page.screenshot(path=str(target), full_page=True)
                rendered.append({"page": 1, "image": str(target)})
                warnings.append("No slide containers found; captured one full-page screenshot.")
            else:
                for index in range(count):
                    number = index + 1
                    if not wanted(number, pages):
                        continue
                    node = page.locator(selector).nth(index)
                    target = out_dir / page_name(number)
                    try:
                        node.scroll_into_view_if_needed(timeout=3000)
                        node.screenshot(path=str(target), timeout=5000)
                        rendered.append({"page": number, "image": str(target)})
                    except Exception as exc:
                        warnings.append(f"Could not screenshot slide {number}: {exc}")
        browser.close()
    return rendered


# --- main -------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render presentation pages to PNG for multimodal reading.")
    parser.add_argument("input", help="PPTX, PDF, or HTML file.")
    parser.add_argument("--out-dir", required=True, help="Directory for page-NNN.png files and manifest.json.")
    parser.add_argument("--pages", help="Only render these pages, e.g. 1,3,5-8. Default: all.")
    parser.add_argument("--dpi", type=int, default=144, help="Render resolution for PDF-based paths (default 144).")
    parser.add_argument("--max-pages", type=int, default=120, help="Safety cap on rendered pages (default 120).")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    source = Path(args.input).expanduser().resolve()
    if not source.is_file():
        print(f"Input file does not exist: {source}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = parse_page_spec(args.pages)
    warnings: List[str] = []
    suffix = source.suffix.lower()

    try:
        if suffix == ".pdf":
            rendered, method = render_pdf(source, out_dir, args.dpi, pages, warnings)
        elif suffix == ".pptx":
            with tempfile.TemporaryDirectory() as tmp:
                pdf = pptx_to_pdf(source, Path(tmp))
                rendered, pdf_method = render_pdf(pdf, out_dir, args.dpi, pages, warnings)
            method = f"soffice+{pdf_method}"
        elif suffix in {".html", ".htm"}:
            rendered = render_html(source, out_dir, pages, warnings)
            method = "playwright"
        else:
            print(f"Unsupported file type '{suffix}'. Supported: .pptx, .pdf, .html", file=sys.stderr)
            return 2
    except Exception as exc:
        print(f"Render failed: {exc}", file=sys.stderr)
        return 1

    if len(rendered) > args.max_pages:
        for extra in rendered[args.max_pages:]:
            Path(extra["image"]).unlink(missing_ok=True)
        warnings.append(
            f"Rendered page count {len(rendered)} exceeds --max-pages {args.max_pages}; extras removed."
        )
        rendered = rendered[: args.max_pages]

    manifest = {
        "source_path": str(source),
        "method": method,
        "dpi": args.dpi,
        "page_count": len(rendered),
        "pages": rendered,
        "warnings": warnings,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "page_count": len(rendered), "method": method, "warnings": warnings}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
