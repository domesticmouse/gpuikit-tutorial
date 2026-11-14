# GPUI Kit Tutorial — Antigravity Markdown & Conversation Workbench

An interactive, stateful Rust & **GPUI Kit** (`longbridge/gpui-kit`) course designed for Rust novices building desktop interfaces around `antigravity-sdk-rust`.

## Lessons

| Lesson | Topic | Companion App |
| :--- | :--- | :--- |
| [0001 — Bootstrap the Workbench Shell](lessons/0001-bootstrap-workbench-shell.md) | GPUI Kit layers, `Root` window lifecycle, Rust structs/enums/traits, and `cargo test` + `clippy` gates | [`apps/0001-bootstrap-workbench-shell`](apps/0001-bootstrap-workbench-shell) |

## Reference Sheets

- [Glossary of GPUI Kit & Rust UI Terms](reference/GLOSSARY.md)
- [GPUI Kit & Rust Quick Reference](reference/gpui-kit-cheatsheet.md)

## Quickstart

Compile and validate the HTML course site locally:

```bash
uv venv .venv
uv pip install --python .venv/bin/python markdown-it-py pyyaml
.venv/bin/python build.py --check
```

Run tests and strict lints for Lesson 0001:

```bash
cargo test --manifest-path apps/0001-bootstrap-workbench-shell/Cargo.toml
cargo clippy --manifest-path apps/0001-bootstrap-workbench-shell/Cargo.toml --all-targets -- -D warnings
```
