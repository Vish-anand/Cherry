"""
Cherry Computer-Use Tools
Full suite of powerful computer-use capabilities:
- Shell / terminal command execution (git, npm, pip, gradle, etc.)
- Screenshot with vision AI analysis
- Full file system operations (delete, copy, move, zip, extract)
- File downloading from URLs
- Clipboard read/write
- Process management (list, kill)
- System info (CPU, RAM, disk)
"""

import os
import sys
import json
import shutil
import subprocess
import platform
from datetime import datetime
from agent.tools import TOOL_REGISTRY, register_tool, WORKSPACE_ROOT, call_llm

# ==========================================
# SHELL / TERMINAL EXECUTION
# ==========================================

@register_tool(
    name="run_shell_command",
    description=(
        "Execute any PowerShell or CMD command on the user's Windows PC and return the output. "
        "Use this for: git operations (clone, push, pull, commit), building Android apps (gradlew build), "
        "running npm/pip/python scripts, creating directories, listing files, deploying projects, "
        "running any terminal command, and more. This is the most powerful tool — use it for anything that needs a shell."
    ),
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The PowerShell command to execute (e.g. 'git push origin main', 'npm install', 'python script.py', 'mkdir newproject')."
            },
            "working_directory": {
                "type": "string",
                "description": "Optional absolute path to run the command in. Defaults to workspace root."
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum seconds to wait (default: 120)."
            }
        },
        "required": ["command"]
    }
)
def run_shell_command(command: str, working_directory: str = None, timeout: int = 120):
    cwd = WORKSPACE_ROOT
    if working_directory and os.path.exists(working_directory):
        cwd = working_directory

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            encoding="utf-8",
            errors="replace"
        )
        parts = [f"Exit Code: {result.returncode}"]
        if result.stdout.strip():
            stdout = result.stdout.strip()
            if len(stdout) > 6000:
                stdout = stdout[:6000] + "\n...[output truncated]..."
            parts.append(f"Output:\n{stdout}")
        if result.stderr.strip():
            stderr = result.stderr.strip()
            if len(stderr) > 3000:
                stderr = stderr[:3000] + "\n...[error truncated]..."
            parts.append(f"Errors:\n{stderr}")
        return "\n".join(parts) if len(parts) > 1 else "Command completed with no output."
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds. Consider increasing timeout for long builds."
    except Exception as e:
        return f"Error running shell command: {str(e)}"


# ==========================================
# SCREENSHOT + VISION ANALYSIS
# ==========================================

@register_tool(
    name="take_screenshot",
    description=(
        "Take a screenshot of the current screen, save it to workspace, and analyze it using vision AI. "
        "Use this to check the state of an app after launching it, verify build results, read text on screen, "
        "or see what the user is currently looking at. Returns a full description of what is visible."
    ),
    parameters={
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Optional name to save screenshot as (e.g. 'build_result.png'). Auto-generated if not provided."
            }
        },
        "required": []
    }
)
def take_screenshot(filename: str = None):
    if not filename:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    if not filename.endswith(".png"):
        filename += ".png"

    save_path = os.path.join(WORKSPACE_ROOT, filename)

    # Try PIL first
    taken = False
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(save_path)
        taken = True
    except Exception:
        pass

    # Fallback: PowerShell .NET screenshot
    if not taken:
        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save('{save_path.replace(chr(92), '/')}')
