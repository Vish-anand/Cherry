import os
import sys
import tempfile
import unittest

from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.schemas import ActionProposal, RiskLevel, ScreenSize, VisualElement
from agent.screen_parser import build_grid_elements, denormalize_point, map_box_to_pixels, normalize_point
from agent.visual_overlay import draw_overlay


class TestScreenParser(unittest.TestCase):
    def test_build_grid_elements(self):
        elements = build_grid_elements(300, 200, columns=3, rows=2)

        self.assertEqual(len(elements), 6)
        self.assertEqual(elements[0].id, "A1")
        self.assertEqual(elements[0].bbox, (0.0, 0.0, 100.0, 100.0))
        self.assertEqual(elements[-1].id, "B3")
        self.assertEqual(elements[-1].bbox, (200.0, 100.0, 300.0, 200.0))
        self.assertEqual(elements[-1].center, (250.0, 150.0))

    def test_visual_element_to_dict_includes_center(self):
        element = VisualElement(id="A1", label="screen_region", bbox=(10, 20, 30, 60))
        data = element.to_dict()

        self.assertEqual(data["center"], (20.0, 40.0))
        self.assertEqual(data["bbox"], (10.0, 20.0, 30.0, 60.0))

    def test_action_proposal_serializes_risk_level(self):
        proposal = ActionProposal(action_id="1", action_type="click", target=(10, 20), risk_level=RiskLevel.HIGH)
        data = proposal.to_dict()

        self.assertEqual(data["risk_level"], RiskLevel.HIGH)
        self.assertEqual(data["target"], (10.0, 20.0))

    def test_coordinate_normalization_helpers(self):
        screen = ScreenSize(width=1920, height=1080)
        self.assertEqual(normalize_point(500, 500, screen), (960, 540))
        self.assertEqual(denormalize_point(960, 540, screen), (500.0, 500.0))
        self.assertEqual(map_box_to_pixels([0, 0, 1000, 1000], screen).as_tuple(), (0, 0, 1919, 1079))

    def test_draw_overlay_creates_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            screenshot_path = os.path.join(temp_dir, "screen.png")
            overlay_path = os.path.join(temp_dir, "screen_overlay.png")
            Image.new("RGB", (120, 80), "white").save(screenshot_path)

            result_path = draw_overlay(
                screenshot_path,
                [VisualElement(id="A1", label="screen_region", bbox=(5, 5, 60, 40))],
                output_path=overlay_path,
            )

            self.assertEqual(result_path, overlay_path)
            self.assertTrue(os.path.exists(overlay_path))
            self.assertGreater(os.path.getsize(overlay_path), 0)


if __name__ == "__main__":
    unittest.main()