import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Song:
    """Represents a song and its attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    popularity: int = 50
    release_decade: str = "2020s"
    mood_tag: str = ""
    instrumentalness: float = 0.5
    loudness: float = 0.5


@dataclass
class UserProfile:
    """Represents a user's taste preferences."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    preferred_mood_tag: Optional[str] = None
    preferred_decade: Optional[str] = None
    target_instrumentalness: Optional[float] = None
    target_loudness: Optional[float] = None


SCORING_MODES = {
    "balanced": {"genre": 2.0, "mood": 1.0, "energy": 1.0},
    "genre-first": {"genre": 4.0, "mood": 0.5, "energy": 0.5},
    "mood-first": {"genre": 0.5, "mood": 3.0, "energy": 1.0},
    "energy-focused": {"genre": 0.5, "mood": 0.5, "energy": 3.0},
}


class Recommender:
    """OOP implementation of the recommendation logic."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score_song(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        """Score a single song against a user profile."""
        score = 0.0
        reasons = []

        if song.genre == user.favorite_genre:
            score += 2.0
            reasons.append("genre match (+2.0)")

        if song.mood == user.favorite_mood:
            score += 1.0
            reasons.append("mood match (+1.0)")

        energy_diff = abs(song.energy - user.target_energy)
        energy_score = 1.0 - energy_diff
        score += energy_score
        reasons.append(f"energy similarity (+{energy_score:.2f})")

        # Mood tag match
        if user.preferred_mood_tag and song.mood_tag == user.preferred_mood_tag:
            score += 0.75
            reasons.append("mood tag match (+0.75)")

        # Decade match
        if user.preferred_decade and song.release_decade == user.preferred_decade:
            score += 0.5
            reasons.append("decade match (+0.5)")

        # Instrumentalness similarity
        if user.target_instrumentalness is not None:
            inst_diff = abs(song.instrumentalness - user.target_instrumentalness)
            inst_score = (1.0 - inst_diff) * 0.5
            score += inst_score
            reasons.append(f"instrumentalness similarity (+{inst_score:.2f})")

        # Loudness similarity
        if user.target_loudness is not None:
            loud_diff = abs(song.loudness - user.target_loudness)
            loud_score = (1.0 - loud_diff) * 0.5
            score += loud_score
            reasons.append(f"loudness similarity (+{loud_score:.2f})")

        return (score, reasons)

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k songs sorted by score for the given user."""
        scored = [(song, self._score_song(user, song)[0]) for song in self.songs]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a string explaining why a song was recommended."""
        score, reasons = self._score_song(user, song)
        return f"Score: {score:.2f} -- {', '.join(reasons)}"


def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file and return a list of dicts."""
    songs = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['id'] = int(row['id'])
            row['energy'] = float(row['energy'])
            row['tempo_bpm'] = float(row['tempo_bpm'])
            row['valence'] = float(row['valence'])
            row['danceability'] = float(row['danceability'])
            row['acousticness'] = float(row['acousticness'])
            row['popularity'] = int(row['popularity'])
            row['instrumentalness'] = float(row['instrumentalness'])
            row['loudness'] = float(row['loudness'])
            songs.append(row)
    return songs


def score_song(user_prefs: Dict, song: Dict, mode: str = "balanced") -> Tuple[float, List[str]]:
    """Score a single song against user preferences."""
    weights = SCORING_MODES.get(mode, SCORING_MODES["balanced"])
    score = 0.0
    reasons = []

    if song['genre'] == user_prefs.get('genre'):
        pts = weights["genre"]
        score += pts
        reasons.append(f"genre match (+{pts:.1f})")

    if song['mood'] == user_prefs.get('mood'):
        pts = weights["mood"]
        score += pts
        reasons.append(f"mood match (+{pts:.1f})")

    if 'energy' in user_prefs:
        energy_diff = abs(song['energy'] - user_prefs['energy'])
        energy_score = (1.0 - energy_diff) * weights["energy"]
        score += energy_score
        reasons.append(f"energy similarity (+{energy_score:.2f})")

    # Mood tag match
    if 'mood_tag' in user_prefs and song.get('mood_tag') == user_prefs['mood_tag']:
        score += 0.75
        reasons.append("mood tag match (+0.75)")

    # Decade match
    if 'decade' in user_prefs and song.get('release_decade') == user_prefs['decade']:
        score += 0.5
        reasons.append("decade match (+0.5)")

    # Instrumentalness similarity
    if 'instrumentalness' in user_prefs:
        inst_diff = abs(song.get('instrumentalness', 0.5) - user_prefs['instrumentalness'])
        inst_score = (1.0 - inst_diff) * 0.5
        score += inst_score
        reasons.append(f"instrumentalness similarity (+{inst_score:.2f})")

    # Loudness similarity
    if 'loudness' in user_prefs:
        loud_diff = abs(song.get('loudness', 0.5) - user_prefs['loudness'])
        loud_score = (1.0 - loud_diff) * 0.5
        score += loud_score
        reasons.append(f"loudness similarity (+{loud_score:.2f})")

    return (score, reasons)


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5, mode: str = "balanced") -> List[Tuple[Dict, float, str]]:
    """Score all songs and return the top k sorted by score."""
    scored = []
    for song in songs:
        song_score, reasons = score_song(user_prefs, song, mode=mode)
        explanation = ", ".join(reasons)
        scored.append((song, song_score, explanation))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
