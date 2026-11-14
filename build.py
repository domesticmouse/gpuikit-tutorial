#!/usr/bin/env python3
"""Static site builder compiling Markdown lessons and reference sheets into HTML."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt

ROOT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = ROOT_DIR / "assets"
LESSONS_DIR = ROOT_DIR / "lessons"
REFERENCE_DIR = ROOT_DIR / "reference"

FENCE_RE = re.compile(
    r"^```([a-zA-Z0-9_+-]*)(?:[ \t]+([^\n]*))?\n(.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
ATTR_RE = re.compile(r'([a-zA-Z0-9_-]+)="([^"]*)"')
HEADING_ANCHOR_RE = re.compile(r"<(h[1-6])([^>]*)>(.*?)\s*\{#([a-zA-Z0-9_-]+)\}</\1>", re.DOTALL)
BADGE_LESSON_PREFIX_RE = re.compile(r"^Lesson\s+\d+\s*[•·-]\s*", re.IGNORECASE)
SIDENOTE_RE = re.compile(r"\{\{sidenote:(.*?)\}\}", re.DOTALL)
WIDGET_RE = re.compile(r"\{\{widget:([a-zA-Z0-9_-]+)\}\}")
BLANK_RE = re.compile(r"\{\{blank:(.*?)\}\}")
MD_LINK_RE = re.compile(r'href="([^"]+)"')
PRE_CODE_RE = re.compile(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", re.DOTALL | re.IGNORECASE)
FORBIDDEN_IN_CODE_RE = re.compile(r"<(?:p|h[1-6]|pre)(?:\s|>)", re.IGNORECASE)


@dataclass
class PageMeta:
    source_path: Path
    output_rel: Path
    kind: str  # "index", "lesson", "reference"
    frontmatter: dict[str, Any]
    body_md: str
    lesson_num: str | None = None


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML frontmatter")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"{path}: malformed YAML frontmatter delimiter")
    raw_yaml = parts[0][4:]
    meta = yaml.safe_load(raw_yaml) or {}
    return meta, parts[1]


def parse_attrs(raw_attrs: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in ATTR_RE.finditer(raw_attrs or "")}


def reference_output_name(source_path: Path) -> str:
    if source_path.name == "GLOSSARY.md":
        return "glossary.html"
    return f"{source_path.stem.lower()}.html"


def make_md() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "typographer": False})
    md.enable("table")
    return md


def rewrite_links(text: str, page_kind: str) -> str:
    def _replace_md_link(match: re.Match[str]) -> str:
        prefix, target = match.group(1), match.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        frag = ""
        if "#" in target:
            path_part, frag_part = target.split("#", 1)
            frag = f"#{frag_part}"
        else:
            path_part = target
        if path_part.endswith(".md"):
            p = Path(path_part)
            if p.name == "GLOSSARY.md":
                p = p.with_name("glossary.html")
            else:
                p = p.with_suffix(".html")
            new_target = f"{p.as_posix()}{frag}"
            return f"{prefix}({new_target})"
        return match.group(0)

    return re.sub(r"(\[[^\]]+\])\(([^)]+)\)", _replace_md_link, text)


def expand_sidenotes(text: str, counter: list[int]) -> str:
    md = make_md()

    def _repl(match: re.Match[str]) -> str:
        counter[0] += 1
        idx = counter[0]
        note_md = match.group(1).strip()
        note_html = md.renderInline(note_md)
        return (
            f'<span class="sidenote-anchor">'
            f'<button type="button" class="sidenote-number" aria-expanded="false" '
            f'aria-controls="sidenote-{idx}" aria-label="Toggle note {idx}">{idx}</button>'
            f'<span class="sidenote" id="sidenote-{idx}">'
            f'<span class="sidenote-prefix">{idx}.</span> {note_html}'
            f"</span>"
            f"</span>"
        )

    return SIDENOTE_RE.sub(_repl, text)


def render_code_figure(lang: str, attrs: dict[str, str], code: str) -> str:
    clean_code = code.rstrip("\n")
    if lang == "mermaid":
        caption = attrs.get("caption", "")
        cap_html = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
        return (
            '<figure class="mermaid-figure">'
            f'<pre class="mermaid">{html.escape(clean_code, quote=False)}</pre>'
            f"{cap_html}"
            "</figure>"
        )
    caption = attrs.get("caption", "")
    lang_class = f"language-{html.escape(lang)}" if lang else "language-none"
    header_html = (
        f'<div class="code-caption">{html.escape(caption)}</div>' if caption else ""
    )
    return (
        '<div class="code-figure">'
        f"{header_html}"
        f'<pre><code class="{lang_class}">{html.escape(clean_code, quote=False)}</code></pre>'
        "</div>"
    )


def render_exercise_code(lang: str, code: str) -> str:
    clean_code = code.rstrip("\n")
    parts: list[str] = []
    last = 0
    blank_idx = 0
    for m in BLANK_RE.finditer(clean_code):
        parts.append(html.escape(clean_code[last : m.start()], quote=False))
        spec = m.group(1).split("|")
        answer = spec[0] if len(spec) > 0 else ""
        hint = spec[1] if len(spec) > 1 else "Check the syntax above."
        placeholder = spec[2] if len(spec) > 2 else "???"
        width = spec[3] if len(spec) > 3 else str(max(len(placeholder) + 2, 8))
        blank_idx += 1
        parts.append(
            f'<input type="text" class="blank-input" '
            f'data-blank-index="{blank_idx}" '
            f'data-answer="{html.escape(answer)}" '
            f'data-hint="{html.escape(hint)}" '
            f'placeholder="{html.escape(placeholder)}" '
            f'aria-label="Code blank {blank_idx}: {html.escape(placeholder)}" '
            f'style="width: {html.escape(width)}ch" '
            f'autocomplete="off" spellcheck="false">'
        )
        last = m.end()
    parts.append(html.escape(clean_code[last:], quote=False))
    lang_class = f"language-{html.escape(lang)}" if lang else "language-none"
    return (
        '<div class="code-figure exercise-code">'
        f'<pre><code class="{lang_class}">{"".join(parts)}</code></pre>'
        "</div>"
    )


def extract_fenced_blocks(
    text: str, placeholders: dict[str, str], counter: list[int]
) -> str:
    def _repl(match: re.Match[str]) -> str:
        lang = match.group(1) or ""
        attrs = parse_attrs(match.group(2) or "")
        code = match.group(3)
        counter[0] += 1
        key = f"<!--FENCED_CODE_PLACEHOLDER_{counter[0]}-->"
        placeholders[key] = render_code_figure(lang, attrs, code)
        return f"\n{key}\n"

    return FENCE_RE.sub(_repl, text)


def render_fragment_markdown(
    raw_md: str,
    page_kind: str,
    sidenote_counter: list[int],
    code_placeholders: dict[str, str],
    code_counter: list[int],
) -> str:
    work = rewrite_links(raw_md, page_kind)
    work = extract_fenced_blocks(work, code_placeholders, code_counter)
    work = expand_sidenotes(work, sidenote_counter)
    md = make_md()
    rendered = md.render(work)
    return rendered


def parse_quiz_block(attrs: dict[str, str], body: str, source_path: Path) -> str:
    questions = yaml.safe_load(body)
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"{source_path}: :::quiz must contain a non-empty YAML list")

    quiz_id = attrs.get("id", "quiz")
    title = attrs.get("title", "Retrieval Practice")
    badge = attrs.get("badge", f"{len(questions)} Questions")

    q_html_parts: list[str] = []
    for q_idx, q in enumerate(questions, start=1):
        q_text = q["question"]
        wrong_hint = q.get("wrong_hint", "Review the section above and try again.")
        options = q["options"]
        if len(options) != 4:
            raise ValueError(
                f"{source_path}: quiz '{quiz_id}' Q{q_idx} must have exactly 4 options"
            )
        word_counts = [len(str(opt["text"]).split()) for opt in options]
        if len(set(word_counts)) != 1:
            details = ", ".join(
                f"{opt['letter']}={wc}w" for opt, wc in zip(options, word_counts)
            )
            raise ValueError(
                f"{source_path}: quiz '{quiz_id}' Q{q_idx} ('{q_text}') "
                f"options must have equal word counts, got: {details}"
            )

        opts_html: list[str] = []
        for opt in options:
            letter = str(opt["letter"])
            opt_text = str(opt["text"])
            is_correct = "true" if opt.get("correct") else "false"
            explain = str(opt.get("explain", ""))
            opts_html.append(
                f'<button type="button" class="quiz-option" '
                f'data-letter="{html.escape(letter)}" '
                f'data-correct="{is_correct}" '
                f'data-explain="{html.escape(explain)}">'
                f'<span class="quiz-letter">{html.escape(letter)}</span>'
                f'<span class="quiz-text">{html.escape(opt_text)}</span>'
                f"</button>"
            )

        q_html_parts.append(
            f'<div class="quiz-question" data-q-index="{q_idx}" '
            f'data-wrong-hint="{html.escape(wrong_hint)}">'
            f'<p class="quiz-prompt"><span class="quiz-num">Q{q_idx}.</span> '
            f"{html.escape(q_text)}</p>"
            f'<div class="quiz-options">{"".join(opts_html)}</div>'
            f'<div class="quiz-feedback" aria-live="polite"></div>'
            f"</div>"
        )

    return (
        f'<section class="interactive-card quiz-card" id="{html.escape(quiz_id)}">'
        f'<div class="card-head">'
        f'<span class="card-badge">{html.escape(badge)}</span>'
        f"<h3>{html.escape(title)}</h3>"
        f"</div>"
        f'<div class="quiz-body">{"".join(q_html_parts)}</div>'
        f'<div class="quiz-score" aria-live="polite"></div>'
        f"</section>"
    )


def parse_exercise_block(
    attrs: dict[str, str],
    body: str,
    page_kind: str,
    sidenote_counter: list[int],
    code_placeholders: dict[str, str],
    code_counter: list[int],
) -> str:
    ex_id = attrs.get("id", "exercise")
    title = attrs.get("title", "Interactive Lab")
    badge = attrs.get("badge", "Skill Practice")

    prompts_data: dict[str, str] = {}
    prompts_match = re.search(
        r"^:::prompts\s*\n(.*?)^:::\s*$", body, re.MULTILINE | re.DOTALL
    )
    clean_body = body
    if prompts_match:
        prompts_data = yaml.safe_load(prompts_match.group(1)) or {}
        clean_body = body[: prompts_match.start()] + body[prompts_match.end() :]

    code_match = FENCE_RE.search(clean_body)
    if not code_match:
        raise ValueError(f":::exercise '{ex_id}' must contain a fenced code block")

    prose_before = clean_body[: code_match.start()].strip()
    prose_after = clean_body[code_match.end() :].strip()
    prose_parts = []
    if prose_before:
        prose_parts.append(
            render_fragment_markdown(
                prose_before, page_kind, sidenote_counter, code_placeholders, code_counter
            )
        )
    code_html = render_exercise_code(code_match.group(1) or "rust", code_match.group(3))
    if prose_after:
        prose_parts.append(
            render_fragment_markdown(
                prose_after, page_kind, sidenote_counter, code_placeholders, code_counter
            )
        )

    hint_msg = prompts_data.get("hint", "Check the highlighted blank.")
    success_msg = prompts_data.get("success", "All blanks verified!")

    return (
        f'<section class="interactive-card exercise-card" id="{html.escape(ex_id)}" '
        f'data-hint="{html.escape(hint_msg)}" data-success="{html.escape(success_msg)}">'
        f'<div class="card-head">'
        f'<span class="card-badge">{html.escape(badge)}</span>'
        f"<h3>{html.escape(title)}</h3>"
        f"</div>"
        f'{"".join(prose_parts)}'
        f"{code_html}"
        f'<div class="exercise-actions">'
        f'<button type="button" class="btn-action btn-check">Check Answers</button>'
        f'<button type="button" class="btn-action btn-reset">Reset</button>'
        f"</div>"
        f'<div class="exercise-feedback" aria-live="polite"></div>'
        f"</section>"
    )


def parse_verify_block(
    attrs: dict[str, str],
    body: str,
    page_kind: str,
    sidenote_counter: list[int],
    code_placeholders: dict[str, str],
    code_counter: list[int],
) -> str:
    verify_id = attrs.get("id", "verify")
    title = attrs.get("title", "Verification Lab")
    badge = attrs.get("badge", "Terminal Gate")

    checklist_items: list[str] = []
    prose_lines: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^\s*-\s+\[\s*\]\s+(.*)$", line)
        if m:
            checklist_items.append(m.group(1).strip())
        else:
            prose_lines.append(line)

    prose_html = render_fragment_markdown(
        "\n".join(prose_lines),
        page_kind,
        sidenote_counter,
        code_placeholders,
        code_counter,
    )

    checklist_html = ""
    if checklist_items:
        md = make_md()
        items_li = []
        for idx, item in enumerate(checklist_items, start=1):
            item_id = f"{verify_id}-step-{idx}"
            items_li.append(
                f'<li class="verify-step">'
                f'<label for="{html.escape(item_id)}">'
                f'<input type="checkbox" id="{html.escape(item_id)}"> '
                f"<span>{md.renderInline(item)}</span>"
                f"</label></li>"
            )
        checklist_html = f'<ul class="verify-checklist">{"".join(items_li)}</ul>'

    return (
        f'<section class="interactive-card verify-card" id="{html.escape(verify_id)}">'
        f'<div class="card-head">'
        f'<span class="card-badge">{html.escape(badge)}</span>'
        f"<h3>{html.escape(title)}</h3>"
        f"</div>"
        f"{prose_html}"
        f"{checklist_html}"
        f"</section>"
    )


def build_lesson_cards_html(lessons: list[PageMeta]) -> str:
    if not lessons:
        return '<p class="muted">No lessons published yet.</p>'
    cards: list[str] = []
    for lesson in lessons:
        num = lesson.lesson_num or "0000"
        raw_badge = str(lesson.frontmatter.get("badge", ""))
        clean_badge = BADGE_LESSON_PREFIX_RE.sub("", raw_badge).strip()
        meta_label = f"LESSON {num}" + (f" • {clean_badge}" if clean_badge else "")
        card_meta = lesson.frontmatter.get("card", {})
        card_title = card_meta.get("title", lesson.frontmatter.get("title", ""))
        card_summary = card_meta.get("summary", lesson.frontmatter.get("subtitle", ""))
        md = make_md()
        cards.append(
            f'<a class="lesson-card" href="{lesson.output_rel.as_posix()}">'
            f'<span class="lesson-card-meta">{html.escape(meta_label)}</span>'
            f'<span class="lesson-card-title">{md.renderInline(str(card_title))}</span>'
            f'<span class="lesson-card-summary">{md.renderInline(str(card_summary))}</span>'
            f"</a>"
        )
    return f'<div class="card-grid">{"".join(cards)}</div>'


def build_reference_cards_html(references: list[PageMeta]) -> str:
    if not references:
        return '<p class="muted">No reference sheets published yet.</p>'
    cards: list[str] = []
    md = make_md()
    for ref in references:
        card_meta = ref.frontmatter.get("card", {})
        card_title = card_meta.get("title", ref.frontmatter.get("title", ""))
        card_summary = card_meta.get("summary", ref.frontmatter.get("subtitle", ""))
        cards.append(
            f'<a class="reference-card" href="{ref.output_rel.as_posix()}">'
            f'<span class="reference-card-title">{md.renderInline(str(card_title))}</span>'
            f'<span class="reference-card-summary">{md.renderInline(str(card_summary))}</span>'
            f"</a>"
        )
    return f'<div class="ref-grid">{"".join(cards)}</div>'


def build_gpui_lifecycle_sim_html() -> str:
    return (
        '<section class="interactive-card sim-card" id="gpui-lifecycle-sim" '
        'data-widget="gpui-lifecycle-sim">'
        '<div class="card-head">'
        '<span class="card-badge">Interactive Simulator • Ownership &amp; Lifecycle</span>'
        "<h3>GPUI Kit Window &amp; Entity Ownership Trace</h3>"
        "</div>"
        '<p class="sim-intro">Step through the five stages from OS process start to GPU frame rendering to see which Rust context handle you borrow at each boundary.</p>'
        '<div class="sim-controls" role="tablist" aria-label="GPUI Kit lifecycle stages">'
        '<button type="button" class="sim-step-btn is-active" data-step="0" role="tab" aria-selected="true">1. application().run</button>'
        '<button type="button" class="sim-step-btn" data-step="1" role="tab" aria-selected="false">2. gpui_kit::init(cx)</button>'
        '<button type="button" class="sim-step-btn" data-step="2" role="tab" aria-selected="false">3. open_window &amp; Root</button>'
        '<button type="button" class="sim-step-btn" data-step="3" role="tab" aria-selected="false">4. cx.new Entity</button>'
        '<button type="button" class="sim-step-btn" data-step="4" role="tab" aria-selected="false">5. Render::render</button>'
        "</div>"
        '<div class="sim-stage" aria-live="polite"></div>'
        "</section>"
    )


def render_page_body(
    page: PageMeta,
    lessons: list[PageMeta],
    references: list[PageMeta],
) -> str:
    text = page.body_md
    block_placeholders: dict[str, str] = {}
    code_placeholders: dict[str, str] = {}
    block_counter = [0]
    code_counter = [0]
    sidenote_counter = [0]

    # 1. Extract :::quiz blocks (with inner YAML) before any Markdown or fence extraction
    quiz_re = re.compile(r"^:::quiz([^\n]*)\n(.*?)^:::\s*$", re.MULTILINE | re.DOTALL)

    def _quiz_repl(m: re.Match[str]) -> str:
        attrs = parse_attrs(m.group(1))
        block_counter[0] += 1
        key = f"<!--BLOCK_PLACEHOLDER_{block_counter[0]}-->"
        block_placeholders[key] = parse_quiz_block(attrs, m.group(2), page.source_path)
        return f"\n{key}\n"

    text = quiz_re.sub(_quiz_repl, text)

    # 2. Extract :::exercise blocks (which contain :::prompts ... ::: nested inside)
    ex_re = re.compile(
        r"^:::exercise([^\n]*)\n(.*?^:::prompts\s*\n.*?^:::\s*\n?)^:::\s*$",
        re.MULTILINE | re.DOTALL,
    )

    def _ex_repl(m: re.Match[str]) -> str:
        attrs = parse_attrs(m.group(1))
        block_counter[0] += 1
        key = f"<!--BLOCK_PLACEHOLDER_{block_counter[0]}-->"
        block_placeholders[key] = parse_exercise_block(
            attrs,
            m.group(2),
            page.kind,
            sidenote_counter,
            code_placeholders,
            code_counter,
        )
        return f"\n{key}\n"

    text = ex_re.sub(_ex_repl, text)

    # 3. Extract :::verify blocks
    verify_re = re.compile(
        r"^:::verify([^\n]*)\n(.*?)^:::\s*$", re.MULTILINE | re.DOTALL
    )

    def _verify_repl(m: re.Match[str]) -> str:
        attrs = parse_attrs(m.group(1))
        block_counter[0] += 1
        key = f"<!--BLOCK_PLACEHOLDER_{block_counter[0]}-->"
        block_placeholders[key] = parse_verify_block(
            attrs,
            m.group(2),
            page.kind,
            sidenote_counter,
            code_placeholders,
            code_counter,
        )
        return f"\n{key}\n"

    text = verify_re.sub(_verify_repl, text)

    # 4. Extract :::callout, :::callout-warn, :::callout-success, :::teacher-prompt
    container_re = re.compile(
        r"^:::(callout-warn|callout-success|callout|teacher-prompt)([^\n]*)\n(.*?)^:::\s*$",
        re.MULTILINE | re.DOTALL,
    )

    def _container_repl(m: re.Match[str]) -> str:
        kind = m.group(1)
        attrs = parse_attrs(m.group(2))
        inner_html = render_fragment_markdown(
            m.group(3),
            page.kind,
            sidenote_counter,
            code_placeholders,
            code_counter,
        )
        title = attrs.get("title", "")
        title_html = f'<div class="callout-title">{html.escape(title)}</div>' if title else ""
        css_cls = {
            "callout": "callout",
            "callout-warn": "callout callout-warn",
            "callout-success": "callout callout-success",
            "teacher-prompt": "callout teacher-prompt",
        }[kind]
        block_counter[0] += 1
        key = f"<!--BLOCK_PLACEHOLDER_{block_counter[0]}-->"
        block_placeholders[key] = f'<aside class="{css_cls}">{title_html}{inner_html}</aside>'
        return f"\n{key}\n"

    text = container_re.sub(_container_repl, text)

    # 5. Extract remaining fenced code blocks BEFORE md.render(), link rewriting, and sidenotes
    text = extract_fenced_blocks(text, code_placeholders, code_counter)

    # 6. Rewrite .md links and expand sidenotes outside fenced code blocks
    text = rewrite_links(text, page.kind)
    text = expand_sidenotes(text, sidenote_counter)

    # 7. Extract {{widget:...}} placeholders
    def _widget_repl(m: re.Match[str]) -> str:
        wname = m.group(1)
        block_counter[0] += 1
        key = f"<!--BLOCK_PLACEHOLDER_{block_counter[0]}-->"
        if wname == "lesson-cards":
            block_placeholders[key] = build_lesson_cards_html(lessons)
        elif wname == "reference-cards":
            block_placeholders[key] = build_reference_cards_html(references)
        elif wname == "gpui-lifecycle-sim":
            block_placeholders[key] = build_gpui_lifecycle_sim_html()
        else:
            raise ValueError(f"{page.source_path}: unknown widget '{{{{widget:{wname}}}}}'")
        return f"\n{key}\n"

    text = WIDGET_RE.sub(_widget_repl, text)

    # 8. Convert Pipe Table Captions ("Table: ...") right before tables
    text = re.sub(
        r"^Table:\s*(.+)$",
        r'<div class="table-caption">\1</div>',
        text,
        flags=re.MULTILINE,
    )

    # 9. Render Markdown
    md = make_md()
    rendered_html = md.render(text)

    # 10. Add class="ref-table" to rendered tables and convert {#anchor-id} headings
    rendered_html = rendered_html.replace("<table>", '<table class="ref-table">')
    rendered_html = HEADING_ANCHOR_RE.sub(
        lambda m: f'<{m.group(1)}{m.group(2)} id="{m.group(4)}">{m.group(3)}</{m.group(1)}>',
        rendered_html,
    )

    # 11. Restore placeholders after md.render()
    for key, val in block_placeholders.items():
        rendered_html = rendered_html.replace(f"<p>{key}</p>", val).replace(key, val)
    for key, val in code_placeholders.items():
        rendered_html = rendered_html.replace(f"<p>{key}</p>", val).replace(key, val)

    return rendered_html


def build_nav_html(
    page: PageMeta, lessons: list[PageMeta], references: list[PageMeta]
) -> str:
    prefix = "" if page.kind == "index" else "../"

    if page.kind == "index":
        crumbs = '<span class="crumb-current" aria-current="page">Index</span>'
    elif page.kind == "lesson":
        crumbs = (
            f'<a href="{prefix}index.html">Index</a>'
            f'<span class="crumb-sep" aria-hidden="true">›</span>'
            f'<span class="crumb-current" aria-current="page">Lesson {page.lesson_num}</span>'
        )
    else:
        label = page.frontmatter.get("nav_label", page.frontmatter.get("title", "Reference"))
        crumbs = (
            f'<a href="{prefix}index.html">Index</a>'
            f'<span class="crumb-sep" aria-hidden="true">›</span>'
            f'<span class="crumb-current" aria-current="page">{html.escape(str(label))}</span>'
        )

    pager_group = ""
    if page.kind == "lesson":
        idx = next(i for i, l in enumerate(lessons) if l.output_rel == page.output_rel)
        if idx > 0:
            prev_l = lessons[idx - 1]
            prev_html = (
                f'<a class="nav-pill" href="{prefix}{prev_l.output_rel.as_posix()}" '
                f'title="{html.escape(str(prev_l.frontmatter.get("title", "")))}">← Prev</a>'
            )
        else:
            prev_html = '<span class="nav-pill is-disabled" aria-disabled="true">← Prev</span>'

        if idx + 1 < len(lessons):
            next_l = lessons[idx + 1]
            next_html = (
                f'<a class="nav-pill" href="{prefix}{next_l.output_rel.as_posix()}" '
                f'title="{html.escape(str(next_l.frontmatter.get("title", "")))}">Next →</a>'
            )
        else:
            next_html = '<span class="nav-pill is-disabled" aria-disabled="true">Next →</span>'

        pager_group = (
            f'<div class="nav-pager-group">{prev_html}'
            f'<span class="nav-dot" aria-hidden="true">·</span>{next_html}</div>'
            f'<span class="nav-sep" aria-hidden="true">|</span>'
        )

    ref_links: list[str] = []
    for ref in references:
        label = ref.frontmatter.get("nav_label", ref.frontmatter.get("title", "Ref"))
        is_active = page.output_rel == ref.output_rel
        aria = ' aria-current="page"' if is_active else ""
        cls = "nav-ref is-active" if is_active else "nav-ref"
        ref_links.append(
            f'<a class="{cls}" href="{prefix}{ref.output_rel.as_posix()}"{aria}>'
            f"{html.escape(str(label))}</a>"
        )

    return (
        '<header class="site-header">'
        '<nav class="course-nav" aria-label="Course">'
        f'<div class="nav-breadcrumbs">{crumbs}</div>'
        f'<div class="nav-controls">{pager_group}{"".join(ref_links)}'
        '<span class="mission-badge">Antigravity Workbench</span></div>'
        "</nav>"
        "</header>"
    )


def build_lesson_pager_html(page: PageMeta, lessons: list[PageMeta]) -> str:
    if page.kind != "lesson":
        return ""
    idx = next(i for i, l in enumerate(lessons) if l.output_rel == page.output_rel)

    if idx > 0:
        prev_l = lessons[idx - 1]
        prev_card = (
            f'<a class="lesson-pager-card" href="../{prev_l.output_rel.as_posix()}">'
            f'<span class="pager-meta">← Previous • Lesson {prev_l.lesson_num}</span>'
            f'<span class="pager-title">{html.escape(str(prev_l.frontmatter.get("title", "")))}</span>'
            f"</a>"
        )
    else:
        prev_card = (
            '<div class="lesson-pager-card is-empty" aria-hidden="true">'
            '<span class="pager-meta">Course Start</span>'
            '<span class="pager-title">First Lesson</span>'
            "</div>"
        )

    if idx + 1 < len(lessons):
        next_l = lessons[idx + 1]
        next_card = (
            f'<a class="lesson-pager-card pager-next" href="../{next_l.output_rel.as_posix()}">'
            f'<span class="pager-meta">Next • Lesson {next_l.lesson_num} →</span>'
            f'<span class="pager-title">{html.escape(str(next_l.frontmatter.get("title", "")))}</span>'
            f"</a>"
        )
    else:
        next_card = (
            '<div class="lesson-pager-card pager-next is-empty" aria-hidden="true">'
            '<span class="pager-meta">Up Next</span>'
            '<span class="pager-title">More lessons coming soon</span>'
            "</div>"
        )

    return (
        '<nav class="lesson-pager" aria-label="Lesson pagination">'
        f"{prev_card}{next_card}"
        "</nav>"
    )


def wrap_html_document(
    page: PageMeta,
    body_html: str,
    nav_html: str,
    pager_html: str,
) -> str:
    prefix = "" if page.kind == "index" else "../"
    page_title = str(page.frontmatter.get("page_title", page.frontmatter.get("title", "GPUI Kit Course")))
    title = str(page.frontmatter.get("title", ""))
    badge = str(page.frontmatter.get("badge", ""))
    subtitle = str(page.frontmatter.get("subtitle", ""))

    badge_html = f'<div class="article-badge">{html.escape(badge)}</div>' if badge else ""
    subtitle_html = f'<p class="article-subtitle">{html.escape(subtitle)}</p>' if subtitle else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>{html.escape(page_title)}</title>
  <link rel="stylesheet" href="{prefix}assets/style.css">
  <script src="{prefix}assets/course.js" defer></script>
</head>
<body data-page-kind="{html.escape(page.kind)}">
  <a href="#main-content" class="skip-link">Skip to content</a>
  {nav_html}
  <main class="page-main">
    <article class="lesson-article">
      <header class="article-header">
        {badge_html}
        <h1 id="main-content" tabindex="-1">{html.escape(title)}</h1>
        {subtitle_html}
      </header>
      <div class="article-body">
        {body_html}
      </div>
      {pager_html}
    </article>
  </main>
  <footer class="site-footer">
    <p>GPUI Kit Interactive Course — Built for Rust novices crafting <code>antigravity-sdk-rust</code> desktop interfaces.</p>
  </footer>
</body>
</html>
"""


