"""
Command line runner for the Music Recommender Simulation.

Loads data/songs.csv, then prints the top 5 recommendations for several
deliberately different listener profiles so you can see how the scoring rule
treats each one.

Run from the project root:
    python3 -m src.main
"""

from pathlib import Path
from typing import Dict, List, Tuple

from src.recommender import load_songs, max_score, rank_songs

SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"
TOP_K = 5

PROFILES: List[Tuple[str, Dict]] = [
    ("Happy high-energy pop listener",
     {"genre": "pop", "mood": "happy", "energy": 0.85, "likes_acoustic": False}),
    ("Relaxed low-energy lofi listener",
     {"genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True}),
    ("Intense rock/workout listener",
     {"genre": "rock", "mood": "intense", "energy": 0.92, "likes_acoustic": False}),
    ("Edge case: high-energy classical fan (conflicting tastes)",
     {"genre": "classical", "mood": "melancholy", "energy": 0.90, "likes_acoustic": True}),
]


def describe_prefs(prefs: Dict) -> str:
    return ", ".join(f"{key}={value}" for key, value in prefs.items())


def print_profile(name: str, prefs: Dict, songs: List[Dict]) -> None:
    ranked = rank_songs(prefs, songs, k=TOP_K)
    print(f"=== {name} ===")
    print(f"Preferences: {describe_prefs(prefs)}")
    print(f"Top {len(ranked)} (a perfect match would score {max_score(prefs):.2f}):")
    for place, rec in enumerate(ranked, start=1):
        song = rec.song
        print(f"{place}. {song['title']} by {song['artist']} - score {rec.score:.2f}")
        for reason in rec.reasons:
            print(f"     - {reason}")
    print()


def main() -> None:
    songs = load_songs(str(SONGS_CSV))
    print(f"Loaded {len(songs)} songs from data/songs.csv\n")
    for name, prefs in PROFILES:
        print_profile(name, prefs, songs)


if __name__ == "__main__":
    main()
