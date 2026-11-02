"""
Reproducible experiments used in the README and model card.

Run from the project root:
    python3 -m src.experiments
"""

from dataclasses import replace
from typing import Dict, List

from src.main import PROFILES, SONGS_CSV
from src.recommender import ScoringWeights, load_songs, max_score, rank_songs

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
        key = "energy < 0.40" if song["energy"] < 0.40 else ("0.40 - 0.69" if song["energy"] < 0.70 else "energy >= 0.70")
        bands[key] += 1
    lines = [f"Songs: {len(songs)}, artists: {len({s['artist'] for s in songs})}",
             f"Genres ({len(genres)}): " + ", ".join(f"{g} {n}" for g, n in sorted(genres.items(), key=lambda x: (-x[1], x[0]))),
             f"Genres with exactly one song: {single_genre} of {len(genres)}",
             f"Moods ({len(moods)}): " + ", ".join(f"{m} {n}" for m, n in sorted(moods.items(), key=lambda x: (-x[1], x[0]))),
             "Energy bands: " + ", ".join(f"{k}: {v}" for k, v in bands.items())]
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


def main() -> None:
    print("=== Catalog counts ===")
    print(catalog_counts())
    print("\n=== Weight sensitivity ===")
    print(weight_sensitivity())
    print("\n=== Profile comparison ===")
    print(profile_comparison())
    print("\n=== Exact-label brittleness ===")
    print(label_brittleness())


if __name__ == "__main__":
    main()
