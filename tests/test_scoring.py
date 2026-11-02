"""Tests for scoring, ranking, edge cases and OOP/functional consistency."""
import math
import random
import re
from pathlib import Path

import pytest

from src.main import PROFILES
from src.recommender import (
    Recommender, ScoringWeights, Song, UserProfile,
    load_songs, max_score, rank_songs, recommend_songs, score_breakdown, score_song, validate_prefs,
)

SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"


def make_song(**overrides):
    song = {"id": 1, "title": "T", "artist": "A", "genre": "pop", "mood": "happy",
            "energy": 0.8, "tempo_bpm": 120.0, "valence": 0.7, "danceability": 0.7, "acousticness": 0.2}
    song.update(overrides)
    return song


PREFS = {"genre": "pop", "mood": "happy", "energy": 0.8}


@pytest.fixture(scope="module")
def catalog():
    return load_songs(str(SONGS_CSV))


def points_in(reasons):
    return [float(p) for p in re.findall(r"\(([+-]\d+\.\d+)\)", " ".join(reasons))]


# --- genre / mood / energy rules --------------------------------------------

def test_exact_genre_match_adds_full_genre_weight():
    weights = ScoringWeights()
    match, _ = score_song({"genre": "pop"}, make_song(genre="pop"))
    other, _ = score_song({"genre": "pop"}, make_song(genre="rock"))
    assert match == pytest.approx(weights.genre)
    assert other == 0.0


def test_exact_mood_match_adds_full_mood_weight():
    match, _ = score_song({"mood": "happy"}, make_song(mood="happy"))
    other, _ = score_song({"mood": "happy"}, make_song(mood="sad"))
    assert match == pytest.approx(ScoringWeights().mood)
    assert other == 0.0


def test_genre_and_mood_matching_ignores_case_and_whitespace():
    score, _ = score_song({"genre": " POP ", "mood": "Happy"}, make_song())
    assert score == pytest.approx(ScoringWeights().genre + ScoringWeights().mood)


def test_indie_pop_does_not_match_pop():
    score, _ = score_song({"genre": "pop"}, make_song(genre="indie pop"))
    assert score == 0.0


def test_energy_rewards_closeness_not_high_energy():
    prefs = {"energy": 0.3}
    low, _ = score_song(prefs, make_song(energy=0.3))
    near, _ = score_song(prefs, make_song(energy=0.4))
    high, _ = score_song(prefs, make_song(energy=0.95))
    assert low > near > high


def test_energy_score_is_symmetric_around_target():
    prefs = {"energy": 0.5}
    below, _ = score_song(prefs, make_song(energy=0.3))
    above, _ = score_song(prefs, make_song(energy=0.7))
    assert below == pytest.approx(above)


def test_energy_points_follow_distance_formula():
    score, _ = score_song({"energy": 0.8}, make_song(energy=0.5))
    assert score == pytest.approx(ScoringWeights().energy * (1 - 0.3))


def test_acoustic_taste_direction():
    acoustic, flat = make_song(acousticness=0.9), make_song(acousticness=0.1)
    assert score_song({"likes_acoustic": True}, acoustic)[0] > score_song({"likes_acoustic": True}, flat)[0]
    assert score_song({"likes_acoustic": False}, flat)[0] > score_song({"likes_acoustic": False}, acoustic)[0]


def test_optional_numeric_prefs_only_count_when_given():
    song = make_song()
    base, _ = score_song(PREFS, song)
    with_valence, reasons = score_song({**PREFS, "valence": 0.7}, song)
    assert with_valence == pytest.approx(base + ScoringWeights().valence)
    assert any(r.startswith("valence") for r in reasons)
    assert not any(r.startswith("valence") for r in score_song(PREFS, song)[1])


def test_tempo_similarity_falls_off_with_distance():
    prefs = {"tempo_bpm": 120}
    close = score_song(prefs, make_song(tempo_bpm=125.0))[0]
    far = score_song(prefs, make_song(tempo_bpm=170.0))[0]
    way_off = score_song(prefs, make_song(tempo_bpm=200.0))[0]
    assert close > far > way_off == 0.0


def test_custom_weights_change_the_score():
    heavy = ScoringWeights(genre=5.0)
    assert score_song({"genre": "pop"}, make_song(), heavy)[0] == pytest.approx(5.0)


def test_zero_weight_removes_a_feature_and_its_reason():
    score, reasons = score_song(PREFS, make_song(), ScoringWeights(genre=0.0))
    assert not any(r.startswith("genre") for r in reasons)
    assert score == pytest.approx(ScoringWeights().mood + ScoringWeights().energy)


def test_scores_are_finite_and_bounded_for_every_profile(catalog):
    for _, prefs in PROFILES:
        ceiling = max_score(prefs)
        for song in catalog:
            score, _ = score_song(prefs, song)
            assert math.isfinite(score) and 0.0 <= score <= ceiling + 1e-9


