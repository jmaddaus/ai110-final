# Reflection: Observations from the Music Discovery Engine

## Audio features alone are not enough

The most useful thing I tried was running "Stairway to Heaven" as a seed with the Last.fm layer turned off. The top neighbors on pure audio similarity were a Josh Groban opera ballad, a Hins Cheung cantopop ballad, and a B Praak Indian film-pop track. They were basically tied, within a thousandth of a point. The math is not wrong. Those songs really do share Stairway's slow tempo, low valence, high acousticness, and vocal-forward mix. But musically the result feels like a joke. What it showed me is that audio features capture the production signature of a track, not its cultural context. A system built only on those numbers will quietly flatten long-tail genres into whatever majority cluster has the closest numeric profile.

## The tag layer earns its weight

Once Last.fm tags are in the mix, the same Stairway query gets pulled back toward "classic rock", "70s", "british", and similar tags, and the opera and cantopop neighbors drop out. Jaccard similarity on tags is a very simple metric. It is just set overlap between the seed artist's tags and the candidate artist's tags. But it ends up doing most of the real work in this system, because it is riding on top of thousands of listeners who already framed each artist for us. That was a good reminder that a lot of what reads as "AI" in a recommender is actually borrowed from human labels. The system is only as good as how many artists have been tagged and how consistent those tags are.

## Explanations are fluent but not grounded

Gemini will happily describe a connection between any two tracks I hand it, given the features and shared tags. On a high-confidence match the explanation is actually helpful. On a low-confidence match the explanation is just as fluent and just as confident, even when the connection is barely there. That is the same failure mode I see in every LLM product. The prose quality runs ahead of the actual reasoning. Putting the confidence badge and the raw scores right next to the explanation was the right call. It gives the user something to weigh the prose against instead of trusting it by default.

## Weights as a policy lever

Moving the audio/tag slider from 70/30 to 30/70 changes the feel of the results more than any single feature weight does. That echoes what the earlier 18-song prototype taught me about genre, mood, and energy weights, just at a much bigger scale. The choice of which signal to weight most heavily is a policy decision, not a technical one. Someone making that same call at a real streaming company is shaping what millions of people end up hearing as "similar". It is strange to realize how much cultural reach a small number of weight values can have.

## Where the system is honest about its limits

The part I feel best about is how the app behaves when signals are missing. With no Last.fm key the sidebar says so. With no Gemini key the results still render, just without explanations. Every result shows its own confidence level. The user can always see what is present and what is not. That sounds like a small thing, but it is the piece I notice is usually missing from real recommenders, where the model's uncertainty is hidden from you entirely.

---

## Responsible AI

A few questions worth answering directly: limits, misuse, surprises, and how I worked with AI on this project.

### What are the system's limitations or biases?

The biggest one is structural. The catalog comes from the Kaggle Spotify Tracks Dataset, which over-represents popular Western artists. Last.fm community tagging has the same skew, and the track-tag layer adds a second skew on top because contemporary pop and hip-hop get tagged densely while classic rock, jazz, and most non-English music do not. The result is that two of the three layers we use to judge "is this a real match" are noisier the further the seed gets from the popular-Western mainstream. A K-pop seed and a Bollywood seed return reasonable neighbors. An Argentine tango seed gets fewer real matches, lower confidence, and more audio-only fallback noise.

A second, less obvious bias is in the explanation layer. Gemini will write a confident-sounding paragraph about any two tracks I hand it, given the features and shared tags. The explanation prose is fluent regardless of how strong the underlying signals actually are. The confidence badge helps a user weigh that, but a casual reader could easily read the explanation as ground truth.

### Could the system be misused?

A music recommender at scale shapes what people hear as "similar". The choices baked into this system (which signals get weighted, what the popularity bucket does, what the canon penalty looks like) are policy decisions, not technical ones. A bad-faith operator could weight the system to push specific artists, exclude certain genres, or homogenize listening into a narrow band. A naive operator could let it run with the default popularity bias and quietly under-surface long-tail artists for everyone.

The defenses I put in place are deliberately limited but real. Every result shows its scores, its shared tags, and its confidence rating, so the user can see what is driving the recommendation rather than trusting a black box. The discovery-mode toggle gives the user a way to step outside the canon when the canonical recommendations feel like an echo chamber. There is no engagement-based feedback loop (no "users who clicked this also clicked that"), so the system cannot build self-reinforcing filter bubbles from prior usage. Real-world deployment would need at minimum an audit of which artists get under-recommended at default settings, plus a way for users to flag bad recommendations.

### What surprised me while testing reliability?

Two things. First, how much "AI quality" turned out to be coverage quality. The MusicBrainz instrument-fingerprint signal looked rich on paper. In practice it was 19% coverage, mostly silent. The Last.fm track-tag layer hit a 16% wall on popular tracks. After both of those, the lesson sank in: the algorithm did not matter once the data dropped below roughly 40%. The thing I had been building was a machine for combining signals that often were not there.

Second, how confident the LLM stayed even when the recommendation was weak. Gemini does not hedge based on the confidence rating I send it. The prose is just as smooth on a low-confidence pick as on a high-confidence one. That made the confidence badge feel essential, not optional, because the prose itself does not carry the uncertainty.

### Collaboration with AI

I built this system in a paired session with Claude. Most of the engineering decisions were proposed by the AI and either accepted, rejected, or modified by me. Two examples stand out.

**A useful suggestion.** When I articulated the song-first goal (a band's slow ballad and hard-rock track should produce different recommendations), Claude proposed track-level Last.fm tags as the concrete fix and built the wiring before the data finished landing. The first real validation was Taylor Swift's "august" surfacing Vance Joy's "Riptide" via shared *indie folk / indie pop*, which is exactly the cross-artist song-first match the prior architecture missed. The reframing came from me; the implementation path came from Claude.

**A flawed suggestion.** Earlier in the project, Claude proposed adding a MusicBrainz instrument fingerprint as a similarity signal. The pitch was that band-composition similarity (rock band with guitar / drums / bass vs jazz quartet with piano / sax) would catch cross-genre coincidences the audio cosine missed. I went along with it. After the cache landed, we measured 19% coverage and confirmed the signal was effectively dead for ~80% of artists. The first attempt at discovery mode had a similar shape: the initial implementation surfaced children's-pop covers and EDM remixes for a Black Dog seed because the canon penalty was too aggressive, and we needed several correction passes before it produced anything useful. The general lesson is that AI suggestions are good at finding clever-looking signals but tend to underweight the question of whether the signal will fire often enough to matter.
