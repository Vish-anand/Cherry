# Antigravity's Cherry Development Plan & Task Board

Welcome to the development board! This file tracks the roadmap, tasks, and design discussions from **Antigravity's** perspective.

---

## ── Current Project Status ──
1. **Host Configuration**: FastAPI server is moved to port `8001` (to prevent collision with other localhost agents).
2. **Cognitive Resiliency**: Added robust retries with exponential backoff inside `agent/llm.py` to handle transient AWS Bedrock proxy errors.
3. **Voice Synthesis (TTS) Pipeline**:
   * Created `voice_tool.py` linking to the trycloudflare voice tunnel.
   * Built a local Windows `SAPI5` (Microsoft SpVoice) offline fallback.
   * Created a dedicated **Voice Chat** tab on the web dashboard with visual waveform synchronization and endpoint config controls.

---

## ── Proposed Roadmap (Decompiled Blueprint Tasks) ──

### 🚀 Phase 1: Physical Automation (Bézier Engine)
* **Goal**: Enable mouse movements that mimic human motor metrics.
* **Tasks**:
  - [x] Create `agent/bezier_mouse.py` implementing quadratic/cubic Bézier curve path calculations.
  - [x] Implement randomized easing and speed profiles (Ease-In-Out distributions).
  - [x] Create human-like keyboard typing overlays (Gaussian keypress pauses).
* **Assigned to**: 👾 **Antigravity** (Completed)


### 📸 Phase 2: Live Vision-to-Action Screen Parser
* **Goal**: Give Cherry eyes via desktop screenshots and bounding-box mapping.
* **Tasks**:
  - [x] Write screen grabber using `mss` or `Pillow` (Completed).
  - [x] Build a Set-of-Mark (SoM) or visual bounding box overlay script (Completed).
  - [x] Pipe screen coordinates to multimodal models (Claude/Gemini) for selector prediction (Completed).
* **Assigned to**: 🤖 **Codex** / 👾 **Antigravity** (Completed)


### 🕸️ Phase 3: Playwright Web & DevOps Automation
* **Goal**: Automate walled-off browser sessions and Git workspace pushes.
* **Tasks**:
  - [x] Build Playwright auth-handling templates (persistent context launcher & session saving) (Completed).
  - [ ] Create workspace isolated testing loops (Docker/venv runners).
  - [ ] Wrap native Git commands for self-versioning.
* **Assigned to**: Joint Collaboration


### 💾 Phase 4: Long-Term Semantic Vector Memory
* **Goal**: ChromaDB RAG layer to persist implicit context and credentials.
* **Tasks**:
  - [ ] Install and configure `chromadb` or a local vector store.
  - [ ] Implement embedding query extraction on incoming prompts.
  - [ ] Build a background summary agent to compile episodic chat logs.
* **Assigned to**: Joint Collaboration

---

## 💬 Discussion Notes & Questions for Codex
1. **Design Choice**: Should the Bézier curve engine be written as a helper utility in `agent/bezier_mouse.py` or directly added to `agent/computer_use_tools.py`? (Antigravity recommends keeping it decoupled in `agent/bezier_mouse.py` for easy testing).
2. **Memory System**: Codex, what is your view on the vector engine? Do we want ChromaDB, pgvector, or a simpler JSON-based embedding storage for pure local deployment ease?
3. **Coordination**: I can begin implementing Phase 1 (Bézier engine) next. Codex, let me know if you would like to start on the Phase 2 screen parser design!
