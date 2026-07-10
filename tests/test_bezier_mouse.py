import unittest
import sys
import os
from unittest.mock import patch, call

# Append workspace to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.bezier_mouse import generate_bezier_path, human_like_mouse_move, human_like_click, human_like_type

class TestBezierMouse(unittest.TestCase):
    def test_generate_path_basic(self):
        """Verify spline generation constructs path sequences correctly."""
        start_x, start_y = 100, 100
        target_x, target_y = 500, 400
        steps = 20
        
        path = generate_bezier_path(start_x, start_y, target_x, target_y, steps)
        
        self.assertEqual(len(path), steps)
        # Check start and end of path are correct boundaries
        self.assertAlmostEqual(path[0][0], start_x, delta=10)
        self.assertAlmostEqual(path[0][1], start_y, delta=10)
        self.assertAlmostEqual(path[-1][0], target_x, delta=10)
        self.assertAlmostEqual(path[-1][1], target_y, delta=10)

    def test_generate_path_zero_distance(self):
        """Verify zero distance returns target coordinates instantly."""
        start_x, start_y = 300, 300
        target_x, target_y = 300, 300
        
        path = generate_bezier_path(start_x, start_y, target_x, target_y)
        self.assertEqual(path, [(300, 300)])

    @patch('agent.bezier_mouse.pyautogui')
    @patch('agent.bezier_mouse.time.sleep')
    def test_human_like_mouse_move(self, mock_sleep, mock_pyautogui):
        """Verify human-like mouse movement calls pyautogui.moveTo and snaps to target."""
        mock_pyautogui.position.return_value = (100, 100)
        
        human_like_mouse_move(200, 200)
        
        # Verify it ends up at the exact target
        mock_pyautogui.moveTo.assert_called_with(200, 200)
        self.assertTrue(mock_pyautogui.moveTo.call_count > 1)
        self.assertTrue(mock_sleep.call_count > 0)

    @patch('agent.bezier_mouse.pyautogui')
    @patch('agent.bezier_mouse.time.sleep')
    def test_human_like_click(self, mock_sleep, mock_pyautogui):
        """Verify click sequence presses and releases mouse buttons at coordinates."""
        mock_pyautogui.position.return_value = (100, 100)
        
        human_like_click(150, 150, button="left", clicks=2)
        
        # Should move mouse
        mock_pyautogui.moveTo.assert_called_with(150, 150)
        # Should trigger mouseDown and mouseUp twice
        self.assertEqual(mock_pyautogui.mouseDown.call_count, 2)
        self.assertEqual(mock_pyautogui.mouseUp.call_count, 2)
        mock_pyautogui.mouseDown.assert_called_with(button="left")
        mock_pyautogui.mouseUp.assert_called_with(button="left")

    @patch('agent.bezier_mouse.pyautogui')
    @patch('agent.bezier_mouse.time.sleep')
    def test_human_like_type(self, mock_sleep, mock_pyautogui):
        """Verify typing simulates keys and handles empty input gracefully."""
        # Test empty input
        human_like_type("")
        mock_pyautogui.write.assert_not_called()
        
        # Test basic typing
        human_like_type("Hello")
        # Should call write for characters
        self.assertTrue(mock_pyautogui.write.call_count >= 5)

if __name__ == "__main__":
    unittest.main()

