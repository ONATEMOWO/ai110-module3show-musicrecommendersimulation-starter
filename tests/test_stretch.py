"""Tests for the stretch features: extra song attributes, ranking modes and variety reranking."""
import dataclasses
import random
import re
from pathlib import Path

import pytest

from src.main import PROFILES
from src.recommender import (
    DEFAULT_MODE, OPTIONAL_COLUMNS, RANKING_MODES, DiversityConfig, Recommender, ScoringWeights,
    Song, UserProfile, get_mode, load_songs, max_score, rank_songs, recommend_songs, score_song,
)

SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"
FOLK = {"genre": "folk", "mood": "nostalgic", "energy": 0.40, "likes_acoustic": True}
POP, LOFI, ROCK, CLASSICAL = (prefs for _, prefs in PROFILES)


def make_song(**overrides):
    song = {"id": 1, "title": "T", "artist": "A", "genre": "pop", "mood": "happy",
            "energy": 0.8, "tempo_bpm": 120.0, "valence": 0.7, "danceability": 0.7, "acousticness": 0.2,
            "popularity": 50, "release_decade": 2010, "instrumentalness": 0.2, "speechiness": 0.1,
            "liveness": 0.2}
    song.update(overrides)
    return song


@pytest.fixture(scope="module")
def catalog():
    return load_songs(str(SONGS_CSV))


def titles(results):
    return [song["title"] for song, _, _ in results]


def points_in(reasons):
    return [float(p) for p in re.findall(r"\(([+-]\d+\.\d+)\)", " ".join(reasons))]


# =============================== Stretch 1: new attributes =====================

def test_catalog_songs_carry_all_five_new_attributes(catalog):
    assert all(column in song for song in catalog for column in OPTIONAL_COLUMNS)


def test_decade_similarity_formula():
    exact, _ = score_song({"decade": 2010}, make_song(release_decade=2010))
    ten_off, _ = score_song({"decade": 2010}, make_song(release_decade=2020))
    fifty_off, _ = score_song({"decade": 1970}, make_song(release_decade=2020))
    assert exact == pytest.approx(ScoringWeights().decade)
    assert ten_off == pytest.approx(ScoringWeights().decade * (1 - 10 / 50))
    assert fifty_off == 0.0


def test_popularity_similarity_formula():
    score, reasons = score_song({"popularity": 80}, make_song(popularity=70))
    assert score == pytest.approx(ScoringWeights().popularity * (1 - 10 / 50))
    assert reasons == ["popularity 70 vs target 80 (+0.40)"]


@pytest.mark.parametrize("pref, column, near, far", [
    ("popularity", "popularity", 55, 5),
    ("decade", "release_decade", 2010, 1970),
    ("instrumentalness", "instrumentalness", 0.9, 0.1),
    ("speechiness", "speechiness", 0.3, 0.0),
    ("liveness", "liveness", 0.6, 0.05),
])
def test_each_new_attribute_can_decide_a_ranking(pref, column, near, far):
    target = near
    near_song = make_song(id=2, title="Near", **{column: near})
    far_song = make_song(id=1, title="Far", **{column: far})   # lower id: wins a tie
    without = rank_songs(POP, [near_song, far_song], 2)
    with_pref = rank_songs({**POP, pref: target}, [near_song, far_song], 2)
    assert without[0].song["title"] == "Far"
    assert with_pref[0].song["title"] == "Near"
    assert with_pref[0].score > with_pref[1].score
    assert any(r.startswith(column.replace("_", " ")) for r in with_pref[0].reasons)


def test_new_attributes_add_nothing_when_user_did_not_ask():
    rich = make_song()
    bare = {k: v for k, v in rich.items() if k not in OPTIONAL_COLUMNS}
    assert score_song(POP, rich) == score_song(POP, bare)
    assert not any(word in " ".join(score_song(POP, rich)[1])
                   for word in ("popularity", "decade", "instrumentalness", "speechiness", "liveness"))