$g.Dispose(); $bmp.Dispose()
Write-Output "saved"
"""
        try:
            r = subprocess.run(["powershell", "-Command", ps_script],
                               capture_output=True, text=True, timeout=15)
            if os.path.exists(save_path):
                taken = True
        except Exception as e:
            return f"Failed to take screenshot: {str(e)}"

    if not taken:
        return "Screenshot could not be captured."

    # Analyze the screenshot with vision AI
    try:
        description = call_llm(
            prompt=(
                "Look at this screenshot carefully. Describe in detail what you see: "
                "any open applications, content on screen, status messages, error messages, "
                "build output, or any other relevant information visible on the screen."
            ),
            attachment_path=save_path
        )
        return f"Screenshot saved as '{filename}'.\n\nScreen Content:\n{description}"
    except Exception:
        return f"Screenshot saved as '{filename}'. (Vision analysis unavailable — file is in workspace.)"


# ==========================================
# FILE OPERATIONS
# ==========================================

@register_tool(
    name="delete_file",
    description="Delete a file or an entire folder (recursively) from the file system. Use when the user asks to delete, remove, or clean up files or directories.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path or workspace-relative path of the file or folder to delete."
            },
            "recursive": {
                "type": "boolean",
                "description": "Set to true to delete a folder and all its contents. Default: false."
            }
        },
        "required": ["file_path"]
    }
)
def delete_file(file_path: str, recursive: bool = False):
    full_path = file_path if os.path.isabs(file_path) else os.path.join(WORKSPACE_ROOT, file_path)
    if not os.path.exists(full_path):
        return f"Error: '{file_path}' does not exist."
    try:
        if os.path.isdir(full_path):
            if recursive:
                shutil.rmtree(full_path)
                return f"Deleted folder '{full_path}' and all its contents."
            else:
                os.rmdir(full_path)
                return f"Deleted empty folder '{full_path}'."
        else:
            os.remove(full_path)
            return f"Deleted file '{full_path}'."
    except Exception as e:
        return f"Error deleting '{file_path}': {str(e)}"


@register_tool(
    name="copy_file",
    description="Copy a file or folder to a new location. Works for duplicating files, creating backups, or moving copies.",
    parameters={
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Source file or folder path (absolute or workspace-relative)."},
            "destination": {"type": "string", "description": "Destination path (absolute or workspace-relative)."}
        },
        "required": ["source", "destination"]
    }
)
def copy_file(source: str, destination: str):
    src = source if os.path.isabs(source) else os.path.join(WORKSPACE_ROOT, source)
    dst = destination if os.path.isabs(destination) else os.path.join(WORKSPACE_ROOT, destination)
    if not os.path.exists(src):
        return f"Error: Source '{source}' does not exist."
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            return f"Copied folder '{src}' to '{dst}'."
        else:
            shutil.copy2(src, dst)
            return f"Copied '{src}' to '{dst}'."
    except Exception as e:
        return f"Error copying: {str(e)}"


@register_tool(
    name="move_file",
    description="Move or rename a file or folder. Use for reorganizing the file system or renaming items.",
    parameters={
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Source path (absolute or workspace-relative)."},
            "destination": {"type": "string", "description": "Destination path (absolute or workspace-relative)."}
        },
        "required": ["source", "destination"]
    }
)
def move_file(source: str, destination: str):
    src = source if os.path.isabs(source) else os.path.join(WORKSPACE_ROOT, source)
    dst = destination if os.path.isabs(destination) else os.path.join(WORKSPACE_ROOT, destination)
    if not os.path.exists(src):
        return f"Error: Source '{source}' does not exist."
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        return f"Moved '{src}' to '{dst}'."
    except Exception as e:
        return f"Error moving: {str(e)}"


@register_tool(
    name="download_file",
    description=(
        "Download any file from a URL and save it to the workspace or a specified path. "
        "Use this to download images, music, PDFs, code files, or any other content from the internet."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The direct download URL of the file."},
            "save_path": {
                "type": "string",
                "description": "Where to save the file (absolute or workspace-relative path including filename, e.g. 'downloads/photo.jpg'). If not provided, auto-detects filename from URL."
            }
        },
        "required": ["url"]
    }
)
def download_file(url: str, save_path: str = None):
    import urllib.request
    import urllib.parse

    if not save_path:
        filename = os.path.basename(urllib.parse.urlparse(url).path) or "downloaded_file"
        save_path = os.path.join("downloads", filename)

    full_path = save_path if os.path.isabs(save_path) else os.path.join(WORKSPACE_ROOT, save_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response, open(full_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
        size_kb = os.path.getsize(full_path) / 1024
        return f"Downloaded file from '{url}' and saved to '{full_path}' ({size_kb:.1f} KB)."
    except Exception as e:
        return f"Failed to download '{url}': {str(e)}"


@register_tool(
    name="zip_folder",
    description="Compress a folder into a ZIP archive. Useful for packaging project builds or backing up folders.",
    parameters={
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Path to the folder to compress."},
            "output_path": {"type": "string", "description": "Path for the output ZIP file (e.g. 'my_project.zip'). Defaults to folder name."}
        },
        "required": ["folder_path"]
    }
)
def zip_folder(folder_path: str, output_path: str = None):
    src = folder_path if os.path.isabs(folder_path) else os.path.join(WORKSPACE_ROOT, folder_path)
    if not os.path.exists(src):
        return f"Error: '{folder_path}' does not exist."
    if not output_path:
        output_path = os.path.basename(src.rstrip("/\\")) + ".zip"
    dst = output_path if os.path.isabs(output_path) else os.path.join(WORKSPACE_ROOT, output_path)
    try:
        base = dst[:-4] if dst.endswith(".zip") else dst
        shutil.make_archive(base, "zip", src)
        return f"Created ZIP archive at '{base}.zip'."
    except Exception as e:
        return f"Error creating ZIP: {str(e)}"


@register_tool(
    name="extract_zip",
    description="Extract a ZIP archive to a specified folder.",
    parameters={
        "type": "object",
        "properties": {
            "zip_path": {"type": "string", "description": "Path to the ZIP file to extract."},
            "destination": {"type": "string", "description": "Folder to extract into. Defaults to same directory as ZIP."}
        },
        "required": ["zip_path"]
    }
)
def extract_zip(zip_path: str, destination: str = None):
    import zipfile
    full_zip = zip_path if os.path.isabs(zip_path) else os.path.join(WORKSPACE_ROOT, zip_path)
    if not os.path.exists(full_zip):
        return f"Error: ZIP file '{zip_path}' not found."
    dst = destination if destination else os.path.dirname(full_zip)
    if not os.path.isabs(dst):
        dst = os.path.join(WORKSPACE_ROOT, dst)
    try:
        with zipfile.ZipFile(full_zip, "r") as z:
            z.extractall(dst)
        return f"Extracted '{zip_path}' to '{dst}'."
    except Exception as e:
        return f"Error extracting ZIP: {str(e)}"


# ==========================================
# CLIPBOARD
# ==========================================

@register_tool(
    name="get_clipboard",
    description="Read the current text content of the Windows clipboard. Use when the user says 'what's in my clipboard' or wants to use copied content.",
    parameters={"type": "object", "properties": {}, "required": []}
)
def get_clipboard():
    ps = "Get-Clipboard"
    try:
        result = subprocess.run(["powershell", "-Command", ps],
                                capture_output=True, text=True, timeout=5)
        text = result.stdout.strip()
        return f"Clipboard content:\n{text}" if text else "Clipboard is empty."
    except Exception as e:
        return f"Error reading clipboard: {str(e)}"


@register_tool(
    name="set_clipboard",
    description="Write text to the Windows clipboard. Use when the user wants to copy something to clipboard.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The text to copy to the clipboard."}
        },
        "required": ["text"]
    }
)
def set_clipboard(text: str):
    escaped = text.replace("'", "''")
    ps = f"Set-Clipboard -Value '{escaped}'"
    try:
        subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True, timeout=5)
        preview = text[:100] + ("..." if len(text) > 100 else "")
        return f"Copied to clipboard: {preview}"
    except Exception as e:
        return f"Error writing clipboard: {str(e)}"


# ==========================================
# PROCESS MANAGEMENT
# ==========================================

@register_tool(
    name="list_running_processes",
    description="List all currently running processes on the PC with name, PID, and CPU usage. Use when the user asks what apps are running or wants to manage processes.",
    parameters={
        "type": "object",
        "properties": {
            "filter": {"type": "string", "description": "Optional filter string to show only matching process names."}
        },
        "required": []
    }
)
def list_running_processes(filter: str = None):
    ps = "Get-Process | Select-Object Name, Id, CPU, WorkingSet | Sort-Object CPU -Descending | ConvertTo-Json -Depth 1"
    try:
        result = subprocess.run(["powershell", "-Command", ps],
                                capture_output=True, text=True, timeout=15)
        procs = json.loads(result.stdout.strip())
        if not isinstance(procs, list):
            procs = [procs]
        if filter:
            f = filter.lower()
            procs = [p for p in procs if f in (p.get("Name") or "").lower()]
        lines = [f"{'NAME':<35} {'PID':<8} {'CPU':<10} {'MEM(MB)':<10}"]
        lines.append("-" * 65)
        for p in procs[:50]:
            name = (p.get("Name") or "")[:34]
            pid = str(p.get("Id", ""))
            cpu = f"{p.get('CPU', 0):.1f}" if p.get('CPU') else "0.0"
            mem = f"{(p.get('WorkingSet', 0) or 0) / 1024 / 1024:.1f}"
            lines.append(f"{name:<35} {pid:<8} {cpu:<10} {mem:<10}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing processes: {str(e)}"


@register_tool(
    name="kill_process",
    description="Kill / terminate a running process by name or PID. Use when the user wants to close or force-stop an application.",
    parameters={
        "type": "object",
        "properties": {
            "process_name": {"type": "string", "description": "Name of the process to kill (e.g. 'chrome', 'notepad'). Leave blank if using pid."},
            "pid": {"type": "integer", "description": "Process ID to kill. Leave blank if using process_name."}
        },
        "required": []
    }
)
def kill_process(process_name: str = None, pid: int = None):
    try:
        if pid:
            result = subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                                    capture_output=True, text=True, timeout=10)
        elif process_name:
            name = process_name.replace(".exe", "")
            result = subprocess.run(["taskkill", "/F", "/IM", f"{name}.exe"],
                                    capture_output=True, text=True, timeout=10)
        else:
            return "Please provide either a process name or PID."
        if result.returncode == 0:
            return f"Successfully terminated '{process_name or pid}'."
        else:
            return f"Could not terminate: {result.stderr.strip() or result.stdout.strip()}"
    except Exception as e:
        return f"Error killing process: {str(e)}"


# ==========================================
# SYSTEM INFO
# ==========================================

@register_tool(
    name="get_system_info",
    description="Get detailed system information: OS version, CPU, RAM usage, disk space, GPU, battery level, and network info. Use when the user asks about their PC specs or system status.",
    parameters={"type": "object", "properties": {}, "required": []}
)
def get_system_info():
    ps = r"""
