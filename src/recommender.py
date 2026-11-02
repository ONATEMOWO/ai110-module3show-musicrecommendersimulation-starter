"""
Music recommender core: data model, scoring and ranking.

Two interfaces sit on top of ONE implementation:

- Functional: load_songs / score_song / recommend_songs (used by src/main.py)
- OOP: Song / UserProfile / Recommender (used by tests/test_recommender.py)

Both call score_breakdown() for scoring and rank_songs() for ranking, so they
cannot disagree about which song is better. All song data in data/songs.csv is
fictional and the feature values are illustrative, not real audio measurements.
"""

import csv
import math
import warnings
from dataclasses import asdict, dataclass, fields, is_dataclass
from numbers import Real
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REQUIRED_COLUMNS = (
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
)

# Valid (low, high) range for every numeric song column. Used by the CSV loader,
# the scorer and the preference validator so they all agree on what "valid" means.
FEATURE_RANGES: Dict[str, Tuple[float, float]] = {
    "energy": (0.0, 1.0),
    "valence": (0.0, 1.0),
    "danceability": (0.0, 1.0),
    "acousticness": (0.0, 1.0),
    "tempo_bpm": (1.0, 300.0),
}


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "Song":
        """Build a Song from a dict such as the ones load_songs() returns."""
        return cls(**{f.name: row[f.name] for f in fields(cls) if f.name in row})


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py

    The first four fields are the starter profile. The target_* fields are
    optional extra tastes; None means "no preference", so they add nothing to a
    song's score.
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    target_valence: Optional[float] = None
    target_danceability: Optional[float] = None
    target_tempo_bpm: Optional[float] = None

    def to_prefs(self) -> Dict[str, Any]:
        """Convert to the dict format the functional interface uses."""
        prefs = {
            "genre": self.favorite_genre,
            "mood": self.favorite_mood,
            "energy": self.target_energy,
            "likes_acoustic": self.likes_acoustic,
            "valence": self.target_valence,
            "danceability": self.target_danceability,
            "tempo_bpm": self.target_tempo_bpm,
        }
        return {key: value for key, value in prefs.items() if value is not None}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoringWeights:
    """
    Maximum points each feature can add to a song's score.

    genre and mood are all-or-nothing (exact match earns the full weight). The
    numeric features earn weight * similarity, where similarity is 1.0 for a
    perfect match and falls linearly to 0.0 as the song moves away from the
    user's target. acousticness is used only when the user states a taste for
    acoustic (or non-acoustic) music; valence, danceability and tempo only when
    the user gives a target for them.
    """
    genre: float = 2.0
    mood: float = 1.5
    energy: float = 2.0
    acousticness: float = 0.5
    valence: float = 0.5
    danceability: float = 0.5
    tempo: float = 0.5

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if not _is_real(value) or value < 0:
                raise ValueError(f"weight '{f.name}' must be a finite number >= 0, got {value!r}")


@dataclass(frozen=True)
class _Closeness:
    """A numeric feature scored by how close the song is to the user's target."""
    pref: str       # key in the user's preference dict
    column: str     # key in the song
    weight: str     # ScoringWeights attribute holding its weight
    label: str      # word used in explanations
    span: float     # distance from the target at which similarity hits 0
    digits: int     # decimals shown in explanations

    @property
    def low_high(self) -> Tuple[float, float]:
        return FEATURE_RANGES[self.column]


_CLOSENESS_FEATURES: Tuple[_Closeness, ...] = (
    _Closeness("energy", "energy", "energy", "energy", 1.0, 2),
    _Closeness("valence", "valence", "valence", "valence", 1.0, 2),
    _Closeness("danceability", "danceability", "danceability", "danceability", 1.0, 2),
    _Closeness("tempo_bpm", "tempo_bpm", "tempo", "tempo", 60.0, 0),
)

_TEXT_PREFS = ("genre", "mood")
_ALLOWED_PREFS = frozenset(_TEXT_PREFS) | {"likes_acoustic"} | {c.pref for c in _CLOSENESS_FEATURES}


@dataclass(frozen=True)
class ScoreComponent:
    """One line of a score: what was rewarded (or penalized) and by how much."""
    name: str
    points: float
    label: str

    @property
    def reason(self) -> str:
        return f"{self.label} ({self.points:+.2f})"


@dataclass(frozen=True)
class ScoreBreakdown:
    """A song's score together with the exact components that add up to it."""
    components: Tuple[ScoreComponent, ...]

    @property
    def total(self) -> float:
        return sum(c.points for c in self.components)

    @property
    def reasons(self) -> List[str]:
        if not self.components:
            return ["no preference matched (+0.00)"]
        return [c.reason for c in self.components]


@dataclass(frozen=True)
class Recommendation:
    """A ranked result. `score` is final; `reasons` explain every point in it."""
    song: Any
    score: float
    reasons: Tuple[str, ...]

    @property
    def explanation(self) -> str:
        return "; ".join(self.reasons)


