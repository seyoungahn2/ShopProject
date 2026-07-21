#!/usr/bin/env python3
"""Retitle ISA episodes: keyword-first | ISA계좌 (N화) format."""

from __future__ import annotations

import re
from pathlib import Path

ISA_DIR = Path(__file__).resolve().parents[1]

# Episodes without manuscript files (catalog-only)
EXTRA_TITLES: dict[int, str] = {
    3: "가입 전 반드시 알아야 할 치명적인 함정 3가지",
    4: "ISA vs 연금저축 vs IRP, 뭐가 더 좋을까?",
}


def convert_h1(line: str) -> tuple[str, int | None, str | None]:
    m = re.match(r"^# ISA계좌 \((\d+)화\) : (.+)$", line)
    if m:
        ep = int(m.group(1))
        title = m.group(2)
        return f"# {title} | ISA계좌 ({ep}화)", ep, title

    m = re.match(r"^# (.+) \((\d+)화\)$", line)
    if m:
        ep = int(m.group(2))
        title = m.group(1)
        return f"# {title} | ISA계좌 ({ep}화)", ep, title

    return line, None, None


def build_title_map() -> dict[int, str]:
    titles: dict[int, str] = dict(EXTRA_TITLES)

    for path in sorted(ISA_DIR.glob("[0-9]*.md")):
        raw = path.read_text(encoding="utf-8")
        lines = raw.splitlines()
        if not lines:
            continue
        new_h1, ep, title = convert_h1(lines[0])
        if ep is None or title is None:
            continue
        lines[0] = new_h1
        path.write_text("\n".join(lines) + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")
        titles[ep] = title

    return titles


def sync_references(titles: dict[int, str]) -> None:
    md_files = list(ISA_DIR.glob("*.md")) + list((ISA_DIR / "scripts").glob("*.md"))

    for path in md_files:
        content = path.read_text(encoding="utf-8")
        original = content

        for ep in sorted(titles, reverse=True):
            title = titles[ep]
            escaped = re.escape(title)

            content = re.sub(
                rf"(\| {ep} \|)[^|]+(\| \[읽기\]\(https://mynews20482\.tistory\.com/{ep}\) \|)",
                rf"\1 {title} \2",
                content,
            )
            content = re.sub(
                rf"(\| {ep} \|) [^|]+(\| https://mynews20482\.tistory\.com/{ep} \|)",
                rf"\1 {title} \2",
                content,
            )
            content = re.sub(
                rf"\[{ep}화:[^\]]+\]",
                f"[{ep}화: {title}]",
                content,
            )

        if content != original:
            path.write_text(content, encoding="utf-8")


def main() -> None:
    titles = build_title_map()
    sync_references(titles)
    print(f"Retitled {len([k for k in titles if k not in EXTRA_TITLES])} manuscripts; catalog has {len(titles)} episode titles.")


if __name__ == "__main__":
    main()
