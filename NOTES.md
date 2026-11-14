# GPUI Kit Tutorial — Curriculum Notes

## Published 10-Lesson Arc (0001–0010)

All ten initial lessons and runnable companion Rust crates (`apps/0001-*` through `apps/0010-*`) build progressively into an **Antigravity Markdown & Conversation Workbench**:

1. **Lessons 0001–0003 (Shell, Cards, Selection)** — `WorkbenchDoc` / `ConversationTurn` data model, `Render`, `v_flex`/`h_flex`, `Tag`/`Badge`, `Option<T>`, `cx.listener(...)`, `cx.notify()`.
2. **Lessons 0004–0006 (Inputs, Multiline Editor, Live Markdown)** — `Entity<InputState>`, `Subscription` + `cx.subscribe_in`, `Textarea` two-way sync, `TextView::markdown` with interactive `on_task_toggle` via `WeakEntity`.
3. **Lessons 0007–0008 (Split Layout & Code Editor)** — `h_resizable` + `resizable_panel().size_range(...)`, segmented `TabBar`/`Tab`, upgrading `Textarea` to syntax-highlighted `Editor`/`EditorState`.
4. **Lesson 0009 (Keyboard Dispatch & Toasts)** — `gpui_kit::actions!` typed action structs, `KeyBinding::new`, `FocusHandle` + `.key_context("Workbench")`, clipboard copy (`ClipboardItem::new_string`), `WindowExt::push_notification`.
5. **Lesson 0010 (Disk Persistence & SDK Bridge)** — `WorkbenchIoError` (`Display`, `Error`, `From<std::io::Error>`), lossless `from_markdown`/`to_markdown`, filesystem `save_to_path`/`load_from_path`, `Notification::error`, and `AntigravitySessionBridge` JSONL serialization aligned with `antigravity-sdk-rust` roles (`"user"` / `"model"`).

## Build & Deployment Pipeline

- Static site generation uses `build.py` (`.venv/bin/python build.py --out-dir _site --check`), enforcing quiz option count (`4`) and equal word counts per question plus internal link checking.
- GitHub Pages workflow (`.github/workflows/pages.yml`) runs `python build.py --out-dir _site --check` on every push to `main` and publishes `_site`.
