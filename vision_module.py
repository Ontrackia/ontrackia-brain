"""Vision module (image analysis).

In production this should call an OpenAI vision-capable model (e.g. gpt-4.1-mini with image input).
"""
from typing import Dict, Any


def analyze_image(image_bytes: bytes, question: str) -> Dict[str, Any]:
    # Placeholder: describe that in real deployment this will call a vision model.
    summary = (
        "Vision analysis placeholder. In a real deployment this will analyse the image to detect "
        "component condition, obvious damage, FOD risks, and support the reasoning process. "
        "Always validate visually and with OEM instructions."
    )
    return {"summary": summary}
