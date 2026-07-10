import unittest
import os
import sys

from unittest.mock import patch, MagicMock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from agent.screen_capture import capture_screen, get_active_window_info, ScreenCaptureError

class TestScreenCapture(unittest.TestCase):
    def test_get_active_window_info(self):
        """Verify we retrieve info dictionary from active window calls."""
        info = get_active_window_info()
        self.assertIn("title", info)
        self.assertIn("box", info)
        
    @patch('agent.screen_capture.Image')
    @patch('mss.MSS')
    def test_capture_screen_success(self, mock_mss_class, mock_image):
        """Verify screen capture returns valid image file details using mock."""
        mock_sct = MagicMock()
        mock_mss_class.return_value.__enter__.return_value = mock_sct
        mock_sct_img = MagicMock()
        mock_sct_img.size = (1920, 1080)
        mock_sct_img.bgra = b'fakebytes'
        mock_sct.monitors = [{}, {"width": 1920, "height": 1080}]
        mock_sct.grab.return_value = mock_sct_img
        
        mock_pil_img = MagicMock()
        mock_pil_img.width = 1920
        mock_pil_img.height = 1080
        mock_image.frombytes.return_value = mock_pil_img
        
        temp_path = os.path.join(os.getcwd(), "test_temp_screenshot.png")
        path, w, h = capture_screen(temp_path)
        self.assertEqual(path, temp_path)
        self.assertEqual(w, 1920)
        self.assertEqual(h, 1080)
        mock_pil_img.save.assert_called_with(temp_path)

if __name__ == "__main__":
    from unittest.mock import patch, MagicMock
    unittest.main()

