# 🎧 Model Card: Music Discovery Engine

## 1. Model Name

**Music Discovery Engine 2.0** (Streamlit web app)

This replaces the earlier 18-song CLI prototype (VibeFinder 1.0). That system scored a tiny handcrafted catalog against a genre/mood/energy user profile. The current system is a content-based similarity engine over an ~81k-track catalog, with a tag-similarity layer and LLM-generated explanations.

---

## 2. Intended Use

Exploration, not personalization. A user enters a seed track they already know and likes, and the system surfaces other tracks whose audio features and community tags resemble the seed. It is meant for learning and demoing how a content-based recommender works. It is not built for production use, for children, or as a substitute for curated editorial recommendations.

---

## 3. How the Model Works

1. Load the cleaned catalog (`data/catalog.csv`) and optionally the Last.fm tag / similar-artist cache.
2. The user searches for an artist or song, picks a seed.
3. The seed's audio-feature vector is multiplied by user-adjustable per-feature weights and compared against every other track via cosine similarity.
4. The top-`2k` audio-similar tracks are enriched with:
   - Jaccard similarity between the seed artist's Last.fm tags and the candidate artist's tags.
   - A +0.05 bonus if Last.fm's `artist.getSimilar` list for the seed artist includes the candidate artist.
5. A blended score (`audio * audio_weight + tag * tag_weight + lastfm_bonus`, clamped to `[0, 1]`) reranks the results; the top `k` are returned.
6. Each result is tagged `high` / `medium` / `low` confidence based on how many of the signals agree and the score margin to the next result.
7. For the top 5 results, Google Gemini generates a short natural-language explanation from a context block of features, tags, and scores.

---

## 4. Data

- **Catalog:** Kaggle Spotify Tracks Dataset, cleaned by `scripts/prepare_catalog.py`. 81,344 tracks, 31,437 unique artists, 114 genres. Loudness and tempo are min-max normalized; the other seven features (danceability, energy, speechiness, acousticness, instrumentalness, liveness, valence) already arrive in `[0, 1]`.
- **Last.fm tags and similar artists:** fetched on demand from the Last.fm API at 1 request/second, cached as JSON under `data/lastfm_cache/`. Coverage depends on how many artists have been enriched. An empty cache means the app runs audio-only.
- **Explanations:** generated at request time by Google Gemini; nothing is cached.

---

## 5. Strengths

- **Two complementary signals.** Audio features capture production and sonic profile; community tags capture the cultural framing listeners actually use. Blending them surfaces cross-genre matches that neither signal alone would find.
- **Adjustable weights.** Per-feature sliders and the audio/tag blend slider let a user see how the recommendation set shifts when the system cares more about, e.g., valence than tempo.
- **Graceful degradation.** The app runs with no Last.fm data (audio-only) and with no Gemini key (no explanations). Missing signals are surfaced in the UI rather than hidden.
- **Transparent scoring.** Each result shows its audio score, tag score, shared tags, and confidence. The explanation layer makes the reasoning legible in plain language.

---

## 6. Limitations and Bias

- **Audio features are genre-agnostic.** Two tracks with similar danceability, energy, and tempo can come from totally different musical worlds. Audio-only results for "Stairway to Heaven" cluster with any slow acoustic ballad in the catalog, including cantopop, opera, and Indian film pop, because those all match the audio profile. The tag layer is what narrows this to the user's actual genre neighborhood; without Last.fm data the results are weak.
- **Catalog skew.** The Kaggle dataset is Spotify-centric and over-represents popular Western artists. Seeds from under-represented regions or styles will pull toward majority clusters.
- **Last.fm tag coverage is uneven.** Popular Western artists have rich consensus tags; long-tail or non-English artists often have sparse or idiosyncratic ones, so tag similarity is noisier for them.
- **Gemini confidence vs. ground truth.** The model generates fluent explanations from whatever context we feed it. If the underlying features disagree with reality (a mislabeled track, say), Gemini will confidently explain a connection that is not actually there.
- **No personalization.** Every session starts cold. The system does not remember prior seeds, prior clicks, or prior "not this" feedback.
- **Popularity bias.** Search results are sorted by popularity, which nudges users toward seeds that already have dense metadata, reinforcing the long-tail gap.

---

## 7. Reliability and Evaluation

The system uses four complementary approaches to prove that it works rather than just seems to: automated tests, confidence scoring, logging and error handling, and human evaluation through ad-hoc and Playwright-driven A/B captures.

### 7.1 Automated tests

`pytest` runs 27 unit tests in under a second. The breakdown:

| Category | Count | What it covers |
|---|---|---|
| Data loader | 8 | Catalog load, missing-file raising, normalization range, search (case-insensitive, no-results, empty-query), `get_unique_artists`, `get_artist_tracks` |
| Audio cosine | 5 | Feature-matrix shape, weighted matrix, identical-vector similarity ≈ 1.0, seed exclusion from results, correct top-k count |
| Tag similarity | 8 | Plain Jaccard (identical / disjoint / partial / empty / case-mixed) plus IDF-weighted variants (rare tags weigh more, None falls back to plain, unknown tags contribute zero) |
| Blended score | 3 | Audio-only weighting, default 70/30 blend, clamping at 1.0 |
| Confidence rating | 3 | `high` / `medium` / `low` correctness across signal counts |

