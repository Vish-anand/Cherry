import os
import urllib.request
import wave
import time

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voice_models")
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
CONFIG_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"

model_path = os.path.join(MODEL_DIR, "en_US-lessac-medium.onnx")
config_path = os.path.join(MODEL_DIR, "en_US-lessac-medium.onnx.json")

def download_file(url, dest):
    if not os.path.exists(dest):
        print(f"Downloading {url} to {dest}...")
        urllib.request.urlretrieve(url, dest)
        print("Download complete.")
    else:
        print(f"File {dest} already exists.")

# Download the model and config
download_file(MODEL_URL, model_path)
download_file(CONFIG_URL, config_path)

# Initialize Piper and synthesize text
from piper.voice import PiperVoice

print("Loading Piper model...")
t0 = time.time()
voice = PiperVoice.load(model_path)
print(f"Model loaded in {time.time() - t0:.2f}s")

output_wav = "test_piper_output.wav"
print(f"Synthesizing speech to {output_wav}...")
t0 = time.time()
with wave.open(output_wav, "wb") as wav_file:
    voice.synthesize_wav("Hello, this is Cherry speaking with local neural text to speech!", wav_file)
print(f"Synthesis complete in {time.time() - t0:.2f}s")
