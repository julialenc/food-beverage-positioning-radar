"""
Shared rendering helpers for the Streamlit app.

Chip styling is deliberately muted for both claim chips and benchmark
flag chips — no red/orange "warning" colors anywhere — per the brief's
no-blame requirement (see docs/ADR.md and the project's onboarding
notes: "muted benchmark chips, not red warning boxes"). The two chip
tones below distinguish *category* (a positioning claim vs. a nutrition
benchmark flag vs. a co-occurrence), never severity or judgment. Do not
add a third "alert" tone without re-reading that requirement.
"""

from __future__ import annotations

import html
from typing import Optional

import streamlit as st

# (background, text) — both tones are intentionally close in visual
# weight to each other; neither should read as more "severe" than the
# other.
CHIP_STYLES = {
    "claim": ("#EFE7DC", "#5B4636"),       # warm sand — positioning claims
    "benchmark": ("#E4E8E6", "#3F4A47"),   # cool slate — nutrition benchmark flags
    "neutral": ("#ECECEC", "#4A4A4A"),     # claim-benchmark intersections, fallback
}

PRIMARY_ACCENT = "#4F6D64"


def inject_base_css() -> None:
    st.markdown(
        """
        <style>
        /* System font stack — no external CDN dependency, no flash of
           unstyled content. Space Grotesk/IBM Plex Mono are used if
           locally installed; otherwise falls back cleanly. */

        .fbpr-header { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.1rem; }
        .fbpr-header h1 {
            font-family: 'Space Grotesk', ui-sans-serif, system-ui, sans-serif;
            font-weight: 600; font-size: 1.6rem; margin: 0; color: #232723;
        }
        .fbpr-tagline { color: #6B756F; font-size: 0.95rem; margin-bottom: 1.1rem; }

        .fbpr-chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.2rem 0 0.8rem 0; }
        .fbpr-chip {
            display: inline-block; padding: 0.18rem 0.65rem; border-radius: 999px;
            font-size: 0.82rem; font-weight: 500; line-height: 1.4;
            border: 1px solid rgba(0,0,0,0.07);
        }
        .fbpr-section-label {
            font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.05em;
            color: #8A8F8A; margin: 1.0rem 0 0.2rem 0; font-weight: 600;
        }
        .fbpr-empty-note { color: #9A9F9A; font-style: italic; font-size: 0.88rem; }
        .fbpr-mono { font-family: 'IBM Plex Mono', ui-monospace, 'Cascadia Code', 'Consolas', monospace; }
        .fbpr-caption { color: #8A8F8A; font-size: 0.82rem; margin-top: -0.3rem; margin-bottom: 0.6rem; }
        .fbpr-badge {
            display: inline-flex; align-items: center; gap: 0.4rem;
            border: 1px solid #DEE2DE; border-radius: 8px; padding: 0.35rem 0.7rem;
            font-size: 0.85rem; color: #232723; background: #FBFCFB;
        }
        .fbpr-product-image-box {
            width: min(100%, 340px);
            aspect-ratio: 4 / 5;
            border: 1px solid #D8DDD8;
            border-radius: 12px;
            background: #F7F8F6;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .fbpr-product-image-box img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }
        .fbpr-product-image-empty {
            color: #8A918A;
            font-size: 0.85rem;
            text-align: center;
            padding: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str, tagline: str) -> None:
    radar_svg = f"""
    <svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
      <circle cx="15" cy="15" r="13" fill="none" stroke="{PRIMARY_ACCENT}" stroke-width="1.2" opacity="0.35"/>
      <circle cx="15" cy="15" r="8.5" fill="none" stroke="{PRIMARY_ACCENT}" stroke-width="1.2" opacity="0.55"/>
      <circle cx="15" cy="15" r="4" fill="none" stroke="{PRIMARY_ACCENT}" stroke-width="1.2" opacity="0.8"/>
      <line x1="15" y1="15" x2="26" y2="6" stroke="{PRIMARY_ACCENT}" stroke-width="1.6" stroke-linecap="round"/>
      <circle cx="15" cy="15" r="1.6" fill="{PRIMARY_ACCENT}"/>
    </svg>
    """
    st.markdown(
        f'<div class="fbpr-header">{radar_svg}<h1>{title}</h1></div>'
        f'<div class="fbpr-tagline">{tagline}</div>',
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(f'<div class="fbpr-section-label">{html.escape(str(text))}</div>', unsafe_allow_html=True)


def caption(text: str) -> None:
    st.markdown(f'<div class="fbpr-caption">{html.escape(str(text))}</div>', unsafe_allow_html=True)


def render_chips(labels: list[str], kind: str = "neutral", empty_text: str = "None identified") -> None:
    if not labels:
        st.markdown(f'<div class="fbpr-empty-note">{empty_text}</div>', unsafe_allow_html=True)
        return
    bg, fg = CHIP_STYLES.get(kind, CHIP_STYLES["neutral"])
    chips_html = "".join(
        f'<span class="fbpr-chip" style="background:{bg}; color:{fg};">{html.escape(str(label))}</span>'
        for label in labels
    )
    st.markdown(f'<div class="fbpr-chip-row">{chips_html}</div>', unsafe_allow_html=True)


def render_badge(text: str) -> str:
    """Returns badge HTML (caller wraps in st.markdown) so two badges
    can sit side by side in columns without each call adding its own
    block-level spacing."""
    return f'<span class="fbpr-badge">{text}</span>'



def render_product_pack_image(image_url: Optional[str], product_name: str = "") -> None:
    """Render product pack image inside a controlled responsive preview box.

    Uses object-fit: contain so the full pack is always visible, but the
    image cannot expand to fill a tall column — which would make tall pack
    formats (bottles, chocolate bars) dominate the card layout. The CSS
    box has a fixed aspect ratio (4:5) so all product cards maintain the
    same proportions regardless of the source image dimensions.

    Callers should pass the already-validated URL from product_image_url()
    rather than the raw DB value, but this function also handles None
    directly so it can be called unconditionally without a prior check.
    """
    if not image_url:
        st.markdown(
            '<div class="fbpr-product-image-box fbpr-product-image-empty">'
            "No pack image available"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    safe_url = html.escape(str(image_url), quote=True)
    safe_alt = html.escape(
        f"Pack image for {product_name}" if product_name else "Product pack image"
    )
    st.markdown(
        f'<div class="fbpr-product-image-box">'
        f'<img src="{safe_url}" alt="{safe_alt}" />'
        f"</div>",
        unsafe_allow_html=True,
    )


def product_image_url(raw_url: Optional[str]) -> Optional[str]:
    """Returns None for missing, NaN, or known-placeholder image URLs
    (Open Food Facts marks unavailable images with '/invalid/' in the
    path — see docs/COLUMN_DESCRIPTIONS.md) so callers can render a
    neutral "no image available" placeholder instead of a broken image.
    NaN (not just None) is handled explicitly: pandas returns NaN, not
    None, for a NULL TEXT column in at least some read paths, and the
    `in` operator on a float raises TypeError."""
    if raw_url is None:
        return None

    text = str(raw_url).strip()
    if text == "" or text.lower() == "nan" or "/invalid/" in text:
        return None

    return text
