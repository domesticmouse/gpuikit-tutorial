---
title: "Bootstrap the Workbench Shell"
page_title: "Lesson 0001: Bootstrap the Workbench Shell — GPUI Kit Course"
nav_id: "lesson-0001"
badge: "Lesson 0001 • GPUI Kit & Rust Foundations"
subtitle: "Create the Antigravity Workbench Cargo crate, model conversation turns in Rust, wrap WorkbenchView in Root, and verify everything with cargo test and clippy."
card:
  title: "**Bootstrap the Workbench Shell**"
  summary: "Initialize gpui-kit, learn Rust structs, enums, traits, and borrowing inline, open a Root-managed window, and verify with automated tests."
---

Every project-based agentic workbench—including the interfaces you will build around [`antigravity-sdk-rust`](https://crates.io/crates/antigravity-sdk-rust)—starts with two things: a clean data model for conversations and Markdown documents, and a GPU-accelerated desktop shell that renders them reliably. In this first lesson, you will build and test the foundation of your **Antigravity Markdown & Conversation Workbench** using **GPUI Kit** (`gpui-kit`), learning the essential Rust building blocks right as they appear in the code.

:::callout title="Recommended Primary Sources"
- [GPUI Kit Official Documentation](https://gpui-kit.com/) — Architecture guide covering `application()`, `init(cx)`, `open_window`, and `Root`.
- [GPUI Kit API Reference (`docs.rs/gpui-kit`)](https://docs.rs/gpui-kit/latest/gpui_kit/) — Authoritative signatures for `gpui_kit`, `component`, `base`, and `assets`.
- [The Rust Programming Language](https://doc.rust-lang.org/book/) — Reference chapters on structs, enums, traits, and ownership.
- Course References: [Glossary](../reference/GLOSSARY.md) and [GPUI Kit & Rust Quick Reference](../reference/gpui-kit-cheatsheet.md).
:::

## How GPUI Kit Organizes Desktop Apps

Unlike web frameworks that require wiring separate state libraries, UI kits, icon packs, and rendering backends, `gpui-kit` acts as a single umbrella **Crate**{{sidenote:A **Crate** is Rust's compilation unit and package boundary. Listing `gpui-kit = "0.9.1"` in `Cargo.toml` pulls in matching pinned versions of `gpui`, `gpui-base`, `gpui-component`, and `gpui-kit-assets`.}} that pins matching versions of four cooperating layers.

```mermaid caption="Figure 1.1: The four-layer GPUI Kit stack and window startup sequence"
flowchart TD
    Crate["Cargo.toml: gpui-kit = 0.9.1"] --> App["gpui_kit::application().with_assets(Assets)"]
    App --> Run["run(|cx| ...) — borrows &mut App"]
    Run --> Init["gpui_kit::init(cx) — registers themes & base registries"]
    Init --> Open["gpui_kit::open_window(..., cx, |_, cx| ...)"]
    Open --> Root["gpui_kit::component::Root — hosts overlays, dialogs & notifications"]
    Open --> Entity["cx.new(|_| WorkbenchView::new()) -> Entity&lt;WorkbenchView&gt;"]
    Root --> Render["Render::render(&mut self, window, cx) -> impl IntoElement"]
    Entity --> Render
```

Notice what `gpui_kit::open_window` does for you automatically: it wraps your `WorkbenchView` inside a **`Root` View**{{sidenote:If you called raw GPUI's `cx.open_window` directly without `Root`, modal dialogs, menus, sheets, and toast notifications would have no top-level overlay host.}}. Step through all five startup stages below to see exactly which Rust ownership handle is active at each step.

{{widget:gpui-lifecycle-sim}}

## Step 1: Configure the Crate Manifest (`Cargo.toml`)

Every Rust project begins with a `Cargo.toml` manifest at its root. Create the project directory `apps/0001-bootstrap-workbench-shell/` (or navigate into it) and inspect its manifest:

```toml caption="apps/0001-bootstrap-workbench-shell/Cargo.toml"
[package]
name = "antigravity-workbench"
version = "0.1.0"
edition = "2024"

[dependencies]
gpui-kit = "0.9.1"
```

- `[package]` names your binary crate (`antigravity-workbench`), sets its semantic version, and locks Rust `edition = "2024"`.
- `[dependencies]` pulls in `gpui-kit = "0.9.1"`, giving you `gpui_kit::*` (core GPUI rendering and layout), `gpui_kit::base`, `gpui_kit::component`, and `gpui_kit::assets` without managing mismatched sub-crate commits.

## Step 2: Build the Application Block by Block

Rather than dumping an entire UI framework file on screen at once, let us build `src/main.rs` in five small, self-contained blocks—unpacking every new Rust concept right where it first appears.

### Block 1: Imports & Conversation Domain Types {#block-1}

```rust caption="Block 1: Imports, TurnRole enum, and ConversationTurn struct"
use gpui_kit::component::ActiveTheme as _;
use gpui_kit::component::button::{Button, ButtonVariants as _};
use gpui_kit::*;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TurnRole {
    User,
    Assistant,
}

impl TurnRole {
    pub fn badge_label(&self) -> &'static str {
        match self {
            TurnRole::User => "USER",
            TurnRole::Assistant => "AGENT",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConversationTurn {
    pub role: TurnRole,
    pub markdown: String,
}

impl ConversationTurn {
    pub fn new(role: TurnRole, markdown: impl Into<String>) -> Self {
        Self {
            role,
            markdown: markdown.into(),
        }
    }

    pub fn word_count(&self) -> usize {
        self.markdown.split_whitespace().count()
    }
}
```

- **`use ... as _;` (Trait Imports)**: Importing `ButtonVariants as _` and `ActiveTheme as _` brings their extension methods (`.primary()` on `Button`, `.theme()` on `cx`) into scope without polluting your namespace with the trait names themselves.
- **`#[derive(Debug, Clone, Copy, PartialEq, Eq)]`**: Attributes tell the Rust compiler to auto-generate standard capabilities (**Traits**): printing with `{:?}` (`Debug`), duplicating values (`Clone` / `Copy`), and comparing values with `==` (`PartialEq` / `Eq`).
- **`pub enum TurnRole`**: An **Enum** guarantees at compile time that a conversation turn's speaker can only be `User` or `Assistant`—never an arbitrary typo like `"assitant"`.
- **`impl TurnRole` and `match self`**: An `impl` block attaches methods to a type. In `badge_label(&self)`, `&self` is a read-only **Borrow**{{sidenote:Borrowing with `&` lets a method inspect data without taking ownership or destroying it when the method returns.}}, and `match` forces you to handle every variant of the enum.
- **`&'static str` vs. `String`**: `&'static str` is an immutable string literal baked straight into the compiled binary (`"USER"`, `"AGENT"`), whereas `String` in `ConversationTurn` is a heap-allocated, growable UTF-8 buffer owned by the struct.
- **`impl Into<String>`**: Accepting `impl Into<String>` lets callers pass either a string literal (`"Ready"`) or an owned `String`—`.into()` converts it cleanly once.

### Block 2: Workbench Document & Pure Markdown Serialization {#block-2}

```rust caption="Block 2: WorkbenchDoc struct and Markdown export helper"
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkbenchDoc {
    pub title: String,
    pub turns: Vec<ConversationTurn>,
}

impl WorkbenchDoc {
    pub fn sample_session() -> Self {
        Self {
            title: String::from("Antigravity Session: Refactor CLI Parser"),
            turns: vec![
                ConversationTurn::new(
                    TurnRole::User,
                    "Inspect `src/args.rs` and summarize why `--quiet` overrides `--verbose`.",
                ),
                ConversationTurn::new(
                    TurnRole::Assistant,
                    "In `parse_flags`, `--quiet` runs second and mutates `verbosity` to `0`.",
                ),
            ],
        }
    }

    pub fn total_words(&self) -> usize {
        self.turns.iter().map(ConversationTurn::word_count).sum()
    }

    pub fn to_markdown(&self) -> String {
        let mut out = format!("# {}\n\n", self.title);
        for turn in &self.turns {
            out.push_str(&format!(
                "## {}\n\n{}\n\n",
                turn.role.badge_label(),
                turn.markdown
            ));
        }
        out.trim_end().to_string()
    }
}
```

- **`Vec<ConversationTurn>` and `vec![...]`**: `Vec<T>` is Rust's growable heap array. Notice how we separate pure domain logic (`WorkbenchDoc::to_markdown`, `total_words`) from GPUI rendering—this makes core conversation logic testable in milliseconds without opening a window.
- **Iterators (`.iter().map(...).sum()`)**: `.iter()` borrows each `ConversationTurn` in `self.turns` without moving or copying the `Vec`, `.map(...)` transforms each borrowed turn into its `usize` word count, and `.sum()` totals them with zero heap allocations.
- **`let mut out`**: Variables in Rust are immutable by default. Writing `mut` explicitly opts into mutating `out` via `out.push_str(...)`.
- **`for turn in &self.turns`**: Iterating over `&self.turns` borrows the vector rather than consuming `self.turns`—if you omitted `&`, the loop would consume `self.turns` and the compiler would reject moving out of `&self`.

### Block 3: The `WorkbenchView` & `Render` Trait {#block-3}

```rust caption="Block 3: View struct and declarative Render implementation"
pub struct WorkbenchView {
    pub doc: WorkbenchDoc,
}

impl WorkbenchView {
    pub fn new() -> Self {
        Self {
            doc: WorkbenchDoc::sample_session(),
        }
    }
}

impl Default for WorkbenchView {
    fn default() -> Self {
        Self::new()
    }
}

impl Render for WorkbenchView {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let theme = cx.theme();
        let summary = format!(
            "{} ({} turns, {} words)",
            self.doc.title,
            self.doc.turns.len(),
            self.doc.total_words()
        );
        let markdown_preview = self.doc.to_markdown();

        div()
            .flex()
            .flex_col()
            .size_full()
            .p_6()
            .gap_4()
            .bg(theme.background)
            .text_color(theme.foreground)
            .child(
                div()
                    .flex()
                    .items_center()
                    .justify_between()
                    .child("Antigravity Markdown & Conversation Workbench")
                    .child(
                        Button::new("export-md")
                            .primary()
                            .label("Print Markdown")
                            .on_click(move |_, _, _| {
                                println!("{markdown_preview}");
                            }),
                    ),
            )
            .child(div().text_color(theme.muted_foreground).child(summary))
    }
}
```

- **`impl Render for WorkbenchView`**: Implementing the **`Render` Trait** plugs your **Struct** into GPUI's layout and GPU paint pipeline. Whenever state changes, GPUI calls `render(&mut self, window, cx)`.
- **`&mut self` and `cx: &mut Context<Self>`**: Unlike `&self`, `&mut self` grants an exclusive mutable borrow to `WorkbenchView`. Meanwhile, **`Context`** (`cx`) lets you read `cx.theme()` (installed by `gpui_kit::init`), spawn tasks, or notify GPUI to re-render.
- **`impl IntoElement`**: Tells the caller "this returns *some* concrete UI element tree type that GPUI knows how to lay out and draw," saving you from writing out deeply nested generic types by hand.
- **Fluent Flexbox Builders (`div().flex()...`)**: GPUI styles elements with Tailwind-inspired chained builders (`.flex_col()`, `.size_full()`, `.p_6()`, `.gap_4()`, `.bg(...)`).
- **`move |_, _, _| { ... }` (Move Closure)**: The `on_click` callback may outlive the `render` stack frame because clicks happen later! Adding `move` tells Rust to move ownership of `markdown_preview` into the closure instead of keeping a temporary reference that would dangle after `render` returns.

### Block 4: Application Entrypoint & `Root` Window Bootstrap {#block-4}

```rust caption="Block 4: Initializing GPUI Kit and opening the Root-managed window"
fn main() {
    gpui_kit::application()
        .with_assets(gpui_kit::assets::Assets)
        .run(|cx| {
            gpui_kit::init(cx);
            gpui_kit::open_window(WindowOptions::default(), cx, |_, cx| {
                cx.new(|_| WorkbenchView::new())
            })
            .expect("failed to open workbench window");
        });
}
```

- **`gpui_kit::application().with_assets(gpui_kit::assets::Assets)`**: Constructs the platform application and attaches GPUI Kit's bundled icon assets.
- **`.run(|cx| { ... })`**: Starts the native OS event loop and passes a mutable borrow `cx: &mut App` into your startup closure.
- **`gpui_kit::init(cx)`**: Initializes themes, input keybindings, and component registries across `gpui-base` and `gpui-component`. Calling `open_window` before `init(cx)` would leave components un-themed!
- **`cx.new(|_| WorkbenchView::new())`**: Allocates `WorkbenchView` inside GPUI's entity arena and returns an **`Entity`** (`Entity<WorkbenchView>`), which `gpui_kit::open_window` automatically places inside a `Root` view.
- **`.expect("failed to open workbench window")`**: `open_window` returns a `Result`. Calling `.expect(...)` unwraps the window handle on success or exits immediately with a clear error message if the OS fails to create a window.

### Block 5: Inline Unit Tests {#block-5}

```rust caption="Block 5: Automated unit tests living directly inside src/main.rs"
#[cfg(test)]
mod tests {
    use super::{ConversationTurn, TurnRole, WorkbenchDoc, WorkbenchView};

    #[test]
    fn turn_word_count_handles_markdown_tokens() {
        let user_turn = ConversationTurn::new(TurnRole::User, "Hello **GPUI** world");
        let agent_turn = ConversationTurn::new(TurnRole::Assistant, "Ready");

        assert_eq!(user_turn.role.badge_label(), "USER");
        assert_eq!(agent_turn.role.badge_label(), "AGENT");
        assert_eq!(user_turn.word_count(), 3);
        assert_eq!(agent_turn.word_count(), 1);
    }

    #[test]
    fn sample_session_exports_structured_markdown() {
        let doc = WorkbenchDoc::sample_session();
        let md = doc.to_markdown();

        assert_eq!(doc.turns.len(), 2);
        assert_eq!(doc.total_words(), 18);
        assert!(md.starts_with("# Antigravity Session: Refactor CLI Parser"));
        assert!(md.contains("## USER\n\nInspect `src/args.rs`"));
        assert!(md.contains("## AGENT\n\nIn `parse_flags`"));
    }

    #[test]
    fn workbench_view_initializes_with_sample_doc() {
        let view = WorkbenchView::new();

        assert_eq!(view.doc, WorkbenchDoc::sample_session());
        assert_eq!(view.doc.turns.len(), 2);
    }
}
```

- **`#[cfg(test)] mod tests`**: Conditional compilation tells `cargo build` to strip the `tests` submodule out of your release binary while compiling and executing it during `cargo test`.
- **`use super::{...};` (Explicit Test Imports)**: Instead of `use super::*;`, we import only our own four symbols into `tests`. Why? Because `gpui_kit::*` exports GPUI's async UI test macro `#[gpui_kit::test]`—pulling it in via a wildcard `*` would collide with Rust's standard `#[test]` attribute!{{sidenote:We will intentionally use `#[gpui_kit::test]` in a later lesson when we run headless window integration tests with `TestAppContext`.}}
- **`assert_eq!` and `assert!`**: Standard test macros (notice the trailing `!` denoting a Rust macro) that fail the test with a crisp diff whenever an invariant breaks.

## Step 3: Complete `src/main.rs` Listing

Here is the entire `src/main.rs` file in context so you can inspect how all five blocks fit together cleanly:

```rust caption="Complete src/main.rs for Lesson 0001"
use gpui_kit::component::ActiveTheme as _;
use gpui_kit::component::button::{Button, ButtonVariants as _};
use gpui_kit::*;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TurnRole {
    User,
    Assistant,
}

impl TurnRole {
    pub fn badge_label(&self) -> &'static str {
        match self {
            TurnRole::User => "USER",
            TurnRole::Assistant => "AGENT",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConversationTurn {
    pub role: TurnRole,
    pub markdown: String,
}

impl ConversationTurn {
    pub fn new(role: TurnRole, markdown: impl Into<String>) -> Self {
        Self {
            role,
            markdown: markdown.into(),
        }
    }

    pub fn word_count(&self) -> usize {
        self.markdown.split_whitespace().count()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkbenchDoc {
    pub title: String,
    pub turns: Vec<ConversationTurn>,
}

impl WorkbenchDoc {
    pub fn sample_session() -> Self {
        Self {
            title: String::from("Antigravity Session: Refactor CLI Parser"),
            turns: vec![
                ConversationTurn::new(
                    TurnRole::User,
                    "Inspect `src/args.rs` and summarize why `--quiet` overrides `--verbose`.",
                ),
                ConversationTurn::new(
                    TurnRole::Assistant,
                    "In `parse_flags`, `--quiet` runs second and mutates `verbosity` to `0`.",
                ),
            ],
        }
    }

    pub fn total_words(&self) -> usize {
        self.turns.iter().map(ConversationTurn::word_count).sum()
    }

    pub fn to_markdown(&self) -> String {
        let mut out = format!("# {}\n\n", self.title);
        for turn in &self.turns {
            out.push_str(&format!(
                "## {}\n\n{}\n\n",
                turn.role.badge_label(),
                turn.markdown
            ));
        }
        out.trim_end().to_string()
    }
}

pub struct WorkbenchView {
    pub doc: WorkbenchDoc,
}

impl WorkbenchView {
    pub fn new() -> Self {
        Self {
            doc: WorkbenchDoc::sample_session(),
        }
    }
}

impl Default for WorkbenchView {
    fn default() -> Self {
        Self::new()
    }
}

impl Render for WorkbenchView {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let theme = cx.theme();
        let summary = format!(
            "{} ({} turns, {} words)",
            self.doc.title,
            self.doc.turns.len(),
            self.doc.total_words()
        );
        let markdown_preview = self.doc.to_markdown();

        div()
            .flex()
            .flex_col()
            .size_full()
            .p_6()
            .gap_4()
            .bg(theme.background)
            .text_color(theme.foreground)
            .child(
                div()
                    .flex()
                    .items_center()
                    .justify_between()
                    .child("Antigravity Markdown & Conversation Workbench")
                    .child(
                        Button::new("export-md")
                            .primary()
                            .label("Print Markdown")
                            .on_click(move |_, _, _| {
                                println!("{markdown_preview}");
                            }),
                    ),
            )
            .child(div().text_color(theme.muted_foreground).child(summary))
    }
}

fn main() {
    gpui_kit::application()
        .with_assets(gpui_kit::assets::Assets)
        .run(|cx| {
            gpui_kit::init(cx);
            gpui_kit::open_window(WindowOptions::default(), cx, |_, cx| {
                cx.new(|_| WorkbenchView::new())
            })
            .expect("failed to open workbench window");
        });
}

#[cfg(test)]
mod tests {
    use super::{ConversationTurn, TurnRole, WorkbenchDoc, WorkbenchView};

    #[test]
    fn turn_word_count_handles_markdown_tokens() {
        let user_turn = ConversationTurn::new(TurnRole::User, "Hello **GPUI** world");
        let agent_turn = ConversationTurn::new(TurnRole::Assistant, "Ready");

        assert_eq!(user_turn.role.badge_label(), "USER");
        assert_eq!(agent_turn.role.badge_label(), "AGENT");
        assert_eq!(user_turn.word_count(), 3);
        assert_eq!(agent_turn.word_count(), 1);
    }

    #[test]
    fn sample_session_exports_structured_markdown() {
        let doc = WorkbenchDoc::sample_session();
        let md = doc.to_markdown();

        assert_eq!(doc.turns.len(), 2);
        assert_eq!(doc.total_words(), 18);
        assert!(md.starts_with("# Antigravity Session: Refactor CLI Parser"));
        assert!(md.contains("## USER\n\nInspect `src/args.rs`"));
        assert!(md.contains("## AGENT\n\nIn `parse_flags`"));
    }

    #[test]
    fn workbench_view_initializes_with_sample_doc() {
        let view = WorkbenchView::new();

        assert_eq!(view.doc, WorkbenchDoc::sample_session());
        assert_eq!(view.doc.turns.len(), 2);
    }
}
```

## Skill Practice & Retrieval

:::exercise id="ex-0001" title="Interactive Lab: Wire the Bootstrap Window" badge="Skill Practice • Tight Feedback Loop"
Fill in the four missing tokens to initialize GPUI Kit, open a `Root`-wrapped window with a new `WorkbenchView` entity, and style the primary button.

```rust
fn main() {
    gpui_kit::application().run(|cx| {
        {{blank:gpui_kit::init(cx);|Initialize GPUI Kit layers first using init(cx);|gpui_kit::init(...);|20}}
        {{blank:gpui_kit::open_window|Use the gpui_kit wrapper that installs Root automatically|gpui_kit::open_???|20}}(WindowOptions::default(), cx, |_, cx| {
            {{blank:cx.new|Allocate the view in GPUI's entity store via cx.new|cx.???|7}}(|_| WorkbenchView::new())
        })
        .expect("failed to open workbench window");
    });
}

fn action_button() -> Button {
    Button::new("export-md").{{blank:primary|Import ButtonVariants as _ to call .primary()|style|8}}().label("Print Markdown")
}
```

:::prompts
hint: "Double-check the startup call order: init(cx) comes before open_window, and cx.new(...) returns an Entity<WorkbenchView>."
success: "Spot on! You initialized GPUI Kit, opened a Root-managed window, allocated an Entity<WorkbenchView>, and applied ButtonVariants::primary."
:::
:::

:::quiz id="quiz-0001" title="Retrieval Practice: GPUI Kit & Rust Foundations" badge="3 Questions • Equal-Length Options"
- question: "Why must gpui_kit::init(cx) run inside application().run(...) before opening a window?"
  wrong_hint: "Think about what themes and component registries need before Render runs."
  options:
    - letter: "A"
      text: "It compiles shader pipelines into native binary files inside target folders."
      correct: false
      explain: "Cargo compiles shaders or Rust crates ahead of time, not inside init(cx)."
    - letter: "B"
      text: "It initializes global themes, styles, and base registries before components render."
      correct: true
      explain: "Correct! init(cx) populates GPUI Kit's themes, keybindings, and component registries before any window opens."
    - letter: "C"
      text: "It spawns background worker threads for running external Go agent harnesses."
      correct: false
      explain: "init(cx) configures GPUI Kit layers synchronously on the UI thread."
    - letter: "D"
      text: "It downloads missing Rust crates directly from crates.io during window startup."
      correct: false
      explain: "Cargo resolves crates at build time, never at runtime inside init(cx)."
- question: "What does gpui_kit::open_window automatically wrap around your view so dialogs and notifications work?"
  wrong_hint: "Check Figure 1.1 and the Root View definition in the Glossary."
  options:
    - letter: "A"
      text: "A mutable Rust vector storing every keyboard shortcut for macOS."
      correct: false
      explain: "Shortcuts are registered in GPUI's keymap, not wrapped around your view."
    - letter: "B"
      text: "A standard Cargo manifest mapping each Markdown file onto disk."
      correct: false
      explain: "Cargo.toml is a build manifest, not a runtime GPUI container."
    - letter: "C"
      text: "The Root view container hosting window overlays, sheets, and menus."
      correct: true
      explain: "Correct! Root sits at the top of the window tree to host overlays, dialogs, sheets, and notifications."
    - letter: "D"
      text: "An async Tokio runtime polling local files on every frame."
      correct: false
      explain: "GPUI runs its own platform event loop and never injects Tokio into windows."
- question: "In fn render(&mut self, ...), what does &mut self tell the Rust compiler?"
  wrong_hint: "Review Borrowing (&T and &mut T) in the Glossary."
  options:
    - letter: "A"
      text: "The method destroys the struct immediately after returning one element."
      correct: false
      explain: "Moving self (by value) consumes a struct; &mut self only borrows it temporarily."
    - letter: "B"
      text: "The method spawns another thread to clone every owned string."
      correct: false
      explain: "Borrow modifiers control ownership and mutability, not thread spawning."
    - letter: "C"
      text: "The method only reads immutable fields without altering view state."
      correct: false
      explain: "Read-only borrowing uses &self without mut."
    - letter: "D"
      text: "The method holds an exclusive mutable borrow to the struct."
      correct: true
      explain: "Correct! &mut self gives render temporary, exclusive mutable access without transferring ownership."
:::

## Verification Lab

:::verify id="verify-0001" title="Verification Lab: Test, Strict Clippy & Window Launch" badge="Terminal Gate"
Run the unit tests and strict linter from the repository root to verify `apps/0001-bootstrap-workbench-shell` compiles cleanly with zero warnings:

```bash caption="Verified Cargo format, test, and clippy commands"
cargo fmt --manifest-path apps/0001-bootstrap-workbench-shell/Cargo.toml --check
cargo test --manifest-path apps/0001-bootstrap-workbench-shell/Cargo.toml
cargo clippy --manifest-path apps/0001-bootstrap-workbench-shell/Cargo.toml --all-targets -- -D warnings
```

Verified output from running the suite above:

```text caption="Verified test & clippy output"
running 3 tests
test tests::workbench_view_initializes_with_sample_doc ... ok
test tests::turn_word_count_handles_markdown_tokens ... ok
test tests::sample_session_exports_structured_markdown ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

    Checking antigravity-workbench v0.1.0 (/Users/brett/Documents/GitHub/gpuikit-tutorial/apps/0001-bootstrap-workbench-shell)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.39s
```

To launch the live macOS window and click **Print Markdown**, run:

```bash caption="Launch the desktop workbench shell"
cargo run --manifest-path apps/0001-bootstrap-workbench-shell/Cargo.toml
```

- [ ] Run `cargo test` and observe `3 passed; 0 failed`.
- [ ] Run `cargo clippy --all-targets -- -D warnings` and observe exit code `0` with zero warnings.
- [ ] Run `cargo run`, verify the dark-themed **Antigravity Markdown & Conversation Workbench** window opens, and click **Print Markdown** to see the `# Antigravity Session` Markdown printed in your terminal.
:::

:::teacher-prompt title="Ask Follow-Up Questions"
Before we move on to Lesson 0002 (making the workbench interactive with `cx.notify()` and turn selection), ask any questions about:
- How `String` vs. `&str`, `Vec<T>`, or `move` closures work in Rust.
- Why GPUI hands out `Entity<WorkbenchView>` handles instead of raw Rust references.
- How `WorkbenchDoc` will map onto `antigravity-sdk-rust` conversation turns in later lessons.
:::
