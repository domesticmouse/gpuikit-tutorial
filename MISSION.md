# Mission: Native Markdown & Conversation Workbench with GPUI Kit

## Why
Build fast, GPU-accelerated desktop interfaces around `antigravity-sdk-rust` that can view, edit, and preview Markdown files and multi-turn agentic conversations, starting by re-implementing best-practice interfaces for project-based agentic coding systems.

## Success looks like
- Read and write idiomatic Rust code (structs, enums, traits, ownership/borrowing, closures, and GPUI's `Entity<T>` / `Context<T>` model) with confidence.
- Ship a tested macOS desktop **Antigravity Markdown & Conversation Workbench** using `gpui-kit` featuring a conversation/file sidebar, multi-line Markdown editor (`Textarea` / `Editor`), live Markdown preview (`TextView`), and local file persistence.
- Verify every stage of the workbench with automated unit tests, headless GPUI checks, and strict `cargo clippy -- -D warnings` gates.

## Constraints
- Learner is a Rust novice: every new Rust syntax or concept (`struct`, `enum`, `impl`, `&mut`, lifetimes/borrowing, closures, `Entity<T>`, `IntoElement`) must be unpacked inline right when it first appears.
- macOS desktop target with `rustc 1.100.0` / `cargo 1.100.0` and `gpui-kit`.

## Out of scope
- Custom GPU shaders or low-level Metal/Vulkan driver programming.
- Modifying the upstream `antigravity-sdk-rust` Go runtime harness (`localharness`) internals before the UI workbench foundation is solid.
