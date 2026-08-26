import os
import json
import shutil
from fastapi import FastAPI, UploadFile, File, Form, Query, Request
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agent.core import run_agent_generator
from agent.memory import list_documents, search_documents, get_messages, clear_messages, list_conversations, create_conversation, update_conversation, delete_conversation, get_db_connection, delete_pending_action
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

import uuid
import secrets

# Active session tokens
ACTIVE_SESSIONS = set()

# Get secure password from environment
CHERRY_PASSWORD = os.getenv("CHERRY_PASSWORD")
if not CHERRY_PASSWORD or not CHERRY_PASSWORD.strip():
    CHERRY_PASSWORD = secrets.token_hex(8)
    print("--------------------------------------------------")
    print("WARNING: CHERRY_PASSWORD is not set in your .env file!")
    print(f"Temporary secure backdoor access password: {CHERRY_PASSWORD}")
    print("--------------------------------------------------")
else:
    print("--------------------------------------------------")
    print("Backdoor portal protection active.")
    print("--------------------------------------------------")

class LoginRequest(BaseModel):
    password: str

@app.post("/api/login")
def login(req: LoginRequest):
    if req.password == CHERRY_PASSWORD:
        token = str(uuid.uuid4())
        ACTIVE_SESSIONS.add(token)
        response = JSONResponse(content={"status": "success", "message": "Authenticated successfully"})
        response.set_cookie(
            key="session_id",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 30  # 30 days session persistence
        )
        return response
    return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid password key"})

@app.post("/api/logout")
def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.remove(session_id)
    response = JSONResponse(content={"status": "success", "message": "Logged out successfully"})
    response.delete_cookie(key="session_id")
    return response

@app.middleware("http")
async def check_session_middleware(request: Request, call_next):
    path = request.url.path
    
    # 1. Exempt public routes and webhook handlers
    exempt_paths = {
        "/",
        "/projects",
        "/login",
        "/api/login",
        "/api/logout",
        "/api/webhook/whatsapp"
    }
    
    # Allow CSS, images, and public elements loaded statically
    if path.startswith("/static/"):
        return await call_next(request)
        
    if path in exempt_paths:
        return await call_next(request)
        
    # 2. Verify Session
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in ACTIVE_SESSIONS:
        # If API path, return 401 JSON
        if path.startswith("/api/"):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        # Otherwise, redirect to login page
        return RedirectResponse(url="/login")
        
    return await call_next(request)

@app.get("/")
def read_root():
    return FileResponse(os.path.join(WORKSPACE_ROOT, "static", "portfolio.html"))

@app.get("/login")
def get_login():
    return FileResponse(os.path.join(WORKSPACE_ROOT, "static", "login.html"))

@app.get("/projects")
def get_projects():
    return FileResponse(os.path.join(WORKSPACE_ROOT, "static", "projects.html"))

@app.get("/dashboard")
def get_dashboard():
    return FileResponse(os.path.join(WORKSPACE_ROOT, "private", "index.html"))

@app.get("/dashboard/script.js")
def get_dashboard_script():
    return FileResponse(os.path.join(WORKSPACE_ROOT, "private", "script.js"))

@app.get("/dashboard/mascot.js")
def get_dashboard_mascot():
    return FileResponse(os.path.join(WORKSPACE_ROOT, "private", "mascot.js"))

@app.get("/api/chat")
def chat_endpoint(
    prompt: str = Query(None), 
    conversation_id: str = Query("default"),
    attachment_rel_path: str = Query(None),
    model: str = Query(None),
    temperature: float = Query(None),
    system_instruction: str = Query(None),
    voice_mode: bool = Query(False),
    voice_model: str = Query(None),
    resume_action_id: str = Query(None)
):
    """
    Server-Sent Events endpoint to stream Cherry agent thought steps.
    """
    if not prompt and not resume_action_id:
        return JSONResponse(status_code=400, content={"error": "Either prompt or resume_action_id is required."})
        
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
            voice_mode=voice_mode,
            voice_model=voice_model,
            resume_action_id=resume_action_id
        ):
            yield f"data: {json.dumps(step)}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/api/chat/audio")
