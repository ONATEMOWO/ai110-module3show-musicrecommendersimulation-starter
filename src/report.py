"""
Plain-text report formatting for recommendation results (standard library only).

Two layouts, chosen by terminal width:
- wide (width >= WIDE_LAYOUT_MIN_WIDTH): a table with rank, song, artist, score and
  the scoring reasons, each cell word-wrapped so long titles never break the grid
- compact (narrower): one block per song, which stays readable on narrow terminals
"""

import textwrap
from typing import List, Optional, Sequence

from src.recommender import Recommendation

MIN_WIDTH = 30
WIDE_LAYOUT_MIN_WIDTH = 76


def _wrap(text: str, width: int, subsequent_indent: str = "") -> List[str]:
    """Wrap text to at most `width` characters per line, splitting over-long words."""
    lines = textwrap.wrap(str(text), width=width, subsequent_indent=subsequent_indent,
                          break_long_words=True, break_on_hyphens=False)
    return lines or [""]


def _join_row(cells: Sequence[str], widths: Sequence[int], align: Sequence[str]) -> str:
    padded = [cell.rjust(w) if how == "r" else cell.ljust(w)
              for cell, w, how in zip(cells, widths, align)]
    return " | ".join(padded).rstrip()


def _format_wide(recs: Sequence[Recommendation], width: int) -> str:
    scores = [f"{rec.score:.2f}" for rec in recs]
    rank_w = max(1, len(str(len(recs))))
    score_w = max(5, *(len(text) for text in scores))
    free = width - rank_w - score_w - 3 * 4          # four " | " separators
    song_w = max(12, free * 26 // 100)
    artist_w = max(10, free * 20 // 100)
    why_w = max(12, free - song_w - artist_w)
    widths = (rank_w, song_w, artist_w, score_w, why_w)
    align = ("r", "l", "l", "r", "l")

    rule = "-+-".join("-" * w for w in widths)
    lines = [_join_row(("#", "Song", "Artist", "Score", "Why (points)"), widths, align), rule]
    for place, (rec, score) in enumerate(zip(recs, scores), start=1):
        song = rec.song
        columns = [
            [str(place)],
            _wrap(song["title"], song_w),
            _wrap(song["artist"], artist_w),
            [score],
            [line for reason in rec.reasons for line in _wrap(reason, why_w, "  ")],
        ]
        for i in range(max(len(column) for column in columns)):
            cells = [column[i] if i < len(column) else "" for column in columns]
            lines.append(_join_row(cells, widths, align))
        lines.append(rule)
    return "\n".join(lines)


def _format_compact(recs: Sequence[Recommendation], width: int) -> str:
    lines: List[str] = []
    for place, rec in enumerate(recs, start=1):
        song = rec.song
        head = f"{place}. {song['title']} by {song['artist']} (score {rec.score:.2f})"
        lines.extend(textwrap.wrap(head, width=width, subsequent_indent="   ",
                                   break_long_words=True, break_on_hyphens=False))
        for reason in rec.reasons:
            lines.extend(textwrap.wrap(reason, width=width, initial_indent="   - ",
                                       subsequent_indent="     ",
                                       break_long_words=True, break_on_hyphens=False))
    return "\n".join(lines)


def format_recommendation_table(recs: Sequence[Recommendation], width: int = 100) -> str:
    """
    Render ranked recommendations as text no wider than `width` (minimum MIN_WIDTH).

    Shows rank, song, artist, final score and every scoring reason. Scores shown are
    final scores, so any variety penalty is visible both in the score and as a
    negative reason.
    """
    width = max(MIN_WIDTH, int(width))
    if not recs:
        return "(no recommendations)"
    if width >= WIDE_LAYOUT_MIN_WIDTH:
        return _format_wide(recs, width)
    return _format_compact(recs, width)


def format_recommendation_list(recs: Sequence[Recommendation], width: Optional[int] = None) -> str:
    """
    The simple numbered list: song, artist, score, then one bullet per reason.
    Lines are wrapped to `width` when given (minimum MIN_WIDTH).
    """
    wrap = max(MIN_WIDTH, int(width)) if width is not None else None

    def emit(text: str, initial: str = "", subsequent: str = "") -> List[str]:
        if wrap is None:
            return [initial + text]
        return textwrap.wrap(text, width=wrap, initial_indent=initial, subsequent_indent=subsequent,
                             break_long_words=True, break_on_hyphens=False)

    lines: List[str] = []
    for place, rec in enumerate(recs, start=1):
        lines.extend(emit(f"{place}. {rec.song['title']} by {rec.song['artist']} - score {rec.score:.2f}",
                          subsequent="   "))
        for reason in rec.reasons:
            lines.extend(emit(reason, "     - ", "       "))
    return "\n".join(lines) if lines else "(no recommendations)"
