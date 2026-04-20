"""Shared pytest setup.

Configure matplotlib to use a CJK-capable font family so worm-gear stress
curves don't emit hundreds of `Glyph XXXX missing from DejaVu Sans`
warnings during UI tests.
"""

from __future__ import annotations

from app.ui.fonts import configure_matplotlib_fonts

configure_matplotlib_fonts()
