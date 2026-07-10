"""Shared Pydantic contracts for Cherry perception and action planning."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ScreenSize(BaseModel):
    width: int
    height: int

    def to_dict(self) -> Dict[str, int]:
        return self.model_dump()


class ElementBoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


class VisualElement(BaseModel):
    id: str
    label: str
    bbox: Tuple[float, float, float, float]
    confidence: float = 1.0
    source: str = "grid"

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        data["center"] = self.center
        return data


class Observation(BaseModel):
    screenshot_path: Optional[str] = None
    screen_size: ScreenSize
    elements: List[VisualElement] = Field(default_factory=list)
    overlay_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ActionProposal(BaseModel):
    action_id: str = Field(..., description="Unique UUID or identifier for the proposed action.")
    action_type: str = Field(..., description="The type of action, e.g. click, move, type, press_key.")
    target: Optional[Tuple[float, float]] = Field(None, description="The coordinate target (x, y) if applicable.")
    text: Optional[str] = Field(None, description="Text to type if applicable.")
    key: Optional[str] = Field(None, description="Key or shortcut to press if applicable.")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Safety risk classification.")
    reasoning: Optional[str] = Field(None, description="Explanation/rationale.")
    source_observation: Optional[str] = Field(None, description="Screenshot path this proposal came from.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata.")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ActionResult(BaseModel):
    proposal: ActionProposal
    success: bool
    message: str
    observation: Optional[Observation] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()