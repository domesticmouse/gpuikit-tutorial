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