def test_perfect_song_reaches_max_score():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
    song = make_song(acousticness=0.0)
    assert score_song(prefs, song)[0] == pytest.approx(max_score(prefs))


# --- explanations ------------------------------------------------------------

def test_reasons_sum_to_score_for_every_profile_and_song(catalog):
    for _, prefs in PROFILES:
        for song in catalog:
            score, reasons = score_song(prefs, song)
            assert abs(sum(points_in(reasons)) - score) <= 0.005 * len(reasons) + 1e-9


def test_breakdown_components_add_up_exactly(catalog):
    breakdown = score_breakdown(PROFILES[0][1], catalog[0])
    assert breakdown.total == pytest.approx(sum(c.points for c in breakdown.components))
    assert all(c.points > 0 for c in breakdown.components)


def test_reasons_only_name_features_that_contributed():
    _, reasons = score_song(PREFS, make_song(genre="rock", mood="sad"))
    assert not any(r.startswith(("genre", "mood")) for r in reasons)
    assert any(r.startswith("energy") for r in reasons)


def test_reason_for_matching_feature_mentions_its_value():
    _, reasons = score_song(PREFS, make_song())
    assert "genre match: pop (+2.00)" in reasons
    assert "mood match: happy (+1.50)" in reasons
    assert "energy 0.80 vs target 0.80 (+2.00)" in reasons


def test_song_with_nothing_in_common_still_gets_an_honest_explanation():
    score, reasons = score_song({"genre": "jazz"}, make_song())
    assert score == 0.0 and reasons == ["no preference matched (+0.00)"]


# --- ranking, ties, edge cases ----------------------------------------------

def test_ranking_is_sorted_best_first(catalog):
    for _, prefs in PROFILES:
        scores = [score for _, score, _ in recommend_songs(prefs, catalog, k=len(catalog))]
        assert scores == sorted(scores, reverse=True)


def test_ties_break_by_id_regardless_of_input_order():
    twins = [make_song(id=i, title=f"Song {i}") for i in (7, 3, 9, 1)]
    expected = [1, 3, 7, 9]
    for _ in range(5):
        random.shuffle(twins)
        assert [s["id"] for s, _, _ in recommend_songs(PREFS, twins, k=4)] == expected


def test_ranking_is_identical_across_repeated_runs(catalog):
    first = recommend_songs(PROFILES[0][1], catalog, k=10)
    assert first == recommend_songs(PROFILES[0][1], catalog, k=10)


def test_shuffled_catalog_gives_same_ranking(catalog):
    shuffled = list(catalog)
    random.Random(0).shuffle(shuffled)
    for _, prefs in PROFILES:
        assert recommend_songs(prefs, catalog, k=10) == recommend_songs(prefs, shuffled, k=10)


def test_distinct_profiles_get_distinct_recommendations(catalog):
    top_ids = [tuple(s["id"] for s, _, _ in recommend_songs(prefs, catalog, k=3)) for _, prefs in PROFILES]
    assert len(set(top_ids)) == len(PROFILES)
    assert len({ids[0] for ids in top_ids}) == len(PROFILES)


def test_expected_top_song_for_each_core_profile(catalog):
    top = {name: recommend_songs(prefs, catalog, k=1)[0][0]["title"] for name, prefs in PROFILES}
    assert top["Happy high-energy pop listener"] == "Sunrise City"
    assert top["Relaxed low-energy lofi listener"] == "Library Rain"
    assert top["Intense rock/workout listener"] == "Storm Runner"


def test_empty_catalog_returns_empty_list():
    assert recommend_songs(PREFS, [], k=5) == []
    assert Recommender([]).recommend(UserProfile("pop", "happy", 0.8, False)) == []


def test_k_zero_returns_empty_list(catalog):
    assert recommend_songs(PREFS, catalog, k=0) == []


def test_k_larger_than_catalog_returns_every_song_once(catalog):
    results = recommend_songs(PREFS, catalog, k=1000)
    assert len(results) == len(catalog)
    assert len({s["id"] for s, _, _ in results}) == len(catalog)


def test_default_k_is_five(catalog):
    assert len(recommend_songs(PREFS, catalog)) == 5


@pytest.mark.parametrize("bad_k", [-1, 2.5, "3", None, True])
def test_invalid_k_raises(catalog, bad_k):
    with pytest.raises(ValueError, match="k must be"):
        recommend_songs(PREFS, catalog, k=bad_k)


