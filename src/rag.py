"""RAG module: Gemini-powered explanations for music similarity.

Retrieves audio features and tags for a seed and candidate,
then generates a natural language explanation using the Google Gemini API.
"""

from __future__ import annotations

import logging
from typing import Any

from google import genai

from src.config import get_google_api_key, RAG_MODEL, RAG_MAX_TOKENS, AUDIO_FEATURES

logger = logging.getLogger(__name__)


def build_context(
    seed: dict[str, Any],
    candidate: dict[str, Any],
    shared_tags: list[str],
    audio_score: float,
    tag_score: float | None,
    confidence: str,
) -> str:
    """Build the retrieval context string for the Gemini prompt.

    Formats audio features, tags, shared tags, and scores into
    a structured text block that the model can reason about.

    Args:
        seed: Dict with seed track metadata and features.
        candidate: Dict with candidate track metadata and features.
        shared_tags: Tags in common between the two artists.
        audio_score: Audio cosine similarity score.
        tag_score: Tag Jaccard similarity score, or None.
        confidence: Confidence level string.

    Returns:
        Formatted context string.
    """
    lines = []

    # Seed info
    lines.append(f"SEED TRACK: {seed.get('track_name', '?')} by {seed.get('artist', '?')}")
    lines.append(f"  Genre: {seed.get('genre', 'unknown')}")
    seed_features = ", ".join(f"{f}: {seed.get(f, 0):.2f}" for f in AUDIO_FEATURES if f in seed)
    lines.append(f"  Audio features: {seed_features}")

    lines.append("")

    # Candidate info
    lines.append(f"CANDIDATE TRACK: {candidate.get('track_name', '?')} by {candidate.get('artist', '?')}")
    lines.append(f"  Genre: {candidate.get('genre', 'unknown')}")
    cand_features = ", ".join(f"{f}: {candidate.get(f, 0):.2f}" for f in AUDIO_FEATURES if f in candidate)
    lines.append(f"  Audio features: {cand_features}")

    lines.append("")

    # Similarity data
    lines.append(f"SIMILARITY SCORES:")
    lines.append(f"  Audio cosine similarity: {audio_score:.3f}")
    if tag_score is not None:
        lines.append(f"  Tag Jaccard similarity: {tag_score:.3f}")
    if shared_tags:
        lines.append(f"  Shared tags: {', '.join(shared_tags)}")
    lines.append(f"  Confidence: {confidence}")

    return "\n".join(lines)


def build_prompt(context: str) -> str:
    """Build the full prompt for Gemini.

    Args:
        context: The retrieval context from build_context().

    Returns:
        Complete prompt string.
    """
    return (
        "You are a music expert helping users discover new music. "
        "Given the following data about two tracks, explain in 2-3 sentences "
        "why a fan of the seed track might enjoy the candidate track. "
        "Focus on actual musical qualities (instrumentation, production style, "
        "rhythm, vocal delivery, energy), not genre labels. "
        "Reference the specific audio feature similarities from the data. "
        "If confidence is 'low', briefly note that the connection is less certain.\n\n"
        f"{context}"
    )


def generate_explanation(
    seed: dict[str, Any],
    candidate: dict[str, Any],
    shared_tags: list[str],
    audio_score: float,
    tag_score: float | None = None,
    confidence: str = "medium",
) -> str | None:
    """Generate a Gemini explanation for why two tracks are similar.

    This is the main function called by the Streamlit app.

    Args:
        seed: Seed track data dict.
        candidate: Candidate track data dict.
        shared_tags: Common tags between the artists.
        audio_score: Audio cosine similarity.
        tag_score: Tag Jaccard similarity.
        confidence: Confidence level.

    Returns:
        2-3 sentence explanation string, or None if API unavailable.
    """
    if not is_available():
        return None

    context = build_context(seed, candidate, shared_tags, audio_score, tag_score, confidence)
    prompt = build_prompt(context)

    try:
        client = genai.Client(vertexai=True, api_key=get_google_api_key())
        response = client.models.generate_content(
            model=RAG_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                max_output_tokens=RAG_MAX_TOKENS,
            ),
        )
        explanation = response.text.strip()
        logger.info(
            "Generated explanation for '%s' -> '%s'",
            seed.get("track_name", "?"),
            candidate.get("track_name", "?"),
        )
        return explanation

    except Exception as e:
        logger.warning("Gemini API error: %s", e)
        return None


def is_available() -> bool:
    """Check whether the RAG module can be used (API key present)."""
    try:
        get_google_api_key()
        return True
    except ValueError:
        return False
