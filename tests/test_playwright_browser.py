import unittest
import os
import sys
import shutil
from playwright.sync_api import sync_playwright

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.playwright_browser import launch_authenticated_browser, save_session_auth

class TestPlaywrightBrowser(unittest.TestCase):
    def test_browser_launch_success(self):
        """Verify launching the persistent browser context and verifying state serialization."""
        temp_state_dir = os.path.join(os.getcwd(), "test_playwright_state_profile")
        temp_state_file = os.path.join(os.getcwd(), "test_playwright_state.json")
        
        # Clean up in case of leftover directories from dirty runs
        if os.path.exists(temp_state_dir):
            shutil.rmtree(temp_state_dir, ignore_errors=True)
        if os.path.exists(temp_state_file):
            try:
                os.remove(temp_state_file)
            except Exception:
                pass
            
            
        with sync_playwright() as p:
            context = launch_authenticated_browser(
                p,
                state_file_path=temp_state_file,
                headless=True
            )
            try:
                self.assertIsNotNone(context)
                self.assertTrue(len(context.pages) >= 1)
                
                # Save session state
                save_session_auth(context, temp_state_file)
                self.assertTrue(os.path.exists(temp_state_file))
            finally:
                context.close()
                import time
                time.sleep(1.0)
                # Clean up folders/files
                if os.path.exists(temp_state_dir):
                    shutil.rmtree(temp_state_dir, ignore_errors=True)
                if os.path.exists(temp_state_file):
                    try:
                        os.remove(temp_state_file)
                    except Exception:
                        pass

if __name__ == "__main__":
    unittest.main()