Run them with:

```bash
pytest
```

Latest result: **27 of 27 pass**.

### 7.2 Confidence scoring

Every recommendation is labelled `high` / `medium` / `low` by `compute_confidence` in `src/similarity.py`. The label is based on how many of these four independent signals agree:

- audio cosine ≥ 0.9 (strong sonic match)
- tag Jaccard ≥ 0.15 (real overlap on community framing)
- Last.fm corroboration (candidate is in the seed's similar-artist list, or vice versa)
- score margin ≥ 0.03 to the next-ranked result (gap is wide enough to be meaningful, not a coin flip)

3 or 4 signals agreeing → `high`. 2 → `medium`. 0 or 1 → `low`. The label shows up as a coloured badge next to every result in the UI so the user has a runtime cue of how much to trust each pick. During development we used a confidence-collapse across a batch of seeds as an early-warning sign that the engine had regressed.

### 7.3 Logging and error handling

The app logs to both the console and a rotating file handler at `logs/app.log` (1 MB per file, 3 backups; configured in `app.py:setup_logging`). Each module uses a named logger (`src.lastfm_client`, `src.embeddings`, etc.) so failures can be traced to the source.

External-dependency failures degrade gracefully rather than crash:

- **Last.fm and MusicBrainz APIs.** Network errors and HTTP failures are caught, logged as warnings, and treated as cache-miss equivalents. With no Last.fm cache, the app falls back to audio-only scoring and surfaces a sidebar notice.
- **Vertex AI.** Missing credentials disable the embedding signal silently. Auth failures during enrichment retry once with a fresh token before falling through to a logged warning.
- **Catalog edge cases.** NaN values in the catalog (rare, but real) are coerced to empty strings before any `.lower()` or string-join. Long collaboration strings (some catalog tracks credit ~30 artists) get a SHA1 suffix on cache filenames so they fit inside macOS's 255-char filename limit.

All four enrichment scripts are resumable. Each fetched record is written to disk before the next call, so an interrupted run loses no work and re-running the script picks up where it stopped.

### 7.4 Human evaluation

Two forms of human-in-the-loop testing:

- **Manual seed comparison.** A fixed set of 11 seeds covering different genres and coverage regimes (Black Dog, Stairway to Heaven, HUMBLE., august, drivers license, Wildest Dreams, Mozart, Hank Williams, Frank Ocean, Kacey Musgraves, BTS) was re-checked by hand after every major engine change. Reading the top 10 results across that set caught problems unit tests could not: discovery-mode score saturation, low-popularity catalog noise dominating, and the song-first reframing that drove the track-tag enrichment work.
- **Playwright A/B captures.** `scripts/screenshot_app.py` drives a headless Chromium against the running Streamlit app and saves full-page PNGs for each seed under `screenshots/`. The committed `ui_default_*` and `ui_discovery_*` files document the discovery-mode toggle effect; `ui_tracktags_*` files document the track-tag layer behavior across coverage regimes. Engine changes can be diffed visually by re-running the script and comparing PNGs.

### 7.5 Summary

**27 of 27 unit tests pass.** The system struggles when Last.fm community tagging is sparse: track-tag coverage hits a ~16% ceiling outside contemporary pop and hip-hop, so seeds in classic rock and world music fall back to artist-level matching and the song-first effect is muted. Confidence ratings shifted from mostly-low to mostly-medium-or-high after the v2 priority-ordered Last.fm enrichment took artist-tag coverage from ~3k to ~16k. The track-tag layer became visibly useful once both the seed and at least some candidates had per-song tags (8 of 10 [track]-layer hits on the Kendrick HUMBLE. seed; 0 of 10 on the Black Dog seed where Last.fm has not tagged the canonical 70s-rock candidates). No quantitative user-facing evaluation (precision@k against a held-out set, user study) has been run yet; that is the natural next step.

---

## 8. Future Work

- Populate the Last.fm cache for at least the top N most-popular artists before any formal evaluation.
- Add a "why not this" mechanism so a user can reject a result and have its features/tags downweighted.
- Treat multi-artist tracks (`"Sam Smith;Kim Petras"`) as multiple artists for tag lookup rather than a single compound string.
- Cache Gemini explanations so repeat seeds do not re-hit the API.
- Collect explicit precision@k judgments from a small human panel on a fixed set of seeds, with and without the tag layer enabled, to quantify the tag layer's lift.

---

## 9. Personal Reflection

The biggest thing I learned on this project is how much of a recommender's "intelligence" is really just two choices: what data you feed it, and which signal you weight most. The audio features on their own produced results that were mathematically correct and musically useless. It took adding the tag layer, which is just set overlap on human-written labels, for the system to start feeling like it understood anything. That reframed how I think about AI products in general. The parts that feel smart are often the parts leaning hardest on work someone else already did.

The other thing that stuck with me is how confident a generated explanation can sound even when it is standing on shaky ground. Gemini never hesitates. It writes fluently about connections between tracks whether those connections are strong or weak. The only defense against that in this system is showing the scores and the confidence level next to the prose, so the user has something concrete to check the explanation against. That feels like a pattern worth carrying into any future LLM-facing feature I build.
