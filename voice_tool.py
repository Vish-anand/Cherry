import os
import json
import requests
import time

def get_voice_api_url():
    # Check current directory and parent directory for config.json to ensure dynamic loading
    config_path = os.path.join(os.getcwd(), "config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                return config.get("voice_api_url", "https://rolled-jungle-fixtures-thereby.trycloudflare.com/generate_voice")
        except Exception:
            pass
    return "https://rolled-jungle-fixtures-thereby.trycloudflare.com/generate_voice"

def speak_text(text: str):
    if not text or not text.strip():
        return
        
    # Clean text: remove markdown tags, markdown emojis, or code blocks for speech if desired, 
    # but the requirement is "forward that exact string output to the voice synthesis utility"
    url = get_voice_api_url()
    print(f"[Voice Synthesis] Sending request to {url} for text: {text[:60]}...")
    
    played_successfully = False
    
    # 1. Try cloud voice synthesis via the Cloudflare tunnel
    try:
        response = requests.post(url, params={"text": text}, timeout=15)
        if response.status_code == 200:
            content = response.content
            
            # Check if response is mock text "AUDIO_DATA_HERE" or starts with it
            if content.strip() == b"AUDIO_DATA_HERE":
                print("[Voice Synthesis] Cloud server returned mock placeholder 'AUDIO_DATA_HERE'. Falling back to local TTS...")
            else:
                audio_path = "cherry_response.wav"
                with open(audio_path, "wb") as f:
                    f.write(content)
                print(f"[Voice Synthesis] Audio response saved to {audio_path}. Playing...")
                
                # Playback with pygame
                try:
                    import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load(audio_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    played_successfully = True
                except Exception as play_err:
                    print(f"[Voice Synthesis] Error playing audio: {play_err}")
                finally:
                    try:
                        pygame.mixer.music.unload()
                        pygame.mixer.quit()
                    except Exception:
                        pass
        else:
            print(f"[Voice Synthesis] Server returned status code {response.status_code}")
    except Exception as e:
        print(f"[Voice Synthesis] Warning: cloud voice synthesis request failed. {e}")
        
    # 2. Fall back to local SAPI5 TTS if cloud synthesis was mock or failed
    if not played_successfully:
        print("[Voice Synthesis] Executing local Windows SAPI5 voice synthesis...")
        try:
            import comtypes.client
            speaker = comtypes.client.CreateObject("SAPI.SpVoice")
            speaker.Speak(text)
            print("[Voice Synthesis] Local SAPI5 playback completed successfully.")
            played_successfully = True
        except Exception as sapi_err:
            print(f"[Voice Synthesis] Error playing audio via local fallback SAPI5: {sapi_err}")
            raise Exception("Voice synthesis failed (both cloud and local fallbacks were unsuccessful)")

