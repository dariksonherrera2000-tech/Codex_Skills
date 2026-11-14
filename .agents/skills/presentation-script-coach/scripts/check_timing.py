#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""Check speaking-time arithmetic for a speaking brief contract.

Estimates per-page spoken duration from the verbatim script (CJK chars/min +
non-CJK words/min), compares against each page's talk_time budget and the
runtime_plan totals, and reports pages that will likely overrun.

Model-guessed talk times are the most common failure mode of speaking briefs
("15 分钟的稿子实际要讲 22 分钟"); this script makes that check deterministic.

Stdlib only. Exit codes: 0 = within tolerance, 3 = total mismatch beyond
tolerance, 1/2 = errors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

CJK_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-.%]*")

_UNIT_SECONDS = [
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:小时|hours?|hrs?|h)", re.IGNORECASE), 3600.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:分钟|分|minutes?|mins?|m(?![a-z])|')", re.IGNORECASE), 60.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:秒钟|秒|seconds?|secs?|s(?![a-z])|\")", re.IGNORECASE), 1.0),
]


def parse_duration_seconds(text: Optional[str]) -> Optional[int]:
    """Parse '90s' / '1分30秒' / '2min' / '02:30' / '1-2分钟' into seconds.

    Ranges return the upper bound. Bare numbers are treated as minutes when
    <= 30, otherwise seconds. Returns None when nothing parseable is found.
    """
    if not text:
        return None
    value = str(text).strip().lower()
    value = value.replace("：", ":").replace("～", "-").replace("~", "-").replace("—", "-")
    value = value.replace("约", "").replace("大约", "").strip()
    if not value:
        return None

    range_parts = [part for part in re.split(r"\s*(?:-|到|至)\s*", value) if part]
    if len(range_parts) > 1:
        parsed = [parse_duration_seconds(part) for part in range_parts]
        # A range like "1-2分钟" leaves the first part unitless; borrow the
        # unit by parsing the last part first and scaling bare numbers.
        parsed_known = [p for p in parsed if p is not None]
        if parsed_known:
            return max(parsed_known)
        return None

    clock = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
    if clock:
        return int(clock.group(1)) * 60 + int(clock.group(2))

    total = 0.0
    matched = False
    for pattern, factor in _UNIT_SECONDS:
        for match in pattern.finditer(value):
            total += float(match.group(1)) * factor
            matched = True
    if matched:
        return int(round(total))

    bare = re.fullmatch(r"(\d+(?:\.\d+)?)", value)
    if bare:
        number = float(bare.group(1))
        return int(round(number * 60)) if number <= 30 else int(round(number))
    return None


def estimate_seconds(script: str, cjk_cpm: float, en_wpm: float) -> int:
    text = str(script or "")
    cjk_chars = len(CJK_RE.findall(text))
    remaining = CJK_RE.sub(" ", text)
    words = len(WORD_RE.findall(remaining))
    seconds = cjk_chars / cjk_cpm * 60.0 + words / en_wpm * 60.0
    return int(round(seconds))


def format_seconds(seconds: Optional[int]) -> str:
    if seconds is None:
        return "?"
    return f"{seconds // 60}:{seconds % 60:02d}"


def check(contract: Dict[str, Any], cjk_cpm: float, en_wpm: float, tolerance: float) -> Dict[str, Any]:
    page_reports: List[Dict[str, Any]] = []
    total_estimate = 0
    total_budget = 0
    budget_known = True
    compressed_total = 0

    for item in contract.get("page_scripts", []):
        page = item.get("page")
        estimate = estimate_seconds(item.get("verbatim_script") or "", cjk_cpm, en_wpm)
        compressed_total += estimate_seconds(item.get("compressed_version") or "", cjk_cpm, en_wpm)
        budget = parse_duration_seconds(item.get("talk_time"))
        total_estimate += estimate
        if budget is None:
            budget_known = False
        else:
            total_budget += budget
        flag = None
        if budget:
            ratio = estimate / budget
            if ratio > 1 + tolerance:
                flag = "overrun"
            elif ratio < 1 - tolerance:
                flag = "underrun"
        page_reports.append(
            {
                "page": page,
                "title": item.get("title") or "",
                "talk_time": item.get("talk_time") or "",
                "budget_seconds": budget,
                "estimated_seconds": estimate,
                "flag": flag,
            }
        )

    plan = contract.get("runtime_plan", {}) or {}
    plan_talk = parse_duration_seconds(plan.get("talk_time")) or parse_duration_seconds(plan.get("total_duration"))
    total_flag = None
    if plan_talk:
        ratio = total_estimate / plan_talk
        if ratio > 1 + tolerance:
            total_flag = "overrun"
        elif ratio < 1 - tolerance:
            total_flag = "underrun"

    return {
        "assumptions": {"cjk_chars_per_minute": cjk_cpm, "en_words_per_minute": en_wpm, "tolerance": tolerance},
        "pages": page_reports,
        "total_estimated_seconds": total_estimate,
        "total_page_budget_seconds": total_budget if budget_known else None,
        "plan_talk_seconds": plan_talk,
        "compressed_total_estimated_seconds": compressed_total,
        "total_flag": total_flag,
    }


def print_report(report: Dict[str, Any]) -> None:
    print("页  预算     估算     状态  标题")
    for page in report["pages"]:
        flag = page["flag"] or "ok"
        print(
            f"{str(page['page']).rjust(2)}  "
            f"{format_seconds(page['budget_seconds']).rjust(6)}  "
            f"{format_seconds(page['estimated_seconds']).rjust(6)}  "
            f"{flag.ljust(8)[:8]}  {page['title'][:32]}"
        )
    print()
    print(f"全稿口播估算: {format_seconds(report['total_estimated_seconds'])}")
    if report["total_page_budget_seconds"] is not None:
        print(f"各页预算合计: {format_seconds(report['total_page_budget_seconds'])}")
    if report["plan_talk_seconds"] is not None:
        print(f"runtime_plan 口播时长: {format_seconds(report['plan_talk_seconds'])}")
    print(f"压缩版全稿估算: {format_seconds(report['compressed_total_estimated_seconds'])}")
    if report["total_flag"]:
        print(f"STATUS: {report['total_flag'].upper()} — 估算与 runtime_plan 偏差超出容差,请调整逐字稿长度或时长计划。")
    else:
        print("STATUS: OK")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check per-page and total speaking time against the contract.")
    parser.add_argument("--contract", required=True, help="presentation-speaking-brief.contract.json path.")
    parser.add_argument("--cjk-cpm", type=float, default=255.0, help="CJK characters per minute (default 255).")
    parser.add_argument("--en-wpm", type=float, default=150.0, help="English words per minute (default 150).")
    parser.add_argument("--tolerance", type=float, default=0.2, help="Allowed relative deviation (default 0.2).")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the table.")
    args = parser.parse_args(argv)

    path = Path(args.contract).expanduser().resolve()
    if not path.is_file():
        print(f"Contract file does not exist: {path}", file=sys.stderr)
        return 2
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Could not read contract JSON: {exc}", file=sys.stderr)
        return 1

    report = check(contract, args.cjk_cpm, args.en_wpm, args.tolerance)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 3 if report["total_flag"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
