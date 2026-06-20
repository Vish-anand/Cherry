# 🍒 Cherry AI Agent

Cherry is an autonomous, tool-equipped AI personal assistant and system orchestrator. It runs locally on your machine and combines **workspace file editing**, **academic research**, **dynamic browser automation**, and a **multimodal document library** under a premium, clean off-black web dashboard.

---

## 🛠️ Features

1.  **Workspace File Manager:** Edit, patch, create, and browse folders anywhere on your local computer.
2.  **Multimodal Document Vault:** Upload invoices, marklists, and receipts. Cherry automatically classifies the files, extracts metadata (date, amount, company), and indexes them for semantic natural language queries.
3.  **System Volume & Printer Hooks:** Adjust hardware volume and trigger print jobs via chat commands.
4.  **Browser Automation:** Spawns Playwright scripts dynamically to log into web portals, scrape pages, and bypass login walls.
5.  **WhatsApp Mock Sandbox:** Test incoming media and text webhook payloads locally.

---

## 🚀 Setup & Installation (Step-by-Step)

Follow these steps to run Cherry on your local machine:

### 1. Clone the Repository
Open a terminal and clone this repository:
```bash
git clone https://github.com/Vish-anand/Cherry.git
cd Cherry
```

### 2. Create a Virtual Environment
Create a clean virtual environment to isolate the project packages:
```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment
Activate the environment based on your operating system:
*   **Windows (PowerShell):**
    ```powershell
    .venv\Scripts\Activate.ps1
    ```
*   **Windows (Command Prompt):**
    ```cmd
    .venv\Scripts\activate.bat
    ```
*   **macOS / Linux:**
    ```bash
    source .venv/bin/activate
    ```

### 4. Install Dependencies
Install the required packages:
```bash
pip install -r requirements.txt
```

### 5. Install Playwright Browsers
Install the browser engine required for the web automation tools:
```bash
playwright install chromium
```

### 6. Configure API Keys
1.  Copy the environment variables template:
    ```bash
    cp .env.example .env
    ```
2.  Open the newly created `.env` file and insert your API Key:
    *   **Native Gemini Key (Recommended):**
        ```env
        GEMINI_API_KEY=your_gemini_api_key_here
        ```
    *   **OpenRouter / OpenAI Fallback:**
        ```env
        OPENAI_API_KEY=your_openrouter_api_key_here
        OPENAI_BASE_URL=https://openrouter.ai/api/v1
        OPENAI_MODEL=google/gemini-2.5-flash
        ```

### 7. Run the Server
Launch the FastAPI backend server:
```bash
python app.py
```

### 8. Access the Dashboard
Open your web browser and navigate to:
👉 **`http://localhost:8000/static/index.html`**
