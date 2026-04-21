# 🎵 Music Discovery Engine

A Streamlit web app that finds similar music across genre boundaries. You pick a seed track, and the system returns a ranked list of similar tracks using three signals: cosine similarity on audio features, Jaccard similarity on Last.fm community tags, and a small bonus when Last.fm's "similar artists" list agrees. Google Gemini generates a short natural-language explanation for the top results.

---

## How The System Works

Real streaming platforms combine collaborative filtering (what similar users listened to) with content-based filtering (attributes of the songs themselves). This project is content-based only, since we have no user listening data. The novelty is blending a numeric audio-feature layer with a textual community-tag layer so that two tracks can be judged both by *how they sound* and by *how listeners describe them*.

### Data

- **Catalog:** `data/catalog.csv`, derived from the Kaggle Spotify Tracks Dataset (~81k tracks, ~31k artists, 114 genres). Each row has 9 audio features: danceability, energy, loudness, speechiness, acousticness, instrumentalness, liveness, valence, tempo. Loudness and tempo are min-max normalized to `[0, 1]` during catalog preparation; the rest arrive already in range.
- **Last.fm cache:** `data/lastfm_cache/` holds one JSON file per artist per endpoint (`artist_tags_*.json`, `similar_artists_*.json`). Populated on demand by `scripts/enrich_with_lastfm.py`.

### Scoring

For each candidate track in the catalog:

1. **Audio similarity**: cosine similarity between the seed's weighted audio vector and the candidate's. Feature weights are adjustable from the sidebar (default 1.0 each).
2. **Tag similarity**: Jaccard index between the seed artist's Last.fm tags and the candidate artist's tags.
3. **Last.fm bonus**: +0.05 when Last.fm's `artist.getSimilar` for the seed artist lists the candidate artist.
4. **Blended score**: `audio_score * audio_weight + tag_score * tag_weight + lastfm_bonus`, clamped to `[0, 1]`. Default blend is 70% audio / 30% tag.
5. **Confidence**: `high` / `medium` / `low` based on how many signals agree (strong audio score, strong tag overlap, Last.fm confirmation, and margin over the next result).

If the Last.fm cache is empty, the app falls back to audio-only scoring and surfaces a sidebar notice.

### Explanations

For the top 5 results, the app builds a short context block (seed + candidate features, shared tags, scores) and sends it to Gemini, which returns a 2-3 sentence explanation focused on musical qualities rather than genre labels. Explanations are optional. If no `GOOGLE_API_KEY` is set, results render without them.

### Data Flow

See [flowchart.mmd](flowchart.mmd) for a Mermaid diagram.

---

## Getting Started

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate        # Mac or Linux
pip install -r requirements.txt
```

### 2. API keys

Copy `.env.example` to `.env` and fill in whichever keys you have:

- **`LASTFM_API_KEY`**: free, takes about 30 seconds to register at https://www.last.fm/api/account/create. Required for the tag layer and Last.fm confirmations. Without it the app still runs on audio features alone.
- **`GOOGLE_API_KEY`**: free tier at https://aistudio.google.com/apikey. Required for Gemini explanations. Without it results render without explanation text.

### 3. Build the catalog

```bash
python -m scripts.prepare_catalog
```

Reads `data/spotify-tracks.csv`, cleans and deduplicates, writes `data/catalog.csv`.

### 4. (Recommended) Enrich with Last.fm

```bash
python -m scripts.enrich_with_lastfm --limit 500
```

Fetches artist tags and similar-artist lists from Last.fm at 1 request/second. The script is resumable, so cached artists are skipped on re-run. Start with `--limit 500` to cover the most-popular artists quickly; drop the flag to enrich the whole catalog (will take several hours).

Audio-only search works without this step, but recommendations across genre boundaries (e.g. Stairway to Heaven → other Western rock ballads rather than random slow tracks from any language) depend on having tag data.

### 5. Run the app

```bash
streamlit run app.py
```

Then search for an artist or song, pick a seed, and adjust the sliders to see how weighting changes the results.

### Running Tests

```bash
pytest
```

Covers data loading, normalization, catalog search, cosine similarity, Jaccard tag similarity, blended scoring, and confidence rating.

---

## Project Layout

```
app.py                       Streamlit entry point
src/
  config.py                  Paths, feature names, defaults, .env loading
  data_loader.py             Catalog load + search + normalization
  similarity.py              Cosine + Jaccard + blending + confidence
  lastfm_client.py           Rate-limited Last.fm API client with JSON cache
  enrichment.py              Load cached tags/similar artists into dicts
  rag.py                     Gemini prompt construction + API call
scripts/
  prepare_catalog.py         Clean the Kaggle CSV into catalog.csv
  enrich_with_lastfm.py      Batch-fetch Last.fm data
tests/                       Pytest suite for data_loader and similarity
data/
  spotify-tracks.csv         Raw Kaggle dataset (input)
  catalog.csv                Cleaned catalog (output of prepare_catalog)
  lastfm_cache/              Per-artist JSON cache from Last.fm
```

---

## Limitations and Risks

- **Audio features only capture production signatures, not meaning.** Two tracks with near-identical feature vectors can be totally different in lyrical content, language, or cultural context. The tag layer helps, but it's still surface-level.
- **Last.fm tag quality varies.** Popular Western artists have rich, consensus tags. Long-tail or non-Western artists often have sparse or idiosyncratic tags. Tag similarity will be noisier for those.
- **Catalog skew.** The Kaggle dataset over-represents popular Western genres. If a user's seed is from an under-represented region or style, the neighbors will pull toward the majority even when better matches theoretically exist.
- **No personalization or feedback loop.** Every user starts from the same cold state. The system has no notion of "tracks I've already heard" or "tracks I disliked."
- **Explanations are generated text, not ground truth.** Gemini reasons over the context block we give it. If the feature values disagree with genre reality (e.g., a misclassified track), the explanation will confidently describe a connection that doesn't really exist.

See [model_card.md](model_card.md) for a fuller treatment.

---

## Reflection

See [reflection.md](reflection.md) and [model_card.md](model_card.md).
