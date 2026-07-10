"""Convert screen observations into safe, structured action proposals."""

from __future__ import annotations

import json
import uuid
from typing import Optional

from agent.schemas import ActionProposal, Observation, RiskLevel, ScreenSize


SUPPORTED_ACTIONS = {"click", "move", "type", "press_key"}
HIGH_RISK_KEYS = {"enter", "ctrl+s", "ctrl+v", "alt+f4", "delete", "backspace"}


class ActionProposalError(Exception):
    pass


def infer_risk(action_type: str, text: Optional[str] = None, key: Optional[str] = None) -> RiskLevel:
    action = action_type.lower().strip()
    if action == "move":
        return RiskLevel.LOW
    if action == "click":
        return RiskLevel.MEDIUM
    if action == "type":
        if text and len(text) <= 24 and "\n" not in text:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH
    if action == "press_key":
        normalized_key = (key or text or "").lower().strip()
        return RiskLevel.HIGH if normalized_key in HIGH_RISK_KEYS else RiskLevel.MEDIUM
    return RiskLevel.HIGH


def _find_element(observation: Observation, element_id: str):
    requested = element_id.strip().upper()
    for element in observation.elements:
        if element.id.upper() == requested:
            return element
    raise ActionProposalError(f"VisualElement with ID '{element_id}' not found in observation.")


def propose_action_from_element(
    observation: Observation,
    element_id: str,
    action_type: str = "click",
    rationale: Optional[str] = None,
    text: Optional[str] = None,
    key: Optional[str] = None,
) -> ActionProposal:
    action = action_type.lower().strip()
    if action not in SUPPORTED_ACTIONS:
        raise ActionProposalError(f"Unsupported action_type '{action_type}'. Supported actions: {sorted(SUPPORTED_ACTIONS)}.")

    target_element = _find_element(observation, element_id)
    target = None
    if action in {"click", "move", "type"}:
        target = target_element.center

    risk = infer_risk(action, text=text, key=key)
    requires_approval = risk in {RiskLevel.MEDIUM, RiskLevel.HIGH}

    proposal = ActionProposal(
        action_id=str(uuid.uuid4()),
        action_type=action,
        target=target,
        text=text,
        key=key,
        risk_level=risk,
        reasoning=rationale or "",
        source_observation=observation.screenshot_path,
        metadata={
            "requires_approval": requires_approval,
            "element_id": target_element.id,
            "element_label": target_element.label,
            "element_bbox": target_element.bbox,
            "overlay_path": observation.overlay_path,
        },
    )
    validate_action_proposal(proposal, observation.screen_size)
    return proposal


def observation_from_json(json_text: str) -> Observation:
    try:
        data = json.loads(json_text)
        return Observation(**data)
    except Exception as e:
        raise ActionProposalError(f"Failed to decode Observation structure from JSON: {str(e)}")


def proposal_from_observation_json(
    observation_json_text: str,
    element_id: str,
    action_type: str = "click",
    rationale: Optional[str] = None,
    text: Optional[str] = None,
    key: Optional[str] = None,
) -> ActionProposal:
    obs = observation_from_json(observation_json_text)
    return propose_action_from_element(
        observation=obs,
        element_id=element_id,
        action_type=action_type,
        rationale=rationale,
        text=text,
        key=key,
    )


def validate_action_proposal(proposal: ActionProposal, screen_size: ScreenSize) -> None:
    action = proposal.action_type.lower().strip()
    if action not in SUPPORTED_ACTIONS:
        raise ActionProposalError(f"Unsupported action_type '{proposal.action_type}'.")

    if action in {"click", "move", "type"}:
        if proposal.target is None:
            raise ActionProposalError(f"Action '{action}' requires target coordinates.")
        x, y = proposal.target
        if x < 0 or y < 0 or x >= screen_size.width or y >= screen_size.height:
            raise ActionProposalError(
                f"Proposed coordinates ({x}, {y}) lie outside screen boundaries ({screen_size.width}x{screen_size.height})."
            )

    if action == "type" and not proposal.text:
        raise ActionProposalError("Type actions require non-empty 'text' parameter.")

    if action == "press_key" and not (proposal.key or proposal.text):
        raise ActionProposalError("press_key actions require a key name.")