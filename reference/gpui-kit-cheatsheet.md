---
title: "GPUI Kit & Rust Quick Reference"
page_title: "Cheat Sheet — GPUI Kit Course"
nav_id: "cheatsheet"
nav_label: "Cheat Sheet"
badge: "Mission: Antigravity Markdown & Conversation Workbench"
subtitle: "Layer map, Rust-for-UI mental model, window bootstrap recipe, and Cargo verification gates."
card:
  title: "**GPUI Kit & Rust Quick Reference**"
  summary: "Printable reference for the 4-layer GPUI Kit stack, core Rust syntax, and Cargo verification commands."
---

## 1. The 4-Layer GPUI Kit Umbrella

Adding `gpui-kit = "0.9.1"` in `Cargo.toml` pins and re-exports the whole stack under a single namespace:

Table: GPUI Kit crate layers and when you import from each.

| Layer / Module | Re-export Path | Responsibility |
| :--- | :--- | :--- |
| Core Runtime | `gpui_kit::*` | Windows, GPU rendering (`div()`, `Render`), `Entity<T>`, `App`, `application()` |
| Unstyled Primitives | `gpui_kit::base` | Headless behavior, state engines, and keyboard/accessibility primitives |
| Styled Components | `gpui_kit::component` | 75+ themed widgets (`Button`, `Input`, `Textarea`, `Editor`, `TextView`, `Root`) |
| Assets Bundle | `gpui_kit::assets` | Default icon set (`gpui_kit::assets::Assets`) registered at startup |

## 2. Rust Syntax You Meet First in GPUI Kit

Table: Core Rust constructs mapped to GPUI Kit usage.

| Syntax | Meaning | Example in Lesson 0001 |
| :--- | :--- | :--- |
| `#[derive(Debug, Clone)]` | Auto-generate trait implementations | Makes `TurnRole` printable and copyable |
| `impl Type { ... }` | Attach methods to a struct or enum | `WorkbenchDoc::to_markdown(&self)` |
| `&self` / `&mut self` | Shared read borrow vs. exclusive write borrow | `render(&mut self, ...)` |
| `|cx| { ... }` | Closure (anonymous inline function) | Passed to `.run(|cx| ...)` and `.on_click(...)` |
| `pub use` / `Trait as _` | Import a trait's methods without naming the trait | `use gpui_kit::component::ActiveTheme as _;` |

## 3. Minimal Window Bootstrap Template

```rust caption="Canonical GPUI Kit entry point with automatic Root wrapper"
use gpui_kit::component::theme::{Theme, ThemeMode};
use gpui_kit::*;

fn main() {
    gpui_kit::application()
        .with_assets(gpui_kit::assets::Assets)
        .run(|cx| {
            gpui_kit::init(cx);
            Theme::change(ThemeMode::Dark, None, cx);
            gpui_kit::open_window(WindowOptions::default(), cx, |_, cx| {
                cx.new(|_| WorkbenchView::new())
            })
            .expect("failed to open workbench window");
        });
}
```

## 4. Cargo Verification Commands

```bash caption="Fast unit tests and strict zero-warning lint check"
cargo test
cargo clippy --all-targets -- -D warnings
cargo run
```


## 5. Inputs, Markdown, Splits & Persistence (Lessons 0004–0010)

### Controlled Input & Editor Sync
```rust
let input = cx.new(|cx| InputState::new(window, cx).placeholder("Session title..."));
let sub = cx.subscribe_in(&input, window, |this, state, event, _window, cx| {
    if matches!(event, InputEvent::Change) {
        let value = state.read(cx).value().to_string();
        this.doc.set_title(value);
        cx.notify();
    }
});

let editor = cx.new(|cx| {
    EditorState::new(window, cx)
        .language("markdown")
        .line_number(true)
        .soft_wrap(true)
});
```

### Live Markdown Preview + Task Checkbox Callback
```rust
let view = cx.entity().downgrade();
TextView::markdown("turn-markdown-preview", active_markdown)
    .selectable(true)
    .on_task_toggle(move |event: &TaskToggleEvent, window, cx| {
        let range = event.marker_range();
        let checked = event.checked();
        let _ = view.update(cx, |this, cx| {
            if this.toggle_active_task_marker(range, checked, window, cx) {
                cx.notify();
            }
        });
    })
```

### Split Panes & Segmented Mode Tabs
```rust
TabBar::new("layout-mode-tabs")
    .segmented()
    .selected_index(self.layout_mode.index())
    .on_click(cx.listener(|this, ix: &usize, _window, cx| {
        this.set_layout_mode(WorkspaceLayoutMode::from_index(*ix));
        cx.notify();
    }))
    .child(Tab::new().label("Edit"))
    .child(Tab::new().label("Split"))
    .child(Tab::new().label("Preview"))

h_resizable("workbench-main-split")
    .child(
        resizable_panel()
            .size(px(320.))
            .size_range(px(220.)..px(520.))
            .child(turn_list_pane),
    )
    .child(resizable_panel().child(right_workspace))
```

### Actions, Keybindings & Notifications
```rust
gpui_kit::actions!(workbench, [SaveSession, ReloadSession, CopySessionMarkdown]);

cx.bind_keys([
    KeyBinding::new("cmd-s", SaveSession, Some("Workbench")),
    KeyBinding::new("cmd-r", ReloadSession, Some("Workbench")),
    KeyBinding::new("cmd-shift-c", CopySessionMarkdown, Some("Workbench")),
]);

// Inside Render::render on the root element:
div()
    .id("workbench-root")
    .key_context("Workbench")
    .track_focus(handle)
    .on_action(cx.listener(|this, _: &SaveSession, window, cx| {
        this.save_session_to_disk(window, cx);
        cx.notify();
    }))

// Displaying status/error toasts via WindowExt:
window.push_notification(Notification::info("Saved session"), cx);
window.push_notification(Notification::error("Save failed"), cx);
```
