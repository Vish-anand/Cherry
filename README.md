# Cherry AI Agent

Cherry is a local, tool-equipped personal AI assistant and system orchestrator. It combines a FastAPI control hub, a private browser dashboard, document management, voice features, WhatsApp integration, browser automation, and cautious computer-use tools.

## Features

- Workspace tools for reading, writing, patching, and organizing files.
- Multimodal document vault for uploading, classifying, indexing, and searching local documents.
- Agent loop with streaming responses and safety-gated execution for risky actions.
- Browser automation through Playwright.
- Screen observation, mouse, keyboard, and system-control helpers.
- Voice input/output support with local and remote voice options.
- WhatsApp bridge using `whatsapp-web.js`.

## Project Layout

```text
Cherry/
  agent/              Core agent loop, tools, memory, LLM, screen-action helpers
  private/            Authenticated dashboard UI
  static/             Public pages and shared static assets
  tests/              Unit tests for agent, voice, browser, and screen tools
  scratch/            Local experiments
  plans/              Planning notes
  app.py              FastAPI application entry point
  voice_tool.py       Text-to-speech helpers
  whatsapp_bridge.js  WhatsApp Web bridge process
```

Generated runtime state is intentionally ignored by git, including `node_modules/`, `.wwebjs_auth/`, `screenshots/`, `voice_models/`, database files, logs, local audio, and `.env`.

## Setup

### 1. Create and activate a Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Install Node dependencies

```powershell
npm install
```

### 4. Install Playwright browsers

```powershell
playwright install chromium
```

### 5. Configure environment variables

Copy the example file and add your local settings:

```powershell
Copy-Item .env.example .env
```

At minimum, set one supported model provider key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Optional OpenAI/OpenRouter fallback:

```env
OPENAI_API_KEY=your_openrouter_or_openai_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=google/gemini-2.5-flash
```

Recommended local protection:

```env
CHERRY_PASSWORD=choose_a_strong_local_password
WORKSPACE_ROOT=C:\Users\Admin\Desktop\Cherry
```

## Run

Start the FastAPI server:

```powershell
python app.py
```

Open the app:

```text
http://localhost:8001
```

Start the WhatsApp bridge in a separate terminal when needed:

```powershell
node whatsapp_bridge.js
```

## Test

Run the unit test suite:

```powershell
python -m unittest discover -s tests
```

If the browser test fails because Chromium is missing, run:

```powershell
playwright install chromium
```

## Notes

- Cherry can execute powerful local tools. Keep the dashboard password protected and avoid exposing the server outside your trusted machine or network.
- `.wwebjs_auth/` stores local WhatsApp browser session state. It is private runtime data and should not be committed.
- `voice_models/` can contain large local model binaries. Keep them local unless you intentionally publish a separate model artifact.
