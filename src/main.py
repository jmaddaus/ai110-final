"""Command line runner for the Music Recommender Simulation."""

from src.recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs")

    # Default user profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    print(f"\nUser preferences: {user_prefs}")
    print("\nTop recommendations:\n")

    recommendations = recommend_songs(user_prefs, songs, k=5)
    for i, rec in enumerate(recommendations, 1):
        song, score, explanation = rec
        print(f"  {i}. {song['title']} by {song['artist']} - Score: {score:.2f}")
        print(f"     Reasons: {explanation}")
        print()


if __name__ == "__main__":
    main()
