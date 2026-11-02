"""Tests for CSV loading and the shipped song catalog."""
import warnings
from collections import Counter
from pathlib import Path

import pytest

from src.recommender import REQUIRED_COLUMNS, FEATURE_RANGES, load_songs

SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"
HEADER = ",".join(REQUIRED_COLUMNS)
GOOD_ROW = "1,Test Song,Test Artist,pop,happy,0.8,120,0.9,0.7,0.2"


def write_csv(tmp_path, *lines):
    path = tmp_path / "songs.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


# --- loading ---------------------------------------------------------------

def test_load_songs_converts_numeric_types(tmp_path):
    songs = load_songs(write_csv(tmp_path, HEADER, GOOD_ROW))
    assert len(songs) == 1
    song = songs[0]
    assert song["id"] == 1 and isinstance(song["id"], int)
    for column in FEATURE_RANGES:
        assert isinstance(song[column], float), column
    assert song["tempo_bpm"] == 120.0
    assert song["title"] == "Test Song" and song["genre"] == "pop"


def test_load_songs_strips_whitespace(tmp_path):
    row = " 1 , Test Song , Test Artist , Pop , happy ,0.8,120,0.9,0.7,0.2"
    song = load_songs(write_csv(tmp_path, HEADER, row))[0]
    assert song["title"] == "Test Song" and song["id"] == 1


def test_header_only_csv_is_an_empty_catalog(tmp_path):
    assert load_songs(write_csv(tmp_path, HEADER)) == []


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_songs("does/not/exist.csv")


def test_missing_required_column_raises(tmp_path):
    header = ",".join(c for c in REQUIRED_COLUMNS if c != "energy")
    with pytest.raises(ValueError, match="missing required column.*energy"):
        load_songs(write_csv(tmp_path, header, "1,T,A,pop,happy,120,0.9,0.7,0.2"))


def test_empty_file_raises(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    with pytest.raises(ValueError, match="missing required column"):
        load_songs(str(path))


@pytest.mark.parametrize("bad_row, fragment", [
    ("1,T,A,pop,happy,loud,120,0.9,0.7,0.2", "'energy' must be a number"),
    ("1,T,A,pop,happy,1.5,120,0.9,0.7,0.2", "'energy' must be between"),
    ("1,T,A,pop,happy,nan,120,0.9,0.7,0.2", "'energy' must be between"),
    ("1,T,A,pop,happy,0.8,0,0.9,0.7,0.2", "'tempo_bpm' must be between"),
    ("1,T,A,pop,happy,0.8,120,0.9,0.7,", "'acousticness' must be a number"),
    ("x,T,A,pop,happy,0.8,120,0.9,0.7,0.2", "id must be an integer"),
    ("1,,A,pop,happy,0.8,120,0.9,0.7,0.2", "missing value for 'title'"),
    ("1,T,A,pop,happy,0.8,120,0.9,0.7,0.2,extra", "more values than the header"),
])
def test_invalid_rows_raise_with_line_number(tmp_path, bad_row, fragment):
    path = write_csv(tmp_path, HEADER, "2,Ok,Ok,pop,happy,0.5,100,0.5,0.5,0.5", bad_row)
    with pytest.raises(ValueError, match=fragment) as info:
        load_songs(path)
    assert "line 3" in str(info.value)


def test_duplicate_id_raises(tmp_path):
    with pytest.raises(ValueError, match="duplicate id 1"):
        load_songs(write_csv(tmp_path, HEADER, GOOD_ROW, GOOD_ROW))


def test_non_strict_mode_skips_bad_rows_with_warning(tmp_path):
    bad = "2,T,A,pop,happy,9.9,120,0.9,0.7,0.2"
    path = write_csv(tmp_path, HEADER, GOOD_ROW, bad)
    with pytest.warns(UserWarning, match="line 3"):
        songs = load_songs(path, strict=False)
    assert [s["id"] for s in songs] == [1]


def test_strict_mode_emits_no_warnings_for_valid_file(tmp_path):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        load_songs(write_csv(tmp_path, HEADER, GOOD_ROW))


# --- the shipped catalog ---------------------------------------------------

@pytest.fixture(scope="module")
def catalog():
    return load_songs(str(SONGS_CSV))


def test_catalog_has_at_least_twenty_songs(catalog):
    assert len(catalog) >= 20


def test_catalog_preserves_starter_header_columns():
    header = SONGS_CSV.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert tuple(header[:len(REQUIRED_COLUMNS)]) == REQUIRED_COLUMNS


def test_catalog_ids_are_unique(catalog):
    ids = [s["id"] for s in catalog]
    assert len(ids) == len(set(ids))


def test_catalog_values_are_valid(catalog):
    for song in catalog:
        for column in ("title", "artist", "genre", "mood"):
            assert song[column] and song[column] == song[column].strip()
            assert song[column] == song[column].lower() or column in ("title", "artist")
        for column, (low, high) in FEATURE_RANGES.items():
            assert low <= song[column] <= high, (song["id"], column)


def test_catalog_is_not_dominated_by_one_genre(catalog):
    genres = Counter(s["genre"] for s in catalog)
    assert len(genres) >= 10
    assert max(genres.values()) / len(catalog) <= 0.25


def test_catalog_has_variety_in_moods_energy_and_artists(catalog):
    assert len({s["mood"] for s in catalog}) >= 8
    assert len({s["artist"] for s in catalog}) >= 15
    energies = [s["energy"] for s in catalog]
    assert min(energies) < 0.3 and max(energies) > 0.9
