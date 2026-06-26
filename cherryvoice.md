# Cherry Voice Pipeline & Architecture Specification

This document provides a comprehensive blueprint of the cloud-to-local voice architecture for the agent "Cherry". Use this specification to audit, refit, and debug local files (`app.py`, `core.py`, `voice_tool.py`, `config.json`) to resolve the silent audio playback issue.

---

## 1. System Architecture Blueprint

The real-time Text-to-Speech (TTS) engine relies on a hybrid cloud-edge topology to handle heavy model weights without slowing down the local interface.

* **Local Backend (`app.py` / `core.py`):** Drives the user dialogue loop. When text generation is completed by the core agent, the backend passes the text string to the voice synthesis utility.
* **Secure Network Bridge (Cloudflare Tunnel):** Encrypts and forwards the HTTP request directly to the cloud execution node without requiring local port forwarding or third-party client authentication.
* **Cloud Processing Node (Google Colab T4 GPU):** Hosts the heavy 3-billion parameter `maya-research/maya1` model. It processes the text, synthesizes native acoustic expressions, packs the data into a standard WAV container, and streams the binary file back.
* **Local Audio Player (`voice_tool.py`):** Receives the raw byte array stream, writes it safely into a local file buffer, manages thread execution, and executes hardware playback via the local system mixer.

---

## 2. Cloud Server Implementation (Google Colab Code)

The cloud-hosted virtual machine is configured with the following production script. It loads the genuine Maya-1 transformer model pipeline directly onto dedicated Nvidia VRAM:

```python
import nest_asyncio
import uvicorn
import threading
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import io
import torch
import soundfile as sf
from transformers import pipeline

# Patch the asynchronous loop environment for Google Colab notebooks
nest_asyncio.apply()
app = FastAPI()

print("📥 Loading raw Maya-1 model from Hugging Face onto GPU...")

# Load the real 3B emotional voice model onto the dedicated Nvidia GPU
device = 0 if torch.cuda.is_available() else -1
maya_pipeline = pipeline(
    "text-to-speech", 
    model="maya-research/maya1", 
    device=device,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
)

print("🎉 Real Maya-1 model loaded successfully on GPU!")

@app.post("/generate_voice")
async def generate_voice(text: str):
    print(f"🎙️ Maya-1 Synthesizing: {text}")
    
    # Process text through the native transformer pipeline
    # (Supports inline tags like <laugh>, <sigh>, <giggle>, <whisper>)
    speech_output = maya_pipeline(text)
    
    audio_data = speech_output["audio"]
    sampling_rate = speech_output["sampling_rate"]
    
    # Pack the generated waveform array into a standard WAV container file in memory
    buffer = io.BytesIO()
    sf.write(buffer, audio_data, sampling_rate, format='WAV', subtype='PCM_16')
    buffer.seek(0)
    
    # Stream the file back down the tunnel to the local client application
    return StreamingResponse(buffer, media_type="audio/wav")

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000)

# Check if the execution thread is already running to avoid port collision crashes
if not any(t.name == "fastapi_server" for t in threading.enumerate()):
    threading.Thread(target=run_server, name="fastapi_server", daemon=True).start()
    print("🚀 FastAPI server is now running in the background on port 8000.")
