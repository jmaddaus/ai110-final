"""Music Discovery Engine — Streamlit Web Application.

Entry point: streamlit run app.py

Discover similar music across genre boundaries using cosine
similarity on audio features, Last.fm tags, and Claude-powered
explanations.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.config import (
    AUDIO_FEATURES,
    DEFAULT_FEATURE_WEIGHTS,
    DEFAULT_AUDIO_WEIGHT,
    DEFAULT_TAG_WEIGHT,
    CATALOG_PATH,
    LASTFM_CACHE_DIR,
    LOG_DIR,
)
from src.data_loader import load_catalog, search_catalog
from src.similarity import find_similar, build_feature_matrix

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    """Configure logging to console and rotating file."""
    LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)

    # File handler
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    root.addHandler(file_handler)


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

def configure_page() -> None:
    """Set Streamlit page title, icon, and layout."""
    st.set_page_config(
        page_title="Music Discovery Engine",
        page_icon="🎵",
        layout="wide",
    )


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_data() -> pd.DataFrame | None:
    """Load and cache the catalog. Returns None if file not found."""
    try:
        return load_catalog()
    except FileNotFoundError:
        logger.warning("Catalog file not found at %s", CATALOG_PATH)
        return None
    except ValueError as e:
        logger.error("Catalog validation error: %s", e)
        return None


@st.cache_data
def load_enrichment_data() -> tuple[dict, dict] | None:
    """Load cached Last.fm tag and similar-artist data.

    Returns:
        Tuple of (tag_data, similar_data) dicts, or None if unavailable.
    """
    if not LASTFM_CACHE_DIR.exists() or not any(LASTFM_CACHE_DIR.iterdir()):
        return None

    from src.enrichment import load_tag_cache, load_similar_artist_cache
    tag_data = load_tag_cache(LASTFM_CACHE_DIR)
    similar_data = load_similar_artist_cache(LASTFM_CACHE_DIR)

    if not tag_data and not similar_data:
        return None

    return tag_data, similar_data


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

def render_sidebar() -> dict:
    """Render sidebar with feature weight sliders and options.

    Returns:
        Dict with keys: weights (dict[str, float]), audio_weight (float),
        tag_weight (float), top_k (int).
    """
    st.sidebar.header("Discovery Settings")

    st.sidebar.subheader("Feature Weights")
    st.sidebar.caption("Adjust how much each audio feature matters in similarity.")

    weights = {}
    for feature in AUDIO_FEATURES:
        label = feature.replace("_", " ").title()
        weights[feature] = st.sidebar.slider(
            label, min_value=0.0, max_value=3.0, value=1.0, step=0.1, key=f"w_{feature}"
        )

    st.sidebar.subheader("Similarity Blend")
    audio_weight = st.sidebar.slider(
        "Audio similarity weight",
        min_value=0.0, max_value=1.0,
        value=DEFAULT_AUDIO_WEIGHT, step=0.05,
    )
    tag_weight = 1.0 - audio_weight

    st.sidebar.subheader("Results")
    top_k = st.sidebar.slider("Number of results", min_value=5, max_value=25, value=10)

    return {
        "weights": weights,
        "audio_weight": audio_weight,
        "tag_weight": tag_weight,
        "top_k": top_k,
    }


# ---------------------------------------------------------------------------
# Search and seed selection
# ---------------------------------------------------------------------------

def render_search(df: pd.DataFrame) -> pd.Series | None:
    """Render search bar and seed track selection.

    Returns:
        The selected seed track as a pandas Series, or None.
    """
    query = st.text_input("Search for an artist or song", placeholder="e.g., Led Zeppelin")

    if not query or not query.strip():
        return None

    results = search_catalog(df, query.strip(), field="both")

    if results.empty:
        st.warning(f"No results found for '{query}'")
        return None

    # Build display options
    options = []
    for _, row in results.iterrows():
        options.append(f"{row['track_name']} — {row['artist']} ({row.get('genre', 'unknown')})")

    selected_idx = st.selectbox("Select a seed track", range(len(options)), format_func=lambda i: options[i])

    if selected_idx is not None:
        return results.iloc[selected_idx]

    return None


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

def render_confidence_badge(confidence: str) -> None:
    """Display a colored confidence indicator."""
    colors = {"high": "🟢", "medium": "🟡", "low": "🔴"}
    icon = colors.get(confidence, "⚪")
    st.caption(f"{icon} Confidence: **{confidence.upper()}**")


def render_radar_chart(
    seed_features: dict,
    result_features: dict,
    feature_names: list[str],
    seed_name: str = "Seed",
    result_name: str = "Result",
) -> None:
    """Render a matplotlib radar chart comparing two tracks' audio features."""
    labels = [f.replace("_", " ").title() for f in feature_names]
    num_features = len(feature_names)

    angles = np.linspace(0, 2 * np.pi, num_features, endpoint=False).tolist()
    angles += angles[:1]

    seed_values = [seed_features.get(f, 0) for f in feature_names] + [seed_features.get(feature_names[0], 0)]
    result_values = [result_features.get(f, 0) for f in feature_names] + [result_features.get(feature_names[0], 0)]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angles, seed_values, "o-", linewidth=2, label=seed_name, color="#1f77b4")
    ax.fill(angles, seed_values, alpha=0.15, color="#1f77b4")
    ax.plot(angles, result_values, "o-", linewidth=2, label=result_name, color="#ff7f0e")
    ax.fill(angles, result_values, alpha=0.15, color="#ff7f0e")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=8)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)
    plt.tight_layout()

    st.pyplot(fig)
    plt.close(fig)


