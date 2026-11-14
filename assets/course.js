(() => {
  "use strict";

  const PRISM_BASE = "https://cdn.jsdelivr.net/npm/prismjs@1.29.0";
  const MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  async function initPrism() {
    if (!document.querySelector("pre code")) return;
    window.Prism = window.Prism || {};
    window.Prism.manual = true;
    try {
      await loadScript(`${PRISM_BASE}/components/prism-core.min.js`);
      await loadScript(`${PRISM_BASE}/components/prism-clike.min.js`);
      await Promise.all([
        loadScript(`${PRISM_BASE}/components/prism-rust.min.js`),
        loadScript(`${PRISM_BASE}/components/prism-toml.min.js`),
        loadScript(`${PRISM_BASE}/components/prism-bash.min.js`),
        loadScript(`${PRISM_BASE}/plugins/keep-markup/prism-keep-markup.min.js`),
      ]);
      document.querySelectorAll("pre code").forEach((codeEl) => {
        window.Prism.highlightElement(codeEl);
      });
    } catch (_err) {
      // Offline fallback: leave clean semantic monospace blocks unhighlighted.
    }
  }

  async function initMermaid() {
    const graphs = document.querySelectorAll("pre.mermaid");
    if (!graphs.length) return;
    try {
      const mod = await import(MERMAID_URL);
      const mermaid = mod.default;
      mermaid.initialize({
        startOnLoad: false,
        theme: "dark",
        securityLevel: "loose",
      });
      await mermaid.run({ nodes: graphs });
    } catch (_err) {
      // Offline fallback: pre.mermaid preserves readable source.
    }
  }

  function makeCodeBlocksKeyboardScrollable() {
    document.querySelectorAll("pre").forEach((pre) => {
      if (!pre.hasAttribute("tabindex") && !pre.classList.contains("mermaid")) {
        pre.setAttribute("tabindex", "0");
      }
    });
  }

  function initSidenotes() {
    document.querySelectorAll(".sidenote-number").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("aria-controls");
        const note = targetId ? document.getElementById(targetId) : null;
        if (!note) return;
        const expanded = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", String(!expanded));
        note.classList.toggle("is-open", !expanded);
      });
    });
  }

  function initExercises() {
    document.querySelectorAll(".exercise-card").forEach((card) => {
      const inputs = Array.from(card.querySelectorAll(".blank-input"));
      const checkBtn = card.querySelector(".btn-check");
      const resetBtn = card.querySelector(".btn-reset");
      const feedback = card.querySelector(".exercise-feedback");

      if (!checkBtn || !feedback) return;

      checkBtn.addEventListener("click", () => {
        let allCorrect = true;
        let firstHint = "";

        inputs.forEach((input) => {
          const accepted = (input.dataset.answer || "")
            .split("||")
            .map((s) => s.trim());
          const actual = input.value.trim();
          const ok = accepted.includes(actual);
          input.classList.toggle("is-correct", ok);
          input.classList.toggle("is-wrong", !ok);
          if (!ok) {
            allCorrect = false;
            if (!firstHint) {
              firstHint = input.dataset.hint || card.dataset.hint || "Check the syntax.";
            }
          }
        });

        if (allCorrect) {
          feedback.className = "exercise-feedback feedback-ok";
          feedback.textContent = card.dataset.success || "All blanks verified!";
        } else {
          feedback.className = "exercise-feedback feedback-err";
          feedback.textContent = `Hint: ${firstHint}`;
        }
      });

      if (resetBtn) {
        resetBtn.addEventListener("click", () => {
          inputs.forEach((input) => {
            input.value = "";
            input.classList.remove("is-correct", "is-wrong");
          });
          feedback.textContent = "";
          feedback.className = "exercise-feedback";
        });
      }
    });
  }

  function initQuizzes() {
    document.querySelectorAll(".quiz-card").forEach((card) => {
      const questions = Array.from(card.querySelectorAll(".quiz-question"));
      const scoreEl = card.querySelector(".quiz-score");
      const solved = new Set();

      questions.forEach((qEl) => {
        const qIndex = qEl.dataset.qIndex;
        const buttons = Array.from(qEl.querySelectorAll(".quiz-option"));
        const fb = qEl.querySelector(".quiz-feedback");
        const wrongHint = qEl.dataset.wrongHint || "Try another option.";

        buttons.forEach((btn) => {
          btn.addEventListener("click", () => {
            buttons.forEach((b) => b.classList.remove("is-correct", "is-wrong"));
            const isCorrect = btn.dataset.correct === "true";
            const explain = btn.dataset.explain || "";
            if (isCorrect) {
              btn.classList.add("is-correct");
              fb.className = "quiz-feedback feedback-ok";
              fb.textContent = explain || "Correct.";
              solved.add(qIndex);
            } else {
              btn.classList.add("is-wrong");
              fb.className = "quiz-feedback feedback-err";
              fb.textContent = `${explain} ${wrongHint}`.trim();
            }
            if (scoreEl) {
              scoreEl.textContent = `Progress: ${solved.size} / ${questions.length} verified`;
            }
          });
        });
      });
    });
  }

  function initGpuiLifecycleSim() {
    const stages = [
      {
        title: "1. Application Boot (`gpui_kit::application().with_assets(...).run(|cx| ...)`) ",
        handle: "cx: &mut App",
        layer: "gpui / gpui-platform",
        ownership: "OS event loop owns the App; your closure receives a temporary mutable borrow (&mut App).",
        detail: "Registers bundled icons (gpui_kit::assets::Assets) and enters the native macOS/Windows/Linux event loop.",
      },
      {
        title: "2. Kit Initialization (`gpui_kit::init(cx)`)",
        handle: "cx: &mut App",
        layer: "gpui-base + gpui-component",
        ownership: "Passes the mutable borrow &mut App down into GPUI Kit's global theme and component registries.",
        detail: "Must run once before opening any window so default dark/light themes, keybindings, and input actions exist.",
      },
      {
        title: "3. Window & Root Overlay (`gpui_kit::open_window(..., cx, |_, cx| ...)`) ",
        handle: "window: &mut Window, cx: &mut App",
        layer: "gpui_kit::component::Root",
        ownership: "GPUI Kit spawns the native window and automatically wraps your view inside Root.",
        detail: "Root anchors dialogs, sheets, popovers, and toast notifications on top of your custom WorkbenchView.",
      },
      {
        title: "4. Entity Allocation (`cx.new(|_cx| WorkbenchView::new())`)",
        handle: "Returns Entity<WorkbenchView>",
        layer: "GPUI Entity Store",
        ownership: "GPUI owns the WorkbenchView struct in its arena and hands you a cheap copyable Entity<WorkbenchView> handle.",
        detail: "Avoids tangled Rust lifetime annotations across callbacks—views ask GPUI to borrow or mutate state safely via cx.",
      },
      {
        title: "5. Frame Rendering (`impl Render for WorkbenchView`)",
        handle: "&mut self, _window: &mut Window, _cx: &mut Context<Self>",
        layer: "gpui Element Tree",
        ownership: "GPUI borrows your struct mutably (&mut self) to build a declarative tree (impl IntoElement) at up to 120 FPS.",
        detail: "Returns flex containers (div().flex()...) and styled components (Button::new(...).primary()) to GPU layout & paint.",
      },
    ];

    document.querySelectorAll('[data-widget="gpui-lifecycle-sim"]').forEach((root) => {
      const btns = Array.from(root.querySelectorAll(".sim-step-btn"));
      const stageEl = root.querySelector(".sim-stage");
      if (!stageEl || !btns.length) return;

      function renderStage(idx) {
        const s = stages[idx];
        btns.forEach((b, i) => {
          const active = i === idx;
          b.classList.toggle("is-active", active);
          b.setAttribute("aria-selected", String(active));
        });
        stageEl.innerHTML = "";

        const heading = document.createElement("h4");
        heading.style.marginBlock = "0 0.5rem";
        heading.textContent = s.title;

        const desc = document.createElement("p");
        desc.style.marginBlock = "0 0.85rem";
        desc.textContent = s.detail;

        const grid = document.createElement("div");
        grid.className = "sim-grid";

        const items = [
          ["Active Rust Handle", s.handle],
          ["GPUI Kit Layer", s.layer],
          ["Ownership Model", s.ownership],
        ];
        items.forEach(([k, v]) => {
          const box = document.createElement("div");
          box.className = "sim-kv";
          const kEl = document.createElement("span");
          kEl.className = "sim-k";
          kEl.textContent = k;
          const vEl = document.createElement("span");
          vEl.className = "sim-v";
          vEl.textContent = v;
          box.append(kEl, vEl);
          grid.appendChild(box);
        });

        stageEl.append(heading, desc, grid);
      }

      btns.forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.dataset.step || "0");
          renderStage(idx);
        });
      });

      renderStage(0);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    makeCodeBlocksKeyboardScrollable();
    initSidenotes();
    initExercises();
    initQuizzes();
    initGpuiLifecycleSim();
    initPrism();
    initMermaid();
  });
})();
