import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.schemas import RiskLevel
from agent.memory import get_db_connection, get_pending_action
from agent.core import run_agent_generator

class TestSafetyGate(unittest.TestCase):
    def setUp(self):
        self.conversation_id = "test_safety_conv"
        # Pre-clean test databases
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (self.conversation_id,))
        cursor.execute("DELETE FROM pending_actions WHERE conversation_id = ?", (self.conversation_id,))
        conn.commit()
        conn.close()

    @patch('agent.core.call_llm')
    @patch('agent.core.TOOL_REGISTRY')
    def test_safety_gate_flow(self, mock_registry, mock_call_llm):
        """Verify high-risk actions yield requires_approval and pause, then resume execution."""
        # 1. Mock the LLM to output a high-risk Action (e.g. press_key enter)
        mock_call_llm.return_value = 'Thought: Press enter.\nAction: press_key\nAction Input: {"key": "enter"}'
        
        # Mock register tools
        mock_registry.__contains__.return_value = True
        mock_tool_func = MagicMock(return_value="Pressed Enter successfully")
        mock_registry.__getitem__.return_value = {"func": mock_tool_func}
        
        # Run generator
        steps = list(run_agent_generator(
            user_prompt="Press enter key",
            conversation_id=self.conversation_id,
            model="mock-model"
        ))
        
        # Verify it yielded requires_approval step
        approval_step = next((s for s in steps if s.get("type") == "requires_approval"), None)
        self.assertIsNotNone(approval_step)
        self.assertEqual(approval_step["action"], "press_key")
        self.assertEqual(approval_step["input"], {"key": "enter"})
        self.assertEqual(approval_step["risk_level"], "HIGH")
        
        action_id = approval_step["action_id"]
        
        # Verify action exists in database pending_actions table
        pending = get_pending_action(action_id)
        self.assertIsNotNone(pending)
        self.assertEqual(pending["action"], "press_key")
        self.assertEqual(pending["action_input"], {"key": "enter"})
        
        # 2. Mock execution for resume step
        steps_resume = list(run_agent_generator(
            user_prompt=None,
            conversation_id=self.conversation_id,
            resume_action_id=action_id
        ))
        
        # Verify the tool executed and yielded observation
        obs_step = next((s for s in steps_resume if s.get("type") == "observation"), None)
        self.assertIsNotNone(obs_step)
        self.assertEqual(obs_step["content"], "Pressed Enter successfully")
        mock_tool_func.assert_called_once_with(key="enter")

if __name__ == "__main__":
    unittest.main()
