# Comprehensive Architectural & Implementation Blueprint for "Cherry"
## The Autonomous System-Level Personal OS Agent Framework

---

## 1. Executive Summary & Vision

**Cherry** is envisioned not merely as a conversational text assistant or an LLM wrapper, but as an **Autonomous OS Agent (Computer Use Agent)**. Cherry operates directly within the user's local operating system environment, possessing capabilities analogous to a human operator: observing visual layouts, manipulating input devices natively with human-like ergonomics, managing persistent short- and long-term memories, and orchestrating specialized subordinate agent clusters to execute multi-step digital workflows securely.

This blueprint outlines a complete, production-ready, step-by-step engineering architecture to build Cherry from foundation to full operational autonomy.

---

## 2. Core Architecture & Cognitive Engine

Cherry relies on a decoupled, asynchronous engineering architecture. The system separates the cognitive engine (the LLM/VLM "Brain") from the execution environment (the "Body").

```
         +-------------------------------------------------+
         |              User Prompt / Interface            |
         +-------------------------------------------------+
                                  │
                                  ▼
         +-------------------------------------------------+
         |           Cherry Conductor Agent (Brain)        |
         +-------------------------------------------------+
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
+-------------------------+ +-------------------------+ +-------------------------+
|     Memory Subsystem    | |  Multi-Agent Router   | |   Execution Framework   |
| (Short/Long/Episodic)   | | (Specialist Workers)  | |   (Local OS & Tools)    |
+-------------------------+ +-------------------------+ +-------------------------+
```

### 2.1 The Cognitive Agentic Loop (ReAct Framework)
Cherry uses a refined **Reasoning-and-Action (ReAct)** loop driven by state machines to prevent open-ended execution drift:
1. **Perceive:** Capture system state (CLI buffers, active processes, screen captures).
2. **Contextualize:** Rehydrate short-term state, pull vector embeddings from long-term storage, evaluate system permissions.
3. **Plan:** Deconstruct the user's macro-instruction into a finite directed acyclic graph (DAG) of micro-tasks.
4. **Select Tool / Action:** Emits a structured tool call or payload (JSON schema / native function calling).
5. **Execute & Observation:** Run the tool locally, catch stdout/stderr/exceptions, update state.
6. **Self-Evaluate:** Verify if tool execution matches the expected outcome. If an error is caught, perform localized self-correction or rewrite the local DAG dynamically.

### 2.2 Core Framework Foundations
* **Primary Framework:** **LangGraph** (built on top of LangChain). LangGraph is chosen over basic linear agents because it provides cyclical graph architectures. This allows Cherry to enter a loop of testing code, observing errors, self-correcting, and retrying dynamically without resetting context.
* **Multi-Agent Coordination:** **CrewAI** or **Autogen** nodes integrated as specialized sub-graphs within LangGraph.
* **Data Parsing:** **LlamaIndex** for semantic orchestration when ingestion of unstructured files (PDFs, multi-page CSVs, enterprise documents) is requested.

---

## 3. Human-Like Physical Automation Layer

To execute tasks across non-API legacy interfaces (like university portals or local desktop software), Cherry requires a high-fidelity **Vision-to-Action** framework.

### 3.1 Live Mouse Pointer Ergonomics (Bézier Curve Engine)
Instant cursor "teleportation" flags security software and risks UI parsing errors. Cherry implements a mathematical interpolation engine using cubic and quadratic Bézier curves coupled with non-linear easing functions (e.g., Ease-In-Out) and micro-jitters to mimic biological human movement.

```python
import pyautogui
import numpy as np
import time
import random
from scipy.interpolate import make_interp_spline

def human_like_mouse_move(target_x, target_y, duration_min=0.4, duration_max=0.9):
    start_x, start_y = pyautogui.position()
    if start_x == target_x and start_y == target_y:
        return

    # Establish randomized displacement control points for curve variation
    control_x = (start_x + target_x) / 2 + random.randint(-75, 75)
    control_y = (start_y + target_y) / 2 + random.randint(-75, 75)

    x_seq = np.array([start_x, control_x, target_x])
    y_seq = np.array([start_y, control_y, target_y])

    # Construct parametric timeline
    t_points = np.array([0.0, 0.4, 1.0])
    num_steps = random.randint(25, 45)
    t_interpolated = np.linspace(0.0, 1.0, num=num_steps)

    # Generate Spline Profile
    spline_x = make_interp_spline(t_points, x_seq, k=2)(t_interpolated)
    spline_y = make_interp_spline(t_points, y_seq, k=2)(t_interpolated)

    # Dynamic execution with variable micro-pauses (Biological Easing)
    total_duration = random.uniform(duration_min, duration_max)
    step_delay = total_duration / num_steps

    for x, y in zip(spline_x, spline_y):
        pyautogui.moveTo(int(x), int(y))
        # Introduce micro-jittering to simulate human muscle tremor
        time.sleep(step_delay + random.uniform(-0.002, 0.002))

    # Micro-pause adjustment directly preceding interaction
    time.sleep(random.uniform(0.12, 0.28))
```

