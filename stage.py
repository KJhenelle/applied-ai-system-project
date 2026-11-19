"""The interactive companion stage as a Streamlit v2 component.

Python draws everything (SVG art, panels); the JavaScript in ui/pet_stage.js only wires up clicks,
dragging and animation, and reports each interaction back as a trigger value.
"""
from __future__ import annotations

from pathlib import Path

import streamlit.components.v2 as v2

from pawpal_ai.pet_art import component_css
from ui_theme import PANEL_CSS

_UI = Path(__file__).resolve().parent / "ui"

_component = v2.component(
    "pawpal_pet_stage",
    html='<div class="pp-root"></div>',
    css=component_css() + PANEL_CSS + (_UI / "pet_stage.css").read_text(),
    js=(_UI / "pet_stage.js").read_text(),
)


def pet_stage(data: dict, key: str, on_action) -> object:
    """Mount the stage. `on_action` runs (before the script body) whenever the user interacts."""
    return _component(data=data, key=key, on_action_change=on_action)
