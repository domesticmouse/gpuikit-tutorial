# GPUI Kit Resources

## Knowledge

- [GPUI Kit Official Documentation (`gpui-kit.com`)](https://gpui-kit.com/)
  Primary guide and manual covering GPUI Kit architecture, `open_window`, `Root`, theming, and the 75+ component catalog. Use for: learning component ergonomics and window setup conventions.
- [GPUI Kit API Reference (`docs.rs/gpui-kit`)](https://docs.rs/gpui-kit/latest/gpui_kit/)
  Authoritative Rustdoc signatures for `gpui_kit`, `gpui_kit::component`, `gpui_kit::base`, and `gpui_kit::assets`. Use for: checking exact trait bounds, builder methods, and re-exports.
- [`longbridge/gpui-kit` GitHub Repository](https://github.com/longbridge/gpui-kit)
  Official source code, stories, and examples for `Input`, `Textarea`, `Editor`, and `TextView`. Use for: studying real-world component wiring and layout patterns.
- [`antigravity-sdk-rust` on Crates.io](https://crates.io/crates/antigravity-sdk-rust)
  Target agentic SDK ecosystem that our Markdown and conversation workbench interfaces will support. Use for: aligning conversation turn models and transcript formats with real agent workflows.
- [The Rust Programming Language ("The Book")](https://doc.rust-lang.org/book/)
  Official introductory text for ownership, borrowing, structs, enums, traits, and closures as they appear in GPUI code. Use for: deeper dives whenever a Rust language concept first shows up in a lesson.
- [Workspace Skill: GPUI Kit (`0.9.1`) Reference Patterns](.agents/skills/gpui-kit/SKILL.md)
  Verified workspace APIs and guardrails (`open_window`/`Root`, `WeakEntity` in `on_task_toggle`, `EditorState`, `h_resizable`/`size_range`, `actions!`, and test/Clippy workflows) extracted from Lessons 0001–0010.

## Wisdom (Communities)

- [`longbridge/gpui-kit` GitHub Discussions & Issues](https://github.com/longbridge/gpui-kit/issues)
  Maintainer and practitioner discussions on component usage, layout patterns, and editor customization. Use for: troubleshooting edge cases and tracking API evolution.
- [Zed Community & GPUI Discussions](https://github.com/zed-industries/zed/discussions)
  Ecosystem discussions around GPUI's entity-context model and high-FPS layout primitives. Use for: understanding the underlying GPUI mental model and rendering lifecycle.
