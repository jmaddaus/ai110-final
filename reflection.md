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
