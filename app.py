import os
import json
import shutil
from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agent.core import run_agent_generator
from agent.memory import list_documents, search_documents, get_messages, clear_messages, list_conversations, create_conversation, update_conversation, delete_conversation, get_db_connection
from agent.tools import classify_and_organize_document, WORKSPACE_ROOT, INCOMING_DIR, list_workspace_files
import agent.computer_use_tools  # Load all computer-use tools into TOOL_REGISTRY

app = FastAPI(title="Cherry Agent Control Hub")

# Enable CORS for easy cross-origin debugging if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directories if they don't exist
os.makedirs(os.path.join(WORKSPACE_ROOT, "static"), exist_ok=True)

class ChatRequest(BaseModel):
    prompt: str
    conversation_id: str = "default"

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

@app.get("/api/chat")
def chat_endpoint(
    prompt: str = Query(...), 
    conversation_id: str = Query("default"),
    attachment_rel_path: str = Query(None),
    model: str = Query(None),
    temperature: float = Query(None),
    system_instruction: str = Query(None),
    voice_mode: bool = Query(False)
):
    """
    Server-Sent Events endpoint to stream Cherry agent thought steps.
    """
    full_attachment_path = None
    if attachment_rel_path:
        full_attachment_path = os.path.join(WORKSPACE_ROOT, attachment_rel_path)

    def event_stream():
        for step in run_agent_generator(
            prompt, 
            conversation_id, 
            full_attachment_path,
            model=model,
            temperature=temperature,
            system_instruction=system_instruction,
            voice_mode=voice_mode
        ):
            yield f"data: {json.dumps(step)}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/api/chat/history")
def get_chat_history(conversation_id: str = Query("default")):
    """
    Retrieve message history for a conversation.
    """
    return get_messages(conversation_id)

@app.delete("/api/chat/history")
def delete_chat_history(conversation_id: str = Query("default")):
    """
    Clear history for a conversation.
    """
    clear_messages(conversation_id)
    return {"status": "success", "message": "History cleared"}

class CreateConversationRequest(BaseModel):
    id: str
    title: str

class UpdateConversationRequest(BaseModel):
    title: str = None
    pinned: bool = None

@app.get("/api/conversations")
def get_conversations_list():
    """
    Get all conversations.
    """
    return list_conversations()

@app.post("/api/conversations")
def create_new_conversation(req: CreateConversationRequest):
    """
    Create a new conversation.
    """
    create_conversation(req.id, req.title)
    return {"status": "success", "id": req.id}

@app.put("/api/conversations/{conversation_id}")
def update_conv(conversation_id: str, req: UpdateConversationRequest):
    """
    Update conversation title or pinned status.
    """
    pinned_val = int(req.pinned) if req.pinned is not None else None
    update_conversation(conversation_id, title=req.title, pinned=pinned_val)
    return {"status": "success"}

@app.delete("/api/conversations/{conversation_id}")
def delete_conv(conversation_id: str):
    """
    Delete a conversation and all its messages.
    """
    delete_conversation(conversation_id)
    return {"status": "success"}

class ProfileUpdateRequest(BaseModel):
    name: str

@app.get("/api/profile")
def get_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("SELECT value FROM settings WHERE key = 'user_name'")
    row = cursor.fetchone()
    conn.close()
    name = row["value"] if row else "Vishnu"
    return {"name": name, "avatar": name[0].upper() if name else "V"}

