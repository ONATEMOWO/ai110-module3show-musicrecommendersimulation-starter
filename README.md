# 🎵 Music Recommender Simulation

## Project Summary

This project is a small, fully transparent music recommender. It reads a catalog of songs from `data/songs.csv`, compares each song to a listener's stated taste, and returns the top matches, with the exact reasons (and points) behind every score.

It is a **content-based** recommender: it never looks at what other people listened to. It only compares the *features of each song* with the *preferences of one listener*. There is no training step and no learned model. Everything is a hand-written scoring rule you can read in [src/recommender.py](src/recommender.py).

---

## How The System Works

### Two ways recommenders work

- **Content-based filtering** recommends songs whose *features* (genre, mood, energy, tempo, ...) match what a listener says they like. Spotify-style "more songs that sound like this" is the idea. Strength: it works for a brand-new user with no history and it can explain itself. Weakness: it only ever finds more of what you already described, and it can't tell that a song is *good*.
- **Collaborative filtering** ignores song features. It looks at the *behavior of many listeners* (plays, skips, likes, playlists) and recommends what similar listeners enjoyed: "people who liked A and B also liked C". Strength: it can surface songs you could not have described in advance. Weakness: it needs lots of listening data and does poorly on new songs or new users (the "cold start" problem).

### Why this project is content-based and not "machine learning"

There are no listeners in this project's data, only songs, so collaborative filtering is not possible. And nothing here is *trained*: the weights (genre 2.0, mood 1.5, energy 2.0, ...) were chosen by hand and are never adjusted from data. A trained model would learn those numbers from many examples of what people actually liked. This simulation is a rule-based system that borrows the content-based *idea*, which makes it small enough to read and fully explain.

### The four pieces

| Piece | What it is here |
| --- | --- |
| **Song data** | One row per song in `data/songs.csv`: `id, title, artist, genre, mood, energy, tempo_bpm, valence, danceability, acousticness`. Loaded by `load_songs`. |
| **User taste** | A small dict (functional interface) or a `UserProfile` (OOP interface): favorite `genre`, favorite `mood`, a `target energy` between 0 and 1, and whether they like acoustic music. Optional targets for valence, danceability and tempo. |
| **Scoring** | `score_song` turns one song + one taste profile into a number plus a list of reasons. |
| **Ranking** | `recommend_songs` scores *every* song, sorts best-first, and keeps the top `k`. Ties are broken by song `id`, so the result never depends on file order. |

The OOP classes (`Song`, `UserProfile`, `Recommender`) and the functional functions (`load_songs`, `score_song`, `recommend_songs`) are two front doors to the **same** scoring code (`score_breakdown`) and ranking code (`rank_songs`), so they always agree.

### The scoring rule

```
score = 2.0 × (genre == favorite genre)                 # exact match, else 0
      + 1.5 × (mood  == favorite mood)                  # exact match, else 0
      + 2.0 × (1 − |song energy − target energy|)       # closeness, not "more is better"
      + 0.5 × acousticness            if the user likes acoustic music
        0.5 × (1 − acousticness)      if the user prefers non-acoustic music
      + 0.5 × (1 − |song valence − target valence|)             only if the user set a valence target
      + 0.5 × (1 − |song danceability − target danceability|)   only if the user set a danceability target
      + 0.5 × max(0, 1 − |song tempo − target tempo| / 60 bpm)  only if the user set a tempo target
```

With genre, mood, energy and an acoustic preference set, the maximum possible score is **6.0**. Every term that earns points is listed in the explanation, for example `energy 0.82 vs target 0.85 (+1.94)`, and the listed points add up to the score.

**Why these choices?**

- *Genre is worth the most (2.0)* because it is the broadest statement of taste: a listener who wants lofi rarely wants metal, however well the energy lines up. But it is capped at the same value as an exact energy match, so a song can't win on genre alone.
- *Mood is worth 1.5* because it separates songs inside a genre (chill lofi vs. focused lofi) but is a softer signal than genre.
- *Energy is scored by closeness, not size.* A relaxed listener (target 0.3) should get a 0.35-energy track before a 0.95-energy one. The score falls in a straight line with distance, which is easy to explain: "0.1 away costs 0.2 points".
- *Acousticness, valence, danceability and tempo are small (0.5) tie-breakers.* They only count when the listener supplies them, so a profile that doesn't mention tempo is never judged on tempo.
- *Genre and mood are all-or-nothing.* `"indie pop"` does **not** count as `"pop"`. That is simple and predictable, but see the bias section below.

### Potential genre and mood bias

- **Genre gatekeeping.** Because an exact genre match is worth 2.0 points, songs in the listener's genre get a big head start, and near-neighbors (indie pop for a pop fan, synthwave for an electronic fan) get nothing for being similar. A listener can be locked into one genre's slice of the catalog.
- **Mood labels are one word chosen by whoever built the data.** "Chill" and "relaxed" are close in meaning but score as a complete mismatch.
- **The catalog decides who gets served well.** Genres with one song can only ever give a listener one genre match; popular-looking genres with several songs fill the top five with real matches. The numbers behind this are in the evaluation sections.
- **Energy is treated as a single number.** A listener whose genre and energy conflict (for example a classical fan who wants energy 0.9) is pulled in two directions; the rule just adds the pulls together.

---

## Data

`data/songs.csv` holds 30 songs: the 10 starter songs (ids 1-10, unchanged) plus 20 added for this project (ids 11-30) to cover more genres, moods and energy levels.

**All songs, artists and feature values are fictional and illustrative.** Titles and artists are invented, and the numbers (energy, tempo, valence, danceability, acousticness) were written by hand to be plausible. They are *not* measurements from Spotify or any other audio-analysis service, and any resemblance to a real artist is coincidence.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies (the recommender itself only uses the Python standard library; `pytest` is needed to run the tests):

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app from the project root:

   ```bash
   python3 -m src.main
   ```

### Running Tests

```bash
python3 -m pytest
```
