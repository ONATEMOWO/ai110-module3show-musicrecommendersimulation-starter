"""Tests for the table/list formatting and the command line interface."""
import re
from pathlib import Path

import pytest

from src.main import DEFAULT_WIDTH, PROFILES, main
from src.recommender import DiversityConfig, Recommendation, load_songs, rank_songs
from src.report import (
    MIN_WIDTH, WIDE_LAYOUT_MIN_WIDTH, format_recommendation_list, format_recommendation_table,
)

SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"
LONG_TITLE = "The Extraordinarily Long Winded Title of a Song That Never Seems To End Anywhere"
LONG_WORD = "Supercalifragilisticexpialidocious" * 3


@pytest.fixture(scope="module")
def songs():
    return load_songs(str(SONGS_CSV))


def top5(songs, index=0, **kwargs):
    return rank_songs(PROFILES[index][1], songs, 5, **kwargs)


def long_rec(title=LONG_TITLE, artist="An Artist With A Remarkably Long Name Too"):
    song = {"id": 1, "title": title, "artist": artist}
    return Recommendation(song, 4.25, ("genre match: pop (+2.00)", "energy 0.82 vs target 0.85 (+1.94)"))


# --- table content ------------------------------------------------------------

def test_table_has_every_required_column_and_value(songs):
    recs = top5(songs)
    text = format_recommendation_table(recs, 160)
    header = text.splitlines()[0]
    for column in ("#", "Song", "Artist", "Score", "Why"):
        assert column in header
    for place, rec in enumerate(recs, start=1):
        assert rec.song["title"] in text and rec.song["artist"] in text
        assert f"{rec.score:.2f}" in text
        assert all(reason in text for reason in rec.reasons)
    ranks = [line.split(" | ")[0].strip() for line in text.splitlines()[2:] if " | " in line and line[0].isdigit()]
    assert ranks == ["1", "2", "3", "4", "5"]


def test_table_shows_final_score_and_penalty_reason(songs):
    recs = top5(songs, 1, diversity=DiversityConfig(artist_penalty=0.75))
    text = format_recommendation_table(recs, 160)
    assert "variety penalty: 1 earlier pick(s) by LoRoom (-0.75)" in text
    focus = next(rec for rec in recs if rec.song["title"] == "Focus Flow")
    assert f"{focus.score:.2f}" in text and "3.54" in text


def test_empty_results_render_a_message():
    assert format_recommendation_table([], 100) == "(no recommendations)"
    assert format_recommendation_list([]) == "(no recommendations)"


def test_output_is_deterministic(songs):
    assert format_recommendation_table(top5(songs), 90) == format_recommendation_table(top5(songs), 90)


def test_list_format_wraps_to_width_without_losing_text():
    text = format_recommendation_list([long_rec()], 40)
    assert max(len(line) for line in text.splitlines()) <= 40
    assert LONG_TITLE in " ".join(text.split())
    unwrapped = format_recommendation_list([long_rec()])
    assert len(unwrapped.splitlines()) == 3 and LONG_TITLE in unwrapped


def test_list_format_has_song_artist_score_and_reasons(songs):
    rec = top5(songs)[0]
    text = format_recommendation_list([rec])
    assert text.splitlines()[0] == "1. Sunrise City by Neon Echo - score 5.85"
    assert all(f"- {reason}" in text for reason in rec.reasons)


# --- width handling -----------------------------------------------------------

@pytest.mark.parametrize("width", [30, 36, 45, 60, 75, 76, 80, 100, 140])
def test_no_line_exceeds_the_requested_width_even_with_long_names(width):
    text = format_recommendation_table([long_rec(), long_rec(LONG_WORD, LONG_WORD)], width)
    assert max(len(line) for line in text.splitlines()) <= width


@pytest.mark.parametrize("width", [30, 50, 100])
def test_real_catalog_fits_every_width(songs, width):
    for index in range(len(PROFILES)):
        text = format_recommendation_table(top5(songs, index), width)
        assert max(len(line) for line in text.splitlines()) <= width


def test_widths_below_the_minimum_are_clamped():
    text = format_recommendation_table([long_rec()], 5)
    assert max(len(line) for line in text.splitlines()) <= MIN_WIDTH


def test_no_trailing_whitespace(songs):
    for width in (40, 100):
        assert all(line == line.rstrip() for line in format_recommendation_table(top5(songs), width).splitlines())


def test_layout_switches_from_table_to_compact_at_threshold(songs):
    recs = top5(songs)
    assert "Why (points)" in format_recommendation_table(recs, WIDE_LAYOUT_MIN_WIDTH)
    compact = format_recommendation_table(recs, WIDE_LAYOUT_MIN_WIDTH - 1)
    assert "Why (points)" not in compact and compact.startswith("1. Sunrise City by Neon Echo")


