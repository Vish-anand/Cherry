import os
import time
from datetime import datetime
from PIL import Image
import pygetwindow as gw

class ScreenCaptureError(Exception):
    pass

def get_active_window_info() -> dict:
    """
    Returns active window title and coordinates.
    """
    try:
        active_window = gw.getActiveWindow()
        if active_window:
            return {
                "title": active_window.title or "Unknown",
                "box": {
                    "left": active_window.left,
                    "top": active_window.top,
                    "width": active_window.width,
                    "height": active_window.height
                }
            }
    except Exception:
        pass
    return {"title": "Desktop / Unknown", "box": None}

def capture_screen(save_path: str = None) -> tuple[str, int, int]:
    """
    Captures the primary monitor screen and returns (saved_path, width, height).
    Uses mss for high performance, falls back to Pillow ImageGrab.
    """
    if not save_path:
        # Create temp screenshot filename if none provided
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(os.getcwd(), f"screenshot_{timestamp}.png")
        
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    
    # 1. Try mss capture
    try:
        import mss
        with mss.MSS() as sct:
            # Monitor 1 is typically the primary monitor
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(save_path)
            return save_path, img.width, img.height
    except Exception as e:
        # Log or print fallback warning
        print(f"[mss] Screenshot failed, falling back to Pillow: {e}")
        
    # 2. Fallback to Pillow ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(save_path)
        return save_path, img.width, img.height
    except Exception as e:
        raise ScreenCaptureError(f"All screen capture methods failed: {str(e)}")