def chat_audio_endpoint(
    audio: UploadFile = File(...),
    conversation_id: str = Form("default"),
    model: str = Form(None),
    temperature: float = Form(None),
    system_instruction: str = Form(None),
    voice_mode: bool = Form(True),
    voice_model: str = Form(None)
):
    """
    Accepts uploaded microphone audio file, transcribes to text, and sends to agent.
    """
    import time
    import subprocess as sp
    
    # 1. Determine temporary save directory
    temp_dir = os.path.join(WORKSPACE_ROOT, "incoming")
    os.makedirs(temp_dir, exist_ok=True)
    
    orig_ext = os.path.splitext(audio.filename)[1].lower() if audio.filename else ""
    if not orig_ext:
        if audio.content_type == "audio/webm":
            orig_ext = ".webm"
        elif audio.content_type == "audio/wav":
            orig_ext = ".wav"
        else:
            orig_ext = ".webm"
            
    temp_filename = f"voice_input_{int(time.time())}{orig_ext}"
    temp_file_path = os.path.join(temp_dir, temp_filename)
    wav_file_path = os.path.join(temp_dir, f"voice_input_{int(time.time())}.wav")
    
    # 2. Save the uploaded file
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
    
    # 3. Convert to WAV for speech_recognition compatibility
    needs_conversion = orig_ext != ".wav"
    conversion_ok = False
    
    if needs_conversion:
        try:
            from pydub import AudioSegment
            audio_seg = AudioSegment.from_file(temp_file_path)
            audio_seg.export(wav_file_path, format="wav")
            conversion_ok = True
            print(f"[Live Voice] Audio converted to WAV via pydub: {wav_file_path}")
        except Exception as pydub_err:
            print(f"[Live Voice] pydub conversion failed: {pydub_err}")
            try:
                sp.run(
                    ["ffmpeg", "-y", "-i", temp_file_path, wav_file_path],
                    capture_output=True, timeout=15
                )
                if os.path.exists(wav_file_path) and os.path.getsize(wav_file_path) > 0:
                    conversion_ok = True
                    print(f"[Live Voice] Audio converted to WAV via ffmpeg: {wav_file_path}")
            except Exception as ffmpeg_err:
                print(f"[Live Voice] ffmpeg conversion also failed: {ffmpeg_err}")
    else:
        wav_file_path = temp_file_path
        conversion_ok = True
    
    # 4. Transcribe audio to text
    transcript = None
    if conversion_ok:
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_file_path) as source:
                audio_data = recognizer.record(source)
            transcript = recognizer.recognize_google(audio_data)
            print(f"[Live Voice] Transcription result: '{transcript}'")
        except Exception as sr_err:
            print(f"[Live Voice] Speech recognition failed: {sr_err}")
            transcript = None
    
    if not transcript or not transcript.strip():
        def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Could not understand your voice. Please speak louder and clearer, or try again.'})}\n\n"
        
        for f in [temp_file_path, wav_file_path]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
        return StreamingResponse(error_stream(), media_type="text/event-stream")
    
    prompt = transcript.strip()
    
    def event_stream():
        yield f"data: {json.dumps({'type': 'status', 'content': 'Heard: ' + prompt})}\n\n"
        
        for step in run_agent_generator(
            user_prompt=prompt,
            conversation_id=conversation_id,
            attachment_path=None,
            model=model,
            temperature=temperature,
            system_instruction=system_instruction,
            voice_mode=voice_mode,
            voice_model=voice_model
        ):
            yield f"data: {json.dumps(step)}\n\n"
            
        for f in [temp_file_path, wav_file_path]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                print(f"Warning: Failed to clean up temp voice input file: {e}")
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")


class RejectActionRequest(BaseModel):
    action_id: str
    conversation_id: str = "default"

@app.post("/api/chat/reject")
def reject_action(req: RejectActionRequest):
    """
    Reject a pending action proposal, logging the rejection to the history context.
    """
    from agent.memory import save_message
    delete_pending_action(req.action_id)
    save_message(req.conversation_id, "system", "Observation: Error: Action was rejected by the user.")
    return {"status": "success", "message": "Action proposal rejected."}


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

