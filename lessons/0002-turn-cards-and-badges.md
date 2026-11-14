---
title: "Turn Cards, Flexbox Lists & Role Badges"
page_title: "Lesson 0002: Turn Cards, Flexbox Lists & Role Badges — GPUI Kit Course"
nav_id: "lesson-0002"
badge: "Lesson 0002 • Lists, Option<T> & Badges"
subtitle: "Render structured conversation turns with h_flex, v_flex, Tag, and Badge while learning Rust Option<T>, match, and iterator pipelines."
card:
  title: "**Turn Cards, Flexbox Lists & Role Badges**"
  summary: "Turn raw domain structs into styled conversation cards using h_flex/v_flex, Tag, Badge, Option<T>, and enumerate iterators."
---

A single summary line does not cut it when inspecting multi-turn Antigravity sessions. In this lesson you will render every conversation turn as a distinct card with a speaker role **Tag**, word count, and first-line preview, plus a header **Badge** showing the total turn count—all backed by safe Rust **`Option<T>`** lookups instead of panic-prone array indexing.

:::callout title="Recommended Primary Sources"
- [GPUI Kit `Tag` & `Badge` Components](https://gpui-kit.com/) — Component styling variants (`primary`, `secondary`, `outline`) and numeric badge overlays.
- [The Rust Book: `Option<T>` & `match`](https://doc.rust-lang.org/book/ch06-01-defining-an-enum.html) — Why Rust replaces `null` with `Some(value)` and `None`.
- Course References: [Glossary](../reference/GLOSSARY.md) and [GPUI Kit & Rust Quick Reference](../reference/gpui-kit-cheatsheet.md).
:::

## How GPUI Flexbox & Iterators Build Turn Lists

Rather than mutating a list widget imperatively, GPUI builds lists declaratively by mapping a Rust **Iterator** over `&self.doc.turns` straight into `.children(...)`:

```mermaid caption="Figure 2.1: Transforming &self.doc.turns into styled Tag and v_flex cards"
flowchart LR
    VecTurns["&self.doc.turns (Vec&lt;ConversationTurn&gt;)"] --> Iter[".iter() — borrows &ConversationTurn"]
    Iter --> Enum[".enumerate() — yields (ix, turn)"]
    Enum --> Map[".map(|(ix, turn)| ...)"]
    Map --> Tag["Tag::primary() / Tag::secondary()"]
    Map --> Card["v_flex() turn card"]
    Tag --> Card
    Card --> List["v_flex().gap_3().children(...)"]
```

Along the way, you will meet one of Rust's most important safety guarantees: **`Option<T>`**{{sidenote:Rust has no `null` or `nil`. Any lookup that might find nothing—like reading the first line of an empty string or looking up index `99`—returns `Option<T>`, forcing your code to handle the `None` case at compile time.}}.

## Step 1: Clone the Lesson 0001 Crate & Verify Dependencies

Keep every dependency cached by cloning `apps/0001-bootstrap-workbench-shell` (or checking out `apps/0002-turn-cards-and-badges`):

```toml caption="apps/0002-turn-cards-and-badges/Cargo.toml"
[package]
name = "antigravity-workbench"
version = "0.1.0"
edition = "2024"

[dependencies]
gpui-kit = "0.9.1"
```

Notice `Cargo.toml` stays completely unchanged: `Badge`, `Tag`, `h_flex`, and `v_flex` are already bundled inside `gpui-kit = "0.9.1"`.

## Step 2: Build the Application Block by Block

### Block 1: Imports & Line Preview Extraction {#block-1}

```rust caption="Block 1: Badge, Tag, flex helpers, and ConversationTurn::preview_line"
use gpui_kit::component::ActiveTheme as _;
use gpui_kit::component::badge::Badge;
use gpui_kit::component::button::{Button, ButtonVariants as _};
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
```

- **`h_flex` and `v_flex`**: Concise GPUI Kit helpers equivalent to `div().flex().flex_row()` and `div().flex().flex_col()`, keeping layout trees scannable.
- **`Tag` vs. `Badge`**: `Tag` renders an inline colored pill (ideal for `USER` vs. `AGENT` speaker chips), while `Badge` wraps an element and positions a numeric counter (`count`) at its corner.
- **`&str` Return Borrow (`preview_line(&self) -> &str`)**: Returning `&str` borrows a zero-copy slice directly from `self.markdown`'s buffer—no `String::clone()` allocation is needed.
- **`self.markdown.lines().next().unwrap_or("")`**: `.lines()` produces an iterator over line slices; `.next()` returns `Option<&str>` (`None` if the Markdown body is empty); `.unwrap_or("")` safely supplies a fallback empty slice without crashing.

### Block 2: Safe Indexed Lookup with `Option<&ConversationTurn>` {#block-2}

```rust caption="Block 2: Non-panicking slice lookup via .get(index)"
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

- **`Option<&ConversationTurn>`**: `turn_at` takes a zero-based `usize` index and returns `Some(&ConversationTurn)` when `index < self.turns.len()`, or `None` when out of bounds.
- **Why `.get(index)` instead of `&self.turns[index]`?**: Indexing with `[index]` panics and terminates your desktop window immediately if an index is ever out of range. Using `.get(index)` lifts bounds safety into the type system so every caller handles the empty case explicitly.

### Block 3: Mapping Enumerated Turns into Styled `Tag` Cards {#block-3}

```rust caption="Block 3: Pattern-matching Option<T> and building turn cards"
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
        let first_turn_hint = match self.doc.turn_at(0) {
            Some(turn) => format!("Lead speaker: {}", turn.role.badge_label()),
            None => String::from("No conversation turns loaded"),
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
                        Button::new("export-md")
                            .primary()
                            .label("Print Markdown")
                            .on_click(move |_, _, _| {
                                println!("{markdown_preview}");
                            }),
                    ),
            )
            .child(
                h_flex()
                    .items_center()
                    .justify_between()
                    .text_color(theme.muted_foreground)
                    .child(summary)
                    .child(first_turn_hint),
            )
            .child(
                v_flex()
                    .gap_3()
                    .children(self.doc.turns.iter().enumerate().map(|(ix, turn)| {
                        let role_tag = match turn.role {
                            TurnRole::User => Tag::primary().child("USER"),
                            TurnRole::Assistant => Tag::secondary().child("AGENT"),
                        };
                        let meta = format!("#{} • {} words", ix + 1, turn.word_count());

                        v_flex()
                            .p_4()
                            .gap_2()
                            .rounded_md()
                            .border_1()
                            .border_color(theme.border)
                            .bg(theme.secondary)
                            .child(
                                h_flex()
                                    .items_center()
                                    .justify_between()
                                    .child(role_tag)
                                    .child(
                                        div()
                                            .text_sm()
                                            .text_color(theme.muted_foreground)
                                            .child(meta),
                                    ),
                            )
                            .child(turn.preview_line().to_string())
                    })),
            )
    }
}
```

- **`match self.doc.turn_at(0)`**: Exhaustive pattern matching destructures `Some(turn)` to extract `turn.role` while requiring a `None` branch.
- **`.iter().enumerate().map(|(ix, turn)| ...)`**: `.enumerate()` wraps each borrowed item in a `(usize, &ConversationTurn)` **Tuple**. Destructuring `|(ix, turn)|` gives you both the 0-based turn index and the turn reference inside the card builder.
- **`.children(...)`**: Accepts any Rust iterator yielding elements (`v_flex`), eliminating temporary `Vec<Div>` allocations inside `render`.

### Block 4: Entrypoint & Unit Tests {#block-4}

```rust caption="Block 4: Entrypoint and Option<T> + preview unit tests"
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
    fn preview_line_extracts_first_line() {
        let multi = ConversationTurn::new(TurnRole::User, "First line\nSecond line");
        let empty = ConversationTurn::new(TurnRole::Assistant, "");

        assert_eq!(multi.preview_line(), "First line");
        assert_eq!(empty.preview_line(), "");
    }

    #[test]
    fn turn_at_returns_some_and_none_safely() {
        let doc = WorkbenchDoc::sample_session();

        assert_eq!(doc.turn_at(0).map(|t| t.role), Some(TurnRole::User));
        assert_eq!(doc.turn_at(1).map(|t| t.role), Some(TurnRole::Assistant));
        assert!(doc.turn_at(99).is_none());
    }

    #[test]
    fn sample_session_exports_structured_markdown() {
        let doc = WorkbenchDoc::sample_session();
        let view = WorkbenchView::new();
        let md = doc.to_markdown();

        assert_eq!(view.doc, doc);
        assert_eq!(doc.turns.len(), 3);
        assert_eq!(doc.total_words(), 26);
        assert!(md.starts_with("# Antigravity Session: Refactor CLI Parser"));
        assert!(md.contains("## USER\n\nInspect `src/args.rs`"));
        assert!(md.contains("## AGENT\n\nIn `parse_flags`"));
        assert!(md.contains("Draft a regression test checking flag order independence."));
    }
}
```

- **`doc.turn_at(0).map(|t| t.role)`**: Notice `Option::map`! Calling `.map(...)` on an `Option<&ConversationTurn>` transforms the inner value only if it is `Some(...)`, producing `Some(TurnRole::User)` or propagating `None` automatically.
- **`doc.turn_at(99).is_none()`**: Verifies that out-of-bounds indices return `None` cleanly rather than panicking.

## Step 3: Complete `src/main.rs` Listing

```rust caption="Complete src/main.rs for Lesson 0002"
use gpui_kit::component::ActiveTheme as _;
use gpui_kit::component::badge::Badge;
use gpui_kit::component::button::{Button, ButtonVariants as _};
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
        let first_turn_hint = match self.doc.turn_at(0) {
            Some(turn) => format!("Lead speaker: {}", turn.role.badge_label()),
            None => String::from("No conversation turns loaded"),
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
                        Button::new("export-md")
                            .primary()
                            .label("Print Markdown")
                            .on_click(move |_, _, _| {
                                println!("{markdown_preview}");
                            }),
                    ),
            )
            .child(
                h_flex()
                    .items_center()
                    .justify_between()
                    .text_color(theme.muted_foreground)
                    .child(summary)
                    .child(first_turn_hint),
            )
            .child(
                v_flex()
                    .gap_3()
                    .children(self.doc.turns.iter().enumerate().map(|(ix, turn)| {
                        let role_tag = match turn.role {
                            TurnRole::User => Tag::primary().child("USER"),
                            TurnRole::Assistant => Tag::secondary().child("AGENT"),
                        };
                        let meta = format!("#{} • {} words", ix + 1, turn.word_count());

                        v_flex()
                            .p_4()
                            .gap_2()
                            .rounded_md()
                            .border_1()
                            .border_color(theme.border)
                            .bg(theme.secondary)
                            .child(
                                h_flex()
                                    .items_center()
                                    .justify_between()
                                    .child(role_tag)
                                    .child(
                                        div()
                                            .text_sm()
                                            .text_color(theme.muted_foreground)
                                            .child(meta),
                                    ),
                            )
                            .child(turn.preview_line().to_string())
                    })),
            )
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
    fn preview_line_extracts_first_line() {
        let multi = ConversationTurn::new(TurnRole::User, "First line\nSecond line");
        let empty = ConversationTurn::new(TurnRole::Assistant, "");

        assert_eq!(multi.preview_line(), "First line");
        assert_eq!(empty.preview_line(), "");
    }

    #[test]
    fn turn_at_returns_some_and_none_safely() {
        let doc = WorkbenchDoc::sample_session();

        assert_eq!(doc.turn_at(0).map(|t| t.role), Some(TurnRole::User));
        assert_eq!(doc.turn_at(1).map(|t| t.role), Some(TurnRole::Assistant));
        assert!(doc.turn_at(99).is_none());
    }

    #[test]
    fn sample_session_exports_structured_markdown() {
        let doc = WorkbenchDoc::sample_session();
        let view = WorkbenchView::new();
        let md = doc.to_markdown();

        assert_eq!(view.doc, doc);
        assert_eq!(doc.turns.len(), 3);
        assert_eq!(doc.total_words(), 26);
        assert!(md.starts_with("# Antigravity Session: Refactor CLI Parser"));
        assert!(md.contains("## USER\n\nInspect `src/args.rs`"));
        assert!(md.contains("## AGENT\n\nIn `parse_flags`"));
        assert!(md.contains("Draft a regression test checking flag order independence."));
    }
}
```

## Skill Practice & Retrieval

:::exercise id="ex-0002" title="Interactive Lab: Enumerate & Render Turn Cards" badge="Skill Practice • Tight Feedback Loop"
Complete the safe `Option` lookup, enumerated iterator pipeline, and `Badge` counter below.

```rust
fn turn_summary(doc: &WorkbenchDoc, index: usize) -> &str {
    match doc.turns.{{blank:get|Use slice::get to return an Option without panicking|???|5}}(index) {
        Some(turn) => turn.preview_line(),
        None => "Missing turn",
    }
}

