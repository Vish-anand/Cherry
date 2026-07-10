import json
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.schemas import Observation, RiskLevel, ScreenSize, VisualElement
from agent.vision_action import (
    ActionProposalError,
    infer_risk,
    observation_from_json,
    proposal_from_observation_json,
    propose_action_from_element,
    validate_action_proposal,
)


def sample_observation():
    return Observation(
        screenshot_path="screen.png",
        screen_size=ScreenSize(width=300, height=200),
        elements=[
            VisualElement(id="A1", label="top_left", bbox=(0, 0, 100, 100), source="grid"),
            VisualElement(id="B2", label="center", bbox=(100, 100, 200, 199), source="grid"),
        ],
        overlay_path="screen_overlay.png",
    )


class TestVisionAction(unittest.TestCase):
    def test_propose_click_from_element_center(self):
        proposal = propose_action_from_element(sample_observation(), "B2", rationale="open selected region")

        self.assertEqual(proposal.action_type, "click")
        self.assertEqual(proposal.target, (150.0, 149.5))
        self.assertEqual(proposal.risk_level, RiskLevel.MEDIUM)
        self.assertTrue(proposal.metadata["requires_approval"])
        self.assertEqual(proposal.metadata["element_id"], "B2")

    def test_propose_move_is_low_risk(self):
        proposal = propose_action_from_element(sample_observation(), "A1", action_type="move")

        self.assertEqual(proposal.target, (50.0, 50.0))
        self.assertEqual(proposal.risk_level, RiskLevel.LOW)
        self.assertFalse(proposal.metadata["requires_approval"])

    def test_type_requires_text_when_validated(self):
        with self.assertRaises(ActionProposalError):
            propose_action_from_element(sample_observation(), "A1", action_type="type")

    def test_unknown_element_raises(self):
        with self.assertRaises(ActionProposalError):
            propose_action_from_element(sample_observation(), "Z9")

    def test_observation_json_round_trip(self):
        observation = sample_observation()
        proposal = proposal_from_observation_json(
            observation_json_text=json.dumps(observation.to_dict()),
            element_id="A1",
            action_type="click",
        )

        self.assertEqual(proposal.target, (50.0, 50.0))
        self.assertEqual(observation_from_json(json.dumps(observation.to_dict())).screen_size.width, 300)

    def test_boundary_validation_rejects_edge_outside_screen(self):
        observation = Observation(
            screenshot_path="screen.png",
            screen_size=ScreenSize(width=100, height=100),
            elements=[VisualElement(id="A1", label="bad", bbox=(100, 100, 120, 120))],
        )
        with self.assertRaises(ActionProposalError):
            propose_action_from_element(observation, "A1", action_type="click")

    def test_risk_inference(self):
        self.assertEqual(infer_risk("move"), RiskLevel.LOW)
        self.assertEqual(infer_risk("click"), RiskLevel.MEDIUM)
        self.assertEqual(infer_risk("type", text="short text"), RiskLevel.MEDIUM)
        self.assertEqual(infer_risk("type", text="line one\nline two"), RiskLevel.HIGH)
        self.assertEqual(infer_risk("press_key", key="enter"), RiskLevel.HIGH)


if __name__ == "__main__":
    unittest.main()