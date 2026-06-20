import os
import sys
import shutil
import json
import inspect
import subprocess
import urllib.parse
from datetime import datetime
from agent.llm import call_llm
from agent.memory import index_document, search_documents as db_search_documents, list_documents as db_list_documents

WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", r"c:\Users\Admin\Desktop\Cherry")
DOCUMENTS_ROOT = os.path.join(WORKSPACE_ROOT, "documents")
INCOMING_DIR = os.path.join(WORKSPACE_ROOT, "incoming")

# Ensure base folders exist
for folder in ["bills", "education", "identity", "receipts", "uncategorized"]:
    os.makedirs(os.path.join(DOCUMENTS_ROOT, folder), exist_ok=True)
os.makedirs(INCOMING_DIR, exist_ok=True)

TOOL_REGISTRY = {}

def register_tool(name, description, parameters):
    def decorator(func):
        TOOL_REGISTRY[name] = {
            "func": func,
            "name": name,
            "description": description,
            "parameters": parameters
        }
        return func
    return decorator

# ==========================================
# WORKSPACE TOOLS
# ==========================================

@register_tool(
    name="list_workspace_files",
    description="List files and directories in a directory (absolute path or relative to workspace). Defaults to listing the workspace root.",
    parameters={
        "type": "object",
        "properties": {
            "directory_path": {"type": "string", "description": "Optional absolute path or relative path to list (e.g. 'C:\\Users\\Admin\\Desktop'). Defaults to workspace root."}
        },
        "required": []
    }
)
def list_workspace_files(directory_path: str = None):
    target_dir = WORKSPACE_ROOT
    if directory_path:
        target_dir = directory_path if os.path.isabs(directory_path) else os.path.join(WORKSPACE_ROOT, directory_path)
    
    if not os.path.exists(target_dir):
        return f"Error: Directory {target_dir} does not exist."
    
    try:
        items = os.listdir(target_dir)
        results = []
        for item in items:
            item_path = os.path.join(target_dir, item)
            is_dir = os.path.isdir(item_path)
            results.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "path": item_path
            })
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@register_tool(
    name="read_workspace_file",
    description="Read the text content of a file (absolute path or relative to workspace).",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Relative path or absolute system path to read."}
        },
        "required": ["file_path"]
    }
)
def read_workspace_file(file_path: str):
    full_path = file_path if os.path.isabs(file_path) else os.path.join(WORKSPACE_ROOT, file_path)
    if not os.path.exists(full_path):
        return f"Error: File {file_path} does not exist."
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@register_tool(
    name="write_workspace_file",
    description="Create or overwrite a file (absolute path or relative to workspace) with new content.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Relative path or absolute system path to write."},
            "content": {"type": "string", "description": "The exact content to write to the file."}
        },
        "required": ["file_path", "content"]
    }
)
def write_workspace_file(file_path: str, content: str):
    full_path = file_path if os.path.isabs(file_path) else os.path.join(WORKSPACE_ROOT, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote file to {full_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@register_tool(
    name="patch_workspace_file",
    description="Replace a target block of text inside a file (absolute path or relative to workspace) with new content.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Relative path or absolute system path to modify."},
            "target": {"type": "string", "description": "The exact block of code/text to find and replace."},
            "replacement": {"type": "string", "description": "The new replacement text."}
        },
        "required": ["file_path", "target", "replacement"]
    }
)
def patch_workspace_file(file_path: str, target: str, replacement: str):
    full_path = file_path if os.path.isabs(file_path) else os.path.join(WORKSPACE_ROOT, file_path)
    if not os.path.exists(full_path):
        return f"Error: File {file_path} does not exist."
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if target not in content:
            return "Error: The target code block to replace was not found exactly as specified in the file."
        updated_content = content.replace(target, replacement, 1)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        return f"Successfully patched file {full_path}"
    except Exception as e:
        return f"Error patching file: {str(e)}"

# ==========================================
# RESEARCH TOOLS
# ==========================================