@app.post("/api/profile")
def update_profile(req: ProfileUpdateRequest):
    name = req.name.strip()
    if name:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('user_name', ?)", (name,))
        conn.commit()
        conn.close()
    return {"status": "success", "name": name}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts raw file, saves it to incoming/, and runs classifier pipeline.
    """
    filename = file.filename
    target_path = os.path.join(INCOMING_DIR, filename)
    
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    rel_incoming_path = os.path.relpath(target_path, WORKSPACE_ROOT)
    # Run classification
    result = classify_and_organize_document(rel_incoming_path)
    
    return {"status": "success", "message": result}

import subprocess

# Global state for WhatsApp Bridge
whatsapp_process = None
whatsapp_qr_data = None
whatsapp_connection_status = "disconnected"  # "disconnected", "scanning", "connected"

class WhatsappStatusUpdate(BaseModel):
    status: str

class WhatsappQrUpdate(BaseModel):
    qrDataUrl: str

@app.get("/api/whatsapp/status")
def get_whatsapp_status():
    global whatsapp_process, whatsapp_connection_status, whatsapp_qr_data
    
    is_running = False
    if whatsapp_process is not None:
        if whatsapp_process.poll() is None:
            is_running = True
        else:
            whatsapp_process = None
            whatsapp_connection_status = "disconnected"
            whatsapp_qr_data = None
            
    return {
        "running": is_running,
        "status": whatsapp_connection_status,
        "qr": whatsapp_qr_data
    }

@app.post("/api/whatsapp/start")
def start_whatsapp_bridge():
    global whatsapp_process, whatsapp_connection_status, whatsapp_qr_data
    
    if whatsapp_process is not None and whatsapp_process.poll() is None:
        return {"status": "success", "message": "Already running"}
        
    try:
        log_path = os.path.join(WORKSPACE_ROOT, "whatsapp_bridge.log")
        log_file = open(log_path, "a")
        whatsapp_process = subprocess.Popen(
            ["node", "whatsapp_bridge.js"],
            cwd=WORKSPACE_ROOT,
            stdout=log_file,
            stderr=log_file,
            shell=True # Required on Windows to find node in PATH correctly
        )
        whatsapp_connection_status = "scanning"
        whatsapp_qr_data = None
        return {"status": "success", "message": "Bridge started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/whatsapp/stop")
def stop_whatsapp_bridge():
    global whatsapp_process, whatsapp_connection_status, whatsapp_qr_data
    
    if whatsapp_process is not None:
        try:
            whatsapp_process.terminate()
            whatsapp_process.wait(timeout=2)
        except Exception:
            try:
                whatsapp_process.kill()
            except Exception:
                pass
        whatsapp_process = None
        
    whatsapp_connection_status = "disconnected"
    whatsapp_qr_data = None
    return {"status": "success", "message": "Bridge stopped"}

@app.post("/api/whatsapp/qr")
def update_whatsapp_qr(req: WhatsappQrUpdate):
    global whatsapp_qr_data, whatsapp_connection_status
    whatsapp_qr_data = req.qrDataUrl
    whatsapp_connection_status = "scanning"
    return {"status": "success"}

@app.post("/api/whatsapp/status")
def update_whatsapp_status(req: WhatsappStatusUpdate):
    global whatsapp_connection_status, whatsapp_qr_data
    whatsapp_connection_status = req.status
    if req.status == "connected":
        whatsapp_qr_data = None
    return {"status": "success"}

@app.post("/api/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form("whatsapp:+14155238886"),
    Body: str = Form(""),
    media: UploadFile = File(None),
    format: str = Query(None)
):
    """
    Accepts simulated or real inbound text and media files from WhatsApp.
    If media is sent, it is auto-classified and filed.
    If text is sent, runs a fast single-prompt agent query.
    """
    log_msg = f"Webhook received from: {From}\nText: {Body}\n"
    media_msg = ""
    
    if media:
        filename = media.filename
        target_path = os.path.join(INCOMING_DIR, filename)
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(media.file, buffer)
        rel_path = os.path.relpath(target_path, WORKSPACE_ROOT)
        media_msg = classify_and_organize_document(rel_path)
        log_msg += f"Media uploaded and processed: {media_msg}"
        
    # If there is text body, we simulate an agent run and return the final answer
    agent_steps = []
    final_reply = ""
    if Body:
        # Run agent loop synchronously to gather steps
        try:
            for step in run_agent_generator(Body, conversation_id=f"whatsapp_{From}"):
                agent_steps.append(step)
                if step.get("type") == "final_answer":
                    final_reply = step.get("content")
        except Exception as e:
            final_reply = f"Error running agent loop: {str(e)}"
    
    if format == "xml":
        from fastapi import Response
        # Return standard TwiML XML format for Twilio integration
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{final_reply}</Message>
</Response>"""
        return Response(content=twiml_response, media_type="application/xml")

    return {
        "status": "received",
        "log": log_msg,
        "media_processing": media_msg,
        "agent_reply": final_reply,
        "steps": agent_steps
    }

@app.get("/api/documents")
def get_all_documents(category: str = None):
    """List classified documents."""
    return list_documents(category)

@app.get("/api/documents/search")
def search_docs(query: str = Query(...)):
    """Search classified documents."""
    return search_documents(query)

@app.get("/api/workspace/files")
def get_files():
    """List all workspace files."""
    return json.loads(list_workspace_files())

class VoiceConfigRequest(BaseModel):
    voice_api_url: str

@app.get("/api/voice/config")
def get_voice_config():
    """Get the current voice API URL configuration."""
    try:
        from voice_tool import get_voice_api_url
        return {"voice_api_url": get_voice_api_url()}
    except Exception as e:
        return {"voice_api_url": "https://rolled-jungle-fixtures-thereby.trycloudflare.com/generate_voice", "error": str(e)}

@app.post("/api/voice/config")
def set_voice_config(req: VoiceConfigRequest):
    """Update the voice API URL configuration in config.json."""
    try:
        config_path = os.path.join(WORKSPACE_ROOT, "config.json")
        with open(config_path, "w") as f:
            json.dump({"voice_api_url": req.voice_api_url}, f, indent=2)
        return {"status": "success", "voice_api_url": req.voice_api_url}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/volume/get")
