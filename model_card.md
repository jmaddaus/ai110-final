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

## 7. Evaluation

Evaluation so far is limited to unit tests and ad-hoc manual checks:

- **Unit tests (`pytest`):** 24 tests pass. They cover catalog loading, min-max normalization, case-insensitive search, cosine similarity over a synthetic 5-track fixture (identical vectors → similarity ~1.0, seed exclusion, correct top-k count), Jaccard tag similarity on identical / disjoint / partial-overlap / empty / case-mixed tag lists, blended scoring under edge weights, and confidence rating across `high` / `medium` / `low`.
- **Spot checks:** audio-only retrieval on a Led Zeppelin seed returns tracks with matching slow-acoustic-ballad features but mismatched genre/language (see §6). This confirms the design hypothesis that the tag layer is doing most of the semantic work.

No quantitative user-facing evaluation (e.g., precision@k against a held-out set, user study) has been run yet. Human-led testing is the next step.

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
