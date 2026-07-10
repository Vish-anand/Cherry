import os
# Hide pygame support message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import json
import requests
import time
import urllib.request
import wave
import re
import asyncio
import pygame
import edge_tts

# Initialize pygame mixer once globally to completely eliminate audio driver loading delays
try:
    pygame.mixer.init()
except Exception as e:
    print(f"[Voice Warning] Failed to initialize pygame mixer globally: {e}")

VOICE_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_models")

EDGE_VOICE_MAPPING = {
    "en_US-amy-medium": "en-US-AvaNeural",
    "en_US-kristin-medium": "en-US-EmmaMultilingualNeural",
    "en_GB-jenny_dioco-medium": "en-GB-SoniaNeural",
    "en_US-ryan-medium": "en-US-AndrewNeural",
    "en_US-joe-medium": "en-US-BrianNeural"
}

def get_voice_api_url():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(os.getcwd(), "config.json")
        
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                return config.get("voice_api_url", "https://rolled-jungle-fixtures-thereby.trycloudflare.com/generate_voice")
        except Exception:
            pass
    return "https://rolled-jungle-fixtures-thereby.trycloudflare.com/generate_voice"

def get_voice_model():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(os.getcwd(), "config.json")
        
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                return config.get("voice_model", "en-US-AnaNeural")
        except Exception:
            pass
    return "en-US-AnaNeural"

def get_model_paths(model_name: str):
    local_model_path = os.path.join(VOICE_MODELS_DIR, f"{model_name}.onnx")
    local_config_path = os.path.join(VOICE_MODELS_DIR, f"{model_name}.onnx.json")
    
    # If the model files already exist locally, use them directly
    if os.path.exists(local_model_path) and os.path.exists(local_config_path):
        return local_model_path, local_config_path, None, None
        
    parts = model_name.split("-")
    if len(parts) >= 3:
        lang_country = parts[0]
        lang = lang_country.split("_")[0]
        name = parts[1]
        quality = parts[2]
        
        base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{lang}/{lang_country}/{name}/{quality}"
        model_url = f"{base_url}/{model_name}.onnx"
        config_url = f"{base_url}/{model_name}.onnx.json"
        
        return local_model_path, local_config_path, model_url, config_url
    else:
        return local_model_path, local_config_path, None, None

def download_piper_model_if_missing(model_path, config_path, model_url, config_url):
    os.makedirs(VOICE_MODELS_DIR, exist_ok=True)
    if not os.path.exists(model_path):
        if not model_url:
            raise FileNotFoundError(f"Local voice model file missing at {model_path} and no download URL is available.")
        print(f"[Voice Synthesis] Downloading local neural voice model to {model_path}...")
        urllib.request.urlretrieve(model_url, model_path)
    if not os.path.exists(config_path):
        if not config_url:
            raise FileNotFoundError(f"Local voice config file missing at {config_path} and no download URL is available.")
        print(f"[Voice Synthesis] Downloading voice configuration to {config_path}...")
        urllib.request.urlretrieve(config_url, config_path)

def clean_text_for_speech(text: str) -> str:
    if not text:
        return ""
        
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`.*?`", "", text)
    
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[\*\-\+•\d\.\s]+\s+", "", line)
        if line:
            lines.append(line)
            
    cleaned = ". ".join(lines)
    
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"
        "\U0001f300-\U0001f5ff"
        "\U0001f680-\U0001f6ff"
        "\U0001f1e0-\U0001f1ff"
        "\U00002702-\U000027b0"
        "\U000024c2-\U0001f251"
        "\u2600-\u27BF"
        "\U0001f900-\U0001f9ff"
        "\U0001f000-\U0001ffff"
        "]+", flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub(r"", cleaned)
    
    cleaned = re.sub(r"\*\*+", "", cleaned)
    cleaned = re.sub(r"\*", "", cleaned)
    cleaned = re.sub(r"_+", "", cleaned)
    
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\.\.+", ".", cleaned)
    
    return cleaned.strip()