### 3.2 Humanized Input Interactivity

* **Variable Mechanical Typing:** Text insertion avoids monolithic clipboard pasting. Characters are dispatched down the OS keyboard buffer one by one, using Gaussian distributions to space out keypress delays.
* **Contextual Overrides:** If writing large blocks of source code into an IDE, Cherry temporarily bypasses the slow key-by-key typing mechanism. It shifts to a fast clipboard transfer script, simulating a developer executing a copy-paste chunk.

### 3.3 Visual Screen Ingestion

* **The Engine:** A localized loop pulling high-resolution display buffers via `Pillow` or `MSS`.
* **VLM Interpretation:** The screenshot is downsampled intelligently, structured with a dynamic bounding-box grid or **Set-of-Mark (SoM)** visual overlay, and dispatched to a Vision-Language Model (e.g., Claude 3.5 Sonnet or a local fine-tuned Omni-model). The model responds with standardized JSON bounding-box coordinates for its next interaction target.

---

## 4. System-Level Integration & Native Tooling

Cherry requires full integration with local OS binaries and APIs to act as a system-level agent.

### 4.1 Local OS Utilities Engine

A dedicated tool set wraps shell executions securely through an isolated Python subprocess orchestration system.

* **System Hardware Controls:** Adjusting native master volume configurations via platform-specific controls (`ctypes` bindings for Windows Core Audio APIs, `osascript` calls on macOS, or `amixer/pactl` commands on Linux distributions).
* **Native App Lifecycle Manager:** Allows checking for software installations, parsing package registers, and running system installers directly (`brew install` on macOS, `winget install` on Windows, or `apt-get` on Linux systems).

### 4.2 Web Scraping & Deep Web Task Automation

When headless API routes are unavailable (such as authentication-walled university portals), Cherry launches specialized automated browser drivers.

* **Framework:** **Playwright** (Python bindings). Playwright is chosen over Selenium due to its modern async architecture and reliable context isolation.
* **Execution Strategy:** Cherry runs an automated Chromium or Firefox browser instance. It injects user credentials retrieved securely from the credential vault, interacts with dynamically rendered elements, watches network payloads to capture API data, and reads text directly out of the page DOM.

### 4.3 Workspace & DevOps Pipeline Automation

* **Automated Workspace Coding:** A Sandboxed Execution Environment using local Docker instances or isolated virtual environment runtimes (`venv`). Cherry writes code files, runs them via Python or chosen runtimes, captures terminal stack traces, and iterates on fixes until execution returns zero errors.
* **Git Lifecycle Toolset:** Native wrapper execution functions linking directly into local Git configurations. Cherry can systematically perform operations like `git status`, track modified files via `git add`, generate descriptive summaries for `git commit -m`, and securely push code to remote repositories with `git push`.

### 4.4 Communication Integration

* **Unified Email Connector:** Connects to standard mail networks via Python's asynchronous `aiosmtplib` and `imapclient` libraries over TLS. Cherry routes automated notifications, parses inbox subjects, and builds structured file attachments programmatically.
* **WhatsApp Personal Loop:** Built using **Playwright-driven WhatsApp Web automation** or authenticated local network relays. This structure allows Cherry to query active contacts, hook into browser attachments, upload local project files, and submit textual status updates on demand.

---

## 5. Layered Advanced Memory Architecture

To act as a truly intelligent personal assistant, Cherry avoids running out of context window space by storing information across three decoupled abstraction layers.

| Memory Type | Scope & Horizon | Technical Stack | Purge Trigger |
| --- | --- | --- | --- |
| **Short-Term Memory** | Immediate runtime conversation state and step-by-step agent task progression. | Redis / In-Memory LangGraph State Management. | End of current task session or chat interaction. |
| **Long-Term Memory** | Implicit user preferences, profile configurations, credentials, and explicit knowledge facts. | **ChromaDB** / **Pinecone** / Local **pgvector** using semantic embedding models. | Never. Updated via continuous background optimization. |
| **Episodic Memory** | History of complex multi-step tasks, successful code executions, and error-recovery paths. | Structured JSON-LD documents stored inside an embedded relational DB (**SQLite**). | Explicit user manual flush or storage capacity bounds. |

### 5.1 Memory Synchronization Flow

When a user provides an instruction, Cherry performs an asynchronous vector search across its long-term database to pull relevant user preferences or historic variables. This contextual data is injected directly into the system prompt context.

As tasks finish, Cherry passes its runtime execution logs to a background summary agent. This agent extracts key learned patterns and updates the vector database, allowing Cherry to get smarter over time without bloating its active memory.

---

## 6. Multi-Agent Specialist Decomposition

To prevent single-prompt confusion, the macro entity "Cherry" serves as a **Conductor Agent**, delegating specialized tasks to an isolated cluster of subordinate worker nodes.

