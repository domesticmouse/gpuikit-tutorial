# GPUI Kit & Rust — Interactive Workbench Course

Learn Rust and **`gpui-kit` (`0.9.1`)** by incrementally building an **Antigravity Markdown & Conversation Workbench** desktop application with ten verified, self-contained runnable crates.

- **Live Course Site:** [https://domesticmouse.github.io/gpuikit-tutorial/](https://domesticmouse.github.io/gpuikit-tutorial/) — interactive HTML course with Tufte sidenotes, Mermaid diagrams, fill-in-the-blank labs, and retrieval quizzes.

## Lessons

| # | Lesson | Companion Crate | Key Rust & GPUI Kit Concepts |
| --- | --- | --- | --- |
| 0001 | [Bootstrap Workbench Shell](lessons/0001-bootstrap-workbench-shell.md) | [`apps/0001-bootstrap-workbench-shell`](apps/0001-bootstrap-workbench-shell) | `struct`, `impl`, `Render`, `v_flex`, `h_flex`, `ActiveTheme` |
| 0002 | [Turn Cards & Role Badges](lessons/0002-turn-cards-and-badges.md) | [`apps/0002-turn-cards-and-badges`](apps/0002-turn-cards-and-badges) | `enum`, `match`, slices (`&[...]`), `.iter().map()`, `Tag`, `Badge` |
| 0003 | [Reactive Turn Selection & Filtering](lessons/0003-reactive-turn-selection.md) | [`apps/0003-reactive-turn-selection`](apps/0003-reactive-turn-selection) | `Option<T>`, `cx.listener(...)`, `cx.notify()`, `.saturating_sub(...)` |
| 0004 | [Single-Line Inputs & Titles](lessons/0004-single-line-inputs-and-titles.md) | [`apps/0004-single-line-inputs-and-titles`](apps/0004-single-line-inputs-and-titles) | `Entity<InputState>`, `Subscription`, `cx.subscribe_in`, `InputEvent::Change` |
| 0005 | [Multiline Markdown Editing](lessons/0005-multiline-markdown-textarea.md) | [`apps/0005-multiline-markdown-textarea`](apps/0005-multiline-markdown-textarea) | `Textarea`, `InputState::multi_line`, two-way entity sync, `impl Into<String>` |
| 0006 | [Live Markdown Preview & Checkboxes](lessons/0006-live-markdown-preview-textview.md) | [`apps/0006-live-markdown-preview-textview`](apps/0006-live-markdown-preview-textview) | `TextView::markdown`, `on_task_toggle`, `WeakEntity`, `Range<usize>` |
| 0007 | [Split-Pane Resizable Workbench](lessons/0007-split-pane-resizable-workbench.md) | [`apps/0007-split-pane-resizable-workbench`](apps/0007-split-pane-resizable-workbench) | `h_resizable`, `resizable_panel`, `TabBar`/`Tab`, `into_any_element()` |
| 0008 | [Code Editor & Syntax Highlighting](lessons/0008-code-editor-and-syntax-highlighting.md) | [`apps/0008-code-editor-and-syntax-highlighting`](apps/0008-code-editor-and-syntax-highlighting) | `Editor` / `EditorState`, `.language("markdown")`, `line_number`, `soft_wrap` |
| 0009 | [Keyboard Actions & Toast Notifications](lessons/0009-keyboard-actions-and-notifications.md) | [`apps/0009-keyboard-actions-and-notifications`](apps/0009-keyboard-actions-and-notifications) | `gpui_kit::actions!`, `FocusHandle`, `key_context`, `WindowExt::push_notification`, clipboard |
| 0010 | [Markdown Persistence & SDK Bridge](lessons/0010-markdown-persistence-and-sdk-bridge.md) | [`apps/0010-markdown-persistence-and-sdk-bridge`](apps/0010-markdown-persistence-and-sdk-bridge) | `Result<T, E>`, `From<std::io::Error>`, `?`, `AntigravitySessionBridge` trait, `.md` I/O |

## Reference Sheets

- [Rust & GPUI Kit Glossary](reference/GLOSSARY.md) ([live HTML](https://domesticmouse.github.io/gpuikit-tutorial/reference/glossary.html))
- [GPUI Kit Workbench Cheatsheet](reference/gpui-kit-cheatsheet.md) ([live HTML](https://domesticmouse.github.io/gpuikit-tutorial/reference/gpui-kit-cheatsheet.html))

## Repository Structure & Agent Skills

- [`index.md`](index.md), [`lessons/`](lessons/), [`reference/`](reference/), [`assets/`](assets/), [`build.py`](build.py) — Markdown-to-HTML static site pipeline (`markdown-it-py` + `pyyaml`).
- [`apps/`](apps/) — Ten standalone, runnable Cargo crates (`apps/0001-*` to `apps/0010-*`) representing each lesson's verified state.
- [`MISSION.md`](MISSION.md), [`RESOURCES.md`](RESOURCES.md), [`NOTES.md`](NOTES.md), [`learning-records/`](learning-records/) — Course mission, primary documentation sources, curriculum notes, and learner records.
- [`.agents/skills/gpui-kit/SKILL.md`](.agents/skills/gpui-kit/SKILL.md) — Verified `gpui-kit` (`0.9.1`) architectural patterns, widget APIs, and Cargo gates.
- [`.agents/skills/teach-code/SKILL.md`](.agents/skills/teach-code/SKILL.md) & [`sync_listing.py`](.agents/skills/teach-code/scripts/sync_listing.py) — Interactive code-teaching workflow and automated `Complete ... Listing` synchronization script.

## Prerequisites & First-Time Setup

Requires a Rust toolchain (`rustc` / `cargo`) and Python 3.12+ with `uv`. Create the local `.venv` once to run site builds and listing checks:

```bash
uv venv .venv
uv pip install --python .venv/bin/python markdown-it-py pyyaml
```

## Quick Commands

Run the capstone workbench or verify tests, code listings, and static site compilation:

```bash
# Build & validate the static HTML course site (then clean temporary output)
.venv/bin/python build.py --out-dir _site --check && rm -rf _site

# Verify byte-for-byte parity between apps/*/src/main.rs and lessons/*.md
.venv/bin/python .agents/skills/teach-code/scripts/sync_listing.py --check

# Run tests and strict Clippy on Lesson 0010
cargo test --manifest-path apps/0010-markdown-persistence-and-sdk-bridge/Cargo.toml
cargo clippy --manifest-path apps/0010-markdown-persistence-and-sdk-bridge/Cargo.toml --all-targets -- -D warnings

# Launch the desktop workbench app
cargo run --manifest-path apps/0010-markdown-persistence-and-sdk-bridge/Cargo.toml
```
