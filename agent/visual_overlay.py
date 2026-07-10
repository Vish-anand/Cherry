from PIL import Image, ImageDraw, ImageFont
from agent.schemas import VisualElement
from typing import List

def draw_visual_overlay(image_path: str, elements: List[VisualElement], save_path: str) -> str:
    """
    Draws a visual bounding box overlay with identifiers (Set-of-Mark) on a screenshot.
    Red outlines with a tag label block at the top-left of each bounding box.
    """
    # Open screen image
    img = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Try loading a system font, fallback to standard bitmap font
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
        
    for el in elements:
        xmin, ymin, xmax, ymax = el.bbox
        
        # 1. Draw red bounding box with semi-transparent red fill
        draw.rectangle(
            [xmin, ymin, xmax, ymax],
            outline=(255, 0, 0, 255),
            fill=(255, 0, 0, 25),
            width=2
        )
        
        # 2. Compute text bounding dimensions
        label_text = f" {el.id} "
        try:
            text_bbox = draw.textbbox((xmin, ymin), label_text, font=font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
        except AttributeError:
            text_w, text_h = 35, 14
            
        # Draw small background block for the identifier tag
        tag_top = max(0, ymin - text_h - 4)
        draw.rectangle(
            [xmin, tag_top, xmin + text_w + 4, ymin],
            fill=(255, 0, 0, 255)
        )
        
        # 3. Render the text label identifier inside the tag block
        draw.text(
            (xmin + 2, tag_top + 1),
            label_text,
            fill=(255, 255, 255, 255),
            font=font
        )
        
    # Composite the overlay onto the source screenshot
    composted = Image.alpha_composite(img, overlay).convert("RGB")
    composted.save(save_path, "PNG")
    return save_path

def draw_overlay(screenshot_path: str, elements: List[VisualElement], output_path: str = None) -> str:
    if output_path is None:
        import os
        root, ext = os.path.splitext(screenshot_path)
        output_path = f"{root}_overlay{ext or '.png'}"
    return draw_visual_overlay(screenshot_path, elements, output_path)