# Course Notes & Curriculum Roadmap

## Learner Profile
- **Experience**: Rust novice (introduce Rust syntax and ownership/type concepts inline as they appear).
- **Target Ecosystem**: Building alternative desktop interfaces around `antigravity-sdk-rust`, starting by re-implementing best-practice interfaces for project-based agentic coding systems.
- **Core Capabilities Needed**: Fast multi-line Markdown / conversation editing and live Markdown rendering with GPUI Kit.

## Curriculum Roadmap
1. **Lesson 0001 (`0001-bootstrap-workbench-shell`)**: Bootstrap the Cargo project (`gpui-kit = "0.9.1"`), introduce core domain types (`TurnRole`, `ConversationTurn`, `WorkbenchDoc`), render the initial `WorkbenchView` inside `gpui_kit::open_window` (`Root` wrapper), and establish `cargo test` + `cargo clippy --all-targets -- -D warnings`.
2. **Lesson 0002**: Reactive State & Turn Inspector (`Entity<T>`, `Context<T>`, `cx.notify()`, click handlers, and selecting conversation turns).
3. **Lesson 0003**: Multi-Line Markdown Editing (`Textarea` / `InputState` / `Editor`, subscriptions, and live buffer edits).
4. **Lesson 0004**: Live Markdown Rendering (`TextView::markdown`, rich styling, selectable transcripts, and clickable checkboxes).
5. **Lesson 0005**: Split-Pane Workbench Layout (`Resizable` panels, file/conversation sidebar, and keyboard shortcuts).
6. **Lesson 0006**: Disk Persistence & Transcript Export (loading/saving `.md` files and preparing clean data boundaries for `antigravity-sdk-rust`).