def test_song_missing_a_requested_attribute_scores_without_it():
    bare = {k: v for k, v in make_song().items() if k != "release_decade"}
    score, reasons = score_song({**POP, "decade": 2010}, bare)
    assert score == pytest.approx(score_song(POP, bare)[0])
    assert not any("decade" in r for r in reasons)


@pytest.mark.parametrize("bad", [
    {"popularity": 101}, {"popularity": -1}, {"decade": 1800}, {"decade": 2200},
    {"instrumentalness": 1.5}, {"speechiness": -0.2}, {"liveness": "high"},
])
def test_invalid_new_preferences_raise(bad):
    with pytest.raises(ValueError):
        score_song({**POP, **bad}, make_song())


def test_max_score_counts_requested_new_attributes():
    weights = ScoringWeights()
    base = max_score(POP)
    both = max_score({**POP, "decade": 2010, "liveness": 0.3})
    assert both == pytest.approx(base + weights.decade + weights.liveness)


def test_decade_preference_changes_real_catalog_ranking(catalog):
    before = titles(recommend_songs(FOLK, catalog, k=5))
    after = titles(recommend_songs({**FOLK, "decade": 1970}, catalog, k=5))
    assert before != after
    assert before.index("Blue Hour Confessions") == 4 and after.index("Blue Hour Confessions") == 2
    assert "Focus Flow" in before and "Focus Flow" not in after


def test_popularity_preference_changes_real_catalog_scores_and_order(catalog):
    before = recommend_songs(POP, catalog, k=5)
    after = recommend_songs({**POP, "popularity": 40}, catalog, k=5)
    assert titles(before)[2:4] == ["Gym Hero", "Hyperdrive Heartbeat"]
    assert titles(after)[2:4] == ["Hyperdrive Heartbeat", "Gym Hero"]
    assert after[0][1] > before[0][1]


def test_new_attribute_reasons_sum_to_score(catalog):
    prefs = {**FOLK, "decade": 1970, "popularity": 40, "instrumentalness": 0.5,
             "speechiness": 0.05, "liveness": 0.4}
    for song in catalog:
        score, reasons = score_song(prefs, song)
        assert abs(sum(points_in(reasons)) - score) <= 0.005 * len(reasons) + 1e-9


def test_user_profile_new_targets_flow_into_prefs_and_match_functional(catalog):
    user = UserProfile("folk", "nostalgic", 0.4, True, target_decade=1970, target_popularity=40,
                       target_instrumentalness=0.5, target_speechiness=0.05, target_liveness=0.4)
    prefs = user.to_prefs()
    assert prefs["decade"] == 1970 and prefs["popularity"] == 40 and prefs["liveness"] == 0.4
    songs = [Song.from_dict(row) for row in catalog]
    oop = [s.id for s in Recommender(songs).recommend(user, k=8)]
    functional = [s["id"] for s, _, _ in recommend_songs(prefs, catalog, k=8)]
    assert oop == functional


def test_song_dataclass_keeps_old_constructor_and_gains_optional_fields():
    song = Song(1, "T", "A", "pop", "happy", 0.8, 120, 0.9, 0.8, 0.2)
    assert song.popularity is None and song.release_decade is None
    full = Song.from_dict(make_song())
    assert full.release_decade == 2010 and full.liveness == 0.2


# =============================== Stretch 2: ranking modes ======================

def test_at_least_two_modes_with_balanced_default():
    assert len(RANKING_MODES) >= 3
    assert {"balanced", "genre-first", "mood-energy"} <= set(RANKING_MODES)
    assert DEFAULT_MODE == "balanced"
    assert get_mode(DEFAULT_MODE).weights == ScoringWeights()


def test_unknown_mode_raises_with_choices():
    with pytest.raises(ValueError, match="balanced.*genre-first.*mood-energy"):
        get_mode("loudest")


def test_modes_have_distinct_weights_and_documented_emphasis():
    weights = [mode.weights for mode in RANKING_MODES.values()]
    assert len(set(weights)) == len(weights)
    genre_first, mood_energy = get_mode("genre-first").weights, get_mode("mood-energy").weights
    assert genre_first.genre > ScoringWeights().genre > mood_energy.genre
    assert mood_energy.mood > ScoringWeights().mood and mood_energy.energy > ScoringWeights().energy