@register_tool(
    name="search_arxiv",
    description="Search arXiv for scientific papers, returns title, summary, authors, and PDF links.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query (e.g. 'LLM quantization')."}
        },
        "required": ["query"]
    }
)
def search_arxiv(query: str):
    import urllib.request
    import xml.etree.ElementTree as ET
    
    encoded_query = urllib.parse.quote(query)
    url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&max_results=3"
    try:
        response = urllib.request.urlopen(url)
        xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
        
        papers = []
        for entry in root.findall('atom:entry', namespaces):
            title = entry.find('atom:title', namespaces).text.strip().replace("\n", " ")
            summary = entry.find('atom:summary', namespaces).text.strip().replace("\n", " ")
            id_url = entry.find('atom:id', namespaces).text.strip()
            pdf_url = id_url.replace("abs", "pdf") + ".pdf"
            
            papers.append(f"Title: {title}\nSummary: {summary}\nPDF Link: {pdf_url}\n---")
            
        if not papers:
            return "No papers found for this search query."
        return "\n\n".join(papers)
    except Exception as e:
        return f"Error searching arXiv: {str(e)}"

@register_tool(
    name="scrape_web_page",
    description="Scrape and extract the text content of any website as clean Markdown.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The HTTP/HTTPS URL of the website to scrape."}
        },
        "required": ["url"]
    }
)
def scrape_web_page(url: str):
    import httpx
    from bs4 import BeautifulSoup
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = httpx.get(url, headers=headers, timeout=10.0, follow_redirects=True)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.decompose()
            
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        
        if len(text) > 8000:
            text = text[:8000] + "\n\n...[Truncated due to length]..."
        return text
    except Exception as e:
        return f"Error scraping web page: {str(e)}"

# ==========================================
# SYSTEM TOOLS
# ==========================================

@register_tool(
    name="adjust_system_volume",
    description="Adjust the laptop system volume to an exact percentage (0 to 100).",
    parameters={
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "Volume percentage level (0 to 100)."}
        },
        "required": ["level"]
    }
)
def adjust_system_volume(level: int):
    try:
        import comtypes
        try:
            comtypes.CoInitialize()
        except Exception:
            pass
            
        from pycaw.pycaw import AudioUtilities
        
        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume
        
        # Level must be float 0.0 to 1.0
        val = max(0, min(100, level)) / 100.0
        volume.SetMasterVolumeLevelScalar(val, None)
        return f"System volume set to {level}%."
    except Exception as e:
        # Fallback to powershell keybd_event simulation or print message
        return f"Error modifying volume via Python APIs: {str(e)}."

@register_tool(
    name="print_document",
    description="Send a local document file directly to the default system printer.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute or relative path to the file to print."}
        },
        "required": ["file_path"]
    }
)
def print_document(file_path: str):
    full_path = os.path.join(WORKSPACE_ROOT, file_path) if not os.path.isabs(file_path) else file_path
    if not os.path.exists(full_path):
        return f"Error: Document {file_path} not found."
    try:
        # Windows system print verb trigger
        os.startfile(full_path, "print")
        return f"Document {os.path.basename(full_path)} sent to default system printer successfully."
    except Exception as e:
        return f"Failed to trigger printing: {str(e)}"

@register_tool(
    name="run_browser_automation",
    description="Run custom browser automation code using Playwright and return logs or final findings.",
    parameters={
        "type": "object",
        "properties": {
            "script_code": {"type": "string", "description": "The python code to execute. MUST import 'sync_playwright' from 'playwright.sync_api' and execute inside a try-except block."}
        },
        "required": ["script_code"]
    }
)
def run_browser_automation(script_code: str):
    script_path = os.path.join(WORKSPACE_ROOT, "temp_playwright.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_code)
    try:
        # Run script as external process to prevent parent process crashes
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=60.0)
        os.remove(script_path)
        output = f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}"
        return output
    except Exception as e:
        if os.path.exists(script_path):
            os.remove(script_path)
        return f"Playwright automation timed out or failed: {str(e)}"

