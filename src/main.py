"""Command line runner for the Music Recommender Simulation."""

from src.recommender import load_songs, recommend_songs


def print_recommendations(profile_name, user_prefs, songs, k=5):
    """Print recommendations for a single user profile."""
    print(f"--- {profile_name} ---")
    print(f"Preferences: {user_prefs}\n")

    recommendations = recommend_songs(user_prefs, songs, k=k)
    for i, rec in enumerate(recommendations, 1):
        song, score, explanation = rec
        print(f"  {i}. {song['title']} by {song['artist']} - Score: {score:.2f}")
        print(f"     Reasons: {explanation}")
        print()


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs\n")

    profiles = {
        "Happy Pop Fan": {"genre": "pop", "mood": "happy", "energy": 0.8},
        "Chill Lofi Listener": {"genre": "lofi", "mood": "chill", "energy": 0.4},
        "Intense Rock Fan": {"genre": "rock", "mood": "intense", "energy": 0.9},
        "Relaxed Acoustic": {"genre": "folk", "mood": "relaxed", "energy": 0.3},
    }

    for name, prefs in profiles.items():
        print_recommendations(name, prefs, songs)


if __name__ == "__main__":
    main()