def test_modes_are_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        get_mode("balanced").weights.genre = 99.0


def test_modes_reuse_the_same_scoring_rule():
    perfect = make_song(acousticness=0.0)
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
    for mode in RANKING_MODES.values():
        w = mode.weights
        assert score_song(prefs, perfect, w)[0] == pytest.approx(w.genre + w.mood + w.energy + w.acousticness)
        assert score_song(prefs, perfect, w)[0] == pytest.approx(max_score(prefs, w))


def test_modes_produce_different_rankings_on_the_classical_edge_case(catalog):
    ranks = {name: titles(recommend_songs(CLASSICAL, catalog, k=5, weights=mode.weights))
             for name, mode in RANKING_MODES.items()}
    assert ranks["balanced"][:2] == ["Moonlit Sonata Sketch", "Glass Cathedral"]
    assert ranks["genre-first"][:2] == ["Moonlit Sonata Sketch", "Glass Cathedral"]
    assert ranks["mood-energy"][1] == "Laser Garden" and "Glass Cathedral" not in ranks["mood-energy"]
    assert ranks["balanced"] != ranks["mood-energy"] != ranks["genre-first"]


def test_modes_change_scores_even_when_order_is_unchanged(catalog):
    balanced = recommend_songs(POP, catalog, k=5)
    genre_first = recommend_songs(POP, catalog, k=5, weights=get_mode("genre-first").weights)
    assert titles(balanced) == titles(genre_first)
    assert genre_first[0][1] != pytest.approx(balanced[0][1])


def test_mood_energy_mode_lets_a_non_pop_song_in_for_the_pop_listener(catalog):
    balanced = titles(recommend_songs(POP, catalog, k=5))
    mood_energy = titles(recommend_songs(POP, catalog, k=5, weights=get_mode("mood-energy").weights))
    assert "Fuego en la Calle" not in balanced and "Fuego en la Calle" in mood_energy


def test_oop_recommender_matches_functional_in_every_mode(catalog):
    songs = [Song.from_dict(row) for row in catalog]
    user = UserProfile("pop", "happy", 0.85, False)
    for mode in RANKING_MODES.values():
        oop = [s.id for s in Recommender(songs, mode.weights).recommend(user, k=10)]
        functional = [s["id"] for s, _, _ in recommend_songs(POP, catalog, k=10, weights=mode.weights)]
        assert oop == functional


def test_every_mode_keeps_reasons_consistent_with_scores(catalog):
    for mode in RANKING_MODES.values():
        for _, prefs in PROFILES:
            for song, score, explanation in recommend_songs(prefs, catalog, k=5, weights=mode.weights):
                reasons = explanation.split("; ")
                assert abs(sum(points_in(reasons)) - score) <= 0.005 * len(reasons) + 1e-9


# =============================== Stretch 3: variety reranking ==================

ARTIST_75 = DiversityConfig(artist_penalty=0.75)


def artists(results):
    return [song["artist"] for song, _, _ in results]


def test_disabled_diversity_equals_the_baseline_exactly(catalog):
    baseline = recommend_songs(POP, catalog, k=10)
    for off in (None, DiversityConfig(), DiversityConfig(0.0, 0.0)):
        assert recommend_songs(POP, catalog, k=10, diversity=off) == baseline
    assert not DiversityConfig().enabled and ARTIST_75.enabled


def test_artist_penalty_changes_the_top_results(catalog):
    baseline = recommend_songs(POP, catalog, k=5)
    diverse = recommend_songs(POP, catalog, k=5, diversity=ARTIST_75)
    assert artists(baseline).count("Max Pulse") == 2
    assert artists(diverse).count("Max Pulse") == 1
    assert "Hyperdrive Heartbeat" in titles(baseline) and "Hyperdrive Heartbeat" not in titles(diverse)
    assert "Fuego en la Calle" in titles(diverse)
    assert titles(diverse)[:3] == titles(baseline)[:3]


