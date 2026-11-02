"""
Reproducible experiments used in the README and model card.

Run from the project root:
    python3 -m src.experiments
"""

from dataclasses import replace
from typing import Dict, List

from src.main import PROFILES, SONGS_CSV
from src.recommender import (
    DiversityConfig, RANKING_MODES, ScoringWeights, load_songs, max_score, rank_songs, score_song,
)

BASELINE = ScoringWeights()


def weight_sensitivity(profile_index: int = 0) -> str:
    """
    Hold one profile and the song data fixed; halve and double ONE weight at a time.

    Everything except the changed weight stays at its baseline value, so any change
    in the ranking is caused by that weight alone.
    """
    songs = load_songs(str(SONGS_CSV))
    name, prefs = PROFILES[profile_index]
    titles = {s["id"]: s["title"] for s in songs}

    variants = [("baseline (genre 2.0, mood 1.5, energy 2.0)", BASELINE)]
    for feature in ("genre", "mood", "energy"):
        base_value = getattr(BASELINE, feature)
        variants.append((f"{feature} x0.5 -> {base_value * 0.5:.2f}", replace(BASELINE, **{feature: base_value * 0.5})))
        variants.append((f"{feature} x2   -> {base_value * 2:.2f}", replace(BASELINE, **{feature: base_value * 2})))

    baseline_top = [r.song["id"] for r in rank_songs(prefs, songs, 5, BASELINE)]
    lines: List[str] = [f"Profile: {name}", f"Preferences: {prefs}", f"Songs: {len(songs)} (fixed)", ""]
    for label, weights in variants:
        ranked = rank_songs(prefs, songs, 5, weights)
        ids = [r.song["id"] for r in ranked]
        changed = "same top 5 in same order" if ids == baseline_top else (
            "same 5 songs, new order" if set(ids) == set(baseline_top) else
            f"top 5 changed (in: {', '.join(titles[i] for i in ids if i not in baseline_top)}; "
            f"out: {', '.join(titles[i] for i in baseline_top if i not in ids)})")
        lines.append(f"[{label}] -> {changed}")
        for place, rec in enumerate(ranked, start=1):
            lines.append(f"  {place}. {rec.song['title']} ({rec.song['genre']}/{rec.song['mood']}, "
                         f"energy {rec.song['energy']:.2f}) score {rec.score:.2f}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _counts(counter: Dict[str, int]) -> str:
    """'name n' pairs, most common first, ties alphabetical."""
    return ", ".join(f"{name} {n}" for name, n in sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def catalog_counts() -> str:
    """Genre / mood / energy counts that back the dataset-imbalance claims."""
    songs = load_songs(str(SONGS_CSV))
    genres: Dict[str, int] = {}
    moods: Dict[str, int] = {}
    for song in songs:
        genres[song["genre"]] = genres.get(song["genre"], 0) + 1
        moods[song["mood"]] = moods.get(song["mood"], 0) + 1
    single_genre = sum(1 for n in genres.values() if n == 1)
    bands = {"energy < 0.40": 0, "0.40 - 0.69": 0, "energy >= 0.70": 0}
    for song in songs:
        if song["energy"] < 0.40:
            key = "energy < 0.40"
        elif song["energy"] < 0.70:
            key = "0.40 - 0.69"
        else:
            key = "energy >= 0.70"
        bands[key] += 1
    lines = [f"Songs: {len(songs)}, artists: {len({s['artist'] for s in songs})}",
             f"Genres ({len(genres)}): " + _counts(genres),
             f"Genres with exactly one song: {single_genre} of {len(genres)}",
             f"Moods ({len(moods)}): " + _counts(moods),
             "Energy bands: " + ", ".join(f"{k}: {v}" for k, v in bands.items())]
    decades: Dict[int, int] = {}
    for song in songs:
        decades[song["release_decade"]] = decades.get(song["release_decade"], 0) + 1
    popularity = [song["popularity"] for song in songs]
    lines.append("Release decades: " + ", ".join(f"{d}s {n}" for d, n in sorted(decades.items())))
    lines.append(f"Popularity: min {min(popularity)}, max {max(popularity)}, "
                 f"{sum(1 for p in popularity if p >= 70)} songs at 70 or above")
    for column in ("instrumentalness", "speechiness", "liveness"):
        values = [song[column] for song in songs]
        lines.append(f"{column}: min {min(values):.2f}, max {max(values):.2f}, "
                     f"{sum(1 for v in values if v >= 0.5)} songs at 0.50 or above")
    return "\n".join(lines)


def label_brittleness() -> str:
    """
    Show that genre/mood are exact string matches: 'relaxed' earns nothing for a
    'chill' listener even when every number about the song fits better.
    """
    songs = load_songs(str(SONGS_CSV))
    name, prefs = PROFILES[1]
    ranked = rank_songs(prefs, songs, len(songs))
    lines = [f"Profile: {name}", f"Preferences: {prefs}"]
    for wanted in ("Late Bus Home", "Coffee Shop Stories"):
        place = next(i for i, r in enumerate(ranked, start=1) if r.song["title"] == wanted)
        rec = ranked[place - 1]
        song = rec.song
        lines.append(f"#{place:<2} {song['title']} ({song['genre']}/{song['mood']}, energy {song['energy']:.2f}, "
                     f"acousticness {song['acousticness']:.2f}) score {rec.score:.2f}: {rec.explanation}")
    return "\n".join(lines)


def profile_comparison() -> str:
    """Summarize how each profile's top 5 was earned, and which songs they share."""
    songs = load_songs(str(SONGS_CSV))
    lines: List[str] = []
    appearances: Dict[str, List[str]] = {}
    for name, prefs in PROFILES:
        top = rank_songs(prefs, songs, 5)
        genre_hits = sum(1 for r in top if r.song["genre"] == prefs["genre"])
        mood_hits = sum(1 for r in top if r.song["mood"] == prefs["mood"])
        neither = sum(1 for r in top if r.song["genre"] != prefs["genre"] and r.song["mood"] != prefs["mood"])
        lines.append(f"{name}")
        scores = ", ".join("{:.2f}".format(r.score) for r in top)
        lines.append(f"  scores: {scores}  (max {max_score(prefs):.2f})")
        lines.append(f"  genre matches: {genre_hits}/5, mood matches: {mood_hits}/5, neither: {neither}/5")
        energies = ", ".join("{:.2f}".format(r.song["energy"]) for r in top)
        lines.append(f"  energy of top 5: {energies} (target {prefs['energy']:.2f})")
        for r in top:
            appearances.setdefault(r.song["title"], []).append(name)
    shared = {t: who for t, who in appearances.items() if len(who) > 1}
    lines.append("Songs in more than one profile's top 5: " + (
        "; ".join(f"{t} ({len(w)} profiles)" for t, w in sorted(shared.items())) or "none"))
    return "\n".join(lines)


def _top_lines(ranked) -> List[str]:
    return [f"  {i}. {r.song['title']} ({r.song['artist']}, {r.song['genre']}) score {r.score:.2f}"
            for i, r in enumerate(ranked, start=1)]


def _changes(before, after) -> str:
    """Say what moved between two ranked lists, computed from the lists themselves."""
    old = {r.song["title"]: i for i, r in enumerate(before, start=1)}
    new = {r.song["title"]: i for i, r in enumerate(after, start=1)}
    parts = []
    entered = [t for t in new if t not in old]
    dropped = [t for t in old if t not in new]
    moved = [f"{t} #{old[t]}->#{new[t]}" for t in new if t in old and old[t] != new[t]]
    if entered:
        parts.append("entered: " + ", ".join(entered))
    if dropped:
        parts.append("dropped: " + ", ".join(dropped))
    if moved:
        parts.append("moved: " + ", ".join(moved))
    return "; ".join(parts) or "no change in the top 5"


def attribute_demo() -> str:
    """Stretch 1: an optional new attribute preference changes scores and rankings."""
    songs = load_songs(str(SONGS_CSV))
    cases = [
        ("Nostalgic folk listener, then also prefers the 1970s (decade=1970)",
         {"genre": "folk", "mood": "nostalgic", "energy": 0.40, "likes_acoustic": True}, {"decade": 1970}),
        ("Happy pop listener, then also prefers lesser-known songs (popularity=40)",
         PROFILES[0][1], {"popularity": 40}),
    ]
    lines: List[str] = []
    for title, prefs, extra in cases:
        before = rank_songs(prefs, songs, 5)
        after = rank_songs({**prefs, **extra}, songs, 5)
        lines.append(title)
        lines.append(f"Without the new preference ({describe(prefs)}):")
        lines.extend(_top_lines(before))
        lines.append(f"With {describe(extra)} added:")
        lines.extend(_top_lines(after))
        lines.append(f"What changed: {_changes(before, after)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def describe(prefs: Dict) -> str:
    return ", ".join(f"{key}={value}" for key, value in prefs.items())


def mode_comparison() -> str:
    """Stretch 2: the same profile and songs, ranked by each strategy."""
    songs = load_songs(str(SONGS_CSV))
    lines: List[str] = []
    for index in (0, 3):
        name, prefs = PROFILES[index]
        lines.append(f"Profile: {name}")
        baseline = rank_songs(prefs, songs, 5, RANKING_MODES["balanced"].weights)
        for mode in RANKING_MODES.values():
            ranked = rank_songs(prefs, songs, 5, mode.weights)
            lines.append(f"[{mode.name}] {mode.description}")
            lines.extend(_top_lines(ranked))
            if mode.name != "balanced":
                lines.append(f"  vs balanced -> {_changes(baseline, ranked)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def diversity_demo() -> str:
    """Stretch 3: baseline versus variety-penalty rankings."""
    songs = load_songs(str(SONGS_CSV))
    cases = [
        (0, DiversityConfig(artist_penalty=0.75)),
        (1, DiversityConfig(artist_penalty=0.75)),
        (1, DiversityConfig(genre_penalty=0.5)),
    ]
    lines: List[str] = []
    for index, config in cases:
        name, prefs = PROFILES[index]
        baseline = rank_songs(prefs, songs, 5)
        reranked = rank_songs(prefs, songs, 5, diversity=config)
        lines.append(f"Profile: {name}; variety penalty: "
                     f"artist {config.artist_penalty:g}, genre {config.genre_penalty:g}")
        lines.append("Baseline (no penalty):")
        lines.extend(_top_lines(baseline))
        lines.append("With penalty:")
        lines.extend(_top_lines(reranked))
        for rec in reranked:
            for reason in rec.reasons:
                if reason.startswith("variety penalty"):
                    lines.append(f"  {rec.song['title']}: {reason}")
        lines.append(f"What changed: {_changes(baseline, reranked)}")
        before = sum(score_song(prefs, r.song)[0] for r in baseline)
        after = sum(score_song(prefs, r.song)[0] for r in reranked)
        lines.append(f"Match quality (sum of the five songs' penalty-free scores): "
                     f"baseline {before:.2f}, with penalty {after:.2f}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> None:
    print("=== Catalog counts ===")
    print(catalog_counts())
    print("\n=== Weight sensitivity ===")
    print(weight_sensitivity())
    print("\n=== Profile comparison ===")
    print(profile_comparison())
    print("\n=== Exact-label brittleness ===")
    print(label_brittleness())
    print("\n=== Stretch 1: new attributes ===")
    print(attribute_demo())
    print("\n=== Stretch 2: ranking modes ===")
    print(mode_comparison())
    print("\n=== Stretch 3: variety penalty ===")
    print(diversity_demo())


if __name__ == "__main__":
    main()