@pytest.mark.parametrize("bad_prefs, fragment", [
    ({"energy": 1.5}, "'energy' must be a number between 0 and 1"),
    ({"energy": -0.1}, "'energy'"),
    ({"energy": "high"}, "'energy'"),
    ({"energy": float("nan")}, "'energy'"),
    ({"valence": 2}, "'valence'"),
    ({"tempo_bpm": 0}, "'tempo_bpm'"),
    ({"genre": ""}, "'genre' must be a non-empty string"),
    ({"mood": 5}, "'mood'"),
    ({"likes_acoustic": "yes"}, "'likes_acoustic'"),
    ({"enrgy": 0.5}, "unknown preference"),
    ({}, "no preferences"),
    ({"energy": None}, "no preferences"),
])
def test_invalid_preferences_raise(bad_prefs, fragment):
    with pytest.raises(ValueError, match=fragment):
        score_song(bad_prefs, make_song())
    with pytest.raises(ValueError):
        recommend_songs(bad_prefs, [make_song()], k=1)


def test_invalid_prefs_raise_even_with_empty_catalog_or_k_zero():
    with pytest.raises(ValueError):
        recommend_songs({"energy": 9}, [], k=5)
    with pytest.raises(ValueError):
        recommend_songs({"energy": 9}, [make_song()], k=0)


def test_negative_or_nan_weights_are_rejected():
    for bad in (-1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="weight 'genre'"):
            ScoringWeights(genre=bad)


def test_none_preference_means_not_specified():
    assert validate_prefs({"genre": "pop", "energy": None}) == {"genre": "pop"}


def test_song_with_missing_or_invalid_feature_is_scored_without_it():
    broken = make_song(energy=None)
    score, reasons = score_song(PREFS, broken)
    assert score == pytest.approx(ScoringWeights().genre + ScoringWeights().mood)
    assert not any(r.startswith("energy") for r in reasons)
    nan_song = make_song(energy=float("nan"))
    assert math.isfinite(score_song(PREFS, nan_song)[0])
    no_key = {k: v for k, v in make_song().items() if k != "energy"}
    assert math.isfinite(score_song(PREFS, no_key)[0])


def test_score_song_rejects_non_song_input():
    with pytest.raises(TypeError):
        score_song(PREFS, "not a song")


# --- functional / OOP consistency --------------------------------------------

def profile_to_user(prefs):
    return UserProfile(
        favorite_genre=prefs["genre"], favorite_mood=prefs["mood"],
        target_energy=prefs["energy"], likes_acoustic=prefs["likes_acoustic"])


def test_user_profile_round_trips_to_prefs():
    user = UserProfile("pop", "happy", 0.8, False, target_valence=0.7)
    assert user.to_prefs() == {"genre": "pop", "mood": "happy", "energy": 0.8,
                               "likes_acoustic": False, "valence": 0.7}


def test_oop_and_functional_interfaces_rank_identically(catalog):
    song_objects = [Song.from_dict(row) for row in catalog]
    recommender = Recommender(song_objects)
    for _, prefs in PROFILES:
        functional = recommend_songs(prefs, catalog, k=10)
        oop = recommender.recommend(profile_to_user(prefs), k=10)
        assert [s.id for s in oop] == [song["id"] for song, _, _ in functional]
        assert all(isinstance(s, Song) for s in oop)


def test_oop_details_match_functional_scores_and_reasons(catalog):
    recommender = Recommender([Song.from_dict(row) for row in catalog])
    prefs = PROFILES[1][1]
    details = recommender.recommend_with_details(profile_to_user(prefs), k=5)
    functional = recommend_songs(prefs, catalog, k=5)
    for rec, (_, score, explanation) in zip(details, functional):
        assert rec.score == pytest.approx(score)
        assert rec.explanation == explanation


def test_explain_recommendation_uses_the_shared_score(catalog):
    song = Song.from_dict(catalog[0])
    user = profile_to_user(PROFILES[0][1])
    text = Recommender([song]).explain_recommendation(user, song)
    score, reasons = score_song(PROFILES[0][1], catalog[0])
    assert f"score {score:.2f}" in text
    assert all(reason in text for reason in reasons)


def test_recommender_accepts_custom_weights(catalog):
    songs = [Song.from_dict(row) for row in catalog]
    user = profile_to_user(PROFILES[0][1])
    default_top = Recommender(songs).recommend(user, k=1)[0]
    energy_only = Recommender(songs, ScoringWeights(genre=0, mood=0, acousticness=0)).recommend(user, k=1)[0]
    assert default_top.title == "Sunrise City"
    assert abs(energy_only.energy - 0.85) <= abs(default_top.energy - 0.85)


def test_recommend_returns_requested_number_of_songs(catalog):
    recommender = Recommender([Song.from_dict(row) for row in catalog])
    user = profile_to_user(PROFILES[0][1])
    assert len(recommender.recommend(user, k=3)) == 3
    assert recommender.recommend(user, k=0) == []
    assert len(recommender.recommend(user, k=999)) == len(catalog)


def test_rank_songs_returns_original_objects():
    songs = [make_song(id=2, title="B"), make_song(id=1, title="A")]
    ranked = rank_songs(PREFS, songs, k=2)
    assert ranked[0].song is songs[1] and ranked[1].song is songs[0]
