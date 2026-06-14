#!/usr/bin/env python3
"""
build.py — собирает statиc HTML дашборд из vault.

Источники: vault/Проекты.md, reminders.md, topics/Литература.md, topics/Изучить.md.
Эра Перемен НЕ включается (платный контент).

Выход: docs/index.html.
"""
from __future__ import annotations

import html
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup


# ────────── inline markdown renderer ──────────

MD_LINK_RE     = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")             # [text](url)
MD_AUTOLINK_RE = re.compile(r"&lt;(https?://[^\s&]+)&gt;")           # <https://…>
MD_BARE_URL_RE = re.compile(r"(?<![\"'>])(https?://\S+)")            # голый https://…
MD_WIKI_RE     = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")     # [[target]] / [[target|label]]
MD_BOLD_RE     = re.compile(r"\*\*([^*]+)\*\*")                     # **bold**
MD_CODE_RE     = re.compile(r"`([^`]+)`")                           # `code`


def md_inline(text: str) -> Markup:
    """Минимальный inline-markdown в HTML. На вход — сырая строка из vault."""
    if not text:
        return Markup("")
    s = html.escape(text)
    # Сначала explicit [text](url), потом <…autolink>, потом голые URL
    s = MD_LINK_RE.sub(
        lambda m: f'<a href="{m.group(2)}" rel="noopener" target="_blank">{m.group(1)}</a>', s)
    s = MD_AUTOLINK_RE.sub(
        lambda m: f'<a href="{m.group(1)}" rel="noopener" target="_blank">{m.group(1)}</a>', s)
    s = MD_BARE_URL_RE.sub(
        lambda m: f'<a href="{m.group(1)}" rel="noopener" target="_blank">{m.group(1)}</a>', s)
    s = MD_WIKI_RE.sub(
        lambda m: f'<span class="wiki">{m.group(2) or m.group(1)}</span>', s)
    s = MD_CODE_RE.sub(r"<code>\1</code>", s)
    s = MD_BOLD_RE.sub(r"<strong>\1</strong>", s)
    return Markup(s)

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


def vault_last_commit_time() -> str:
    """Берём время последнего vault-коммита — стабильно между запусками build."""
    try:
        out = subprocess.run(
            ["git", "-C", str(VAULT), "log", "-1", "--format=%cd",
             "--date=format:%Y-%m-%d %H:%M"],
            check=True, capture_output=True, text=True)
        return out.stdout.strip()
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M")


def main() -> int:
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["md"] = md_inline
    tpl = env.get_template("index.html")
    rendered = tpl.render(
        now=vault_last_commit_time(),
        focus=read_focus(),
        tasks=read_open_tasks(),
        books=read_books_current(),
        study=read_study(),
    )
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    print(f"wrote {out} ({len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