@register_tool(
    name="download_youtube_video",
    description="Download a YouTube video given its URL and save it to a workspace folder.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL of the YouTube video to download."},
            "folder_name": {"type": "string", "description": "Name of the folder inside Cherry to save the download."}
        },
        "required": ["url", "folder_name"]
    }
)
def download_youtube_video(url: str, folder_name: str):
    import yt_dlp
    output_dir = os.path.join(WORKSPACE_ROOT, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return f"Successfully downloaded YouTube video: '{info.get('title')}' and saved to {os.path.relpath(filename, WORKSPACE_ROOT)}"
    except Exception as e:
        return f"Error downloading video: {str(e)}"

# ==========================================
# DOCUMENT ORGANIZER TOOLS
# ==========================================

@register_tool(
    name="classify_and_organize_document",
    description="Run multimodal analysis to classify an incoming document (PDF/Image), extract details, index it, and organize it.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Relative or absolute path of the raw file to organize."}
        },
        "required": ["file_path"]
    }
)
def classify_and_organize_document(file_path: str):
    full_path = os.path.join(WORKSPACE_ROOT, file_path) if not os.path.isabs(file_path) else file_path
    if not os.path.exists(full_path):
        return f"Error: Document {file_path} not found."
        
    filename = os.path.basename(full_path)
    
    # Try parsing text for better indexing if PDF
    extracted_text = ""
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(full_path)
            for page in reader.pages:
                extracted_text += page.extract_text() or ""
        except Exception:
            pass

    # Prompt the LLM to identify the document type and return structured details
    system_inst = "You are an expert document manager. Analyze the document (PDF or Image) and organize its contents."
    prompt = """
    Analyze the document. Categorize it into one of these exact categories: 'bills', 'education', 'identity', 'receipts', 'uncategorized'.
    Also generate:
    1. A clean, standard filename based on the document type, date, or subject (e.g. '2026-05_electricity_bill.pdf', 'university_marklist.jpg'). Do not use spaces, use underscores.
    2. An extraction schema in JSON formatting containing:
       - document_type (e.g. 'Marksheet', 'Electricity Bill', 'Salary Slip')
       - date_issued (YYYY-MM-DD or null)
       - summary (1-2 sentences of contents)
       - amount_due_or_paid (float value or null if not financial)
       - primary_name (person's name or company name associated)
    
    Respond strictly with a JSON matching this structure:
    {
      "category": "bills",
      "clean_filename": "2026-05_electricity_bill.pdf",
      "metadata": {
         "document_type": "Electricity Bill",
         "date_issued": "2026-05-15",
         "summary": "Electricity bill for house 42",
         "amount_due_or_paid": 125.40,
         "primary_name": "PowerCorp"
      }
    }
    """
    
    try:
        response_text = call_llm(
            prompt=prompt,
            system_instruction=system_inst,
            attachment_path=full_path,
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "category": {"type": "STRING"},
                    "clean_filename": {"type": "STRING"},
                    "metadata": {
                        "type": "OBJECT",
                        "properties": {
                            "document_type": {"type": "STRING"},
                            "date_issued": {"type": "STRING"},
                            "summary": {"type": "STRING"},
                            "amount_due_or_paid": {"type": "NUMBER"},
                            "primary_name": {"type": "STRING"}
                        },
                        "required": ["document_type", "summary", "primary_name"]
                    }
                },
                "required": ["category", "clean_filename", "metadata"]
            }
        )
        
        classification = json.loads(response_text)
        category = classification.get("category", "uncategorized")
        clean_name = classification.get("clean_filename", filename)
        doc_metadata = classification.get("metadata", {})
        
        # Ensure clean name matches extension
        if not clean_name.endswith(ext):
            clean_name = os.path.splitext(clean_name)[0] + ext
            
        target_dir = os.path.join(DOCUMENTS_ROOT, category)
        target_path = os.path.join(target_dir, clean_name)
        
        # Move the file
        shutil.move(full_path, target_path)
        
        # Index in memory db
        rel_target_path = os.path.relpath(target_path, WORKSPACE_ROOT)
        index_document(
            filename=clean_name,
            original_name=filename,
            file_path=rel_target_path,
            category=category,
            extracted_text=extracted_text,
            doc_metadata=doc_metadata
        )
        
        return f"Successfully classified and organized file '{filename}' into '{category}/{clean_name}'\nMetadata: {json.dumps(doc_metadata, indent=2)}"
    except Exception as e:
        return f"Failed to classify and organize document: {str(e)}"

@register_tool(
    name="search_documents",
    description="Search organized documents index in SQLite based on query search terms.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search keyword or description of the document."}
        },
        "required": ["query"]
    }
)
def search_documents(query: str):
    results = db_search_documents(query)
    if not results:
        return f"No documents found matching: '{query}'"
    return json.dumps(results, indent=2)

@register_tool(
    name="list_organized_documents",
    description="List all classified and organized files by category.",
    parameters={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Filter by category: 'bills', 'education', 'identity', 'receipts'."}
        },
        "required": []
    }
)
def list_organized_documents(category: str = None):
    results = db_list_documents(category)
    return json.dumps(results, indent=2)
