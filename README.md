# GPUI Kit & Rust — Interactive Workbench Course

Learn Rust and **`gpui-kit` (`0.9.1`)** by incrementally building an **Antigravity Markdown & Conversation Workbench** desktop application with ten verified, self-contained runnable crates.

## Lessons

| # | Lesson | Companion Crate | Key Rust & GPUI Kit Concepts |
| --- | --- | --- | --- |
| 0001 | [Bootstrap Workbench Shell](lessons/0001-bootstrap-workbench-shell.md) | `apps/0001-bootstrap-workbench-shell` | `struct`, `impl`, `Render`, `v_flex`, `h_flex`, `ActiveTheme` |
| 0002 | [Turn Cards & Role Badges](lessons/0002-turn-cards-and-badges.md) | `apps/0002-turn-cards-and-badges` | `enum`, `match`, slices (`&[...]`), `.iter().map()`, `Tag`, `Badge` |
| 0003 | [Reactive Turn Selection & Filtering](lessons/0003-reactive-turn-selection.md) | `apps/0003-reactive-turn-selection` | `Option<T>`, `cx.listener(...)`, `cx.notify()`, `.saturating_sub(...)` |
| 0004 | [Single-Line Inputs & Titles](lessons/0004-single-line-inputs-and-titles.md) | `apps/0004-single-line-inputs-and-titles` | `Entity<InputState>`, `Subscription`, `cx.subscribe_in`, `InputEvent::Change` |
| 0005 | [Multiline Markdown Editing](lessons/0005-multiline-markdown-textarea.md) | `apps/0005-multiline-markdown-textarea` | `Textarea`, `InputState::multi_line`, two-way entity sync, `impl Into<String>` |
| 0006 | [Live Markdown Preview & Checkboxes](lessons/0006-live-markdown-preview-textview.md) | `apps/0006-live-markdown-preview-textview` | `TextView::markdown`, `on_task_toggle`, `WeakEntity`, `Range<usize>` |
| 0007 | [Split-Pane Resizable Workbench](lessons/0007-split-pane-resizable-workbench.md) | `apps/0007-split-pane-resizable-workbench` | `h_resizable`, `resizable_panel`, `TabBar`/`Tab`, `into_any_element()` |
| 0008 | [Code Editor & Syntax Highlighting](lessons/0008-code-editor-and-syntax-highlighting.md) | `apps/0008-code-editor-and-syntax-highlighting` | `Editor` / `EditorState`, `.language("markdown")`, `line_number`, `soft_wrap` |
| 0009 | [Keyboard Actions & Toast Notifications](lessons/0009-keyboard-actions-and-notifications.md) | `apps/0009-keyboard-actions-and-notifications` | `gpui_kit::actions!`, `FocusHandle`, `key_context`, `WindowExt::push_notification`, clipboard |
| 0010 | [Markdown Persistence & SDK Bridge](lessons/0010-markdown-persistence-and-sdk-bridge.md) | `apps/0010-markdown-persistence-and-sdk-bridge` | `Result<T, E>`, `From<std::io::Error>`, `?`, `AntigravitySessionBridge` trait, `.md` I/O |

## Reference Sheets

- [Rust & GPUI Kit Glossary](reference/GLOSSARY.md)
- [GPUI Kit Workbench Cheatsheet](reference/gpui-kit-cheatsheet.md)

## Quick Commands

Run the capstone workbench or verify tests and static site compilation:

```bash
# Build & validate the static HTML course site
.venv/bin/python build.py --out-dir _site --check

# Run tests and strict Clippy on Lesson 0010
cargo test --manifest-path apps/0010-markdown-persistence-and-sdk-bridge/Cargo.toml
cargo clippy --manifest-path apps/0010-markdown-persistence-and-sdk-bridge/Cargo.toml --all-targets -- -D warnings

# Launch the desktop workbench app
cargo run --manifest-path apps/0010-markdown-persistence-and-sdk-bridge/Cargo.toml
```