def kill_orphaned_whatsapp_bridges():
    """Query and force-terminate any node processes running whatsapp_bridge.js on Windows."""
    try:
        ps_cmd = 'Get-CimInstance Win32_Process -Filter "CommandLine like \'%whatsapp_bridge.js%\'" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }'
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True)
    except Exception as e:
        print(f"Warning: Failed to clean up orphaned WhatsApp processes: {e}")

@app.on_event("shutdown")
def shutdown_event():
    """Triggered on FastAPI shutdown to clean up all background threads and processes."""
    global whatsapp_process
    print("FastAPI server is shutting down. Cleaning up background process trees...")
    if whatsapp_process is not None:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(whatsapp_process.pid)], capture_output=True)
        except Exception:
            pass
    kill_orphaned_whatsapp_bridges()

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
    
    # Ensure any lingering previous processes are terminated before starting a new one
    kill_orphaned_whatsapp_bridges()
    
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
            # Kill process tree on Windows to ensure both the shell and the child node process are terminated
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(whatsapp_process.pid)], capture_output=True)
        except Exception:
            try:
                whatsapp_process.kill()
            except Exception:
                pass
        whatsapp_process = None
        
    kill_orphaned_whatsapp_bridges()
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

@app.get("/api/voice/local_models")
def get_local_voice_models():
    """List all locally available voice models (.onnx files in VOICE_MODELS_DIR)."""
    try:
        from voice_tool import VOICE_MODELS_DIR
        if not os.path.exists(VOICE_MODELS_DIR):
            return []
        models = []
        for f in os.listdir(VOICE_MODELS_DIR):
            if f.endswith(".onnx"):
                models.append(f[:-5]) # remove '.onnx'
        return models
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/voice/upload")
async def upload_voice_model(
    model_file: UploadFile = File(...),
    config_file: UploadFile = File(...)
):
    """Upload custom .onnx and .onnx.json Piper models."""
    try:
        from voice_tool import VOICE_MODELS_DIR
        os.makedirs(VOICE_MODELS_DIR, exist_ok=True)
        
        # Verify extensions
        if not model_file.filename.endswith(".onnx") or not config_file.filename.endswith(".onnx.json"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Model must be .onnx and config must be .onnx.json"})
            
        model_path = os.path.join(VOICE_MODELS_DIR, model_file.filename)
        config_path = os.path.join(VOICE_MODELS_DIR, config_file.filename)
        
        with open(model_path, "wb") as f:
            shutil.copyfileobj(model_file.file, f)
        with open(config_path, "wb") as f:
            shutil.copyfileobj(config_file.file, f)
            
        return {"status": "success", "model": model_file.filename[:-5]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

class VoiceConfigRequest(BaseModel):
    voice_api_url: str
    voice_model: str

@app.get("/api/voice/config")
def get_voice_config():
    """Get the current voice configuration."""
    try:
        from voice_tool import get_voice_api_url, get_voice_model
        return {
            "voice_api_url": get_voice_api_url(),
            "voice_model": get_voice_model()
        }
    except Exception as e:
        return {
            "voice_api_url": "https://rolled-jungle-fixtures-thereby.trycloudflare.com/generate_voice",
            "voice_model": "en-US-AnaNeural",
            "error": str(e)
        }

@app.post("/api/voice/config")
def set_voice_config(req: VoiceConfigRequest):
    """Update the voice configuration in config.json."""
    try:
        config_path = os.path.join(WORKSPACE_ROOT, "config.json")
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
            except Exception:
                pass
        config["voice_api_url"] = req.voice_api_url
        config["voice_model"] = req.voice_model
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return {"status": "success", "voice_api_url": req.voice_api_url, "voice_model": req.voice_model}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class VoiceSampleRequest(BaseModel):
    text: str
    voice: str

@app.post("/api/voice/sample")
def play_voice_sample(req: VoiceSampleRequest):
    """Generate and play a voice sample locally using voice_tool.py."""
    try:
        import voice_tool
        # Play sample directly with the requested voice
        voice_tool.speak_text(req.text, voice_model=req.voice)
        return {"status": "success"}
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
