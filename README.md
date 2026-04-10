# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

This is a simple music recommender that takes a user's preferences (like genre, mood, and energy level) and scores songs from a CSV catalog to find the best matches. It uses content-based filtering, meaning it looks at the attributes of each song rather than tracking what other users listened to. The output is a ranked list of recommendations with explanations for why each song was picked.

---

## How The System Works

Real streaming platforms like Spotify use two main approaches to recommend music. Collaborative filtering looks at what similar users listened to and assumes you might like the same things. Content-based filtering looks at the actual attributes of songs (genre, energy, mood, etc.) and tries to match them to your preferences. Our system uses content-based filtering since we don't have real user data to work with.

### Song Features

Each song in the catalog has these attributes:
- **genre** -- the style of the song (pop, lofi, rock, etc.)
- **mood** -- the general feeling (happy, chill, intense, etc.)
- **energy** -- how intense the song feels (0.0 to 1.0)
- **tempo_bpm** -- beats per minute
- **valence** -- how positive the song sounds (0.0 to 1.0)
- **danceability** -- how easy it is to dance to (0.0 to 1.0)
- **acousticness** -- how acoustic vs electronic it sounds (0.0 to 1.0)

### User Profile

The `UserProfile` stores a user's taste preferences:
- **favorite_genre** -- the genre they prefer
- **favorite_mood** -- the mood they gravitate toward
- **target_energy** -- their ideal energy level (0.0 to 1.0)
- **likes_acoustic** -- whether they prefer acoustic-sounding music

### Algorithm Recipe

The scoring logic works like this:
- **+2.0 points** for a genre match
- **+1.0 point** for a mood match
- **Up to +1.0 points** for energy similarity (the closer the song's energy is to the user's target, the more points)

After every song gets a score, we sort them highest to lowest and return the top results.

### Expected Biases

This system will probably lean too heavily on genre since it is worth the most points. A song that matches genre but has the wrong mood and energy could still beat a song that nails everything except genre. The catalog is also pretty small, so some genres only have one or two songs to choose from.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Experiments You Tried

I tested the system with four different user profiles: Happy Pop Fan, Chill Lofi Listener, Intense Rock Fan, and Relaxed Acoustic. Each one returned results that mostly made sense. The pop fan got Sunrise City at the top, the lofi listener got Midnight Coding, the rock fan got Storm Runner, and the acoustic listener got Campfire Songs.

I then ran an experiment where I halved the genre weight (from 2.0 to 1.0) and doubled the energy weight (from 1.0 to 2.0). The biggest change was in the Happy Pop Fan results. With the original weights, Gym Hero (pop, intense) ranked #2 because it matched on genre. After the shift, Rooftop Lights (indie pop, happy) jumped above it because its mood and energy were a better fit, even though its genre was not an exact match. That result actually felt more accurate to me, since someone who wants "happy pop" probably cares more about the vibe than the exact genre label.

The other profiles did not change as much. The top result stayed the same across all of them.

---

## Limitations and Risks

- The catalog only has 18 songs, so some genres (like rock or classical) only have one song. That means the system cannot really give variety for those users.
- Genre matching is worth the most points, which can push songs with the wrong mood or energy above songs that actually fit the vibe better.
- The system does not consider lyrics, language, or anything about the actual sound of the music. Two songs labeled "happy" could sound completely different.
- It treats every user the same way. Someone who cares mostly about mood has no way to tell the system that genre does not matter to them.

More details in the [model card](model_card.md).

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this


---

## 7. `model_card_template.md`

Combines reflection and model card framing from the Module 3 guidance. :contentReference[oaicite:2]{index=2}  

```markdown
# 🎧 Model Card - Music Recommender Simulation

## 1. Model Name

Give your recommender a name, for example:

> VibeFinder 1.0

---

## 2. Intended Use

- What is this system trying to do
- Who is it for

Example:

> This model suggests 3 to 5 songs from a small catalog based on a user's preferred genre, mood, and energy level. It is for classroom exploration only, not for real users.

---

## 3. How It Works (Short Explanation)

Describe your scoring logic in plain language.

- What features of each song does it consider
- What information about the user does it use
- How does it turn those into a number

Try to avoid code in this section, treat it like an explanation to a non programmer.

---

## 4. Data

Describe your dataset.

- How many songs are in `data/songs.csv`
- Did you add or remove any songs
- What kinds of genres or moods are represented
- Whose taste does this data mostly reflect

---

## 5. Strengths

Where does your recommender work well

You can think about:
- Situations where the top results "felt right"
- Particular user profiles it served well
- Simplicity or transparency benefits

---

## 6. Limitations and Bias

Where does your recommender struggle

Some prompts:
- Does it ignore some genres or moods
- Does it treat all users as if they have the same taste shape
- Is it biased toward high energy or one genre by default
- How could this be unfair if used in a real product

---

## 7. Evaluation

How did you check your system

Examples:
- You tried multiple user profiles and wrote down whether the results matched your expectations
- You compared your simulation to what a real app like Spotify or YouTube tends to recommend
- You wrote tests for your scoring logic

You do not need a numeric metric, but if you used one, explain what it measures.

---

## 8. Future Work

If you had more time, how would you improve this recommender

Examples:

- Add support for multiple users and "group vibe" recommendations
- Balance diversity of songs instead of always picking the closest match
- Use more features, like tempo ranges or lyric themes

---

## 9. Personal Reflection

A few sentences about what you learned:

- What surprised you about how your system behaved
- How did building this change how you think about real music recommenders
- Where do you think human judgment still matters, even if the model seems "smart"