$os = Get-WmiObject Win32_OperatingSystem
$cpu = Get-WmiObject Win32_Processor | Select-Object -First 1
$mem_total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
$mem_free = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$mem_used = $mem_total - $mem_free
$disks = Get-PSDrive -PSProvider FileSystem | Where-Object {$_.Used -ne $null} | Select-Object Name, @{N='UsedGB';E={[math]::Round($_.Used/1GB,2)}}, @{N='FreeGB';E={[math]::Round($_.Free/1GB,2)}}

Write-Output "=== System Information ==="
Write-Output "OS: $($os.Caption) $($os.OSArchitecture)"
Write-Output "Uptime: $([math]::Round(($os.LocalDateTime - $os.LastBootUpTime).TotalHours, 1)) hours"
Write-Output "CPU: $($cpu.Name)"
Write-Output "CPU Cores: $($cpu.NumberOfCores) cores, $($cpu.NumberOfLogicalProcessors) threads"
Write-Output "RAM: $mem_used GB used / $mem_total GB total ($([math]::Round($mem_used/$mem_total*100,1))% used)"
Write-Output "Drives:"
foreach ($d in $disks) { Write-Output "  $($d.Name): $($d.UsedGB) GB used / $([math]::Round($d.UsedGB+$d.FreeGB,2)) GB total ($($d.FreeGB) GB free)" }
$battery = Get-WmiObject Win32_Battery -ErrorAction SilentlyContinue
if ($battery) { Write-Output "Battery: $($battery.EstimatedChargeRemaining)% ($($battery.BatteryStatus))" }
"""
    try:
        result = subprocess.run(["powershell", "-Command", ps],
                                capture_output=True, text=True, timeout=15)
        return result.stdout.strip() or "Could not retrieve system info."
    except Exception as e:
        return f"Error getting system info: {str(e)}"


# ==========================================
# SCREEN / MOUSE / KEYBOARD
# ==========================================

@register_tool(
    name="type_text",
    description="Type text as keyboard input into the currently focused window. Use when you need to type into an app, form, or dialog on screen.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The text to type."},
            "delay_seconds": {"type": "number", "description": "How many seconds to wait before typing (e.g. 2 to give time to click a window)."}
        },
        "required": ["text"]
    }
)
def type_text(text: str, delay_seconds: float = 0):
    try:
        import pyautogui
        import time
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        pyautogui.typewrite(text, interval=0.05)
        return f"Typed: {text[:100]}"
    except ImportError:
        # Fallback: PowerShell SendKeys
        escaped = text.replace("'", "\\'")
        ps = f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Threading.Thread]::Sleep({int(delay_seconds * 1000)})
[System.Windows.Forms.SendKeys]::SendWait('{escaped}')
"""
        try:
            subprocess.run(["powershell", "-Command", ps], timeout=15)
            return f"Typed text via SendKeys."
        except Exception as e:
            return f"Error typing text: {str(e)}"
    except Exception as e:
        return f"Error typing text: {str(e)}"


