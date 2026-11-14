---
title: "Glossary of GPUI Kit & Rust UI Terms"
page_title: "Glossary — GPUI Kit Course"
nav_id: "glossary"
nav_label: "Glossary"
badge: "Mission: Antigravity Markdown & Conversation Workbench"
subtitle: "Canonical definitions used across all lessons and reference sheets. Designed for quick screen lookup and clean printing."
card:
  title: "**Glossary of GPUI Kit & Rust UI Terms**"
  summary: "Tight, canonical definitions for Rust ownership primitives and GPUI Kit window/entity concepts."
---

## 1. Rust Foundations for UI Developers

**Crate**:
A compilation unit and distributable package in Rust, configured by a `Cargo.toml` manifest and resolved by Cargo.
_Avoid_: "module" (a module is a namespace inside a crate) or "package file".

**Struct**:
A custom record type (`struct Name { field: Type }`) that groups named fields in contiguous memory and attaches methods via `impl Name`.
_Avoid_: "class" or "object" (Rust structs have no inheritance hierarchy).

**Enum**:
A tagged union type (`enum Role { User, Assistant }`) whose value is guaranteed by the compiler to be exactly one of its declared variants.
_Avoid_: "string flag" or "integer constant".

**Trait**:
A shared capability contract (such as `Render` or `ButtonVariants`) defining methods that a Struct or Enum can implement to plug into generic APIs.
_Avoid_: "base class" or "abstract superclass".

**Borrowing (`&T` and `&mut T`)**:
Temporary access to data owned elsewhere without transferring ownership: `&T` allows shared read-only access, whereas `&mut T` grants exclusive mutable access.
_Avoid_: "pointer copying" or "aliasing freely".

## 2. GPUI Kit Architecture

**Entity (`Entity<T>`)**:
A lightweight, copyable handle managed by GPUI's central store that owns an instance of view or state struct `T` without forcing manual lifetime annotations across callbacks.
_Avoid_: "raw pointer" or "global singleton".

**Context (`Context<T>`)**:
The capability token (`&mut Context<Self>`) passed into GPUI callbacks and render methods, granting access to themes, entity reads/writes, and re-render scheduling.
_Avoid_: "global app state" or "DOM window".

**Render Trait**:
The core GPUI contract (`impl Render for MyView`) whose `render(&mut self, window, cx)` method converts current view state into a declarative element tree (`impl IntoElement`).
_Avoid_: "draw callback" or "imperative canvas loop".

**Root View**:
The top-level window container (`gpui_kit::component::Root`) automatically installed around your application view by `gpui_kit::open_window` so dialogs, sheets, menus, and notifications render above app panes.
_Avoid_: "main div" or "HTML body".


## 3. Concurrency, State, & Error Patterns (Lessons 0004–0010)

- **`Entity<S>` & `Subscription`**: `Entity<S>` is a GPUI handle to a state object (`InputState`, `EditorState`) managed by the app context. Keep event listeners alive by storing their returned `Subscription` inside `Vec<Subscription>`.
- **`WeakEntity<V>` (`cx.entity().downgrade()`)**: A non-owning weak handle safe to capture inside `Send + Sync + 'static` callbacks (like `TextView::on_task_toggle`) without creating reference cycles.
- **`Result<T, E>`, `From`, & `?`**: Standard Rust error handling. Implementing `From<std::io::Error>` for a custom enum like `WorkbenchIoError` lets `?` automatically wrap OS filesystem failures into your domain error type.
- **Traits & Extension Traits (`use Trait as _;`)**: Shared behavior interfaces. Importing `ActiveTheme as _`, `Selectable as _`, or `WindowExt as _` adds extension methods (such as `window.push_notification`) to existing types without exposing extra type names.
- **Declarative Macros (`actions!`)**: Compile-time code generation (`gpui_kit::actions!(workbench, [...])`) that declares zero-sized typed unit structs implementing GPUI's `Action` trait.

## 4. Interactive Workbench Components (Lessons 0004–0010)

- **`Input` & `InputState`**: Single-line (`InputState::new(window, cx)`) and multiline (`multi_line(true)`) text controls synchronizing edits via `InputEvent::Change`.
- **`Editor` & `EditorState`**: Code-aware editor widget supporting `.language("markdown")`, `.line_number(bool)`, and `.soft_wrap(bool)`.
- **`TextView::markdown`**: Rich Markdown renderer supporting `.selectable(true)` and `.on_task_toggle(...)` interactive checkbox callbacks.
- **`h_resizable` & `resizable_panel`**: Draggable split-pane containers configured via `.size(px(...))` and `.size_range(min..max)`.
- **`TabBar` & `Tab`**: Segmented mode switcher (e.g., `Edit` / `Split` / `Preview`) driven by selected index.
- **`Notification::info` / `Notification::error`**: Toast alerts pushed via `WindowExt::push_notification` into the outer `Root` overlay created automatically by `gpui_kit::open_window`.