def get_volume():
    """Get system volume (requires pycaw)."""
    try:
        import comtypes
        try:
            comtypes.CoInitialize()
        except Exception:
            pass
            
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume
        scalar_val = volume.GetMasterVolumeLevelScalar()
        return {"volume": int(scalar_val * 100)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/volume/set")
def set_volume(level: int = Query(...)):
    """Set system volume directly."""
    from agent.tools import adjust_system_volume
    res = adjust_system_volume(level)
    return {"status": "success", "message": res}


from fastapi.responses import FileResponse
from PIL import ImageGrab

class KillProcessRequest(BaseModel):
    pid: int = None
    name: str = None

@app.get("/api/system/info")
def get_system_info():
    """Retrieve structured system diagnostics via PowerShell."""
    ps_script = r"""
    $os = Get-WmiObject Win32_OperatingSystem
    $cpu = Get-WmiObject Win32_Processor | Select-Object -First 1
    $cpu_pct = if ($cpu.LoadPercentage) { $cpu.LoadPercentage } else { 0 }
    $mem_total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $mem_free = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $mem_used = $mem_total - $mem_free
    $disk = Get-PSDrive C | Select-Object Used, Free
    $disk_used = [math]::Round($disk.Used / 1GB, 2)
    $disk_free = [math]::Round($disk.Free / 1GB, 2)
    $disk_total = $disk_used + $disk_free
    $battery = Get-WmiObject Win32_Battery -ErrorAction SilentlyContinue
    $battery_level = if ($battery) { $battery.EstimatedChargeRemaining } else { 100 }
    
    $res = @{
        os = "$($os.Caption) $($os.OSArchitecture)"
        cpu = $cpu.Name.Trim()
        cpu_percent = $cpu_pct
        ram_used = $mem_used
        ram_total = $mem_total
        ram_percent = [math]::Round(($mem_used / $mem_total) * 100, 1)
        disk_used = $disk_used
        disk_total = $disk_total
        disk_percent = [math]::Round(($disk_used / $disk_total) * 100, 1)
        battery = $battery_level
    }
    $res | ConvertTo-Json
    """
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, timeout=15, encoding="utf-8"
        )
        return json.loads(res.stdout.strip())
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/system/screenshot")
def get_screenshot():
    """Capture host screen and return as PNG file."""
    screenshot_path = os.path.join(WORKSPACE_ROOT, "temp_screenshot.png")
    try:
        img = ImageGrab.grab()
        img.save(screenshot_path)
        return FileResponse(screenshot_path, media_type="image/png")
    except Exception:
        # Fallback: PowerShell .NET screen grabber
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms,System.Drawing
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bmp = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $bmp.Save('{screenshot_path.replace(chr(92), '/')}')
        $g.Dispose(); $bmp.Dispose()
        """
        try:
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=10)
            if os.path.exists(screenshot_path):
                return FileResponse(screenshot_path, media_type="image/png")
        except Exception as ex:
            return {"error": f"Failed to capture screen: {str(ex)}"}
    return {"error": "Failed to capture screen"}

@app.get("/api/system/processes")
def get_processes(filter: str = Query(None)):
    """List running processes."""
    ps_cmd = "Get-Process | Select-Object Name, Id, CPU, WorkingSet | Sort-Object CPU -Descending | ConvertTo-Json -Depth 1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace"
        )
        stdout_str = result.stdout.strip()
        if not stdout_str:
            return []
        data = json.loads(stdout_str)
        if not isinstance(data, list):
            data = [data]
        
        processes = []
        for p in data[:80]:
            cpu_val = p.get("CPU")
            cpu_str = f"{cpu_val:.1f}" if cpu_val is not None else "0.0"
            mem_mb = int((p.get("WorkingSet") or 0) / 1024 / 1024)
            processes.append({
                "name": p.get("Name"),
                "pid": p.get("Id"),
                "cpu": cpu_str,
                "mem": mem_mb
            })
        if filter:
            f_lower = filter.lower()
            processes = [p for p in processes if f_lower in (p["name"] or "").lower()]
        return processes
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/system/kill")
def kill_system_process(req: KillProcessRequest):
    """Force terminate a process by PID or Name."""
    try:
        if req.pid:
            res = subprocess.run(["taskkill", "/F", "/PID", str(req.pid)], capture_output=True, text=True, timeout=5)
        elif req.name:
            name_clean = req.name.replace(".exe", "")
            res = subprocess.run(["taskkill", "/F", "/IM", f"{name_clean}.exe"], capture_output=True, text=True, timeout=5)
        else:
            return {"status": "error", "message": "Specify name or pid"}
            
        if res.returncode == 0:
            return {"status": "success", "message": "Terminated task successfully."}
        else:
            return {"status": "error", "message": res.stderr.strip() or res.stdout.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Serve static frontend dashboard assets
app.mount("/static", StaticFiles(directory=os.path.join(WORKSPACE_ROOT, "static")), name="static")


if __name__ == "__main__":
    import uvicorn
    # Pre-warm DB
    import agent.memory
    print("--------------------------------------------------")
    print("Cherry Agent Hub is starting!")
    print("To access the web interface, please open one of these in your browser:")
    print("  -> http://localhost:8001")
    print("  -> http://127.0.0.1:8001")
    print("--------------------------------------------------")
    uvicorn.run(app, host="0.0.0.0", port=8001)
