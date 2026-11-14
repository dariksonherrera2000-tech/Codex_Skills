#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["python-pptx", "pdfplumber", "lxml"]
# ///
"""Build presentation-assist derivatives from a speaking brief contract.

HTML output receives a hidden teleprompter payload and a T-key popup runtime
(with per-page time budget, elapsed timer, must-keep list, font controls, and
an in-page overlay fallback when the popup is blocked).
PPTX output receives per-slide script blocks in speaker notes.
Cards output renders printable presenter cue cards as Markdown for any
source type, including PDF and strategy briefs.

Run with `uv run build_presentation_assist.py ...` if dependencies are missing.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from extract_slides_context import extract, short_hash
from check_timing import parse_duration_seconds


START_RE = re.compile(
    r"PRESENTATION SCRIPT COACH START page=(?P<page>\d+) checksum=(?P<checksum>[a-f0-9]+)"
    r".*?"
    r"PRESENTATION SCRIPT COACH END",
    re.DOTALL,
)


def load_contract(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Could not read contract JSON: {exc}") from exc


def scripts_by_page(contract: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    scripts: Dict[int, Dict[str, Any]] = {}
    for item in contract.get("page_scripts", []):
        page = item.get("page")
        if not isinstance(page, int):
            raise ValueError(f"page_scripts item has invalid page: {page!r}")
        script = str(item.get("verbatim_script") or "").strip()
        if not script:
            raise ValueError(f"page_scripts[{page}] has no verbatim_script")
        scripts[page] = item
    if not scripts:
        raise ValueError("contract has no page_scripts")
    return scripts


def expected_page_meta(contract: Dict[str, Any], page: int) -> Dict[str, Any]:
    pages = contract.get("slides_context", {}).get("pages", [])
    for item in pages:
        if item.get("page") == page:
            return item
    return {}


def ensure_out_path(source: Path, out: Path, overwrite: bool) -> None:
    if source.resolve() == out.resolve():
        raise ValueError("Refusing to overwrite the source file; choose a derived output path.")
    if out.exists() and not overwrite:
        raise ValueError(f"Output already exists: {out}. Pass --overwrite to replace it.")
    out.parent.mkdir(parents=True, exist_ok=True)


def compare_identity(
    extracted: Dict[str, Any],
    contract: Dict[str, Any],
    scripts: Dict[int, Dict[str, Any]],
    *,
    strict: bool,
) -> List[str]:
    warnings: List[str] = []
    pages = extracted.get("pages", [])
    expected_count = contract.get("slides_context", {}).get("page_count")
    if isinstance(expected_count, int) and expected_count != len(pages):
        raise ValueError(
            f"Page count mismatch: contract has {expected_count}, source has {len(pages)}."
        )

    for page, script in scripts.items():
        if page < 1 or page > len(pages):
            raise ValueError(f"Script page {page} is outside source page range 1..{len(pages)}")

        actual = pages[page - 1]
        expected = {**expected_page_meta(contract, page), **script}

        for key in ("source_page_id", "slide_id", "html_locator"):
            if expected.get(key) is not None and actual.get(key) is not None:
                if str(expected[key]) != str(actual[key]):
                    raise ValueError(
                        f"Page {page} {key} mismatch: contract={expected[key]!r}, source={actual[key]!r}"
                    )

        if expected.get("content_hash") and actual.get("content_hash"):
            if expected["content_hash"] != actual["content_hash"]:
                raise ValueError(
                    f"Page {page} content_hash mismatch. The PPT/slides may have changed after script approval."
                )

        if expected.get("title_hash") and actual.get("title_hash"):
            if expected["title_hash"] != actual["title_hash"]:
                message = (
                    f"Page {page} title_hash mismatch: contract title={expected.get('title')!r}, "
                    f"source title={actual.get('title')!r}"
                )
                if strict:
                    raise ValueError(message)
                warnings.append(message)
    return warnings


def must_keep_list(item: Dict[str, Any]) -> List[str]:
    value = item.get("must_keep")
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def teleprompter_payload(contract: Dict[str, Any], scripts: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    pages = []
    for page in sorted(scripts):
        item = scripts[page]
        talk_time = str(item.get("talk_time") or "").strip()
        pages.append(
            {
                "page": page,
                "title": item.get("title") or f"Slide {page}",
                "purpose": str(item.get("purpose") or "").strip(),
                "script": item.get("verbatim_script") or "",
                "transition": item.get("transition") or "",
                "compressed": item.get("compressed_version") or "",
                "talk_time": talk_time,
                "talk_seconds": parse_duration_seconds(talk_time),
                "must_keep": must_keep_list(item),
            }
        )
    return {
        "version": 2,
        "source_type": contract.get("source_type"),
        "pages": pages,
    }


def safe_json_for_script(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


TELEPROMPTER_RUNTIME = r"""
(function () {
  const dataEl = document.getElementById("psc-teleprompter-data");
  if (!dataEl) return;
  const payload = JSON.parse(dataEl.textContent || "{}");
  const pages = payload.pages || [];
  let popup = null;
  let overlay = null;
  let fontSize = 22;
  let shownPage = null;
  let pageStartedAt = null;
  let timerHandle = null;

  const PANEL_CSS = `
    .psc-body { margin: 0; background: #101114; color: #f2f2f2; font: 22px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; }
    .psc-root { padding: 20px 26px 40px; }
    .psc-header { display: flex; align-items: center; gap: 12px; position: sticky; top: 0; background: #101114; padding: 8px 0 10px; border-bottom: 1px solid #343842; }
    .psc-meta { color: #9ca3af; font-size: 14px; flex: 1; }
    .psc-timer { font-variant-numeric: tabular-nums; font-size: 18px; color: #34d399; }
    .psc-timer.psc-over { color: #f87171; font-weight: 700; }
    .psc-btn { background: #1f2430; color: #e5e7eb; border: 1px solid #3a4150; border-radius: 6px; font-size: 13px; padding: 2px 9px; cursor: pointer; }
    .psc-title { font-size: 1.1em; font-weight: 700; margin: 16px 0 4px; }
    .psc-purpose { color: #9ca3af; font-size: 0.72em; margin-bottom: 12px; }
    .psc-mustkeep { background: #1c2333; border-left: 3px solid #fbbf24; border-radius: 4px; color: #fde68a; font-size: 0.75em; padding: 8px 12px; margin-bottom: 14px; white-space: pre-wrap; }
    .psc-script { white-space: pre-wrap; }
    .psc-extra { margin-top: 20px; color: #d1d5db; font-size: 0.82em; border-top: 1px solid #343842; padding-top: 14px; white-space: pre-wrap; }
  `;

  const PANEL_HTML = `
    <div class="psc-root">
      <div class="psc-header">
        <div class="psc-meta"></div>
        <div class="psc-timer">00:00</div>
        <button class="psc-btn" data-psc-font="-1">A-</button>
        <button class="psc-btn" data-psc-font="1">A+</button>
      </div>
      <div class="psc-title"></div>
      <div class="psc-purpose"></div>
      <div class="psc-mustkeep"></div>
      <div class="psc-script"></div>
      <div class="psc-extra psc-transition"></div>
      <div class="psc-extra psc-compressed"></div>
    </div>
  `;

  function pageByNumber(n) {
    return pages.find((p) => p.page === n) || pages[0] || null;
  }

  function currentPageNumber() {
    if (window.Reveal && typeof window.Reveal.getCurrentSlide === "function") {
      const slide = window.Reveal.getCurrentSlide();
      if (slide && slide.dataset && slide.dataset.pscPage) {
        return Number(slide.dataset.pscPage);
      }
    }
    const active = document.querySelector(
      "[data-psc-page].present, [data-psc-page].active, [data-psc-page].current, [data-psc-page][aria-current='true']"
    );
    if (active) return Number(active.dataset.pscPage);
    if (location.hash) {
      const hashTarget = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (hashTarget) {
        const pageNode = hashTarget.closest("[data-psc-page]");
        if (pageNode) return Number(pageNode.dataset.pscPage);
      }
    }
    const first = document.querySelector("[data-psc-page]");
    return first ? Number(first.dataset.pscPage) : 1;
  }

  function wireButtons(root) {
    root.querySelectorAll("[data-psc-font]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        fontSize = Math.min(40, Math.max(14, fontSize + 2 * Number(btn.dataset.pscFont)));
        applyFontSize();
      });
    });
  }

  function applyFontSize() {
    if (popup && !popup.closed) popup.document.body.style.fontSize = fontSize + "px";
    if (overlay) overlay.style.fontSize = fontSize + "px";
  }

  function ensurePopup() {
    if (popup && !popup.closed) return popup;
    popup = window.open("", "pscTeleprompter", "width=560,height=780,menubar=no,toolbar=no,location=no,status=no");
    if (!popup) return null;
    if (!popup.document.querySelector(".psc-root")) {
      popup.document.open();
      popup.document.write("<!doctype html><html><head><meta charset='utf-8'><title>Teleprompter</title><style>" +
        PANEL_CSS + "</style></head><body class='psc-body'>" + PANEL_HTML + "</body></html>");
      popup.document.close();
      wireButtons(popup.document);
    }
    return popup;
  }

  function ensureOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.id = "psc-teleprompter-overlay";
    overlay.style.cssText = "display:none; position:fixed; top:0; right:0; bottom:0; width:min(440px,90vw); " +
      "z-index:2147483646; overflow-y:auto; box-shadow:-8px 0 30px rgba(0,0,0,.55); background:#101114; " +
      "color:#f2f2f2; font:22px/1.55 -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;";
    const style = document.createElement("style");
    style.textContent = PANEL_CSS.replace(/\.psc-body[^}]+}/, "");
    overlay.appendChild(style);
    const inner = document.createElement("div");
    inner.innerHTML = PANEL_HTML;
    overlay.appendChild(inner);
    document.body.appendChild(overlay);
    wireButtons(overlay);
    return overlay;
  }

  function surfaceRoot() {
    if (popup && !popup.closed) return popup.document;
    if (overlay && overlay.style.display !== "none") return overlay;
    return null;
  }

  function surfaceVisible() {
    return !!surfaceRoot();
  }

  function setText(root, selector, text) {
    const el = root.querySelector(selector);
    if (el) {
      el.textContent = text || "";
      el.style.display = text ? "" : "none";
    }
  }

  function formatClock(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
  }

  function tick() {
    const root = surfaceRoot();
    if (!root || pageStartedAt === null) return;
    const el = root.querySelector(".psc-timer");
    if (!el) return;
    const elapsed = (Date.now() - pageStartedAt) / 1000;
    const current = pageByNumber(shownPage || currentPageNumber());
    const budget = current && current.talk_seconds ? current.talk_seconds : null;
    el.textContent = formatClock(elapsed) + (budget ? " / " + formatClock(budget) : "");
    el.classList.toggle("psc-over", !!budget && elapsed > budget);
  }

  function render() {
    const root = surfaceRoot();
    if (!root) return;
    const number = currentPageNumber();
    const current = pageByNumber(number);
    if (!current) return;
    if (shownPage !== current.page) {
      shownPage = current.page;
      pageStartedAt = Date.now();
    }
    setText(root, ".psc-meta", "Page " + current.page + " / " + pages.length +
      (current.talk_time ? " · 建议 " + current.talk_time : ""));
    setText(root, ".psc-title", current.title || "");
    setText(root, ".psc-purpose", current.purpose || "");
    setText(root, ".psc-mustkeep", (current.must_keep && current.must_keep.length)
      ? "必须保留:\n" + current.must_keep.map(function (x) { return "• " + x; }).join("\n") : "");
    setText(root, ".psc-script", current.script || "");
    setText(root, ".psc-transition", current.transition ? "转场:" + current.transition : "");
    setText(root, ".psc-compressed", current.compressed ? "压缩版:" + current.compressed : "");
    tick();
  }

  function openAndRender() {
    if (!ensurePopup()) {
      const box = ensureOverlay();
      box.style.display = box.style.display === "none" ? "block" : "none";
    }
    if (!timerHandle) timerHandle = setInterval(tick, 1000);
    if (pageStartedAt === null) pageStartedAt = Date.now();
    applyFontSize();
    render();
  }

  if (window.Reveal && typeof window.Reveal.on === "function") {
    window.Reveal.on("slidechanged", render);
    if (typeof window.Reveal.addKeyBinding === "function") {
      window.Reveal.addKeyBinding({ keyCode: 84, key: "T", description: "Open teleprompter" }, openAndRender);
    }
  }

  document.addEventListener("keydown", function (event) {
    const tag = (event.target && event.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || event.target.isContentEditable) return;
    if (event.key === "t" || event.key === "T") {
      event.preventDefault();
      openAndRender();
    }
    if (event.key === "Escape" && overlay && overlay.style.display !== "none") {
      overlay.style.display = "none";
    }
  });
  window.addEventListener("hashchange", function () { if (surfaceVisible()) render(); });
  new MutationObserver(function () { if (surfaceVisible()) render(); }).observe(document.documentElement, {
    subtree: true,
    attributes: true,
    attributeFilter: ["class", "style", "aria-current"]
  });
})();
"""


def csp_blocks_inline(doc: Any) -> bool:
    metas = doc.xpath(
        "//meta[translate(@http-equiv, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='content-security-policy']"
    )
    for meta in metas:
        content = (meta.get("content") or "").lower()
        if "script-src" in content and "'unsafe-inline'" not in content:
            return True
    return False


def html_slide_candidates(doc: Any) -> List[Any]:
    candidates = doc.xpath(
        "//*[self::section or contains(concat(' ', normalize-space(@class), ' '), ' slide ') or @data-slide or @data-slide-index or @data-page]"
    )
    if not candidates:
        candidates = doc.xpath("//article")
    if not candidates:
        body = doc.find("body")
        candidates = [body if body is not None else doc]
    return candidates


def ensure_utf8_meta(doc: Any) -> None:
    from lxml import html

    head = doc.find("head")
    if head is None:
        head = html.Element("head")
        doc.insert(0, head)
    existing = head.xpath(".//meta[translate(@charset, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='utf-8']")
    if existing:
        return
    meta = html.Element("meta", charset="utf-8")
    head.insert(0, meta)


def build_html(source: Path, contract_path: Path, out: Path, overwrite: bool, strict: bool) -> List[str]:
    from lxml import html

    ensure_out_path(source, out, overwrite)
    contract = load_contract(contract_path)
    if contract.get("source_type") not in ("html", "mixed"):
        raise ValueError("HTML assist output requires contract source_type html or mixed.")
    scripts = scripts_by_page(contract)
    extracted = extract(source)
    if extracted.get("source_type") != "html":
        raise ValueError("Source file is not recognized as HTML slides.")
    warnings = compare_identity(extracted, contract, scripts, strict=strict)

    raw = source.read_text(encoding="utf-8", errors="replace")
    doc = html.document_fromstring(raw)
    if csp_blocks_inline(doc):
        raise ValueError(
            "This HTML includes a Content-Security-Policy that blocks inline scripts. "
            "v1 refuses to inject a popup runtime into this file."
        )

    candidates = html_slide_candidates(doc)
    for index, node in enumerate(candidates, start=1):
        node.set("data-psc-page", str(index))
    ensure_utf8_meta(doc)

    body = doc.find("body")
    if body is None:
        body = doc

    old_payload = doc.xpath("//*[@id='psc-teleprompter-data']")
    old_runtime = doc.xpath("//*[@id='psc-teleprompter-runtime']")
    for node in old_payload + old_runtime:
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)

    payload = html.Element("script", id="psc-teleprompter-data", type="application/json")
    payload.text = safe_json_for_script(teleprompter_payload(contract, scripts))
    runtime = html.Element("script", id="psc-teleprompter-runtime")
    runtime.text = TELEPROMPTER_RUNTIME
    body.append(payload)
    body.append(runtime)

    out.write_bytes(html.tostring(doc, encoding="utf-8", method="html", doctype="<!doctype html>"))
    verify_html_output(out, len(scripts))
    return warnings


def script_block(page: int, script: Dict[str, Any]) -> Tuple[str, str]:
    parts = [
        str(script.get("verbatim_script") or "").strip(),
    ]
    transition = str(script.get("transition") or "").strip()
    compressed = str(script.get("compressed_version") or "").strip()
    if transition:
        parts.append(f"转场：{transition}")
    if compressed:
        parts.append(f"压缩版：{compressed}")
    body = "\n\n".join(part for part in parts if part)
    checksum = short_hash(body)
    block = (
        f"PRESENTATION SCRIPT COACH START page={page} checksum={checksum}\n"
        f"{body}\n"
        "PRESENTATION SCRIPT COACH END"
    )
    return block, checksum


def strip_managed_blocks(text: str) -> str:
    return START_RE.sub("", text or "").strip()


def build_pptx(source: Path, contract_path: Path, out: Path, overwrite: bool, strict: bool) -> List[str]:
    try:
        from pptx import Presentation
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"python-pptx is required for PPTX notes injection: {exc}") from exc

    ensure_out_path(source, out, overwrite)
    contract = load_contract(contract_path)
    if contract.get("source_type") not in ("pptx", "mixed"):
        raise ValueError("PPTX assist output requires contract source_type pptx or mixed.")
    scripts = scripts_by_page(contract)
    extracted = extract(source)
    if extracted.get("source_type") != "pptx":
        raise ValueError("Source file is not recognized as PPTX.")
    warnings = compare_identity(extracted, contract, scripts, strict=strict)

    shutil.copyfile(source, out)
    prs = Presentation(str(out))
    checksums: Dict[int, str] = {}
    for page, script in scripts.items():
        slide = prs.slides[page - 1]
        notes_frame = getattr(slide.notes_slide, "notes_text_frame", None)
        if notes_frame is None:
            raise ValueError(f"Slide {page} has no writable notes_text_frame.")
        existing = strip_managed_blocks(notes_frame.text)
        block, checksum = script_block(page, script)
        checksums[page] = checksum
        notes_frame.text = f"{existing}\n\n{block}".strip() if existing else block
    prs.save(str(out))
    verify_pptx_output(out, checksums)
    return warnings


def verify_html_output(path: Path, expected_pages: int) -> None:
    from lxml import html

    doc = html.document_fromstring(path.read_text(encoding="utf-8", errors="replace"))
    data_nodes = doc.xpath("//*[@id='psc-teleprompter-data']")
    runtime_nodes = doc.xpath("//*[@id='psc-teleprompter-runtime']")
    if len(data_nodes) != 1 or len(runtime_nodes) != 1:
        raise ValueError("HTML verification failed: teleprompter payload/runtime not found.")
    payload = json.loads(data_nodes[0].text or "{}")
    if len(payload.get("pages", [])) != expected_pages:
        raise ValueError("HTML verification failed: payload page count mismatch.")
    if doc.xpath("//*[contains(concat(' ', normalize-space(@class), ' '), ' psc-teleprompter-panel ')]"):
        raise ValueError("HTML verification failed: visible main-screen teleprompter panel found.")


def verify_pptx_output(path: Path, checksums: Dict[int, str]) -> None:
    from pptx import Presentation

    prs = Presentation(str(path))
    for page, checksum in checksums.items():
        text = prs.slides[page - 1].notes_slide.notes_text_frame.text
        expected = f"PRESENTATION SCRIPT COACH START page={page} checksum={checksum}"
        if expected not in text or "PRESENTATION SCRIPT COACH END" not in text:
            raise ValueError(f"PPTX verification failed: managed notes block missing on slide {page}.")


def build_cards(contract_path: Path, out: Path, overwrite: bool, source: Optional[Path], strict: bool) -> List[str]:
    contract = load_contract(contract_path)
    scripts = scripts_by_page(contract)
    warnings: List[str] = []
    if out.exists() and not overwrite:
        raise ValueError(f"Output already exists: {out}. Pass --overwrite to replace it.")
    out.parent.mkdir(parents=True, exist_ok=True)
    if source is not None:
        extracted = extract(source)
        warnings = compare_identity(extracted, contract, scripts, strict=strict)

    runtime = contract.get("runtime_plan", {}) or {}
    lines: List[str] = [
        "# 提词卡（Presenter Cue Cards）",
        "",
        f"- 来源类型：{contract.get('source_type', 'unknown')}",
        f"- 总时长：{runtime.get('total_duration', 'TBD')}（讲 {runtime.get('talk_time', 'TBD')} / Q&A {runtime.get('qa_time', 'TBD')}）",
        f"- 页数：{len(scripts)}",
        "",
        "> 打印建议：每页一卡。现场只看「必须保留」和逐字稿首句，不逐字念。",
    ]
    for page in sorted(scripts):
        item = scripts[page]
        talk_time = str(item.get("talk_time") or "").strip()
        lines += [
            "",
            "---",
            "",
            f"## 第 {page} 页 · {item.get('title') or f'Slide {page}'}"
            + (f"（建议 {talk_time}）" if talk_time else ""),
            "",
        ]
        purpose = str(item.get("purpose") or "").strip()
        if purpose:
            lines += [f"**本页目的**：{purpose}", ""]
        keeps = must_keep_list(item)
        if keeps:
            lines.append("**必须保留**：")
            lines += [f"- {keep}" for keep in keeps]
            lines.append("")
        lines.append("**逐字稿**：")
        lines += [f"> {row}" if row.strip() else ">" for row in str(item.get("verbatim_script") or "").splitlines()]
        transition = str(item.get("transition") or "").strip()
        if transition:
            lines += ["", f"**转场**：{transition}"]
        compressed = str(item.get("compressed_version") or "").strip()
        if compressed:
            lines += ["", f"**压缩版**：{compressed}"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    verify_cards_output(out, len(scripts))
    return warnings


def verify_cards_output(path: Path, expected_pages: int) -> None:
    text = path.read_text(encoding="utf-8")
    found = len(re.findall(r"(?m)^## 第 \d+ 页", text))
    if found != expected_pages:
        raise ValueError(
            f"Cards verification failed: expected {expected_pages} page cards, found {found}."
        )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build HTML teleprompter, PPTX speaker-notes, or Markdown cue-card assist output.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    for mode in ("html", "pptx"):
        sub = subparsers.add_parser(mode)
        sub.add_argument("--source", required=True, help="Input HTML or PPTX file.")
        sub.add_argument("--contract", required=True, help="presentation-speaking-brief.contract.json path.")
        sub.add_argument("--out", required=True, help="Derived output path.")
        sub.add_argument("--overwrite", action="store_true", help="Replace output if it already exists.")
        sub.add_argument(
            "--allow-title-drift",
            action="store_true",
            help="Allow title hash mismatch when content/page identity still matches.",
        )

    cards = subparsers.add_parser("cards", help="Printable Markdown cue cards; works for any source type incl. pdf.")
    cards.add_argument("--contract", required=True, help="presentation-speaking-brief.contract.json path.")
    cards.add_argument("--out", required=True, help="Output Markdown path.")
    cards.add_argument("--source", help="Optional source file; if given, page identity is re-checked.")
    cards.add_argument("--overwrite", action="store_true", help="Replace output if it already exists.")
    cards.add_argument(
        "--allow-title-drift",
        action="store_true",
        help="Allow title hash mismatch when content/page identity still matches.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    contract = Path(args.contract).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    source = Path(args.source).expanduser().resolve() if getattr(args, "source", None) else None
    if source is not None and not source.exists():
        print(f"Source file does not exist: {source}", file=sys.stderr)
        return 2
    if args.mode in ("html", "pptx") and source is None:
        print("--source is required for html/pptx modes.", file=sys.stderr)
        return 2
    if not contract.exists():
        print(f"Contract file does not exist: {contract}", file=sys.stderr)
        return 2

    strict = not args.allow_title_drift
    try:
        if args.mode == "html":
            warnings = build_html(source, contract, out, args.overwrite, strict)
        elif args.mode == "pptx":
            warnings = build_pptx(source, contract, out, args.overwrite, strict)
        elif args.mode == "cards":
            warnings = build_cards(contract, out, args.overwrite, source, strict)
        else:
            raise ValueError(f"Unsupported mode: {args.mode}")
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {out}")
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
