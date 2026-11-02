"""
Command line runner for the Music Recommender Simulation.

Loads data/songs.csv, then prints the top 5 recommendations for several
deliberately different listener profiles so you can see how the scoring rule
treats each one.

Run from the project root:
    python3 -m src.main                           # baseline: balanced mode, no variety penalty
    python3 -m src.main --mode genre-first        # other ranking strategies
    python3 -m src.main --mode mood-energy
    python3 -m src.main --artist-penalty 0.75     # rerank to avoid repeating an artist
    python3 -m src.main --format list --width 60  # plain list / narrower output
"""

import argparse
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from src.recommender import (
    DEFAULT_MODE, RANKING_MODES, DiversityConfig, get_mode, load_songs, max_score, rank_songs,
)
from src.report import MIN_WIDTH, format_recommendation_list, format_recommendation_table

SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"
TOP_K = 5
DEFAULT_WIDTH = 100

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


def say(text: str, width: int) -> None:
    """Print text word-wrapped so no line is wider than the requested width."""
    print(textwrap.fill(text, width=width, break_long_words=True, break_on_hyphens=False))


def _width(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a whole number") from None
    if value < MIN_WIDTH:
        raise argparse.ArgumentTypeError(f"width must be at least {MIN_WIDTH}")
    return value


def build_parser() -> argparse.ArgumentParser:
    modes = "\n".join(f"  {mode.name}: {mode.description}" for mode in RANKING_MODES.values())
    parser = argparse.ArgumentParser(
        prog="python3 -m src.main",
        description="Music Recommender Simulation: top 5 songs for each demo listener profile.",
        epilog="ranking modes:\n" + modes,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=list(RANKING_MODES), default=DEFAULT_MODE,
                        help=f"ranking strategy (default: {DEFAULT_MODE})")
    parser.add_argument("--artist-penalty", type=float, default=0.0, metavar="P",
                        help="points subtracted for each earlier pick by the same artist "
                             "(default 0 = off, i.e. the baseline ranking)")
    parser.add_argument("--genre-penalty", type=float, default=0.0, metavar="P",
                        help="points subtracted for each earlier pick in the same genre (default 0 = off)")
    parser.add_argument("--format", choices=("table", "list"), default="table",
                        help="output layout (default: table)")
    parser.add_argument("--width", type=_width, default=DEFAULT_WIDTH, metavar="N",
                        help=f"maximum line width for the table (default {DEFAULT_WIDTH}, minimum {MIN_WIDTH})")
    return parser


def print_profile(name: str, prefs: Dict, songs: List[Dict], mode_name: str,
                  diversity: DiversityConfig, layout: str, width: int) -> None:
    weights = get_mode(mode_name).weights
    ranked = rank_songs(prefs, songs, k=TOP_K, weights=weights, diversity=diversity)
    say(f"=== {name} ===", width)
    say(f"Preferences: {describe_prefs(prefs)}", width)
    say(f"Top {len(ranked)} (a perfect match would score {max_score(prefs, weights):.2f}):", width)
    print(format_recommendation_table(ranked, width) if layout == "table"
          else format_recommendation_list(ranked, width))
    print()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        diversity = DiversityConfig(args.artist_penalty, args.genre_penalty)
    except ValueError as err:
        parser.error(str(err))

    songs = load_songs(str(SONGS_CSV))
    mode = get_mode(args.mode)
    say(f"Loaded {len(songs)} songs from data/songs.csv", args.width)
    say(f"Mode: {mode.name} - {mode.description}", args.width)
    if diversity.enabled:
        say(f"Variety penalty: ON (artist {diversity.artist_penalty:g}, genre {diversity.genre_penalty:g})", args.width)
    else:
        say("Variety penalty: off (baseline: ranked by score alone)", args.width)
    print()
    for name, prefs in PROFILES:
        print_profile(name, prefs, songs, args.mode, diversity, args.format, args.width)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