def test_final_score_reflects_the_penalty(catalog):
    baseline = {s["title"]: score for s, score, _ in recommend_songs(LOFI, catalog, k=30)}
    diverse = recommend_songs(LOFI, catalog, k=5, diversity=ARTIST_75)
    scores = {s["title"]: score for s, score, _ in diverse}
    assert scores["Focus Flow"] == pytest.approx(baseline["Focus Flow"] - 0.75)
    assert scores["Midnight Coding"] == pytest.approx(baseline["Midnight Coding"])
    assert titles(diverse) == ["Library Rain", "Midnight Coding", "Spacewalk Thoughts", "Focus Flow", "Late Bus Home"]


def test_explanations_state_the_penalty_truthfully(catalog):
    diverse = {s["title"]: (score, why) for s, score, why in recommend_songs(LOFI, catalog, k=5, diversity=ARTIST_75)}
    score, why = diverse["Focus Flow"]
    assert "variety penalty: 1 earlier pick(s) by LoRoom (-0.75)" in why
    assert "variety penalty" not in diverse["Midnight Coding"][1]
    assert "variety penalty" not in diverse["Library Rain"][1]


def test_baseline_explanations_never_mention_a_penalty(catalog):
    assert all("variety" not in why for _, _, why in recommend_songs(LOFI, catalog, k=30))


def test_reasons_still_sum_to_score_with_penalties(catalog):
    configs = [ARTIST_75, DiversityConfig(genre_penalty=0.5), DiversityConfig(1.0, 0.5)]
    for config in configs:
        for _, prefs in PROFILES:
            for _, score, why in recommend_songs(prefs, catalog, k=12, diversity=config):
                reasons = why.split("; ")
                assert abs(sum(points_in(reasons)) - score) <= 0.005 * len(reasons) + 1e-9


def test_penalty_accumulates_per_repeat():
    songs = [make_song(id=i, title=f"S{i}", artist="Same") for i in (1, 2, 3)]
    results = rank_songs(POP, songs, 3, diversity=DiversityConfig(artist_penalty=0.5))
    base = results[0].score
    assert [r.score for r in results] == pytest.approx([base, base - 0.5, base - 1.0])
    assert "2 earlier pick(s) by Same (-1.00)" in results[2].explanation


def test_artist_grouping_ignores_case_and_whitespace():
    songs = [make_song(id=1, artist="Neon Echo"), make_song(id=2, artist=" neon echo ")]
    second = rank_songs(POP, songs, 2, diversity=ARTIST_75)[1]
    assert "variety penalty" in second.explanation


def test_genre_penalty_is_configurable_and_independent(catalog):
    genre_only = DiversityConfig(genre_penalty=0.5)
    results = recommend_songs(LOFI, catalog, k=5, diversity=genre_only)
    assert titles(results) == ["Library Rain", "Midnight Coding", "Spacewalk Thoughts", "Late Bus Home", "Focus Flow"]
    scores = {s["title"]: score for s, score, _ in results}
    assert scores["Midnight Coding"] == pytest.approx(5.71 - 0.5, abs=0.01)
    assert scores["Focus Flow"] == pytest.approx(4.29 - 1.0, abs=0.01)
    assert all("by " not in why.split("variety penalty")[-1] for _, _, why in results if "variety" in why)


def test_stronger_penalty_gives_more_variety(catalog):
    counts = []
    for penalty in (0.0, 0.75, 100.0):
        top = recommend_songs(ROCK, catalog, k=8, diversity=DiversityConfig(artist_penalty=penalty))
        counts.append(len(set(artists(top))))
    assert counts[0] <= counts[1] <= counts[2] == 8


def test_variety_never_changes_the_top_pick_or_the_first_instance_of_each_artist(catalog):
    for _, prefs in PROFILES:
        baseline = recommend_songs(prefs, catalog, k=1)[0]
        diverse = recommend_songs(prefs, catalog, k=1, diversity=DiversityConfig(5.0, 5.0))[0]
        assert baseline == diverse


