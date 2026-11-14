---
title: "Single-Line Inputs, Child Entities & Subscriptions"
page_title: "Lesson 0004: Single-Line Inputs, Child Entities & Subscriptions — GPUI Kit Course"
nav_id: "lesson-0004"
badge: "Lesson 0004 • Entity<InputState> & Subscriptions"
subtitle: "Edit session titles and filter conversation turns live using Input, InputState, Option<Entity<T>>, and cx.subscribe_in."
card:
  title: "**Single-Line Inputs, Child Entities & Subscriptions**"
  summary: "Separate stateful child InputState entities from lightweight Input elements, and react to keystrokes via Subscription handles."
---

Every agentic coding workbench lets you rename sessions and filter long transcripts on the fly. Unlike stateless buttons, a text field has to track cursor offsets, text selections, IME composition, and focus across hundreds of rendered frames. GPUI Kit solves this cleanly with the **State-vs-Element Split**: you allocate a long-lived `Entity<InputState>` once during setup, subscribe to its `InputEvent` stream, and render a cheap `Input::new(&entity)` wrapper every frame.

:::callout title="Recommended Primary Sources"
- [GPUI Kit `Input` & `InputState` Reference](https://docs.rs/gpui-kit/latest/gpui_kit/component/input/index.html) — `InputState`, `Input::new`, `.cleanable(true)`, and `InputEvent::Change`.
- [The Rust Book: Iterators & Closures](https://doc.rust-lang.org/book/ch13-02-iterators.html) — `.filter()`, `.filter_map()`, and `.collect::<Vec<_>>()`.
- Course References: [Glossary](../reference/GLOSSARY.md) and [GPUI Kit & Rust Quick Reference](../reference/gpui-kit-cheatsheet.md).
:::

## The State-vs-Element Split & Subscriptions

Why not pass `&mut String` directly into `Input`? Because text fields handle blinking carets, clipboard selection, and undo history internally. Creating an `Entity<InputState>` lets `gpui-base` manage that editing engine inside GPUI's entity store while notifying `WorkbenchView` whenever text changes:

```mermaid caption="Figure 4.1: Parent view subscribing to child InputState entities"
flowchart LR
    View["WorkbenchView (Parent Entity)"] -- "cx.new(|cx| InputState::new(...))" --> Title["Entity&lt;InputState&gt; (title_input)"]
    View -- "cx.new(|cx| InputState::new(...))" --> Filter["Entity&lt;InputState&gt; (filter_input)"]
    Title -- "InputEvent::Change" --> Sub["Subscription in _subscriptions"]
    Filter -- "InputEvent::Change" --> Sub
    Sub -- "this.doc.set_title / this.filter_query" --> Notify["cx.notify() -> Render"]
    Title -. "Input::new(input)" .-> Render["Render::render(...)"]
    Filter -. "Input::new(input).cleanable(true)" .-> Render
```

Notice the **`Subscription`** field `_subscriptions: Vec<Subscription>`{{sidenote:In Rust, dropping a `Subscription` cancels the listener (an idiomatic **RAII** resource guard). Storing `Subscription` values inside `WorkbenchView` keeps listeners active for the exact lifetime of the view and automatically tears them down if the window closes.}}.

## Step 1: Verify `apps/0004-single-line-inputs-and-titles/Cargo.toml`

Clone Lesson 0003 into `apps/0004-single-line-inputs-and-titles`—`Cargo.toml` continues using `gpui-kit = "0.9.1"`:

```toml caption="apps/0004-single-line-inputs-and-titles/Cargo.toml"
[package]
name = "antigravity-workbench"
version = "0.1.0"
edition = "2024"

[dependencies]
gpui-kit = "0.9.1"
```

## Step 2: Build the Application Block by Block

### Block 1: Imports, Session Renaming & Filter Query Pipeline {#block-1}

```rust caption="Block 1: Importing Input widgets and filtering turns in WorkbenchDoc"
use gpui_kit::component::ActiveTheme as _;
use gpui_kit::component::Disableable as _;
use gpui_kit::component::Selectable as _;
use gpui_kit::component::badge::Badge;
use gpui_kit::component::button::{Button, ButtonVariants as _};
use gpui_kit::component::input::{Input, InputEvent, InputState};
use gpui_kit::component::tag::Tag;
use gpui_kit::component::{h_flex, v_flex};
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

    pub fn preview_line(&self) -> &str {
        self.markdown.lines().next().unwrap_or("")
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
                ConversationTurn::new(
                    TurnRole::User,
                    "Draft a regression test checking flag order independence.",
                ),
            ],
        }
    }

    pub fn set_title(&mut self, title: impl Into<String>) {
        let trimmed = title.into();
        if !trimmed.trim().is_empty() {
            self.title = trimmed;
        }
    }

    pub fn filtered_turn_indices(&self, query: &str) -> Vec<usize> {
        let needle = query.trim().to_lowercase();
        self.turns
            .iter()
            .enumerate()
            .filter(|(_, turn)| {
                needle.is_empty()
                    || turn.markdown.to_lowercase().contains(&needle)
                    || turn.role.badge_label().to_lowercase().contains(&needle)
            })
            .map(|(ix, _)| ix)
            .collect()
    }

    pub fn turn_at(&self, index: usize) -> Option<&ConversationTurn> {
        self.turns.get(index)
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

- **`.filter(...).map(...).collect()`**: Returning `Vec<usize>` (original turn indices rather than copied `ConversationTurn` values) preserves true turn numbers (`#2`) even while filtered and avoids cloning turn strings.
- **Short-Circuit Boolean `||`**: When `needle.is_empty()` is `true`, Rust skips both `.to_lowercase()` allocations per turn!

### Block 2: Allocating `Entity<InputState>` and Subscribing with `cx.subscribe_in` {#block-2}

```rust caption="Block 2: Window-free new() plus new_with_window(window, cx)"
pub struct WorkbenchView {
    pub doc: WorkbenchDoc,
    pub active_turn: usize,
    pub filter_query: String,
    pub title_input: Option<Entity<InputState>>,
    pub filter_input: Option<Entity<InputState>>,
    _subscriptions: Vec<Subscription>,
}

impl WorkbenchView {
    pub fn new() -> Self {
        Self {
            doc: WorkbenchDoc::sample_session(),
            active_turn: 0,
            filter_query: String::new(),
            title_input: None,
            filter_input: None,
            _subscriptions: Vec::new(),
        }
    }

    pub fn new_with_window(window: &mut Window, cx: &mut Context<Self>) -> Self {
        let mut view = Self::new();
        let initial_title = view.doc.title.clone();

        let title_input = cx.new(|cx| {
            InputState::new(window, cx)
                .placeholder("Session title...")
                .default_value(initial_title)
        });
        let filter_input = cx.new(|cx| {
            InputState::new(window, cx)
                .clean_on_escape()
                .placeholder("Filter turns by text or role (USER / AGENT)...")
        });

        let title_sub = cx.subscribe_in(
            &title_input,
            window,
            |this, state, event: &InputEvent, _window, cx| {
                if matches!(event, InputEvent::Change) {
                    let next_title = state.read(cx).value().to_string();
                    this.doc.set_title(next_title);
                    cx.notify();
                }
            },
        );

        let filter_sub = cx.subscribe_in(
            &filter_input,
            window,
            |this, state, event: &InputEvent, _window, cx| {
                if matches!(event, InputEvent::Change) {
                    this.filter_query = state.read(cx).value().to_string();
                    cx.notify();
                }
            },
        );

        view.title_input = Some(title_input);
        view.filter_input = Some(filter_input);
        view._subscriptions.push(title_sub);
        view._subscriptions.push(filter_sub);
        view
    }

    pub fn select_turn(&mut self, index: usize) -> bool {
        if index < self.doc.turns.len() {
            self.active_turn = index;
            true
        } else {
            false
        }
    }

    pub fn select_next_turn(&mut self) {
        if self.active_turn + 1 < self.doc.turns.len() {
            self.active_turn += 1;
        }
    }

    pub fn select_prev_turn(&mut self) {
        self.active_turn = self.active_turn.saturating_sub(1);
    }

    pub fn append_turn(&mut self, role: TurnRole, markdown: impl Into<String>) -> usize {
        self.doc.turns.push(ConversationTurn::new(role, markdown));
        let new_index = self.doc.turns.len() - 1;
        self.active_turn = new_index;
        new_index
    }

    pub fn remove_active_turn(&mut self) -> Option<ConversationTurn> {
        if self.doc.turns.len() <= 1 || self.active_turn >= self.doc.turns.len() {
            return None;
        }
        let removed = self.doc.turns.remove(self.active_turn);
        if self.active_turn >= self.doc.turns.len() {
            self.active_turn = self.doc.turns.len() - 1;
        }
        Some(removed)
    }

    pub fn active_turn_ref(&self) -> Option<&ConversationTurn> {
        self.doc.turn_at(self.active_turn)
    }
}

impl Default for WorkbenchView {
    fn default() -> Self {
        Self::new()
    }
}
```

- **Two Constructors (`new()` + `new_with_window()`)**: Wrapping child entity fields in `Option<Entity<InputState>>` lets fast `#[test]` cases construct `WorkbenchView::new()` without an OS `Window`, while the live app calls `WorkbenchView::new_with_window(window, cx)`.
- **`InputState::new(window, cx).clean_on_escape()`**: Chained builder methods configure initial text, placeholder copy, and Escape-to-clear behavior before `cx.new` stores the `InputState`.
- **`cx.subscribe_in(&entity, window, |this, state, event: &InputEvent, _window, cx| ...)`**: Listens specifically to `InputEvent::Change` emitted by the child `Entity<InputState>`, reads its buffer via `state.read(cx).value()`, updates `WorkbenchView`, and calls `cx.notify()`.
- **`matches!(event, InputEvent::Change)`**: A concise Rust macro that tests an enum variant without needing a verbose `match` with empty wildcard arms.

### Block 3: Rendering `Input::new(&state)` and Filtered Cards {#block-3}

```rust caption="Block 3: Placing Input bars above the filtered turn list"
impl Render for WorkbenchView {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let theme = cx.theme();
        let visible_indices = self.doc.filtered_turn_indices(&self.filter_query);
        let summary = format!(
            "{} ({} / {} visible, {} words) — Selected #{}",
            self.doc.title,
            visible_indices.len(),
            self.doc.turns.len(),
            self.doc.total_words(),
            self.active_turn + 1
        );
        let markdown_preview = self.doc.to_markdown();
        let can_delete = self.doc.turns.len() > 1;
        let selected_body = match self.active_turn_ref() {
            Some(turn) => format!("[{}] {}", turn.role.badge_label(), turn.markdown),
            None => String::from("No turn selected"),
        };

        v_flex()
            .size_full()
            .p_6()
            .gap_4()
            .bg(theme.background)
            .text_color(theme.foreground)
            .child(
                h_flex()
                    .items_center()
                    .justify_between()
                    .child(
                        h_flex()
                            .items_center()
                            .gap_3()
                            .child("Antigravity Markdown & Conversation Workbench")
                            .child(
                                Badge::new()
                                    .count(visible_indices.len())
                                    .child(div().px_2().py_1().child("Visible")),
                            ),
                    )
                    .child(
                        h_flex()
                            .gap_2()
                            .child(Button::new("prev-turn").secondary().label("Prev").on_click(
                                cx.listener(|this, _, _, cx| {
                                    this.select_prev_turn();
                                    cx.notify();
                                }),
                            ))
                            .child(Button::new("next-turn").secondary().label("Next").on_click(
                                cx.listener(|this, _, _, cx| {
                                    this.select_next_turn();
                                    cx.notify();
                                }),
                            ))
                            .child(
                                Button::new("add-user-turn")
                                    .secondary()
                                    .label("+ User Turn")
                                    .on_click(cx.listener(|this, _, _, cx| {
                                        this.append_turn(
                                            TurnRole::User,
                                            "Follow-up question about CLI flag precedence.",
                                        );
                                        cx.notify();
                                    })),
                            )
                            .child(
                                Button::new("add-agent-turn")
                                    .secondary()
                                    .label("+ Agent Turn")
                                    .on_click(cx.listener(|this, _, _, cx| {
                                        this.append_turn(
                                            TurnRole::Assistant,
                                            "Proposed patch keeps the last flag explicit.",
                                        );
                                        cx.notify();
                                    })),
                            )
                            .child(
                                Button::new("delete-turn")
                                    .danger()
                                    .label("Delete Turn")
                                    .disabled(!can_delete)
                                    .on_click(cx.listener(|this, _, _, cx| {
                                        this.remove_active_turn();
                                        cx.notify();
                                    })),
                            )
                            .child(
                                Button::new("export-md")
                                    .primary()
                                    .label("Print Markdown")
                                    .on_click(move |_, _, _| {
                                        println!("{markdown_preview}");
                                    }),
                            ),
                    ),
            )
            .child(
                h_flex()
                    .gap_3()
                    .children(
                        self.title_input
                            .as_ref()
                            .map(|input| div().flex_1().child(Input::new(input))),
                    )
                    .children(
                        self.filter_input.as_ref().map(|input| {
                            div().w(px(320.)).child(Input::new(input).cleanable(true))
                        }),
                    ),
            )
            .child(div().text_color(theme.muted_foreground).child(summary))
            .child(
                v_flex()
                    .gap_2()
                    .children(visible_indices.into_iter().filter_map(|ix| {
                        let turn = self.doc.turn_at(ix)?;
                        let is_active = ix == self.active_turn;
                        let role_tag = match turn.role {
                            TurnRole::User => Tag::primary().child("USER"),
                            TurnRole::Assistant => Tag::secondary().child("AGENT"),
                        };
                        let border_color = if is_active {
                            theme.primary
                        } else {
                            theme.border
                        };

                        Some(
                            h_flex()
                                .p_3()
                                .gap_3()
                                .items_center()
                                .justify_between()
                                .rounded_md()
                                .border_1()
                                .border_color(border_color)
                                .bg(theme.secondary)
                                .child(
                                    h_flex()
                                        .gap_3()
                                        .items_center()
                                        .child(role_tag)
                                        .child(format!("#{} — {}", ix + 1, turn.preview_line())),
                                )
                                .child(
                                    Button::new(("select-turn", ix))
                                        .ghost()
                                        .selected(is_active)
                                        .label(if is_active { "Selected" } else { "Inspect" })
                                        .on_click(cx.listener(move |this, _, _, cx| {
                                            this.select_turn(ix);
                                            cx.notify();
                                        })),
                                ),
                        )
                    })),
            )
            .child(
                v_flex()
                    .p_4()
                    .gap_2()
                    .rounded_md()
                    .border_1()
                    .border_color(theme.border)
                    .bg(theme.background)
                    .child(
                        div()
                            .text_sm()
                            .text_color(theme.muted_foreground)
                            .child("Active Turn Inspector"),
                    )
                    .child(selected_body),
            )
    }
}
```

- **`self.title_input.as_ref().map(|input| ...)`**: Notice `.as_ref()` converts `&Option<Entity<InputState>>` into `Option<&Entity<InputState>>` so `Input::new(input)` borrows the `Entity` handle without moving it out of `self`!
- **`Option::into_iter()` via `.children(...)`**: `Option<T>` implements `IntoIterator` (0 items for `None`, 1 item for `Some(T)`), making optional UI controls effortless.
- **The `?` Operator inside `filter_map`**: Inside `.filter_map(|ix| { let turn = self.doc.turn_at(ix)?; ... Some(...) })`, `?` returns `None` early if an index were ever invalid.

### Block 4: Entrypoint & Filter Unit Tests {#block-4}

```rust caption="Block 4: Opening with window handle and verifying filtering logic"
fn main() {
    gpui_kit::application()
        .with_assets(gpui_kit::assets::Assets)
        .run(|cx| {
            gpui_kit::init(cx);
            gpui_kit::open_window(WindowOptions::default(), cx, |window, cx| {
                cx.new(|cx| WorkbenchView::new_with_window(window, cx))
            })
            .expect("failed to open workbench window");
        });
}

#[cfg(test)]
mod tests {
    use super::{TurnRole, WorkbenchDoc, WorkbenchView};

    #[test]
    fn set_title_ignores_blank_input() {
        let mut doc = WorkbenchDoc::sample_session();
        doc.set_title("   ");
        assert_eq!(doc.title, "Antigravity Session: Refactor CLI Parser");

        doc.set_title("Updated Session Title");
        assert_eq!(doc.title, "Updated Session Title");
    }

    #[test]
    fn filtered_turn_indices_matches_text_and_role_case_insensitively() {
        let doc = WorkbenchDoc::sample_session();

        assert_eq!(doc.filtered_turn_indices(""), vec![0, 1, 2]);
        assert_eq!(doc.filtered_turn_indices("agent"), vec![1]);
        assert_eq!(doc.filtered_turn_indices("USER"), vec![0, 2]);
        assert_eq!(doc.filtered_turn_indices("parse_flags"), vec![1]);
        assert!(doc.filtered_turn_indices("nonexistent-token").is_empty());
    }

    #[test]
    fn append_and_remove_update_filtered_results() {
        let mut view = WorkbenchView::new();
        let added = view.append_turn(TurnRole::Assistant, "Cargo test passed");

        assert_eq!(added, 3);
        assert_eq!(view.doc.filtered_turn_indices("cargo test"), vec![3]);

        assert!(view.remove_active_turn().is_some());
        assert!(view.doc.filtered_turn_indices("cargo test").is_empty());
    }

    #[test]
    fn select_turn_respects_bounds() {
        let mut view = WorkbenchView::new();
        assert!(view.select_turn(1));
        assert!(!view.select_turn(42));
        assert_eq!(view.active_turn, 1);
    }

    #[test]
    fn default_view_starts_without_window_inputs() {
        let view = WorkbenchView::new();
        assert!(view.title_input.is_none());
        assert!(view.filter_input.is_none());
        assert!(view.filter_query.is_empty());
    }
}
```

- **`|window, cx|` in `open_window`**: Notice we switched from `|_, cx|` in Lesson 0003 to `|window, cx|` because `InputState::new(window, cx)` needs `&mut Window` for focus handles and platform IME integration.

## Step 3: Complete `src/main.rs` Listing

```rust caption="Complete src/main.rs for Lesson 0004"
use gpui_kit::component::ActiveTheme as _;
use gpui_kit::component::Disableable as _;
use gpui_kit::component::Selectable as _;
use gpui_kit::component::badge::Badge;
use gpui_kit::component::button::{Button, ButtonVariants as _};
use gpui_kit::component::input::{Input, InputEvent, InputState};
use gpui_kit::component::tag::Tag;
use gpui_kit::component::{h_flex, v_flex};
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

    pub fn preview_line(&self) -> &str {
        self.markdown.lines().next().unwrap_or("")
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
                ConversationTurn::new(
                    TurnRole::User,
                    "Draft a regression test checking flag order independence.",
                ),
            ],
        }
    }

    pub fn set_title(&mut self, title: impl Into<String>) {
        let trimmed = title.into();
        if !trimmed.trim().is_empty() {
            self.title = trimmed;
        }
    }

    pub fn filtered_turn_indices(&self, query: &str) -> Vec<usize> {
        let needle = query.trim().to_lowercase();
        self.turns
            .iter()
            .enumerate()
            .filter(|(_, turn)| {
                needle.is_empty()
                    || turn.markdown.to_lowercase().contains(&needle)
                    || turn.role.badge_label().to_lowercase().contains(&needle)
            })
            .map(|(ix, _)| ix)
            .collect()
    }

    pub fn turn_at(&self, index: usize) -> Option<&ConversationTurn> {
        self.turns.get(index)
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
    pub active_turn: usize,
    pub filter_query: String,
    pub title_input: Option<Entity<InputState>>,
    pub filter_input: Option<Entity<InputState>>,
    _subscriptions: Vec<Subscription>,
}

impl WorkbenchView {
    pub fn new() -> Self {
        Self {
            doc: WorkbenchDoc::sample_session(),
            active_turn: 0,
            filter_query: String::new(),
            title_input: None,
            filter_input: None,
            _subscriptions: Vec::new(),
        }
    }

    pub fn new_with_window(window: &mut Window, cx: &mut Context<Self>) -> Self {
        let mut view = Self::new();
        let initial_title = view.doc.title.clone();

        let title_input = cx.new(|cx| {
            InputState::new(window, cx)
                .placeholder("Session title...")
                .default_value(initial_title)
        });
        let filter_input = cx.new(|cx| {
            InputState::new(window, cx)
                .clean_on_escape()
                .placeholder("Filter turns by text or role (USER / AGENT)...")
        });

        let title_sub = cx.subscribe_in(
            &title_input,
            window,
            |this, state, event: &InputEvent, _window, cx| {
                if matches!(event, InputEvent::Change) {
                    let next_title = state.read(cx).value().to_string();
                    this.doc.set_title(next_title);
                    cx.notify();
                }
            },
        );

        let filter_sub = cx.subscribe_in(
            &filter_input,
            window,
            |this, state, event: &InputEvent, _window, cx| {
                if matches!(event, InputEvent::Change) {
                    this.filter_query = state.read(cx).value().to_string();
                    cx.notify();
                }
            },
        );

        view.title_input = Some(title_input);
        view.filter_input = Some(filter_input);
        view._subscriptions.push(title_sub);
        view._subscriptions.push(filter_sub);
        view
    }

    pub fn select_turn(&mut self, index: usize) -> bool {
        if index < self.doc.turns.len() {
            self.active_turn = index;
            true
        } else {
            false
        }
    }

    pub fn select_next_turn(&mut self) {
        if self.active_turn + 1 < self.doc.turns.len() {
            self.active_turn += 1;
        }
    }

    pub fn select_prev_turn(&mut self) {
        self.active_turn = self.active_turn.saturating_sub(1);
    }

    pub fn append_turn(&mut self, role: TurnRole, markdown: impl Into<String>) -> usize {
        self.doc.turns.push(ConversationTurn::new(role, markdown));
        let new_index = self.doc.turns.len() - 1;
        self.active_turn = new_index;
        new_index
    }

    pub fn remove_active_turn(&mut self) -> Option<ConversationTurn> {
        if self.doc.turns.len() <= 1 || self.active_turn >= self.doc.turns.len() {
            return None;
        }
        let removed = self.doc.turns.remove(self.active_turn);
        if self.active_turn >= self.doc.turns.len() {
            self.active_turn = self.doc.turns.len() - 1;
        }
        Some(removed)
    }

    pub fn active_turn_ref(&self) -> Option<&ConversationTurn> {
        self.doc.turn_at(self.active_turn)
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
        let visible_indices = self.doc.filtered_turn_indices(&self.filter_query);
        let summary = format!(
            "{} ({} / {} visible, {} words) — Selected #{}",
            self.doc.title,
            visible_indices.len(),
            self.doc.turns.len(),
            self.doc.total_words(),
            self.active_turn + 1
        );
        let markdown_preview = self.doc.to_markdown();
        let can_delete = self.doc.turns.len() > 1;
        let selected_body = match self.active_turn_ref() {
            Some(turn) => format!("[{}] {}", turn.role.badge_label(), turn.markdown),
            None => String::from("No turn selected"),
        };

        v_flex()
            .size_full()
            .p_6()
            .gap_4()
            .bg(theme.background)
            .text_color(theme.foreground)
            .child(
                h_flex()
                    .items_center()
                    .justify_between()
                    .child(
                        h_flex()
                            .items_center()
                            .gap_3()
                            .child("Antigravity Markdown & Conversation Workbench")
                            .child(
                                Badge::new()
                                    .count(visible_indices.len())
                                    .child(div().px_2().py_1().child("Visible")),
                            ),
                    )
                    .child(
                        h_flex()
                            .gap_2()
                            .child(Button::new("prev-turn").secondary().label("Prev").on_click(
                                cx.listener(|this, _, _, cx| {
                                    this.select_prev_turn();
                                    cx.notify();
                                }),
                            ))
                            .child(Button::new("next-turn").secondary().label("Next").on_click(
                                cx.listener(|this, _, _, cx| {
                                    this.select_next_turn();
                                    cx.notify();
                                }),
                            ))
                            .child(
                                Button::new("add-user-turn")
                                    .secondary()
                                    .label("+ User Turn")
                                    .on_click(cx.listener(|this, _, _, cx| {
                                        this.append_turn(
                                            TurnRole::User,
                                            "Follow-up question about CLI flag precedence.",
                                        );
                                        cx.notify();
                                    })),
                            )
                            .child(
                                Button::new("add-agent-turn")
                                    .secondary()
                                    .label("+ Agent Turn")
                                    .on_click(cx.listener(|this, _, _, cx| {
                                        this.append_turn(
                                            TurnRole::Assistant,
                                            "Proposed patch keeps the last flag explicit.",
                                        );
                                        cx.notify();
                                    })),
                            )
                            .child(
                                Button::new("delete-turn")
                                    .danger()
                                    .label("Delete Turn")
                                    .disabled(!can_delete)
                                    .on_click(cx.listener(|this, _, _, cx| {
                                        this.remove_active_turn();
                                        cx.notify();
                                    })),
                            )
                            .child(
                                Button::new("export-md")
                                    .primary()
                                    .label("Print Markdown")
                                    .on_click(move |_, _, _| {
                                        println!("{markdown_preview}");
                                    }),
                            ),
                    ),
            )
            .child(
                h_flex()
                    .gap_3()
                    .children(
                        self.title_input
                            .as_ref()
                            .map(|input| div().flex_1().child(Input::new(input))),
                    )
                    .children(
                        self.filter_input.as_ref().map(|input| {
                            div().w(px(320.)).child(Input::new(input).cleanable(true))
                        }),
                    ),
            )
            .child(div().text_color(theme.muted_foreground).child(summary))
            .child(
                v_flex()
                    .gap_2()
                    .children(visible_indices.into_iter().filter_map(|ix| {
                        let turn = self.doc.turn_at(ix)?;
                        let is_active = ix == self.active_turn;
                        let role_tag = match turn.role {
                            TurnRole::User => Tag::primary().child("USER"),
                            TurnRole::Assistant => Tag::secondary().child("AGENT"),
                        };
                        let border_color = if is_active {
                            theme.primary
                        } else {
                            theme.border
                        };

                        Some(
                            h_flex()
                                .p_3()
                                .gap_3()
                                .items_center()
                                .justify_between()
                                .rounded_md()
                                .border_1()
                                .border_color(border_color)
                                .bg(theme.secondary)
                                .child(
                                    h_flex()
                                        .gap_3()
                                        .items_center()
                                        .child(role_tag)
                                        .child(format!("#{} — {}", ix + 1, turn.preview_line())),
                                )
                                .child(
                                    Button::new(("select-turn", ix))
                                        .ghost()
                                        .selected(is_active)
                                        .label(if is_active { "Selected" } else { "Inspect" })
                                        .on_click(cx.listener(move |this, _, _, cx| {
                                            this.select_turn(ix);
                                            cx.notify();
                                        })),
                                ),
                        )
                    })),
            )
            .child(
                v_flex()
                    .p_4()
                    .gap_2()
                    .rounded_md()
                    .border_1()
                    .border_color(theme.border)
                    .bg(theme.background)
                    .child(
                        div()
                            .text_sm()
                            .text_color(theme.muted_foreground)
                            .child("Active Turn Inspector"),
                    )
                    .child(selected_body),
            )
    }
}

fn main() {
    gpui_kit::application()
        .with_assets(gpui_kit::assets::Assets)
        .run(|cx| {
            gpui_kit::init(cx);
            gpui_kit::open_window(WindowOptions::default(), cx, |window, cx| {
                cx.new(|cx| WorkbenchView::new_with_window(window, cx))
            })
            .expect("failed to open workbench window");
        });
}

#[cfg(test)]
mod tests {
    use super::{TurnRole, WorkbenchDoc, WorkbenchView};

    #[test]
    fn set_title_ignores_blank_input() {
        let mut doc = WorkbenchDoc::sample_session();
        doc.set_title("   ");
        assert_eq!(doc.title, "Antigravity Session: Refactor CLI Parser");

        doc.set_title("Updated Session Title");
        assert_eq!(doc.title, "Updated Session Title");
    }

    #[test]
    fn filtered_turn_indices_matches_text_and_role_case_insensitively() {
        let doc = WorkbenchDoc::sample_session();

        assert_eq!(doc.filtered_turn_indices(""), vec![0, 1, 2]);
        assert_eq!(doc.filtered_turn_indices("agent"), vec![1]);
        assert_eq!(doc.filtered_turn_indices("USER"), vec![0, 2]);
        assert_eq!(doc.filtered_turn_indices("parse_flags"), vec![1]);
        assert!(doc.filtered_turn_indices("nonexistent-token").is_empty());
    }

    #[test]
    fn append_and_remove_update_filtered_results() {
        let mut view = WorkbenchView::new();
        let added = view.append_turn(TurnRole::Assistant, "Cargo test passed");

        assert_eq!(added, 3);
        assert_eq!(view.doc.filtered_turn_indices("cargo test"), vec![3]);

        assert!(view.remove_active_turn().is_some());
        assert!(view.doc.filtered_turn_indices("cargo test").is_empty());
    }

    #[test]
    fn select_turn_respects_bounds() {
        let mut view = WorkbenchView::new();
        assert!(view.select_turn(1));
        assert!(!view.select_turn(42));
        assert_eq!(view.active_turn, 1);
    }

    #[test]
    fn default_view_starts_without_window_inputs() {
        let view = WorkbenchView::new();
        assert!(view.title_input.is_none());
        assert!(view.filter_input.is_none());
        assert!(view.filter_query.is_empty());
    }
}
```

## Skill Practice & Retrieval

:::exercise id="ex-0004" title="Interactive Lab: Create and Subscribe to InputState" badge="Skill Practice • Tight Feedback Loop"
Complete the child `InputState` allocation, change subscription, and cleanable `Input` render wrapper below.

```rust
let filter_input = cx.new(|cx| {
    {{blank:InputState::new|Construct single-line state engine|???|15}}(window, cx)
        .clean_on_escape()
        .placeholder("Filter turns...")
});

let filter_sub = cx.{{blank:subscribe_in|Attach a listener with window access to a child entity|???|12}}(
    &filter_input,
    window,
    |this, state, event: &InputEvent, _window, cx| {
        if {{blank:matches!|Match enum variant cleanly|???|8}}(event, InputEvent::Change) {
            this.filter_query = state.read(cx).value().to_string();
            cx.notify();
        }
    },
);

let bar = div().children(self.filter_input.as_ref().map(|input| Input::new(input).{{blank:cleanable|Show built-in clear button when non-empty|???|9}}(true)));
```

:::prompts
hint: "Use InputState::new, cx.subscribe_in, matches!(event, InputEvent::Change), and .cleanable(true)."
success: "Excellent! Your view now owns child input entities and stays synchronized via Subscription."
:::
:::

:::quiz id="quiz-0004" title="Retrieval Practice: Entities, Subscriptions & Filtering" badge="3 Questions • Equal-Length Options"
- question: "Why does WorkbenchView store the handles returned by cx.subscribe_in inside _subscriptions?"
  wrong_hint: "Think about what Rust drops at the end of new_with_window if a value is not moved into the struct."
  options:
    - letter: "A"
      text: "Keeping Subscription values alive prevents GPUI from unregistering event listeners."
      correct: true
      explain: "Correct! Dropping a Subscription cancels the subscription automatically via RAII, so storing it keeps events flowing."
    - letter: "B"
      text: "Underscored fields export all keyboard shortcuts to macOS system settings."
      correct: false
      explain: "A leading underscore only suppresses unused-field warnings for fields kept alive for Drop semantics."
    - letter: "C"
      text: "Subscriptions copy every user keystroke automatically onto local JSON files."
      correct: false
      explain: "Subscriptions notify in-memory GPUI observers; disk I/O is completely separate."
    - letter: "D"
      text: "GPUI deletes any child InputState created inside new_with_window unless stored."
      correct: false
      explain: "title_input and filter_input already own their Entity<InputState>; _subscriptions keeps listeners alive."
- question: "Why does WorkbenchView define both new() and new_with_window(window, cx)?"
  wrong_hint: "Consider what resources cargo test has compared to cargo run."
  options:
    - letter: "A"
      text: "Unit tests call new() directly without needing an OS window."
      correct: true
      explain: "Correct! InputState::new requires a Window reference, so keeping a window-free new() lets cargo test stay fast and headless."
    - letter: "B"
      text: "Rust forbids constructors with zero arguments inside macOS binary crates."
      correct: false
      explain: "Zero-argument constructors like new() are standard idiom across all Rust targets."
    - letter: "C"
      text: "Two constructors double CPU speed whenever rendering long conversation lists."
      correct: false
      explain: "Constructors run once at creation time and do not speed up per-frame layout."
    - letter: "D"
      text: "GPUI Kit spawns separate background processes for each constructor variant."
      correct: false
      explain: "Both constructors run synchronously inside the main UI process."
- question: "Why can you render Input::new(&input) inside render() without losing cursor position?"
  wrong_hint: "Look at Figure 4.1 comparing transient Input vs. persistent Entity<InputState>."
  options:
    - letter: "A"
      text: "The persistent Entity<InputState> owns cursor selection outside transient element builders."
      correct: true
      explain: "Correct! Entity<InputState> lives across frames in GPUI's store while Input::new(&input) is just a lightweight renderer."
    - letter: "B"
      text: "Every render call writes buffers straight into Cargo build artifacts."
      correct: false
      explain: "GPUI never touches Cargo target artifacts during runtime frames."
    - letter: "C"
      text: "Input clones the entire WorkbenchView vector before drawing a character."
      correct: false
      explain: "Input only borrows &Entity<InputState> without touching conversation turns."
    - letter: "D"
      text: "GPUI pauses all redraw events whenever users focus an Input."
      correct: false
      explain: "Focusing an Input enables caret blinking and keystroke redraws immediately."
:::

## Verification Lab

:::verify id="verify-0004" title="Verification Lab: Live Title Renaming & Filtering" badge="Terminal Gate"
Verify formatting, run all 5 unit tests, and pass strict Clippy on `apps/0004-single-line-inputs-and-titles`:

```bash caption="Verified Cargo format, test, and clippy commands"
cargo fmt --manifest-path apps/0004-single-line-inputs-and-titles/Cargo.toml --check
cargo test --manifest-path apps/0004-single-line-inputs-and-titles/Cargo.toml
cargo clippy --manifest-path apps/0004-single-line-inputs-and-titles/Cargo.toml --all-targets -- -D warnings
```

Verified output from running the suite above:

```text caption="Verified test & clippy output"
running 5 tests
test tests::select_turn_respects_bounds ... ok
test tests::set_title_ignores_blank_input ... ok
test tests::default_view_starts_without_window_inputs ... ok
test tests::filtered_turn_indices_matches_text_and_role_case_insensitively ... ok
test tests::append_and_remove_update_filtered_results ... ok

test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

    Checking antigravity-workbench v0.1.0 (/Users/brett/Documents/GitHub/gpuikit-tutorial/apps/0004-single-line-inputs-and-titles)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 2.48s
```

Launch the desktop app to rename the session live and type `"agent"` or `"parse_flags"` into the cleanable filter field:

```bash caption="Launch Lesson 0004 desktop window"
cargo run --manifest-path apps/0004-single-line-inputs-and-titles/Cargo.toml
```

- [ ] Run `cargo test` and verify `5 passed; 0 failed`.
- [ ] Run `cargo clippy --all-targets -- -D warnings` with exit code `0`.
- [ ] Run `cargo run`, edit the session title input, filter by `agent`, click the clear (`×`) button or hit Escape, and verify **Print Markdown** outputs the updated session title.
:::

:::teacher-prompt title="Ask Follow-Up Questions"
Before upgrading to multi-line Markdown editing with `Textarea` in Lesson 0005, ask any questions about:
- Why `Input` is recreated every frame while `Entity<InputState>` persists across frames.
- How RAII `Subscription` handles prevent listener leaks or silent deregistration.
- How `Vec<usize>` filtering keeps original turn indices intact.
:::