fn turn_list(turns: &[ConversationTurn]) -> impl IntoElement {
    v_flex().gap_3().children(turns.iter().{{blank:enumerate|Pair each element with its 0-based index|???|11}}().map(|(ix, turn)| {
        let tag = match turn.role {
            TurnRole::User => {{blank:Tag::primary()|Primary pill variant for user turns|Tag::???()|14}},
            TurnRole::Assistant => Tag::secondary(),
        }
        .child(turn.role.badge_label());

        h_flex().gap_2().child(tag).child(format!("#{}: {}", ix + 1, turn.preview_line()))
    }))
}

fn count_badge(total: usize) -> Badge {
    Badge::new().{{blank:count|Set the numeric badge counter|???|7}}(total).child("Turns")
}
```

:::prompts
hint: "Remember: .get(index) returns Option<&T>, .enumerate() yields (usize, &T), and Badge::new().count(total) displays the counter."
success: "Nice work! You built panic-free lookups and declarative GPUI turn cards."
:::
:::

:::quiz id="quiz-0002" title="Retrieval Practice: Option<T>, Iterators & Badges" badge="3 Questions • Equal-Length Options"
- question: "Why does doc.turn_at(index) use .get(index) instead of &doc.turns[index]?"
  wrong_hint: "Compare what happens at runtime if index equals 99 on a 3-item vector."
  options:
    - letter: "A"
      text: "Returning Option<&T> via .get avoids runtime panics on out-of-bounds indices."
      correct: true
      explain: "Correct! .get(index) returns Some(&T) or None instead of crashing the UI thread when an index is out of range."
    - letter: "B"
      text: "Square brackets always allocate a fresh heap string on access."
      correct: false
      explain: "Direct slice indexing borrows without allocation, but panics if out of bounds."
    - letter: "C"
      text: "The .get helper sorts all turns alphabetically before returning references."
      correct: false
      explain: "slice::get performs an O(1) bounds-checked lookup without sorting."
    - letter: "D"
      text: "Direct indexing moves ownership out of the borrowed turn slice."
      correct: false
      explain: "&vec[i] still borrows, it simply panics on invalid indices."
- question: "In .iter().enumerate().map(|(ix, turn)| ...), what type is (ix, turn)?"
  wrong_hint: "Check what .iter() yields and what .enumerate() wraps around it."
  options:
    - letter: "A"
      text: "A heap vector storing string slices and owned badges."
      correct: false
      explain: ".enumerate() produces a tuple per element, not a Vec."
    - letter: "B"
      text: "A zero-based usize index paired with a borrowed &ConversationTurn."
      correct: true
      explain: "Correct! .iter() borrows &ConversationTurn, and .enumerate() pairs it with its 0-based usize offset."
    - letter: "C"
      text: "An exclusive mutable pointer to the next UI component."
      correct: false
      explain: ".iter() yields immutable borrows (&T), never mutable pointers."
    - letter: "D"
      text: "An Option wrapping two owned copies of the turn."
      correct: false
      explain: ".enumerate() yields a tuple directly inside the closure."
- question: "When should you choose GPUI Kit's Tag versus Badge widget?"
  wrong_hint: "Look at how the header and each turn card use Badge and Tag in Block 3."
  options:
    - letter: "A"
      text: "Tag labels inline status while Badge overlays counts on parents."
      correct: true
      explain: "Correct! Tag renders standalone pill labels like USER/AGENT, while Badge attaches counts or dots to a child element."
    - letter: "B"
      text: "Tag renders multi-line Markdown while Badge compiles native shader code."
      correct: false
      explain: "TextView renders Markdown; neither Tag nor Badge compiles shaders."
    - letter: "C"
      text: "Tag stores disk files while Badge executes blocking Tokio futures."
      correct: false
      explain: "Both Tag and Badge are pure UI elements."
    - letter: "D"
      text: "Badge edits multiline text while Tag validates Cargo dependency locks."
      correct: false
      explain: "Textarea and Editor handle multiline text editing."
:::

## Verification Lab

:::verify id="verify-0002" title="Verification Lab: Turn Cards, Clippy & Visual Inspection" badge="Terminal Gate"
Verify formatting, run all 4 unit tests, and pass strict Clippy on `apps/0002-turn-cards-and-badges`:

```bash caption="Verified Cargo format, test, and clippy commands"
cargo fmt --manifest-path apps/0002-turn-cards-and-badges/Cargo.toml --check
cargo test --manifest-path apps/0002-turn-cards-and-badges/Cargo.toml
cargo clippy --manifest-path apps/0002-turn-cards-and-badges/Cargo.toml --all-targets -- -D warnings
```

Verified output from running the suite above:

```text caption="Verified test & clippy output"
running 4 tests
test tests::turn_word_count_handles_markdown_tokens ... ok
test tests::turn_at_returns_some_and_none_safely ... ok
test tests::preview_line_extracts_first_line ... ok
test tests::sample_session_exports_structured_markdown ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

    Checking antigravity-workbench v0.1.0 (/Users/brett/Documents/GitHub/gpuikit-tutorial/apps/0002-turn-cards-and-badges)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 2.11s
```

Launch the desktop window to inspect your `Turns` counter badge and styled `USER` / `AGENT` turn cards:

```bash caption="Launch Lesson 0002 desktop window"
cargo run --manifest-path apps/0002-turn-cards-and-badges/Cargo.toml
```

- [ ] Run `cargo test` and verify all 4 tests pass (`4 passed; 0 failed`).
- [ ] Run `cargo clippy --all-targets -- -D warnings` with exit code `0`.
- [ ] Run `cargo run` and confirm all three turn cards render cleanly with distinct `USER` and `AGENT` tags and the header `Badge` displaying `3`.
:::

:::teacher-prompt title="Ask Follow-Up Questions"
Before advancing to Lesson 0003 (selecting, adding, and deleting turns reactively with `cx.listener` and `cx.notify()`), ask any questions about:
- How `Option<T>` replaces `null` and why `.get()` is safer than `[index]`.
- Why `.iter().enumerate()` borrows instead of copying strings.
- Styling layouts with `h_flex()`, `v_flex()`, `Tag`, and `Badge`.
:::