def collect_pages() -> tuple[PageMeta, list[PageMeta], list[PageMeta]]:
    index_path = ROOT_DIR / "index.md"
    idx_meta, idx_body = parse_frontmatter(index_path.read_text(encoding="utf-8"), index_path)
    index_page = PageMeta(
        source_path=index_path,
        output_rel=Path("index.html"),
        kind="index",
        frontmatter=idx_meta,
        body_md=idx_body,
    )

    lessons: list[PageMeta] = []
    if LESSONS_DIR.exists():
        for md_path in sorted(LESSONS_DIR.glob("*.md")):
            meta, body = parse_frontmatter(md_path.read_text(encoding="utf-8"), md_path)
            m = re.match(r"^(\d{4})-", md_path.stem)
            lesson_num = m.group(1) if m else "0000"
            lessons.append(
                PageMeta(
                    source_path=md_path,
                    output_rel=Path("lessons") / f"{md_path.stem}.html",
                    kind="lesson",
                    frontmatter=meta,
                    body_md=body,
                    lesson_num=lesson_num,
                )
            )

    references: list[PageMeta] = []
    if REFERENCE_DIR.exists():
        for md_path in sorted(REFERENCE_DIR.glob("*.md")):
            meta, body = parse_frontmatter(md_path.read_text(encoding="utf-8"), md_path)
            references.append(
                PageMeta(
                    source_path=md_path,
                    output_rel=Path("reference") / reference_output_name(md_path),
                    kind="reference",
                    frontmatter=meta,
                    body_md=body,
                )
            )

    return index_page, lessons, references


