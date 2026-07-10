import unittest
import os
import sys
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.schemas import VisualElement
from agent.visual_overlay import draw_visual_overlay

class TestVisualOverlay(unittest.TestCase):
    def test_draw_overlay_success(self):
        """Verify we draw red Set-of-Mark box overlays on sample source image."""
        temp_src = os.path.join(os.getcwd(), "test_temp_src.png")
        temp_out = os.path.join(os.getcwd(), "test_temp_out.png")
        
        # Create small test background
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        img.save(temp_src)
        
        elements = [
            VisualElement(id="A1", label="test_button", bbox=(20, 20, 100, 80), source="grid")
        ]
        
        try:
            path = draw_visual_overlay(temp_src, elements, temp_out)
            self.assertEqual(path, temp_out)
            self.assertTrue(os.path.exists(temp_out))
            
            # Read created image details
            with Image.open(temp_out) as out_img:
                self.assertEqual(out_img.size, (200, 200))
        finally:
            if os.path.exists(temp_src):
                os.remove(temp_src)
            if os.path.exists(temp_out):
                os.remove(temp_out)

if __name__ == "__main__":
    unittest.main()
