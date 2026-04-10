# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
- What user preferences are considered  
- How does the model turn those into a score  
- What changes did you make from the starter logic  

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

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

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  