def test_long_title_is_wrapped_not_truncated_in_the_wide_table():
    text = format_recommendation_table([long_rec()], 90)
    song_cells = [line.split(" | ")[1].strip() for line in text.splitlines()[2:] if " | " in line]
    assert " ".join(cell for cell in song_cells if cell) == LONG_TITLE


def test_long_unbreakable_word_is_split_and_nothing_is_lost():
    rec = long_rec(LONG_WORD, "X")
    wide = format_recommendation_table([rec], 100)
    cells = [line.split(" | ")[1].strip() for line in wide.splitlines()[2:] if " | " in line]
    assert "".join(cells) == LONG_WORD
    assert len(LONG_WORD) > 100 and len([c for c in cells if c]) > 1
    compact = format_recommendation_table([rec], 40)
    assert LONG_WORD in "".join(compact.split())


def test_long_title_is_complete_in_the_compact_layout():
    text = format_recommendation_table([long_rec()], 40)
    assert text.startswith("1. The Extraordinarily")
    assert LONG_TITLE in " ".join(text.split())


# --- command line interface ---------------------------------------------------

def run_cli(capsys, *argv):
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_default_run_shows_catalog_count_all_profiles_and_five_rows_each(capsys, songs):
    code, out = run_cli(capsys)
    assert code == 0
    assert f"Loaded {len(songs)} songs" in out
    assert "Mode: balanced" in out and "Variety penalty: off" in out
    for name, _ in PROFILES:
        assert f"=== {name} ===" in out
    assert len(PROFILES) >= 3
    assert len(re.findall(r"^[1-5] \| ", out, flags=re.M)) == 5 * len(PROFILES)
    assert max(len(line) for line in out.splitlines()) <= DEFAULT_WIDTH


def test_default_run_is_deterministic(capsys):
    assert run_cli(capsys)[1] == run_cli(capsys)[1]


def test_mode_flags_change_the_output(capsys):
    _, balanced = run_cli(capsys)
    _, genre_first = run_cli(capsys, "--mode", "genre-first")
    _, mood_energy = run_cli(capsys, "--mode", "mood-energy")
    assert "Mode: genre-first" in genre_first and "Mode: mood-energy" in mood_energy
    assert len({balanced, genre_first, mood_energy}) == 3
    assert "Fuego en la Calle" in mood_energy and "Fuego en la Calle" not in balanced


def test_cli_scores_match_the_library(capsys, songs):
    _, out = run_cli(capsys, "--format", "list")
    first = rank_songs(PROFILES[0][1], songs, 5)[0]
    assert f"1. {first.song['title']} by {first.song['artist']} - score {first.score:.2f}" in out


def test_artist_penalty_flag_enables_variety_and_shows_penalties(capsys):
    _, baseline = run_cli(capsys)
    _, diverse = run_cli(capsys, "--artist-penalty", "0.75")
    assert "Variety penalty: ON (artist 0.75, genre 0)" in diverse
    assert "variety penalty:" in diverse and "variety penalty" not in baseline
    assert "Hyperdrive Heartbeat" in baseline.split("=== Relaxed")[0]
    assert "Hyperdrive Heartbeat" not in diverse.split("=== Relaxed")[0]


def test_genre_penalty_flag_is_independent(capsys):
    _, out = run_cli(capsys, "--genre-penalty", "0.5")
    assert "genre 0.5" in out and "earlier lofi pick(s)" in out


def test_narrow_width_flag_switches_to_compact_layout(capsys):
    _, out = run_cli(capsys, "--width", "50")
    assert "Why (points)" not in out
    assert max(len(line) for line in out.splitlines()) <= 50


@pytest.mark.parametrize("mode", ["balanced", "genre-first", "mood-energy"])
@pytest.mark.parametrize("width", [30, 50, 76, 100])
@pytest.mark.parametrize("fmt", ["table", "list"])
def test_every_output_line_respects_width_in_every_mode(capsys, mode, width, fmt):
    _, out = run_cli(capsys, "--mode", mode, "--width", str(width), "--format", fmt, "--artist-penalty", "0.75")
    assert max(len(line) for line in out.splitlines()) <= width


@pytest.mark.parametrize("argv", [
    ["--mode", "loudest"], ["--artist-penalty", "-1"], ["--genre-penalty", "nan"],
    ["--width", "10"], ["--width", "wide"], ["--format", "html"],
])
def test_bad_arguments_exit_with_usage_error(argv, capsys):
    with pytest.raises(SystemExit) as info:
        main(argv)
    assert info.value.code == 2
    assert "usage" in capsys.readouterr().err.lower()