def test_diverse_scores_are_non_increasing(catalog):
    for config in (ARTIST_75, DiversityConfig(0.3, 0.9), DiversityConfig(10.0, 10.0)):
        for _, prefs in PROFILES:
            scores = [score for _, score, _ in recommend_songs(prefs, catalog, k=30, diversity=config)]
            assert scores == sorted(scores, reverse=True)


def test_top_k_semantics_hold_with_diversity(catalog):
    assert recommend_songs(POP, catalog, k=0, diversity=ARTIST_75) == []
    assert recommend_songs(POP, [], k=5, diversity=ARTIST_75) == []
    assert len(recommend_songs(POP, catalog, k=3, diversity=ARTIST_75)) == 3
    everything = recommend_songs(POP, catalog, k=1000, diversity=ARTIST_75)
    assert len(everything) == len(catalog)
    assert len({s["id"] for s, _, _ in everything}) == len(catalog)
    with pytest.raises(ValueError):
        recommend_songs(POP, catalog, k=-1, diversity=ARTIST_75)


def test_diversity_is_deterministic_and_input_order_independent(catalog):
    expected = recommend_songs(ROCK, catalog, k=10, diversity=DiversityConfig(0.75, 0.25))
    for seed in range(5):
        shuffled = list(catalog)
        random.Random(seed).shuffle(shuffled)
        assert recommend_songs(ROCK, shuffled, k=10, diversity=DiversityConfig(0.75, 0.25)) == expected


def test_ties_under_diversity_break_by_id():
    songs = [make_song(id=i, title=f"S{i}", artist=f"Artist {i}") for i in (4, 2, 3, 1)]
    assert [r.song["id"] for r in rank_songs(POP, songs, 4, diversity=ARTIST_75)] == [1, 2, 3, 4]


@pytest.mark.parametrize("kwargs", [{"artist_penalty": -0.1}, {"genre_penalty": -1},
                                    {"artist_penalty": float("nan")}, {"genre_penalty": float("inf")},
                                    {"artist_penalty": "lots"}])
def test_invalid_penalties_raise(kwargs):
    with pytest.raises(ValueError):
        DiversityConfig(**kwargs)


def test_oop_recommender_applies_the_same_diversity(catalog):
    songs = [Song.from_dict(row) for row in catalog]
    user = UserProfile("pop", "happy", 0.85, False)
    oop = Recommender(songs, diversity=ARTIST_75)
    functional = recommend_songs(POP, catalog, k=5, diversity=ARTIST_75)
    assert [s.id for s in oop.recommend(user, k=5)] == [s["id"] for s, _, _ in functional]
    details = oop.recommend_with_details(user, k=5)
    assert [d.explanation for d in details] == [why for _, _, why in functional]
    baseline = Recommender(songs).recommend(user, k=5)
    assert [s.id for s in baseline] != [s.id for s in oop.recommend(user, k=5)]


def test_diversity_combines_with_modes(catalog):
    weights = get_mode("genre-first").weights
    plain = {s["title"]: (rank, score) for rank, (s, score, _) in
             enumerate(recommend_songs(POP, catalog, k=5, weights=weights))}
    diverse = {s["title"]: (rank, score) for rank, (s, score, _) in
               enumerate(recommend_songs(POP, catalog, k=5, weights=weights, diversity=ARTIST_75))}
    assert plain["Hyperdrive Heartbeat"][0] < plain["Heartbeat Static"][0]
    assert diverse["Hyperdrive Heartbeat"][0] > diverse["Heartbeat Static"][0]
    assert diverse["Hyperdrive Heartbeat"][1] == pytest.approx(plain["Hyperdrive Heartbeat"][1] - 0.75)


def test_diversity_does_nothing_when_no_artist_or_genre_repeats(catalog):
    weights = get_mode("mood-energy").weights
    plain = recommend_songs(POP, catalog, k=5, weights=weights)
    assert len(set(artists(plain))) == 5
    assert recommend_songs(POP, catalog, k=5, weights=weights, diversity=DiversityConfig(artist_penalty=3.0)) == plain