def render_results(
    results: list[dict],
    seed: pd.Series,
    df: pd.DataFrame,
) -> None:
    """Display similarity results with scores, tags, and explanations."""
    if not results:
        st.info("No similar tracks found. Try adjusting your weights.")
        return

    st.subheader(f"Similar to: {seed['track_name']} by {seed['artist']}")

    for i, result in enumerate(results, 1):
        with st.expander(
            f"#{i} — {result['track_name']} by {result['artist']} "
            f"(Score: {result['blended_score']:.2f})",
            expanded=(i <= 3),
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Genre:** {result.get('genre', 'unknown')}")
                st.markdown(
                    f"**Audio similarity:** {result['audio_score']:.3f} | "
                    f"**Tag similarity:** {result.get('tag_score', 'N/A') if result.get('tag_score') is not None else 'N/A'}"
                )
                render_confidence_badge(result.get("confidence", "low"))

                shared = result.get("shared_tags", [])
                if shared:
                    st.markdown(f"**Shared tags:** {', '.join(shared[:10])}")

                if result.get("lastfm_confirms"):
                    st.caption("Last.fm confirms these artists are similar")

                # RAG explanation (if available)
                explanation = result.get("explanation")
                if explanation:
                    st.markdown(f"**Why similar:** {explanation}")

            with col2:
                # Radar chart
                seed_features = {f: float(seed.get(f, 0)) for f in AUDIO_FEATURES}
                result_row = df.iloc[result["index"]] if "index" in result else None
                if result_row is not None:
                    result_features = {f: float(result_row.get(f, 0)) for f in AUDIO_FEATURES}
                    render_radar_chart(
                        seed_features, result_features, AUDIO_FEATURES,
                        seed_name=seed["artist"], result_name=result["artist"],
                    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Main application flow."""
    setup_logging()
    configure_page()

    st.title("🎵 Music Discovery Engine")
    st.markdown(
        "Discover similar music across genre boundaries using audio features, "
        "community tags, and AI-powered explanations."
    )

    # Load data
    df = load_data()
    if df is None:
        st.error(
            "Catalog not found. Run `python -m scripts.prepare_catalog` first. "
            "See README for setup instructions."
        )
        return

    # Load enrichment data (optional)
    enrichment = load_enrichment_data()
    tag_data, similar_data = enrichment if enrichment else (None, None)

    if not enrichment:
        st.sidebar.info("Last.fm data not loaded. Showing audio-only results.")

    # Sidebar controls
    settings = render_sidebar()

    # Search and select seed
    seed = render_search(df)

    if seed is not None:
        with st.spinner("Finding similar tracks..."):
            try:
                results = find_similar(
                    seed_track=seed.name,  # DataFrame index
                    df=df,
                    feature_columns=AUDIO_FEATURES,
                    weights=settings["weights"],
                    tag_data=tag_data,
                    lastfm_similar=similar_data,
                    audio_weight=settings["audio_weight"],
                    tag_weight=settings["tag_weight"],
                    top_k=settings["top_k"],
                )

                # Try to add RAG explanations
                try:
                    from src.rag import generate_explanation, is_available
                    if is_available():
                        for result in results[:5]:  # Only top 5 to limit API calls
                            explanation = generate_explanation(
                                seed=seed.to_dict(),
                                candidate=result,
                                shared_tags=result.get("shared_tags", []),
                                audio_score=result["audio_score"],
                                tag_score=result.get("tag_score"),
                                confidence=result.get("confidence", "medium"),
                            )
                            result["explanation"] = explanation
                except (ImportError, ValueError):
                    logger.debug("RAG module not available, skipping explanations")

                render_results(results, seed, df)

            except Exception as e:
                logger.error("Similarity search failed: %s", e)
                st.error(f"Search failed: {e}")


if __name__ == "__main__":
    main()