@register_tool(
    name="press_key",
    description="Simulate pressing a keyboard key or shortcut (e.g. Enter, Escape, Ctrl+C, Win+D, Alt+F4). Use for keyboard shortcuts.",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key or shortcut to press (e.g. 'enter', 'escape', 'ctrl+c', 'win+d', 'alt+f4', 'ctrl+s')."},
            "delay_seconds": {"type": "number", "description": "Seconds to wait before pressing the key."}
        },
        "required": ["key"]
    }
)
def press_key(key: str, delay_seconds: float = 0):
    try:
        import pyautogui
        import time
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        if "+" in key:
            parts = [p.strip() for p in key.split("+")]
            pyautogui.hotkey(*parts)
        else:
            pyautogui.press(key)
        return f"Pressed key: {key}"
    except ImportError:
        # Fallback using PowerShell SendKeys
        key_map = {
            "enter": "{ENTER}", "escape": "{ESC}", "esc": "{ESC}",
            "tab": "{TAB}", "space": " ", "backspace": "{BACKSPACE}",
            "delete": "{DELETE}", "ctrl+c": "^c", "ctrl+v": "^v",
            "ctrl+s": "^s", "ctrl+z": "^z", "ctrl+a": "^a",
            "alt+f4": "%{F4}", "win+d": "^{ESC}", "f5": "{F5}"
        }
        send_key = key_map.get(key.lower(), key)
        ps = f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Threading.Thread]::Sleep({int(delay_seconds * 1000)})
[System.Windows.Forms.SendKeys]::SendWait('{send_key}')
"""
        try:
            subprocess.run(["powershell", "-Command", ps], timeout=10)
            return f"Pressed key: {key}"
        except Exception as e:
            return f"Error pressing key: {str(e)}"
    except Exception as e:
        return f"Error pressing key: {str(e)}"


print("[OK] Cherry Computer-Use Tools loaded successfully.")
