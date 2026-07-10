import time
import random
import numpy as np
import pyautogui
from scipy.interpolate import make_interp_spline

# Configure PyAutoGUI safety guardrails
pyautogui.FAILSAFE = True  # Move mouse to upper-left corner to abort actions
pyautogui.PAUSE = 0.05     # Standard post-action pause

def generate_bezier_path(start_x, start_y, target_x, target_y, steps=30):
    """
    Generates a 2D spline curve path between start and target coordinates using quadratic spline interpolation.
    """
    if start_x == target_x and start_y == target_y:
        return [(target_x, target_y)]
        
    # Generate random control point to create curvature variation
    control_x = (start_x + target_x) / 2 + random.randint(-80, 80)
    control_y = (start_y + target_y) / 2 + random.randint(-80, 80)
    
    # Coordinates array
    x_points = np.array([start_x, control_x, target_x])
    y_points = np.array([start_y, control_y, target_y])
    
    # Parametric steps
    t_points = np.array([0.0, 0.4, 1.0])
    t_new = np.linspace(0.0, 1.0, num=steps)
    
    # Spline fitting
    spline_x = make_interp_spline(t_points, x_points, k=2)(t_new)
    spline_y = make_interp_spline(t_points, y_points, k=2)(t_new)
    
    return list(zip(spline_x, spline_y))

def human_like_mouse_move(target_x, target_y, duration_min=0.35, duration_max=0.75):
    """
    Moves the mouse cursor along a spline curve path with micro-jittering and easing.
    """
    start_x, start_y = pyautogui.position()
    if start_x == target_x and start_y == target_y:
        return
        
    # Determine step counts based on distance
    distance = np.sqrt((target_x - start_x)**2 + (target_y - start_y)**2)
    steps = int(max(15, min(50, distance / 15)))
    
    # Generate movement path
    path = generate_bezier_path(start_x, start_y, target_x, target_y, steps)
    
    # Biological movement easing (Gaussian distribution)
    total_duration = random.uniform(duration_min, duration_max)
    base_delay = total_duration / steps
    
    for i, (x, y) in enumerate(path):
        # Easing multiplier (slower at start and end, faster in middle)
        progress = i / steps
        multiplier = 1.5 - 2.0 * (progress - 0.5)**2  # parabolic multiplier
        delay = base_delay * (1.0 / max(0.1, multiplier))
        
        # Jitter values simulating real muscle tremors
        jitter_x = random.uniform(-0.5, 0.5)
        jitter_y = random.uniform(-0.5, 0.5)
        
        pyautogui.moveTo(int(x + jitter_x), int(y + jitter_y))
        time.sleep(max(0.001, delay + random.uniform(-0.001, 0.001)))
        
    # Final exact position snap
    pyautogui.moveTo(target_x, target_y)
    # Post-movement settling time (human reaction delay)
    time.sleep(random.uniform(0.08, 0.18))

def human_like_click(target_x, target_y, button="left", clicks=1):
    """
    Moves cursor to coordinate and performs physical human-speed click.
    """
    # 1. Move to coordinates
    human_like_mouse_move(target_x, target_y)
    
    # 2. Click interaction sequence
    for i in range(clicks):
        if i > 0:
            time.sleep(random.uniform(0.1, 0.2))  # Delay between clicks
            
        pyautogui.mouseDown(button=button)
        # Simulate button hold duration (milliseconds of physical switch closure)
        time.sleep(random.uniform(0.06, 0.12))
        pyautogui.mouseUp(button=button)
        
    # Settling pause
    time.sleep(random.uniform(0.1, 0.2))

def human_like_type(text, wpm=55):
    """
    Sends characters to the keyboard driver mimicking human typing cadence.
    """
    if not text:
        return
        
    # Calculate average key delay from Words Per Minute (5 characters per word)
    chars_per_min = wpm * 5
    avg_delay = 60.0 / chars_per_min
    
    for char in text:
        # Gaussian distribution delay for natural variation
        delay = random.gauss(avg_delay, avg_delay * 0.4)
        delay = max(0.01, min(1.0, delay))  # clamp delays
        
        # Capital letter and symbol delay adjustment (simulating shift-key activation)
        if char.isupper() or char in '!@#$%^&*()_+{}|:"<>?':
            delay += random.uniform(0.05, 0.15)
            
        pyautogui.write(char)
        time.sleep(delay)
        
        # Simulated typos (2% error rate with self-correction)
        if random.random() < 0.02 and char.isalnum():
            # Send wrong character
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            pyautogui.write(wrong_char)
            time.sleep(random.uniform(0.1, 0.25))
            # Delete it
            pyautogui.press("backspace")
            time.sleep(random.uniform(0.15, 0.3))
            
    # Post-typing settling pause
    time.sleep(random.uniform(0.2, 0.4))
