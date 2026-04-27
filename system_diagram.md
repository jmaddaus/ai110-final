# System Diagram (Text Version)

This is a plain-text version of [system_diagram.mmd](system_diagram.mmd) for environments that do not render Mermaid. The shape and labels match the Mermaid version.

The system has five named components: a **Retriever** that pulls cached data, a **Similarity Engine** that blends six signals into a score, an **Evaluator** that rates each result, a **RAG Generator** that grounds an explanation in the retrieved context, and a **Tester** that catches regressions before they reach the user.

```
                       ┌────────────────────────────────────────┐
                       │ User picks seed song + adjusts sliders │
                       └─────────────────┬──────────────────────┘
                                         │
                                         ▼
                       ┌────────────────────────────────────────┐
                       │           Streamlit Web UI             │
                       └─────────────────┬──────────────────────┘
                                         │
                                         ▼
     ┌─────────────────────────── RETRIEVER ────────────────────────────┐
     │                                                                  │
     │  • Catalog: 81k Spotify tracks, 9 audio features per track       │
     │  • Last.fm artist cache: tags + similar artists + match scores   │
     │  • Last.fm track-tag cache: per-song descriptors                 │
     │  • Vertex AI embedding cache: ~16k 768-dim artist vectors        │
     │  • MusicBrainz cache: member instruments                         │
     │                                                                  │
     └─────────────────────────────┬────────────────────────────────────┘
                                   │
                                   ▼
     ┌──────────────────────── SIMILARITY ENGINE ───────────────────────┐
     │                                                                  │
     │  1. Pull audio-cosine candidate pool                             │
     │     (top 5k for default mode, top 20k for discovery mode)        │
     │                                                                  │
     │  2. Blend six signals into a score:                              │
     │       a. audio cosine                                            │
     │       b. IDF-weighted Jaccard on Last.fm artist tags             │
     │       c. Jaccard on Last.fm track-level tags (when both have)    │
     │       d. embedding cosine in 768-dim space                       │
     │       e. match-weighted Last.fm similar-artist bonus             │
     │       f. popularity-bucket modifier                              │
     │                                                                  │
     │  3. Diversify by artist (cap repeats), take top k                │
     │                                                                  │
     └─────────────────────────────┬────────────────────────────────────┘
                                   │
                                   ▼
     ┌────────────────────────── EVALUATOR ─────────────────────────────┐
     │                                                                  │
     │  Confidence rating per result: high / medium / low,              │
     │  based on how many independent signals agree                     │
     │                                                                  │
     └─────────────────────────────┬────────────────────────────────────┘
                                   │
                                   ▼
     ┌─────────────────────── RAG GENERATOR ────────────────────────────┐
     │                                                                  │
     │  Build context block from seed + candidate features, shared      │
     │  tags, scores, confidence. Pass to Gemini gemini-3-flash-preview │
     │  and return a 2-3 sentence explanation grounded in the context.  │
     │                                                                  │
     └─────────────────────────────┬────────────────────────────────────┘
                                   │
                                   ▼
                       ┌────────────────────────────────────────┐
                       │ Result cards in UI: score, shared      │
                       │ tags, radar chart, RAG explanation     │
                       └─────────────────┬──────────────────────┘
                                         │
                                         ▼
                       ┌────────────────────────────────────────┐
                       │ User reads results + confidence badge  │
                       └────────────────────────────────────────┘


   ┌──────────────────────────── TESTER ─────────────────────────────────┐
   │  Sits alongside the pipeline. Validates rather than serving traffic.│
   │                                                                     │
   │   • pytest unit tests (27 cases)        ─► validates Engine         │
   │   • Playwright A/B screenshots          ─► validates UI             │
   │   • Confidence rating (per result)      ─► inline check to user     │
   │                                                                     │
   └─────────────────────────────────────────────────────────────────────┘
```

## How to read it

1. **Input.** The user enters a seed song through the Streamlit UI and optionally adjusts the sidebar (audio-feature weights, mode toggle, result count).
2. **Process.** The request flows through Retriever → Similarity Engine → Evaluator → RAG Generator. Each component reads from the previous one and adds something to the package.
3. **Output.** Result cards land back in the UI with a score, the shared tags that drove the score, a radar chart of the audio features, and the Gemini explanation.
4. **Validation.** The Tester block sits beside the pipeline rather than inside it. Unit tests catch logic regressions before deploy, the Playwright A/B captures verify that engine changes actually land in the UI, and the inline confidence rating gives the user a runtime signal that some recommendations are stronger than others.