def _is_real(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def _norm(value: Any) -> Optional[str]:
    return value.strip().casefold() if isinstance(value, str) and value.strip() else None


def _number(value: Any, low: float, high: float) -> Optional[float]:
    """Return value as a float if it is a finite number in [low, high], else None."""
    if _is_real(value) and low <= value <= high:
        return float(value)
    return None


def _as_mapping(song: Any) -> Mapping[str, Any]:
    if isinstance(song, Mapping):
        return song
    if is_dataclass(song) and not isinstance(song, type):
        return asdict(song)
    raise TypeError(f"song must be a dict or a Song, got {type(song).__name__}")


def validate_prefs(user_prefs: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Check a user preference dict and return a cleaned copy.

    Accepted keys: genre, mood (non-empty text), likes_acoustic (bool), and the
    numeric targets energy / valence / danceability (0-1) and tempo_bpm (1-300).
    A value of None means "not specified". Unknown keys, out-of-range numbers and
    an empty profile raise ValueError rather than silently scoring nonsense.
    """
    if not isinstance(user_prefs, Mapping):
        raise ValueError(f"user_prefs must be a dict, got {type(user_prefs).__name__}")
    unknown = sorted(str(key) for key in user_prefs if key not in _ALLOWED_PREFS)
    if unknown:
        raise ValueError(f"unknown preference(s): {', '.join(unknown)}")

    clean: Dict[str, Any] = {}
    for key in _TEXT_PREFS:
        value = user_prefs.get(key)
        if value is None:
            continue
        if _norm(value) is None:
            raise ValueError(f"'{key}' must be a non-empty string, got {value!r}")
        clean[key] = _norm(value)

    likes = user_prefs.get("likes_acoustic")
    if likes is not None:
        if not isinstance(likes, bool):
            raise ValueError(f"'likes_acoustic' must be True or False, got {likes!r}")
        clean["likes_acoustic"] = likes

    for spec in _CLOSENESS_FEATURES:
        value = user_prefs.get(spec.pref)
        if value is None:
            continue
        low, high = spec.low_high
        if _number(value, low, high) is None:
            raise ValueError(f"'{spec.pref}' must be a number between {low:g} and {high:g}, got {value!r}")
        clean[spec.pref] = float(value)

    if not clean:
        raise ValueError("user_prefs contains no preferences to score against")
    return clean


def _breakdown(prefs: Mapping[str, Any], song: Any, weights: ScoringWeights) -> ScoreBreakdown:
    """The scoring rule. `prefs` must already be validated."""
    row = _as_mapping(song)
    parts: List[ScoreComponent] = []

    for key in _TEXT_PREFS:
        weight = getattr(weights, key)
        if key in prefs and weight > 0 and _norm(row.get(key)) == prefs[key]:
            parts.append(ScoreComponent(key, weight, f"{key} match: {row[key].strip()}"))

    for spec in _CLOSENESS_FEATURES:
        weight = getattr(weights, spec.weight)
        value = _number(row.get(spec.column), *spec.low_high)
        if spec.pref not in prefs or value is None or weight <= 0:
            continue
        target = prefs[spec.pref]
        points = weight * max(0.0, 1.0 - abs(value - target) / spec.span)
        if points > 0:
            d = spec.digits
            parts.append(ScoreComponent(
                spec.pref, points, f"{spec.label} {value:.{d}f} vs target {target:.{d}f}"))

    acoustic = _number(row.get("acousticness"), *FEATURE_RANGES["acousticness"])
    if "likes_acoustic" in prefs and acoustic is not None and weights.acousticness > 0:
        likes = prefs["likes_acoustic"]
        fit = acoustic if likes else 1.0 - acoustic
        points = weights.acousticness * fit
        if points > 0:
            taste = "acoustic" if likes else "non-acoustic"
            parts.append(ScoreComponent(
                "acousticness", points, f"acousticness {acoustic:.2f} suits a taste for {taste} music"))

    return ScoreBreakdown(tuple(parts))


def score_breakdown(user_prefs: Mapping[str, Any], song: Any,
                    weights: Optional[ScoringWeights] = None) -> ScoreBreakdown:
    """Score one song (a dict or a Song) and return the full breakdown."""
    return _breakdown(validate_prefs(user_prefs), song, weights or ScoringWeights())


def max_score(user_prefs: Mapping[str, Any], weights: Optional[ScoringWeights] = None) -> float:
    """The highest score a song could earn for these preferences (a perfect match)."""
    prefs = validate_prefs(user_prefs)
    weights = weights or ScoringWeights()
    total = sum(getattr(weights, key) for key in _TEXT_PREFS if key in prefs)
    total += sum(getattr(weights, c.weight) for c in _CLOSENESS_FEATURES if c.pref in prefs)
    if "likes_acoustic" in prefs:
        total += weights.acousticness
    return total


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def _check_k(k: Any) -> int:
    if not isinstance(k, int) or isinstance(k, bool) or k < 0:
        raise ValueError(f"k must be a non-negative integer, got {k!r}")
    return k


def _tie_key(song: Any) -> Tuple:
    """Deterministic tie-break: lower id first, then title, so input order never matters."""
    row = _as_mapping(song)
    song_id = row.get("id")
    id_key = (0, song_id, "") if isinstance(song_id, int) and not isinstance(song_id, bool) \
        else (1, 0, str(song_id))
    return (id_key, str(row.get("title", "")).casefold(), str(row.get("artist", "")).casefold())


def rank_songs(user_prefs: Mapping[str, Any], songs: Sequence[Any], k: int = 5,
               weights: Optional[ScoringWeights] = None) -> List[Recommendation]:
    """
    Score every song and return the best k as Recommendation objects, best first.

    Ties are broken by song id, so the result does not depend on input order.
    k=0 or an empty catalog gives []; k larger than the catalog gives every song.
    Invalid k or preferences raise ValueError.
    """
    k = _check_k(k)
    prefs = validate_prefs(user_prefs)
    weights = weights or ScoringWeights()

    scored = []
    for song in songs:
        breakdown = _breakdown(prefs, song, weights)
        scored.append(Recommendation(song, breakdown.total, tuple(breakdown.reasons)))
    scored.sort(key=lambda r: (-round(r.score, 9), _tie_key(r.song)))
    return scored[:k]


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song], weights: Optional[ScoringWeights] = None):
        self.songs = songs
        self.weights = weights or ScoringWeights()

    def recommend_with_details(self, user: UserProfile, k: int = 5) -> List[Recommendation]:
        """Ranked recommendations with final scores and reasons."""
        return rank_songs(user.to_prefs(), self.songs, k, self.weights)

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        return [rec.song for rec in self.recommend_with_details(user, k)]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        breakdown = score_breakdown(user.to_prefs(), song, self.weights)
        return f"{song.title} by {song.artist}: score {breakdown.total:.2f} = " + "; ".join(breakdown.reasons)


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def _parse_song_row(row: Mapping[str, Optional[str]]) -> Dict[str, Any]:
    """Convert one CSV row to a typed dict, raising ValueError describing the first problem."""
    if None in row:
        raise ValueError("row has more values than the header has columns")

    song: Dict[str, Any] = {}
    try:
        song["id"] = int((row.get("id") or "").strip())
    except ValueError:
        raise ValueError(f"id must be an integer, got {row.get('id')!r}") from None
    if song["id"] < 1:
        raise ValueError(f"id must be positive, got {song['id']}")

    for column in ("title", "artist", "genre", "mood"):
        text = (row.get(column) or "").strip()
        if not text:
            raise ValueError(f"missing value for '{column}'")
        song[column] = text

    for column, (low, high) in FEATURE_RANGES.items():
        raw = (row.get(column) or "").strip()
        try:
            number = float(raw)
        except ValueError:
            raise ValueError(f"'{column}' must be a number, got {raw!r}") from None
        if _number(number, low, high) is None:
            raise ValueError(f"'{column}' must be between {low:g} and {high:g}, got {raw!r}")
        song[column] = number
    return song


def load_songs(csv_path: str, strict: bool = True) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py

    Returns one dict per song with numeric columns converted (id to int, the rest
    to float). A missing file raises FileNotFoundError; a missing header column or
    unreadable CSV raises ValueError. A bad row (non-numeric or out-of-range value,
    blank text, duplicate id) raises ValueError naming the line when strict=True;
    with strict=False the row is skipped and a warning is issued instead. A CSV
    with a header but no rows is a valid, empty catalog.
    """
    songs: List[Dict] = []
    seen_ids = set()
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        try:
            header = [name.strip() for name in (reader.fieldnames or [])]
            reader.fieldnames = header
            missing = [c for c in REQUIRED_COLUMNS if c not in header]
            if missing:
                raise ValueError(f"{csv_path}: missing required column(s): {', '.join(missing)}")
            if len(set(header)) != len(header):
                raise ValueError(f"{csv_path}: duplicate column names in header")

            for row in reader:
                try:
                    song = _parse_song_row(row)
                    if song["id"] in seen_ids:
                        raise ValueError(f"duplicate id {song['id']}")
                except ValueError as err:
                    message = f"{csv_path}, line {reader.line_num}: {err}"
                    if strict:
                        raise ValueError(message) from None
                    warnings.warn(f"skipping row - {message}")
                    continue
                seen_ids.add(song["id"])
                songs.append(song)
        except csv.Error as err:
            raise ValueError(f"{csv_path}: unreadable CSV ({err})") from None
    return songs


def score_song(user_prefs: Dict, song: Dict,
               weights: Optional[ScoringWeights] = None) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py

    Returns (score, reasons). Each reason names a feature that earned points and
    shows the exact points, and the points listed add up to the score.
    """
    breakdown = score_breakdown(user_prefs, song, weights)
    return breakdown.total, breakdown.reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5,
                    weights: Optional[ScoringWeights] = None) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py

    Returns [(song_dict, score, explanation_string), ...], best first.
    """
    return [(rec.song, rec.score, rec.explanation)
            for rec in rank_songs(user_prefs, songs, k, weights)]
