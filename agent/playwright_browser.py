import os
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", r"C:\Users\Admin\Desktop\Cherry"))
DEFAULT_STATE_FILE = WORKSPACE_ROOT / "playwright_state.json"

def launch_authenticated_browser(
    playwright,
    state_file_path: str = None,
    headless: bool = False,
    slow_mo: float = 0.0
) -> BrowserContext:
    """
    Launches a Chromium browser instance loading or persisting authorization session state.
    """
    state_path = Path(state_file_path) if state_file_path else DEFAULT_STATE_FILE
    
    # Standard security and anti-bot launching arguments
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized"
    ]
    
    # Launch persistent context to automatically persist and load local/session storage and cookies
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(state_path.with_name(f"{state_path.stem}_profile")),
        headless=headless,
        args=launch_args,
        slow_mo=slow_mo,
        ignore_default_args=["--enable-automation"],
        viewport=None  # Maximize
    )
    
    # Mask webdriver properties
    page = context.new_page() if not context.pages else context.pages[0]
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return context

def save_session_auth(context: BrowserContext, state_file_path: str = None):
    """
    Explicitly serializes and saves browser state (cookies/origins) for future logins.
    """
    state_path = Path(state_file_path) if state_file_path else DEFAULT_STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(state_path))
