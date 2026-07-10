"""Screen parsing and observation assembly for Cherry's vision-to-action layer."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from agent.schemas import ElementBoundingBox, Observation, ScreenSize, VisualElement
from agent.screen_capture import capture_screen
from agent.visual_overlay import draw_visual_overlay


def normalize_point(x: float, y: float, screen: ScreenSize, from_scale: float = 1000.0) -> Tuple[int, int]:
    scale_factor_x = screen.width / from_scale
    scale_factor_y = screen.height / from_scale
    abs_x = int(round(x * scale_factor_x))
    abs_y = int(round(y * scale_factor_y))
    abs_x = max(0, min(screen.width - 1, abs_x))
    abs_y = max(0, min(screen.height - 1, abs_y))
    return abs_x, abs_y


def denormalize_point(abs_x: int, abs_y: int, screen: ScreenSize, target_scale: float = 1000.0) -> Tuple[float, float]:
    norm_x = (abs_x / screen.width) * target_scale
    norm_y = (abs_y / screen.height) * target_scale
    return round(norm_x, 2), round(norm_y, 2)


def extract_boxes_from_text(text: str) -> List[List[float]]:
    pattern = r"\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\]"
    matches = re.findall(pattern, text)
    return [[float(val) for val in match] for match in matches]


def map_box_to_pixels(box: List[float], screen: ScreenSize, from_scale: float = 1000.0) -> ElementBoundingBox:
    ymin, xmin, ymax, xmax = box
    x1, y1 = normalize_point(xmin, ymin, screen, from_scale)
    x2, y2 = normalize_point(xmax, ymax, screen, from_scale)
    return ElementBoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)


def build_grid_elements(width: int, height: int, columns: int = 3, rows: int = 3) -> List[VisualElement]:
    elements: List[VisualElement] = []
    cell_width = width / columns
    cell_height = height / rows
    label_ord = ord("A")

    for row in range(rows):
        for column in range(columns):
            element_id = f"{chr(label_ord + row)}{column + 1}"
            x1 = int(round(column * cell_width))
            y1 = int(round(row * cell_height))
            x2 = int(round((column + 1) * cell_width))
            y2 = int(round((row + 1) * cell_height))
            elements.append(
                VisualElement(
                    id=element_id,
                    label="screen_region",
                    bbox=(x1, y1, x2, y2),
                    confidence=1.0,
                    source="grid",
                )
            )
    return elements


def _default_screenshot_path(filename: Optional[str] = None, output_dir: Optional[str] = None) -> str:
    workspace_root = Path(os.getenv("WORKSPACE_ROOT", r"C:\Users\Admin\Desktop\Cherry"))
    if not filename:
        filename = f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    if not filename.lower().endswith(".png"):
        filename += ".png"
    base = Path(output_dir) if output_dir else workspace_root / "screenshots"
    if not base.is_absolute():
        base = workspace_root / base
    base.mkdir(parents=True, exist_ok=True)
    return str(base / filename)


def observe_screen(
    filename: Optional[str] = None,
    output_dir: Optional[str] = None,
    overlay: bool = True,
    columns: int = 3,
    rows: int = 3,
) -> Observation:
    screenshot_path, width, height = capture_screen(_default_screenshot_path(filename, output_dir))
    screen_size = ScreenSize(width=width, height=height)
    elements = build_grid_elements(width, height, columns=columns, rows=rows)
    overlay_path = None
    if overlay:
        source = Path(screenshot_path)
        overlay_path = str(source.with_name(f"{source.stem}_overlay{source.suffix}"))
        draw_visual_overlay(screenshot_path, elements, overlay_path)

    obs = Observation(
        screenshot_path=screenshot_path,
        screen_size=screen_size,
        elements=elements,
        overlay_path=overlay_path,
        metadata={
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "overlay_enabled": overlay,
            "grid": {"columns": columns, "rows": rows},
        },
    )
    
    try:
        cache_path = Path(screenshot_path).parent / "last_observation.json"
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(obs.to_dict(), indent=2))
    except Exception:
        pass
        
    return obs


def observation_json(observation: Observation) -> str:
    return json.dumps(observation.to_dict(), indent=2)