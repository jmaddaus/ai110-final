# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeFinder 1.0**  

---

## 2. Intended Use  

This system suggests the top 5 songs from a small catalog based on a user's preferred genre, mood, and energy level. It assumes the user knows what genre and mood they are in the mood for and can pick a target energy level between 0 and 1. This is a classroom project for learning how recommender systems work. It is not meant for real users or production use.  

---

## 3. How the Model Works  

The system goes through every song in the catalog and gives each one a score based on how well it matches what the user wants. If the song's genre matches the user's favorite genre, it gets 2 points. If the mood matches, it gets 1 point. Then it looks at how close the song's energy level is to what the user asked for. If the energy is a perfect match, that is another full point. If it is far off, that part of the score is lower. After scoring every song, the system sorts them from highest to lowest and shows the top results along with the reasons each song scored the way it did.

---

## 4. Data  

The catalog has 18 songs in data/songs.csv. The starter file had 10 and I added 8 more to cover genres that were missing. The genres now include pop, lofi, rock, ambient, jazz, synthwave, indie pop, electronic, country, metal, r&b, hip-hop, classical, and folk. Moods range from happy and chill to intense, sad, romantic, and confident. Each song also has numerical attributes for energy, tempo, valence, danceability, and acousticness on a 0 to 1 scale (except tempo which is in BPM). The dataset is still pretty small and some genres only have one song, so it does not represent real musical variety very well.  

---

## 5. Strengths  

- When a user's preferences line up cleanly with a song in the catalog (like the Relaxed Acoustic profile getting Campfire Songs), the system gives a confident and correct answer.
- The explanation output is useful. You can see exactly why each song scored the way it did, which makes it easy to understand and debug.
- The lofi and pop profiles both returned results that felt right. The top picks matched what you would expect someone with those preferences to want to hear.
- The system is simple enough that you can predict what it will do just by looking at the weights, which is a nice property for something meant to be transparent.  

---

## 6. Limitations and Bias 

- Genre is weighted at 2.0 points, which is more than mood and energy combined in some cases. This means a song that matches genre but has the wrong mood can still rank above a song that nails the vibe but is labeled as a different genre. For example, Gym Hero (pop, intense) ranked above Rooftop Lights (indie pop, happy) for a user who wanted happy pop.
- The catalog is small (18 songs) and some genres only have one entry. A classical fan or a metal fan basically gets one result and then a bunch of unrelated filler.
- The system has no way for a user to say "I care about mood more than genre." Everyone gets the same weight formula.
- It does not consider lyrics, artist popularity, release year, or anything beyond the basic CSV attributes. Two songs with similar numbers could sound nothing alike in practice.  

---

## 7. Evaluation  

I tested the system with four user profiles: Happy Pop Fan (pop, happy, energy 0.8), Chill Lofi Listener (lofi, chill, energy 0.4), Intense Rock Fan (rock, intense, energy 0.9), and Relaxed Acoustic (folk, relaxed, energy 0.3). For each one I checked whether the top 5 results felt like reasonable picks.

Most of the results made sense. The lofi listener got lofi and ambient tracks, the rock fan got Storm Runner at the top, and the acoustic listener got Campfire Songs with a perfect score. The one thing that surprised me was Gym Hero showing up at #2 for the happy pop fan. It is pop, but its mood is "intense," not "happy." It ranked that high purely because of the genre match being worth so many points.

I also ran a weight experiment where I halved genre (2.0 to 1.0) and doubled energy (1.0 to 2.0). That fixed the Gym Hero issue for the pop fan, but did not change the top result for any profile. The tests in test_recommender.py also pass, confirming the OOP implementation sorts correctly.

---

## 8. Future Work  

- Let users set their own weights so they can tell the system whether they care more about genre, mood, or energy.
- Add a diversity penalty so the top results do not all come from the same genre or artist.
- Include more song attributes like popularity, release year, or detailed mood tags to give the scoring more to work with.
- Build a way to switch between different scoring strategies (like a "genre-first" mode vs a "mood-first" mode) instead of having one fixed formula.  

---

## 9. Personal Reflection  

The biggest thing I learned is how much the weights matter. A small change in how much genre is worth compared to energy completely changed which songs showed up for certain profiles. It made me realize that when Spotify or YouTube recommends something, there are people making those same kinds of decisions about what to prioritize, and those choices shape what millions of people end up listening to.

I was also surprised by how a system this simple can still produce results that feel like real recommendations. When the lofi profile got back a list of chill, low-energy tracks, it genuinely felt like something a music app would suggest. But at the same time, it is easy to see the cracks. The system does not really understand music. It just matches labels and numbers. A human would know that "Gym Hero" is not a good pick for someone who wants happy pop, but the algorithm cannot tell the difference because the genre label matches.  