def speak_text(text: str, voice_model: str = None):
    text_to_speak = clean_text_for_speech(text)
    if not text_to_speak or not text_to_speak.strip():
        print("[Voice Synthesis] No text left to speak after cleaning.")
        return
        
    played_successfully = False
    model_name = voice_model if voice_model else get_voice_model()
    is_online_neural = "neural" in model_name.lower()
    
    import uuid
    audio_id = uuid.uuid4().hex[:8]
    
    # Helper to play online Edge TTS
    def play_edge_tts():
        edge_voice = model_name if is_online_neural else EDGE_VOICE_MAPPING.get(model_name, "en-US-AnaNeural")
        audio_path = f"cherry_response_{audio_id}.mp3"
        try:
            print(f"[Voice Synthesis] Synthesizing speech via Edge TTS ({edge_voice}) for: {text_to_speak[:60]}...")
            
            # Use a dedicated event loop for background thread execution
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(edge_tts.Communicate(text_to_speak, edge_voice).save(audio_path))
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
                    
            print(f"[Voice Synthesis] Audio response saved to {audio_path}. Playing...")
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
            try:
                os.remove(audio_path)
            except Exception:
                pass
            return True
        except Exception as edge_err:
            print(f"[Voice Synthesis] Edge TTS failed: {edge_err}")
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception:
                pass
            return False

    # Helper to play local offline Piper
    def play_piper():
        piper_model = model_name
        if is_online_neural:
            reverse_mapping = {v: k for k, v in EDGE_VOICE_MAPPING.items()}
            piper_model = reverse_mapping.get(model_name, "en_US-amy-medium")
            
        audio_path_wav = f"cherry_response_{audio_id}.wav"
        try:
            model_path, config_path, model_url, config_url = get_model_paths(piper_model)
            download_piper_model_if_missing(model_path, config_path, model_url, config_url)
            
            from piper.voice import PiperVoice
            print(f"[Voice Synthesis] Synthesizing speech via offline Piper neural model ({piper_model}) for: {text_to_speak[:60]}...")
            voice = PiperVoice.load(model_path)
            with wave.open(audio_path_wav, "wb") as wav_file:
                voice.synthesize_wav(text_to_speak, wav_file)
                
            print(f"[Voice Synthesis] Audio response saved to {audio_path_wav}. Playing...")
            pygame.mixer.music.load(audio_path_wav)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
            try:
                os.remove(audio_path_wav)
            except Exception:
                pass
            return True
        except Exception as piper_err:
            print(f"[Voice Synthesis] Offline Piper TTS failed: {piper_err}")
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            try:
                if os.path.exists(audio_path_wav):
                    os.remove(audio_path_wav)
            except Exception:
                pass
            return False

    # Execute speech synthesis based on choice
    if is_online_neural:
        played_successfully = play_edge_tts()
        if not played_successfully:
            print("[Voice Synthesis] Falling back to offline Piper...")
            played_successfully = play_piper()
    else:
        played_successfully = play_piper()
        if not played_successfully:
            print("[Voice Synthesis] Falling back to online Edge TTS...")
            played_successfully = play_edge_tts()
                
    # 3. Try cloud voice synthesis via the Cloudflare tunnel if previous failed
    if not played_successfully:
        url = get_voice_api_url()
        print(f"[Voice Synthesis] Sending request to cloud endpoint {url}...")
        audio_path_cloud = f"cherry_response_{audio_id}.wav"
        try:
            response = requests.post(url, params={"text": text_to_speak}, timeout=5)
            if response.status_code == 200:
                content = response.content
                if content.strip() != b"AUDIO_DATA_HERE":
                    with open(audio_path_cloud, "wb") as f:
                        f.write(content)
                    pygame.mixer.music.load(audio_path_cloud)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    pygame.mixer.music.unload()
                    try:
                        os.remove(audio_path_cloud)
                    except Exception:
                        pass
                    played_successfully = True
        except Exception as cloud_err:
            print(f"[Voice Synthesis] Cloud voice synthesis request failed: {cloud_err}")
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            try:
                if os.path.exists(audio_path_cloud):
                    os.remove(audio_path_cloud)
            except Exception:
                pass
                
    # 4. Fall back to local SAPI5 TTS if everything else failed
    if not played_successfully:
        print("[Voice Synthesis] Executing local Windows SAPI5 voice synthesis...")
        try:
            import comtypes.client
            speaker = comtypes.client.CreateObject("SAPI.SpVoice")
            speaker.Speak(text_to_speak)
            print("[Voice Synthesis] Local SAPI5 playback completed successfully.")
            played_successfully = True
        except Exception as sapi_err:
            print(f"[Voice Synthesis] Error playing audio via local fallback SAPI5: {sapi_err}")
            raise Exception("Voice synthesis failed (all engines failed)")




