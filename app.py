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
    system_instruction: str = Query(None)
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
            system_instruction=system_instruction
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

@app.post("/api/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form("whatsapp:+14155238886"),
    Body: str = Form(""),
    media: UploadFile = File(None)
):
    """
    Accepts simulated inbound text and media files from WhatsApp.
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

# Serve static frontend dashboard assets
app.mount("/static", StaticFiles(directory=os.path.join(WORKSPACE_ROOT, "static")), name="static")


if __name__ == "__main__":
    import uvicorn
    # Pre-warm DB
    import agent.memory
    print("Starting Cherry Agent Hub on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