def check_outputs(written: dict[Path, str], out_dir: Path) -> None:
    errors: list[str] = []

    for rel_path, content in written.items():
        # 1. Verify no <pre><code> blocks contain <p>, <h1..6>, or nested <pre>
        for match in PRE_CODE_RE.finditer(content):
            inner = match.group(1)
            if FORBIDDEN_IN_CODE_RE.search(inner):
                errors.append(
                    f"{rel_path}: <pre><code> contains forbidden nested HTML block tag"
                )

        # 2. Verify all internal relative links resolve to generated HTML or asset files
        base_parent = (out_dir / rel_path).parent
        for link_match in MD_LINK_RE.finditer(content):
            href = link_match.group(1)
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_part = href.split("#", 1)[0]
            resolved = (base_parent / target_part).resolve()
            if not resolved.exists():
                errors.append(f"{rel_path}: broken internal link '{href}' -> {resolved}")

    if errors:
        raise ValueError("Validation checks failed:\n  - " + "\n  - ".join(errors))


def build_site(out_dir: Path, run_checks: bool) -> None:
    index_page, lessons, references = collect_pages()
    all_pages = [index_page, *lessons, *references]

    out_dir = out_dir.resolve()
    if out_dir != ROOT_DIR:
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ASSETS_DIR, out_dir / "assets")
        (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    written: dict[Path, str] = {}
    for page in all_pages:
        body_html = render_page_body(page, lessons, references)
        nav_html = build_nav_html(page, lessons, references)
        pager_html = build_lesson_pager_html(page, lessons)
        full_html = wrap_html_document(page, body_html, nav_html, pager_html)

        dest = out_dir / page.output_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(full_html, encoding="utf-8")
        written[page.output_rel] = full_html

    if run_checks:
        check_outputs(written, out_dir)

    print(
        f"Built {len(written)} page(s) into {out_dir} "
        f"({len(lessons)} lesson(s), {len(references)} reference sheet(s))"
        + (" [checks passed]" if run_checks else "")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the GPUI Kit tutorial site.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT_DIR,
        help="Destination directory for built HTML files (default: repo root)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate quiz word counts, internal links, and code-block HTML integrity",
    )
    args = parser.parse_args()
    try:
        build_site(args.out_dir, args.check)
    except Exception as exc:
        print(f"build.py error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
