#!/usr/bin/env python3
"""
build.py — собирает statиc HTML дашборд из vault.

Источники: vault/Проекты.md, reminders.md, topics/Литература.md, topics/Изучить.md.
Эра Перемен НЕ включается (платный контент).

Выход: docs/index.html.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
VAULT = Path(os.path.expanduser("~/vault"))


FOCUS_HEAD_RE = re.compile(r"^## 🎯 Фокус сейчас\s*$", re.M)
NEXT_H2_RE = re.compile(r"^## ", re.M)


def read_focus() -> list[str]:
    txt = (VAULT / "Проекты.md").read_text(encoding="utf-8")
    m = FOCUS_HEAD_RE.search(txt)
    if not m:
        return []
    rest = txt[m.end():]
    end = NEXT_H2_RE.search(rest)
    block = rest[: end.start() if end else len(rest)]
    return [
        re.sub(r"^\d+\.\s+", "", l.strip())
        for l in block.splitlines() if re.match(r"^\d+\.\s+", l.strip())
    ]


def read_open_tasks() -> list[dict]:
    txt = (VAULT / "reminders.md").read_text(encoding="utf-8")
    if "## ✅ Архив" in txt:
        txt = txt.split("## ✅ Архив", 1)[0]
    tasks = []
    section = "Без даты"
    for line in txt.splitlines():
        if line.startswith("### "):
            section = line[4:].strip()
        elif re.match(r"^- \[ \] ", line):
            tasks.append({"section": section, "text": line[6:].strip()})
    return tasks


def read_books_current() -> list[str]:
    txt = (VAULT / "topics/Литература.md").read_text(encoding="utf-8")
    m = re.search(r"## 📖 Сейчас читаю\s*\n", txt)
    if not m:
        return []
    rest = txt[m.end():]
    end = re.search(r"^## ", rest, re.M)
    block = rest[: end.start() if end else len(rest)]
    return [l.strip()[2:].strip() for l in block.splitlines() if l.strip().startswith("- ")]


def read_study() -> list[dict]:
    txt = (VAULT / "topics/Изучить.md").read_text(encoding="utf-8")
    sections, current = [], None
    for line in txt.splitlines():
        if line.startswith("## "):
            current = {"name": line[3:].strip(), "todo": []}
            sections.append(current)
        elif current is not None and re.match(r"^- \[ \] ", line):
            current["todo"].append(line[6:].strip())
    return [s for s in sections if s["todo"]]


def main() -> int:
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    tpl = env.get_template("index.html")
    html = tpl.render(
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        focus=read_focus(),
        tasks=read_open_tasks(),
        books=read_books_current(),
        study=read_study(),
    )
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
