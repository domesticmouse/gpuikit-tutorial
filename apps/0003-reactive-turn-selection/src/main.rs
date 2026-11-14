use gpui_kit::component::ActiveTheme as _;
use gpui_kit::component::Disableable as _;
use gpui_kit::component::Selectable as _;
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
