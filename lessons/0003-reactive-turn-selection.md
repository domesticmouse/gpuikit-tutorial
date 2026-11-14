---
title: "Reactive Turn Selection & State Mutation"
page_title: "Lesson 0003: Reactive Turn Selection & State Mutation — GPUI Kit Course"
nav_id: "lesson-0003"
badge: "Lesson 0003 • Reactive State & Listeners"
subtitle: "Select, append, and safely delete conversation turns using cx.listener, cx.notify(), Selectable buttons, and testable view methods."
card:
  title: "**Reactive Turn Selection & State Mutation**"
  summary: "Wire toolbar and turn-list clicks to &mut self via cx.listener and trigger GPU re-renders with cx.notify()."
---

Static turn cards only get you halfway to an Antigravity workbench. To inspect individual agent turns, add follow-ups, or trim noise from a transcript, your view needs mutable state (`active_turn: usize`) that responds to mouse clicks immediately and re-renders cleanly. In this lesson you will connect GPUI buttons to `WorkbenchView` methods using `cx.listener(...)` and `cx.notify()`.

:::callout title="Recommended Primary Sources"
- [GPUI Kit Event & Context Guide](https://gpui-kit.com/) — How `cx.listener` borrows `Entity<V>` mutably and triggers `cx.notify()`.
- [The Rust Book: References & Borrowing Rules](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html) — Why callbacks cannot capture `&mut self` directly across frames.
- Course References: [Glossary](../reference/GLOSSARY.md) and [GPUI Kit & Rust Quick Reference](../reference/gpui-kit-cheatsheet.md).
:::

## Why Event Handlers Use `cx.listener` Instead of Raw `&mut self`

Inside `fn render(&mut self, ...)`, Rust's borrow checker stops `render` from moving `&mut self` directly into multiple button closures—that would create multiple simultaneous mutable aliases. Instead, GPUI lets each button store an `Entity` handle callback created by `cx.listener(|this, event, window, cx| ...)`:

```mermaid caption="Figure 3.1: Reactive click cycle from UI element to cx.notify() re-render"
sequenceDiagram
    participant User as Mouse Click
    participant GPUI as GPUI Dispatch
    participant View as WorkbenchView (&mut Self)
    User->>GPUI: Clicks "Next" or "Inspect"
    GPUI->>View: Invokes cx.listener(|this, _, _, cx|)
    View->>View: Mutates self.active_turn or self.doc.turns
    View->>GPUI: Calls cx.notify()
    GPUI->>View: Schedules next Render::render(&mut self, window, cx)
```

Notice how separating pure state methods (`select_turn`, `append_turn`, `remove_active_turn`) from `render` pays off twice: clicks trigger crisp updates via `cx.notify()`, and your unit tests exercise every edge case without launching an OS window{{sidenote:Keeping mutation logic inside plain `&mut self` methods lets `cargo test` run all edge-case checks in < 0.01 seconds without touching GPU surfaces.}}.

## Step 1: Clone Lesson 0002 to `apps/0003-reactive-turn-selection`

Clone the previous lesson's directory (keeping `Cargo.toml` unchanged at `gpui-kit = "0.9.1"`) and open `src/main.rs`:

```toml caption="apps/0003-reactive-turn-selection/Cargo.toml"
[package]
name = "antigravity-workbench"
version = "0.1.0"
edition = "2024"

[dependencies]
gpui-kit = "0.9.1"
```

## Step 2: Build the Application Block by Block

### Block 1: Imports & Core Domain Structs {#block-1}

```rust caption="Block 1: Adding Disableable and Selectable traits to domain imports"
use gpui_kit::component::ActiveTheme as _;
use gpui_kit::component::Disableable as _;
use gpui_kit::component::Selectable as _;
use gpui_kit::component::badge::Badge;
use gpui_kit::component::button::{Button, ButtonVariants as _};
use gpui_kit::component::tag::Tag;
use gpui_kit::component::theme::{Theme, ThemeMode};
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

- **`Disableable as _` & `Selectable as _`**: Importing these extension traits unlocks `.disabled(bool)` and `.selected(bool)` on GPUI Kit's `Button` widget.

### Block 2: Reactive State Methods on `WorkbenchView` {#block-2}

```rust caption="Block 2: Adding active_turn state and bounds-safe mutation helpers"
pub struct WorkbenchView {
    pub doc: WorkbenchDoc,
    pub active_turn: usize,
}

impl WorkbenchView {
    pub fn new() -> Self {
        Self {
            doc: WorkbenchDoc::sample_session(),
            active_turn: 0,
        }
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

- **`saturating_sub(1)`**: Unsigned integers (`usize`) cannot go below zero; plain `0usize - 1` panics with integer underflow! `saturating_sub(1)` cleanly clamps at `0`.
- **Early `return None;` Guard**: In `remove_active_turn`, we refuse to delete the final remaining turn so `active_turn` always points to a valid index. Notice how returning `Option<ConversationTurn>` communicates whether a deletion actually happened.
- **`&mut self` across Methods**: Every mutating method takes `&mut self` so callers (either `cx.listener` in the UI or `#[test]` functions) own exclusive temporary access while mutating.

### Block 3: Wiring `cx.listener`, `cx.notify()`, and Per-Row Element IDs {#block-3}

```rust caption="Block 3: Connecting toolbar buttons and turn selection cards"
impl Render for WorkbenchView {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let theme = cx.theme();
        let summary = format!(
            "{} ({} turns, {} words) — Selected #{}",
            self.doc.title,
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
                                    .count(self.doc.turns.len())
                                    .child(div().px_2().py_1().child("Turns")),
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
            .child(div().text_color(theme.muted_foreground).child(summary))
            .child(
                v_flex()
                    .gap_2()
                    .children(self.doc.turns.iter().enumerate().map(|(ix, turn)| {
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

- **`cx.listener(|this, _, _, cx| { ... cx.notify(); })`**: GPUI wraps the closure with a weak entity handle so when the user clicks the button, GPUI locks `WorkbenchView` as `&mut Self` (`this`) and gives you a fresh `Context<WorkbenchView>` (`cx`). Calling `cx.notify()` marks the entity dirty so GPUI schedules a redraw on the next frame.
- **Tuple Element IDs `Button::new(("select-turn", ix))`**: Every interactive button rendered inside a loop needs a unique `ElementId`. Passing a `(&'static str, usize)` tuple gives each row its own click hitbox and hover state without string formatting allocations!
- **`cx.listener(move |this, _, _, cx| ...)`**: Notice `move` captures `ix: usize` by value (`usize` implements `Copy`) so every row's closure remembers its own index after the iterator finishes.

### Block 4: Entrypoint & State Mutation Tests {#block-4}

```rust caption="Block 4: Window bootstrap and 5 state-transition tests"
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

#[cfg(test)]
mod tests {
    use super::{ConversationTurn, TurnRole, WorkbenchView};

    #[test]
    fn select_turn_bounds_checks_indices() {
        let mut view = WorkbenchView::new();

        assert!(view.select_turn(2));
        assert_eq!(view.active_turn, 2);
        assert!(!view.select_turn(99));
        assert_eq!(view.active_turn, 2);
    }

    #[test]
    fn next_and_prev_clamp_at_session_edges() {
        let mut view = WorkbenchView::new();

        view.select_prev_turn();
        assert_eq!(view.active_turn, 0);

        view.select_next_turn();
        view.select_next_turn();
        view.select_next_turn();
        assert_eq!(view.active_turn, 2);

        view.select_prev_turn();
        assert_eq!(view.active_turn, 1);
    }

    #[test]
    fn append_turn_adds_and_focuses_new_turn() {
        let mut view = WorkbenchView::new();
        let idx = view.append_turn(TurnRole::Assistant, "Added response");

        assert_eq!(idx, 3);
        assert_eq!(view.active_turn, 3);
        assert_eq!(
            view.active_turn_ref(),
            Some(&ConversationTurn::new(
                TurnRole::Assistant,
                "Added response"
            ))
        );
    }

    #[test]
    fn remove_active_turn_preserves_last_remaining_turn() {
        let mut view = WorkbenchView::new();

        assert!(view.select_turn(2));
        assert!(view.remove_active_turn().is_some());
        assert_eq!(view.doc.turns.len(), 2);
        assert_eq!(view.active_turn, 1);

        assert!(view.remove_active_turn().is_some());
        assert_eq!(view.doc.turns.len(), 1);
        assert_eq!(view.active_turn, 0);

        assert!(view.remove_active_turn().is_none());
        assert_eq!(view.doc.turns.len(), 1);
    }

    #[test]
    fn active_turn_ref_matches_selected_speaker() {
        let mut view = WorkbenchView::new();
        assert_eq!(view.active_turn_ref().map(|t| t.role), Some(TurnRole::User));
        view.select_next_turn();
        assert_eq!(
            view.active_turn_ref().map(|t| t.role),
            Some(TurnRole::Assistant)
        );
    }
}
```

## Step 3: Complete `src/main.rs` Listing

```rust caption="Complete src/main.rs for Lesson 0003"
use gpui_kit::component::ActiveTheme as _;
use gpui_kit::component::Disableable as _;
use gpui_kit::component::Selectable as _;
use gpui_kit::component::badge::Badge;
use gpui_kit::component::button::{Button, ButtonVariants as _};
use gpui_kit::component::tag::Tag;
use gpui_kit::component::theme::{Theme, ThemeMode};
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
}

impl WorkbenchView {
    pub fn new() -> Self {
        Self {
            doc: WorkbenchDoc::sample_session(),
            active_turn: 0,
        }
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
        let summary = format!(
            "{} ({} turns, {} words) — Selected #{}",
            self.doc.title,
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
                                    .count(self.doc.turns.len())
                                    .child(div().px_2().py_1().child("Turns")),
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
            .child(div().text_color(theme.muted_foreground).child(summary))
            .child(
                v_flex()
                    .gap_2()
                    .children(self.doc.turns.iter().enumerate().map(|(ix, turn)| {
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
            Theme::change(ThemeMode::Dark, None, cx);
            gpui_kit::open_window(WindowOptions::default(), cx, |_, cx| {
                cx.new(|_| WorkbenchView::new())
            })
            .expect("failed to open workbench window");
        });
}

#[cfg(test)]
mod tests {
    use super::{ConversationTurn, TurnRole, WorkbenchView};

    #[test]
    fn select_turn_bounds_checks_indices() {
        let mut view = WorkbenchView::new();

        assert!(view.select_turn(2));
        assert_eq!(view.active_turn, 2);
        assert!(!view.select_turn(99));
        assert_eq!(view.active_turn, 2);
    }

    #[test]
    fn next_and_prev_clamp_at_session_edges() {
        let mut view = WorkbenchView::new();

        view.select_prev_turn();
        assert_eq!(view.active_turn, 0);

        view.select_next_turn();
        view.select_next_turn();
        view.select_next_turn();
        assert_eq!(view.active_turn, 2);

        view.select_prev_turn();
        assert_eq!(view.active_turn, 1);
    }

    #[test]
    fn append_turn_adds_and_focuses_new_turn() {
        let mut view = WorkbenchView::new();
        let idx = view.append_turn(TurnRole::Assistant, "Added response");

        assert_eq!(idx, 3);
        assert_eq!(view.active_turn, 3);
        assert_eq!(
            view.active_turn_ref(),
            Some(&ConversationTurn::new(
                TurnRole::Assistant,
                "Added response"
            ))
        );
    }

    #[test]
    fn remove_active_turn_preserves_last_remaining_turn() {
        let mut view = WorkbenchView::new();

        assert!(view.select_turn(2));
        assert!(view.remove_active_turn().is_some());
        assert_eq!(view.doc.turns.len(), 2);
        assert_eq!(view.active_turn, 1);

        assert!(view.remove_active_turn().is_some());
        assert_eq!(view.doc.turns.len(), 1);
        assert_eq!(view.active_turn, 0);

        assert!(view.remove_active_turn().is_none());
        assert_eq!(view.doc.turns.len(), 1);
    }

    #[test]
    fn active_turn_ref_matches_selected_speaker() {
        let mut view = WorkbenchView::new();
        assert_eq!(view.active_turn_ref().map(|t| t.role), Some(TurnRole::User));
        view.select_next_turn();
        assert_eq!(
            view.active_turn_ref().map(|t| t.role),
            Some(TurnRole::Assistant)
        );
    }
}
```

## Skill Practice & Retrieval

:::exercise id="ex-0003" title="Interactive Lab: Wire Reactive Turn Selection" badge="Skill Practice • Tight Feedback Loop"
Fill in the missing GPUI reactive listener, redraw trigger, safe unsigned decrement, and per-row ID tuple below.

```rust
fn wire_prev_button() -> Button {
    Button::new("prev-turn").label("Prev").on_click(
        cx.{{blank:listener|Wrap a closure receiving (&mut Self, &ClickEvent, &mut Window, &mut Context<Self>)|???|8}}(|this, _, _, cx| {
            this.active_turn = this.active_turn.{{blank:saturating_sub|Decrement usize without underflow panic at 0|???|14}}(1);
            cx.{{blank:notify|Schedule GPUI re-render after mutating state|???|6}}();
        }),
    )
}

fn inspect_button(ix: usize, active_turn: usize) -> Button {
    Button::new({{blank:("select-turn", ix)|Pair static label with row index for unique ElementId|("select-turn", ???)|19}})
        .ghost()
        .selected(ix == active_turn)
        .label("Inspect")
}
```

:::prompts
hint: "Use cx.listener, saturating_sub(1), cx.notify(), and (\"select-turn\", ix) for unique button ElementIds."
success: "Spot on! Every click safely mutates &mut Self and schedules a GPUI re-render."
:::
:::

:::quiz id="quiz-0003" title="Retrieval Practice: cx.listener & Reactive Redraws" badge="3 Questions • Equal-Length Options"
- question: "Why does render wire buttons with cx.listener(|this, _, _, cx| ...) instead of plain move closures?"
  wrong_hint: "Consider Rust's rule against multiple &mut self borrows escaping render()."
  options:
    - letter: "A"
      text: "cx.listener provides &mut Self and Context<Self> safely inside event callbacks."
      correct: true
      explain: "Correct! cx.listener holds an entity handle so GPUI can grant exclusive &mut Self access when the user actually clicks."
    - letter: "B"
      text: "Plain closures automatically drop macOS mouse clicks on desktop windows."
      correct: false
      explain: "Plain closures receive clicks fine, but cannot capture &mut self across frames."
    - letter: "C"
      text: "cx.listener runs button handlers asynchronously across background worker pools instead."
      correct: false
      explain: "UI click listeners always run synchronously on GPUI's main UI thread."
    - letter: "D"
      text: "GPUI forbids plain closures from reading immutable theme palette tokens."
      correct: false
      explain: "Plain closures can capture Copied colors freely; the constraint is mutating view state."
- question: "What happens if a click handler updates self.active_turn without calling cx.notify()?"
  wrong_hint: "Check Figure 3.1's loop between state mutation and GPUI scheduling."
  options:
    - letter: "A"
      text: "Rust rejects compilation whenever struct fields mutate without cx.notify() calls."
      correct: false
      explain: "The Rust compiler has no knowledge of GPUI's redraw flag."
    - letter: "B"
      text: "State mutates internally while GPUI leaves the window UI unchanged."
      correct: true
      explain: "Correct! Without cx.notify(), GPUI does not know the entity changed and will not re-run render()."
    - letter: "C"
      text: "The OS closes the desktop window due to missing redraw."
      correct: false
      explain: "The window remains open showing stale pixels until some other event triggers a redraw."
    - letter: "D"
      text: "GPUI wipes the vector and resets active_turn back to zero."
      correct: false
      explain: "Your mutated field stays changed in memory; only the visual frame lags behind."
- question: "Why does Button::new((\"select-turn\", ix)) pass a tuple ID instead of \"select-turn\"?"
  wrong_hint: "Think about how GPUI tracks hover/focus across multiple buttons generated in a loop."
  options:
    - letter: "A"
      text: "Tuple keys sort turns alphabetically inside the GPUI layout engine."
      correct: false
      explain: "Children preserve iterator order; IDs identify elements across frames."
    - letter: "B"
      text: "GPUI requires distinct ElementIds so repeated loop buttons keep identity."
      correct: true
      explain: "Correct! GPUI pairs a (&'static str, usize) tuple into a unique ElementId per row."
    - letter: "C"
      text: "Tuple strings convert usize counters into static ASCII badge labels."
      correct: false
      explain: "Button text comes from .label(...), not from the ElementId tuple."
    - letter: "D"
      text: "Single string IDs allocate ten extra threads on each click."
      correct: false
      explain: "ElementIds identify retained frame state on the UI thread with zero extra threads."
:::

## Verification Lab

:::verify id="verify-0003" title="Verification Lab: Interactive Turn Selection" badge="Terminal Gate"
Verify formatting, run all 5 unit tests, and pass strict Clippy on `apps/0003-reactive-turn-selection`:

```bash caption="Verified Cargo format, test, and clippy commands"
cargo fmt --manifest-path apps/0003-reactive-turn-selection/Cargo.toml --check
cargo test --manifest-path apps/0003-reactive-turn-selection/Cargo.toml
cargo clippy --manifest-path apps/0003-reactive-turn-selection/Cargo.toml --all-targets -- -D warnings
```

Verified output from running the suite above:

```text caption="Verified test & clippy output"
running 5 tests
test tests::active_turn_ref_matches_selected_speaker ... ok
test tests::select_turn_bounds_checks_indices ... ok
test tests::next_and_prev_clamp_at_session_edges ... ok
test tests::remove_active_turn_preserves_last_remaining_turn ... ok
test tests::append_turn_adds_and_focuses_new_turn ... ok

test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

    Checking antigravity-workbench v0.1.0 (/Users/brett/Documents/GitHub/gpuikit-tutorial/apps/0003-reactive-turn-selection)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.03s
```

Launch the desktop app and test clicking **Prev**, **Next**, **+ User Turn**, **+ Agent Turn**, **Delete Turn**, and row **Inspect** buttons:

```bash caption="Launch Lesson 0003 interactive workbench"
cargo run --manifest-path apps/0003-reactive-turn-selection/Cargo.toml
```

- [ ] Run `cargo test` and verify `5 passed; 0 failed`.
- [ ] Run `cargo clippy --all-targets -- -D warnings` and verify exit code `0`.
- [ ] Run `cargo run`, click through turns and add/delete turns, and watch the highlighted border and **Active Turn Inspector** update live.
:::

:::teacher-prompt title="Ask Follow-Up Questions"
Before we add text fields and subscriptions in Lesson 0004, ask any questions about:
- Why `cx.listener` is required instead of capturing `&mut self`.
- How `saturating_sub` prevents unsigned integer underflow bugs.
- Why loop elements use tuple IDs like `("select-turn", ix)`.
:::