```
                  +──────────────────────────────+
                  │    Cherry Conductor Agent    │
                  +──────────────────────────────+
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
+──────────────────+     +──────────────────+     +──────────────────+
|  OS & Automation |     | Software Dev Box |     |  Deep Web Scraper|
|     Specialist   |     |    Specialist    |     |    Specialist    |
+──────────────────+     +──────────────────+     +──────────────────+
| Controls mouse,  |     | Writes, runs,    |     | Puppets browser  |
| keyboard, sound  |     | and debugs code  |     | sessions to bypass|
| and system apps  |     | in a sandbox     |     | legacy firewalls |
+──────────────────+     +──────────────────+     +──────────────────+
```

1. **The Conductor (The Router Layer):** Directly interfaces with the user, handles voice and text conversion, manages memory updates, splits complex jobs into granular sub-tasks, and balances processing loads between worker nodes.
2. **OS & Automation Specialist:** Has dedicated access to hardware controls, Bézier curve mouse tracking engines, volume scripts, and shell utilities.
3. **Software Dev Box Specialist:** Operates within an isolated runtime container. It writes, tests, evaluates, and pushes code patches to remote repositories without touching production host files.
4. **Deep Web Scraper Specialist:** Controls browser sessions via Playwright, bypasses legacy site structures, handles multi-factor web forms, and turns unstructured page layouts into clean JSON data.

---

## 7. Security Architecture & Guardrails

Giving an agent root-level GUI and terminal access presents substantial security risks. Cherry mitigates these with strict, non-negotiable security boundaries built into its runtime layer.

### 7.1 Hardened Local Credential Vault

* **Zero Plaintext Passwords:** Cherry is blocked from writing down or printing passwords in log files, prompts, or standard configuration documents.
* **Cryptographic Access:** Passwords and API secrets are locked inside the local machine's hardware-backed secure storage (such as Windows Credential Manager or macOS Keychain), accessed programmatically using the verified Python `keyring` library. Cherry requests the key at runtime, feeds it straight into the automation memory buffer, and clears the variable from system memory immediately after use.

### 7.2 Defending Against Prompt Injection

If Cherry opens a webpage or parses an incoming email containing hidden malicious instructions, it faces a Prompt Injection risk.

* **Dual-Context Isolation:** Cherry uses a strict architecture separating untrusted inputs (web text, emails, external files) from core system prompt logic. Untrusted text is treated purely as sandboxed data and is never passed to execution engines as direct system commands.
* **Structural Input Sanitation:** RegEx filters and validation guardrails check all data coming from external sources before it reaches Cherry's primary reasoning loop.

### 7.3 Human-in-the-Loop (HITL) Policy

Cherry categorizes system tools into clear risk tiers to prevent accidental damage or data loss:

```
[Tool Call Triggered]
         │
         ├──► Low-Risk Tool (Read text, check volume, compile local file)
         │    └──► Auto-Execute Natively (No User Delay)
         │
         └──► High-Risk Tool (Write file to system, run terminal shell, git push, submit form)
              └──► Suspend Agent Loop ──► Prompt User Confirmation [Y/N] ──► Execute on Approval
```

---

## 8. Milestone Roadmap for Development

```
Phase 1: Foundation (Weeks 1-3)
├── Establish LangGraph core execution loop
└── Build encrypted credential storage using local system keyring

Phase 2: Local & Physical Automation (Weeks 4-6)
├── Deploy Bézier curve engine and human-like typing tools
└── Connect visual screenshot capture with multi-modal VLM parsing

Phase 3: Deep Web & Systems Tools (Weeks 7-9)
├── Build Playwright browser automation engines (University login scripts)
└── Integrate Git wrappers and sandboxed terminal runtimes

Phase 4: Multi-Agent Deployment & Memory (Weeks 10-12)
├── Split logic into Conductor and specialized Worker clusters
└── Set up pgvector/ChromaDB episodic memory optimization layers
```

---

## 9. Comprehensive Tool, Library & Framework Reference Index

To build Cherry to its full potential, use this foundational software stack:

### Core Orchestration

* `langgraph` - Advanced cyclical agent graphs and runtime loop management.
* `langchain` / `langchain-core` - Modular components for LLM connectivity.
* `crewai` / `autogen` - Scalable multi-agent team hierarchies.
* `llamaindex` - RAG pipeline ingestion for internal personal files.

### Vision & Physical Automation

* `pyautogui` - Cross-platform programmatic mouse clicks and keyboard entry.
* `scipy` / `numpy` - Vector calculations and Bézier curve spline interpolation.
* `pillow` / `mss` - Rapid screen capture tools and image preprocessing.
* `keyboard` / `pynput` - Global system keyboard hooks for emergency kill switches.

### Web & Network Utilities

* `playwright` - Modern async web browser automation and page scraping.
* `aiosmtplib` / `imapclient` - Secure async email processing networks.
* `requests` / `httpx` - Multi-threaded API calls and endpoint interactions.

### Local Storage & Cryptography

* `keyring` - Secure platform-native credential management hooks.
* `chromadb` / `pinecone-client` - Vector storage for long-term memory.
* `sqlite3` - Local relational engine for structured logging and episodic history records.
