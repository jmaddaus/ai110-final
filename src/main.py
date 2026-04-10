"""Command line runner for the Music Recommender Simulation."""

from src.recommender import load_songs, recommend_songs, SCORING_MODES


PROFILES = {
    "1": ("Happy Pop Fan", {
        "genre": "pop", "mood": "happy", "energy": 0.8,
        "mood_tag": "euphoric", "decade": "2020s", "loudness": 0.6,
    }),
    "2": ("Chill Lofi Listener", {
        "genre": "lofi", "mood": "chill", "energy": 0.4,
        "mood_tag": "nostalgic", "instrumentalness": 0.7, "loudness": 0.3,
    }),
    "3": ("Intense Rock Fan", {
        "genre": "rock", "mood": "intense", "energy": 0.9,
        "mood_tag": "aggressive", "decade": "2010s", "loudness": 0.85,
    }),
    "4": ("Relaxed Acoustic", {
        "genre": "folk", "mood": "relaxed", "energy": 0.3,
        "mood_tag": "warm", "instrumentalness": 0.8, "loudness": 0.2,
    }),
}


def print_recommendations(profile_name, user_prefs, songs, mode="balanced", k=5):
    """Print recommendations for a single user profile."""
    print(f"\n--- {profile_name} (mode: {mode}) ---")
    print(f"Preferences: {user_prefs}\n")

    recommendations = recommend_songs(user_prefs, songs, k=k, mode=mode)
    for i, rec in enumerate(recommendations, 1):
        song, score, explanation = rec
        print(f"  {i}. {song['title']} by {song['artist']} - Score: {score:.2f}")
        print(f"     Reasons: {explanation}")
        print()


def pick_mode():
    """Let the user pick a scoring mode."""
    print("Scoring modes:")
    modes = list(SCORING_MODES.keys())
    for i, mode in enumerate(modes, 1):
        weights = SCORING_MODES[mode]
        print(f"  {i}. {mode} (genre={weights['genre']}, mood={weights['mood']}, energy={weights['energy']})")
    print()

    while True:
        choice = input(f"Pick a mode (1-{len(modes)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(modes):
            return modes[int(choice) - 1]
        print("Invalid choice, try again.\n")


def show_menu():
    """Print the profile selection menu."""
    print("=== Music Recommender ===")
    print()
    for key, (name, prefs) in PROFILES.items():
        print(f"  {key}. {name}")
    print("  5. All profiles")
    print("  6. Exit")
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs\n")

    mode = "balanced"

    while True:
        show_menu()
        print(f"  Current mode: {mode}")
        print("  (Type 'm' to change mode)\n")
        choice = input("Pick a profile (1-6) or 'm': ").strip().lower()

        if choice == "6":
            print("Goodbye!")
            break
        elif choice == "m":
            mode = pick_mode()
            print(f"Switched to {mode} mode.\n")
        elif choice == "5":
            for name, prefs in PROFILES.values():
                print_recommendations(name, prefs, songs, mode=mode)
        elif choice in PROFILES:
            name, prefs = PROFILES[choice]
            print_recommendations(name, prefs, songs, mode=mode)
        else:
            print("Invalid choice, try again.\n")


if __name__ == "__main__":
    main()
