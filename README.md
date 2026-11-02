# 🎵 Music Recommender Simulation

## Project Summary

This project is a small, fully transparent music recommender. It reads a catalog of 30 songs from `data/songs.csv`, compares each song to a listener's stated taste, and returns the top matches, with the exact reasons (and points) behind every score.

It is a **content-based** recommender: it never looks at what other people listened to. It only compares the *features of each song* with the *preferences of one listener*. There is no training step and no learned model. Everything is a hand-written scoring rule you can read in [src/recommender.py](src/recommender.py).

On top of the required core, four stretch features are implemented and tested:

1. **Five extra song attributes** (popularity, release decade, instrumentalness, speechiness, liveness) that listeners can optionally score against.
2. **Ranking modes** (`balanced`, `genre-first`, `mood-energy`) selectable from the command line.
3. **Variety reranking** that discourages repeating an artist or genre, off by default so the baseline stays comparable.
4. **A readable table** (standard library only) that adapts to narrow terminals.

Everything in the *baseline* sections below (the four-profile output and the weight experiment) uses the default settings: `balanced` mode, variety penalty off. The stretch sections say explicitly when a result comes from an experimental setting.

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
| **Song data** | One row per song in `data/songs.csv`. Ten starter columns (`id, title, artist, genre, mood, energy, tempo_bpm, valence, danceability, acousticness`) plus five extra attributes (`popularity, release_decade, instrumentalness, speechiness, liveness`). Loaded and validated by `load_songs`. |
| **User taste** | A small dict (functional interface) or a `UserProfile` (OOP interface): favorite `genre`, favorite `mood`, a `target energy` between 0 and 1, and whether they like acoustic music. Every other target (valence, danceability, tempo, popularity, decade, instrumentalness, speechiness, liveness) is optional. |
| **Scoring** | `score_song` turns one song + one taste profile into a number plus a list of reasons. |
| **Ranking** | `recommend_songs` scores *every* song, sorts best-first, and keeps the top `k`. Ties are broken by song `id`, so the result never depends on file order. Optionally reranked for variety. |

The OOP classes (`Song`, `UserProfile`, `Recommender`) and the functional functions (`load_songs`, `score_song`, `recommend_songs`) are two front doors to the **same** scoring code (`score_breakdown`) and ranking code (`rank_songs`), so they always agree. Tests compare them directly, in every mode and with variety reranking on.

### The scoring rule

```
score = 2.0 × (genre == favorite genre)                 # exact match, else 0
      + 1.5 × (mood  == favorite mood)                  # exact match, else 0
      + 2.0 × (1 − |song energy − target energy|)       # closeness, not "more is better"
      + 0.5 × acousticness            if the user likes acoustic music
        0.5 × (1 − acousticness)      if the user prefers non-acoustic music

      # each of these counts ONLY if the user set that target (weight 0.5 each):
      + 0.5 × (1 − |song valence − target valence|)
      + 0.5 × (1 − |song danceability − target danceability|)
      + 0.5 × max(0, 1 − |song tempo − target tempo| / 60 bpm)
      + 0.5 × max(0, 1 − |song popularity − target popularity| / 50)
      + 0.5 × max(0, 1 − |song release decade − target decade| / 50 years)
      + 0.5 × (1 − |song instrumentalness − target instrumentalness|)
      + 0.5 × max(0, 1 − |song speechiness − target speechiness| / 0.5)
      + 0.5 × max(0, 1 − |song liveness − target liveness| / 0.5)

      − variety penalty               only if reranking is switched on (see Stretch 3)
```

With genre, mood, energy and an acoustic preference set, the maximum possible score is **6.0** in the default mode. Every term that earns points (or loses them to a variety penalty) is listed in the explanation, for example `energy 0.82 vs target 0.85 (+1.94)`, and the listed points add up to the score.

**Why these choices?**

- *Genre is worth the most (2.0)* because it is the broadest statement of taste: a listener who wants lofi rarely wants metal, however well the energy lines up. But it is capped at the same value as an exact energy match, so a song can't win on genre alone.
- *Mood is worth 1.5* because it separates songs inside a genre (chill lofi vs. focused lofi) but is a softer signal than genre.
- *Energy is scored by closeness, not size.* A relaxed listener (target 0.3) should get a 0.35-energy track before a 0.95-energy one. The score falls in a straight line with distance, which is easy to explain: "0.1 away costs 0.2 points".
- *Everything else is a small (0.5) nudge and strictly optional.* A profile that doesn't mention tempo or decade is never judged on them, and no default target is ever invented for a listener who didn't give one. The "span" in each formula (60 bpm, 50 popularity points, 50 years, 0.5) is roughly the spread of that column in the catalog: the distance at which a song counts as completely different.
- *Genre and mood are all-or-nothing.* `"indie pop"` does **not** count as `"pop"`. That is simple and predictable, but see the bias section below.

### Potential genre and mood bias

- **Genre gatekeeping.** Because an exact genre match is worth 2.0 points, songs in the listener's genre get a big head start, and near-neighbors (indie pop for a pop fan, synthwave for an electronic fan) get nothing for being similar. A listener can be locked into one genre's slice of the catalog.
- **Mood labels are one word chosen by whoever built the data.** "Chill" and "relaxed" are close in meaning but score as a complete mismatch.
- **The catalog decides who gets served well.** Genres with one song can only ever give a listener one genre match; popular-looking genres with several songs fill the top five with real matches. The numbers behind this are in the evaluation sections.
- **Energy is treated as a single number.** A listener whose genre and energy conflict (for example a classical fan who wants energy 0.9) is pulled in two directions; the rule just adds the pulls together.

---

## Data

`data/songs.csv` holds 30 songs: the 10 starter songs (ids 1-10, with their original ten columns unchanged) plus 20 added for this project (ids 11-30) to cover more genres, moods and energy levels. Five extra columns were then added for every song (Stretch 1).

**All songs, artists and feature values are fictional and illustrative.** Titles and artists are invented, and every number (energy, tempo, valence, danceability, acousticness, popularity, release decade, instrumentalness, speechiness, liveness) was written by hand to be plausible. They are *not* measurements from Spotify or any other audio-analysis service, and any resemblance to a real artist is coincidence.

Catalog counts (from `python3 -m src.experiments`):

<!-- OUTPUT: python3 -m src.experiments | section Catalog counts -->
```text
Songs: 30, artists: 24
Genres (19): pop 5, lofi 3, classical 2, hip hop 2, jazz 2, rock 2, synthwave 2, ambient 1, blues 1, country 1, electronic 1, folk 1, indie pop 1, latin 1, metal 1, punk 1, r&b 1, reggae 1, soul 1
Genres with exactly one song: 12 of 19
Moods (14): chill 4, energetic 4, happy 4, relaxed 4, romantic 3, angry 2, intense 2, confident 1, focused 1, melancholy 1, moody 1, nostalgic 1, sad 1, uplifting 1
Energy bands: energy < 0.40: 8, 0.40 - 0.69: 8, energy >= 0.70: 14
Release decades: 1970s 3, 1980s 2, 1990s 2, 2000s 5, 2010s 8, 2020s 10
Popularity: min 28, max 88, 9 songs at 70 or above
instrumentalness: min 0.00, max 0.97, 11 songs at 0.50 or above
speechiness: min 0.03, max 0.34, 0 songs at 0.50 or above
liveness: min 0.07, max 0.62, 3 songs at 0.50 or above
```

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

### Command line options

```bash
python3 -m src.main                            # baseline: balanced mode, variety penalty off, table layout
python3 -m src.main --mode genre-first         # ranking strategy: balanced | genre-first | mood-energy
python3 -m src.main --mode mood-energy
python3 -m src.main --artist-penalty 0.75      # rerank so one artist doesn't fill the list
python3 -m src.main --genre-penalty 0.5        # ... or one genre (both can be combined)
python3 -m src.main --format list --width 60   # plain list layout; limit line width (default 100, minimum 30)
python3 -m src.main --help
```

### Running Tests

```bash
python3 -m pytest
```

The suite has **210 tests** across [tests/test_recommender.py](tests/test_recommender.py) (the two original starter tests, unchanged), [tests/test_data.py](tests/test_data.py), [tests/test_scoring.py](tests/test_scoring.py), [tests/test_stretch.py](tests/test_stretch.py) and [tests/test_report.py](tests/test_report.py).

### Reproducing the evaluation

Every number and output block in this README was produced by these commands (nothing is typed in by hand):

```bash
python3 -m src.main          # the four listener profiles
python3 -m src.experiments   # catalog counts, weight sensitivity, profile comparison, stretch demos
```

---

## Sample Recommendation Output (baseline)

Output of `python3 -m src.main`: balanced mode, variety penalty off, 30 songs, four listener profiles, top 5 each. A perfect match would score 6.00 for these profiles. Each line under "Why" is a real term in the score, and the points add up to the score shown.

<details>
<summary>Full output (click to expand)</summary>

<!-- OUTPUT: python3 -m src.main -->
```text
Loaded 30 songs from data/songs.csv
Mode: balanced - genre, mood and energy all count (default)
Variety penalty: off (baseline: ranked by score alone)

=== Happy high-energy pop listener ===
Preferences: genre=pop, mood=happy, energy=0.85, likes_acoustic=False
Top 5 (a perfect match would score 6.00):
# | Song                  | Artist           | Score | Why (points)
--+-----------------------+------------------+-------+----------------------------------------------
1 | Sunrise City          | Neon Echo        |  5.85 | genre match: pop (+2.00)
  |                       |                  |       | mood match: happy (+1.50)
  |                       |                  |       | energy 0.82 vs target 0.85 (+1.94)
  |                       |                  |       | acousticness 0.18, wants non-acoustic (+0.41)
--+-----------------------+------------------+-------+----------------------------------------------
2 | Golden Hour Parade    | Cherry Meridian  |  5.79 | genre match: pop (+2.00)
  |                       |                  |       | mood match: happy (+1.50)
  |                       |                  |       | energy 0.78 vs target 0.85 (+1.86)
  |                       |                  |       | acousticness 0.15, wants non-acoustic (+0.42)
--+-----------------------+------------------+-------+----------------------------------------------
3 | Gym Hero              | Max Pulse        |  4.31 | genre match: pop (+2.00)
  |                       |                  |       | energy 0.93 vs target 0.85 (+1.84)
  |                       |                  |       | acousticness 0.05, wants non-acoustic (+0.47)
--+-----------------------+------------------+-------+----------------------------------------------
4 | Hyperdrive Heartbeat  | Max Pulse        |  4.28 | genre match: pop (+2.00)
  |                       |                  |       | energy 0.95 vs target 0.85 (+1.80)
  |                       |                  |       | acousticness 0.04, wants non-acoustic (+0.48)
--+-----------------------+------------------+-------+----------------------------------------------
5 | Heartbeat Static      | Velvet Circuit   |  3.89 | genre match: pop (+2.00)
  |                       |                  |       | energy 0.62 vs target 0.85 (+1.54)
  |                       |                  |       | acousticness 0.30, wants non-acoustic (+0.35)
--+-----------------------+------------------+-------+----------------------------------------------

=== Relaxed low-energy lofi listener ===
Preferences: genre=lofi, mood=chill, energy=0.35, likes_acoustic=True
Top 5 (a perfect match would score 6.00):
# | Song                  | Artist           | Score | Why (points)
--+-----------------------+------------------+-------+----------------------------------------------
1 | Library Rain          | Paper Lanterns   |  5.93 | genre match: lofi (+2.00)
  |                       |                  |       | mood match: chill (+1.50)
  |                       |                  |       | energy 0.35 vs target 0.35 (+2.00)
  |                       |                  |       | acousticness 0.86, wants acoustic (+0.43)
--+-----------------------+------------------+-------+----------------------------------------------
2 | Midnight Coding       | LoRoom           |  5.71 | genre match: lofi (+2.00)
  |                       |                  |       | mood match: chill (+1.50)
  |                       |                  |       | energy 0.42 vs target 0.35 (+1.86)
  |                       |                  |       | acousticness 0.71, wants acoustic (+0.35)
--+-----------------------+------------------+-------+----------------------------------------------
3 | Focus Flow            | LoRoom           |  4.29 | genre match: lofi (+2.00)
  |                       |                  |       | energy 0.40 vs target 0.35 (+1.90)
  |                       |                  |       | acousticness 0.78, wants acoustic (+0.39)
--+-----------------------+------------------+-------+----------------------------------------------
4 | Spacewalk Thoughts    | Orbit Bloom      |  3.82 | mood match: chill (+1.50)
  |                       |                  |       | energy 0.28 vs target 0.35 (+1.86)
  |                       |                  |       | acousticness 0.92, wants acoustic (+0.46)
--+-----------------------+------------------+-------+----------------------------------------------
5 | Late Bus Home         | Marlow Vance     |  3.44 | mood match: chill (+1.50)
  |                       |                  |       | energy 0.48 vs target 0.35 (+1.74)
  |                       |                  |       | acousticness 0.40, wants acoustic (+0.20)
--+-----------------------+------------------+-------+----------------------------------------------

=== Intense rock/workout listener ===
Preferences: genre=rock, mood=intense, energy=0.92, likes_acoustic=False
Top 5 (a perfect match would score 6.00):
# | Song                  | Artist           | Score | Why (points)
--+-----------------------+------------------+-------+----------------------------------------------
1 | Storm Runner          | Voltline         |  5.93 | genre match: rock (+2.00)
  |                       |                  |       | mood match: intense (+1.50)
  |                       |                  |       | energy 0.91 vs target 0.92 (+1.98)
  |                       |                  |       | acousticness 0.10, wants non-acoustic (+0.45)
--+-----------------------+------------------+-------+----------------------------------------------
2 | Rust Belt Anthem      | The Gravel Roads |  4.26 | genre match: rock (+2.00)
  |                       |                  |       | energy 0.84 vs target 0.92 (+1.84)
  |                       |                  |       | acousticness 0.15, wants non-acoustic (+0.42)
--+-----------------------+------------------+-------+----------------------------------------------
3 | Gym Hero              | Max Pulse        |  3.96 | mood match: intense (+1.50)
  |                       |                  |       | energy 0.93 vs target 0.92 (+1.98)
  |                       |                  |       | acousticness 0.05, wants non-acoustic (+0.47)
--+-----------------------+------------------+-------+----------------------------------------------
4 | Laser Garden          | Pulse Arcade     |  2.43 | energy 0.90 vs target 0.92 (+1.96)
  |                       |                  |       | acousticness 0.06, wants non-acoustic (+0.47)
--+-----------------------+------------------+-------+----------------------------------------------
5 | Basement Riot         | Static Youth     |  2.42 | energy 0.94 vs target 0.92 (+1.96)
  |                       |                  |       | acousticness 0.08, wants non-acoustic (+0.46)
--+-----------------------+------------------+-------+----------------------------------------------

=== Edge case: high-energy classical fan (conflicting tastes) ===
Preferences: genre=classical, mood=melancholy, energy=0.9, likes_acoustic=True
Top 5 (a perfect match would score 6.00):
# | Song                  | Artist           | Score | Why (points)
--+-----------------------+------------------+-------+----------------------------------------------
1 | Moonlit Sonata Sketch | Aria Voss        |  4.54 | genre match: classical (+2.00)
  |                       |                  |       | mood match: melancholy (+1.50)
  |                       |                  |       | energy 0.18 vs target 0.90 (+0.56)
  |                       |                  |       | acousticness 0.97, wants acoustic (+0.48)
--+-----------------------+------------------+-------+----------------------------------------------
2 | Glass Cathedral       | Aria Voss        |  3.12 | genre match: classical (+2.00)
  |                       |                  |       | energy 0.22 vs target 0.90 (+0.64)
  |                       |                  |       | acousticness 0.96, wants acoustic (+0.48)
--+-----------------------+------------------+-------+----------------------------------------------
3 | Storm Runner          | Voltline         |  2.03 | energy 0.91 vs target 0.90 (+1.98)
  |                       |                  |       | acousticness 0.10, wants acoustic (+0.05)
--+-----------------------+------------------+-------+----------------------------------------------
4 | Laser Garden          | Pulse Arcade     |  2.03 | energy 0.90 vs target 0.90 (+2.00)
  |                       |                  |       | acousticness 0.06, wants acoustic (+0.03)
--+-----------------------+------------------+-------+----------------------------------------------
5 | Gym Hero              | Max Pulse        |  1.96 | energy 0.93 vs target 0.90 (+1.94)
  |                       |                  |       | acousticness 0.05, wants acoustic (+0.03)
--+-----------------------+------------------+-------+----------------------------------------------
```

</details>

---

## Comparing the Profiles

The same scoring code gave four very different lists. `python3 -m src.experiments` summarizes how each top 5 was earned (baseline settings):

<!-- OUTPUT: python3 -m src.experiments | section Profile comparison -->
```text
Happy high-energy pop listener
  scores: 5.85, 5.79, 4.31, 4.28, 3.89  (max 6.00)
  genre matches: 5/5, mood matches: 2/5, neither: 0/5
  energy of top 5: 0.82, 0.78, 0.93, 0.95, 0.62 (target 0.85)
Relaxed low-energy lofi listener
  scores: 5.93, 5.71, 4.29, 3.82, 3.44  (max 6.00)
  genre matches: 3/5, mood matches: 4/5, neither: 0/5
  energy of top 5: 0.35, 0.42, 0.40, 0.28, 0.48 (target 0.35)
Intense rock/workout listener
  scores: 5.93, 4.26, 3.96, 2.43, 2.42  (max 6.00)
  genre matches: 2/5, mood matches: 2/5, neither: 2/5
  energy of top 5: 0.91, 0.84, 0.93, 0.90, 0.94 (target 0.92)
Edge case: high-energy classical fan (conflicting tastes)
  scores: 4.54, 3.12, 2.03, 2.03, 1.96  (max 6.00)
  genre matches: 2/5, mood matches: 1/5, neither: 3/5
  energy of top 5: 0.18, 0.22, 0.91, 0.90, 0.93 (target 0.90)
Songs in more than one profile's top 5: Gym Hero (3 profiles); Laser Garden (2 profiles); Storm Runner (2 profiles)
```

What the results show:

- **Happy high-energy pop listener.** The top two songs (`Sunrise City`, `Golden Hour Parade`) match genre *and* mood and have energy within 0.07 of the target, so they score 5.85 and 5.79. Slots 3-5 are pop but not happy (`Gym Hero` is intense, `Hyperdrive Heartbeat` is energetic, `Heartbeat Static` is romantic), so they score 1.5 to 2.0 points less than the top two. With 5 pop songs in the catalog, all five recommendations are pop.
- **Relaxed low-energy lofi listener.** Two lofi/chill songs score above 5.7. After that the catalog runs out of lofi songs that are chill: slot 3 (`Focus Flow`) is lofi but "focused", and slots 4-5 are not lofi at all (`Spacewalk Thoughts` is ambient/chill, `Late Bus Home` is hip hop/chill). Every song in the top 5 has energy 0.48 or lower, so the "closeness to target energy" rule is clearly working.
- **Intense rock/workout listener.** The catalog has only two rock songs, so the score falls from 5.93 (`Storm Runner`, matches everything) to 2.42 by slot 5. Slots 4-5 (`Laser Garden`, `Basement Riot`) match neither genre nor mood and are in the list purely because their energy is near 0.92. The pop song `Gym Hero` is #3 because it earns the mood match (intense) plus a near-perfect energy match.
- **Edge case: conflicting tastes (classical fan who wants energy 0.90).** The top two are the two classical songs even though their energy (0.18 and 0.22) is far from the 0.90 target. Genre plus mood is worth 3.5 points and the energy mismatch only costs about 1.4, so labels beat the number. The three songs that *do* match the energy (`Storm Runner`, `Laser Garden`, `Gym Hero`) score about 2.0. The rule adds the two pulls together; it does not look for a compromise.
- **Why the lists differ.** Only three songs appear in more than one profile's top 5 (`Gym Hero` in three, `Laser Garden` and `Storm Runner` in two), which is a direct result of different genre, mood and energy targets pulling toward different parts of the catalog. `Gym Hero` shows up repeatedly because it is high-energy and non-acoustic, which suits several of these listeners.

---

## Controlled Experiment: Changing the Weights

**Question:** how much does the top 5 depend on the hand-picked weights?

**Design:** the profile (Happy high-energy pop listener) and the 30-song catalog were held fixed. Starting from the baseline (genre 2.0, mood 1.5, energy 2.0), one weight at a time was halved and then doubled, with every other weight unchanged. Code: `weight_sensitivity` in [src/experiments.py](src/experiments.py).

| Change | Top 5 vs. baseline | What happened |
| --- | --- | --- |
| baseline | - | `Sunrise City`, `Golden Hour Parade`, `Gym Hero`, `Hyperdrive Heartbeat`, `Heartbeat Static` |
| genre x0.5 (1.00) | **changed** | `Fuego en la Calle` (latin/happy) and `Rooftop Lights` (indie pop/happy) replace `Hyperdrive Heartbeat` and `Heartbeat Static` |
| genre x2 (4.00) | same | identical songs and order; all scores rise by 2.0 |
| mood x0.5 (0.75) | same | identical songs and order |
| mood x2 (3.00) | **changed** | same two newcomers as genre x0.5; `Gym Hero` falls from #3 to #5 |
| energy x0.5 (1.00) | same | identical songs and order |
| energy x2 (4.00) | **changed** | `Fuego en la Calle` replaces `Heartbeat Static` at #5 |

Full output:

<details>
<summary>Full sensitivity output (click to expand)</summary>

<!-- OUTPUT: python3 -m src.experiments | section Weight sensitivity -->
```text
Profile: Happy high-energy pop listener
Preferences: {'genre': 'pop', 'mood': 'happy', 'energy': 0.85, 'likes_acoustic': False}
Songs: 30 (fixed)

[baseline (genre 2.0, mood 1.5, energy 2.0)] -> same top 5 in same order
  1. Sunrise City (pop/happy, energy 0.82) score 5.85
  2. Golden Hour Parade (pop/happy, energy 0.78) score 5.79
  3. Gym Hero (pop/intense, energy 0.93) score 4.31
  4. Hyperdrive Heartbeat (pop/energetic, energy 0.95) score 4.28
  5. Heartbeat Static (pop/romantic, energy 0.62) score 3.89

[genre x0.5 -> 1.00] -> top 5 changed (in: Fuego en la Calle, Rooftop Lights; out: Hyperdrive Heartbeat, Heartbeat Static)
  1. Sunrise City (pop/happy, energy 0.82) score 4.85
  2. Golden Hour Parade (pop/happy, energy 0.78) score 4.79
  3. Fuego en la Calle (latin/happy, energy 0.80) score 3.80
  4. Rooftop Lights (indie pop/happy, energy 0.76) score 3.65
  5. Gym Hero (pop/intense, energy 0.93) score 3.31

[genre x2   -> 4.00] -> same top 5 in same order
  1. Sunrise City (pop/happy, energy 0.82) score 7.85
  2. Golden Hour Parade (pop/happy, energy 0.78) score 7.79
  3. Gym Hero (pop/intense, energy 0.93) score 6.31
  4. Hyperdrive Heartbeat (pop/energetic, energy 0.95) score 6.28
  5. Heartbeat Static (pop/romantic, energy 0.62) score 5.89

[mood x0.5 -> 0.75] -> same top 5 in same order
  1. Sunrise City (pop/happy, energy 0.82) score 5.10
  2. Golden Hour Parade (pop/happy, energy 0.78) score 5.04
  3. Gym Hero (pop/intense, energy 0.93) score 4.31
  4. Hyperdrive Heartbeat (pop/energetic, energy 0.95) score 4.28
  5. Heartbeat Static (pop/romantic, energy 0.62) score 3.89

[mood x2   -> 3.00] -> top 5 changed (in: Fuego en la Calle, Rooftop Lights; out: Hyperdrive Heartbeat, Heartbeat Static)
  1. Sunrise City (pop/happy, energy 0.82) score 7.35
  2. Golden Hour Parade (pop/happy, energy 0.78) score 7.29
  3. Fuego en la Calle (latin/happy, energy 0.80) score 5.30
  4. Rooftop Lights (indie pop/happy, energy 0.76) score 5.15
  5. Gym Hero (pop/intense, energy 0.93) score 4.31

[energy x0.5 -> 1.00] -> same top 5 in same order
  1. Sunrise City (pop/happy, energy 0.82) score 4.88
  2. Golden Hour Parade (pop/happy, energy 0.78) score 4.86
  3. Gym Hero (pop/intense, energy 0.93) score 3.40
  4. Hyperdrive Heartbeat (pop/energetic, energy 0.95) score 3.38
  5. Heartbeat Static (pop/romantic, energy 0.62) score 3.12

[energy x2   -> 4.00] -> top 5 changed (in: Fuego en la Calle; out: Heartbeat Static)
  1. Sunrise City (pop/happy, energy 0.82) score 7.79
  2. Golden Hour Parade (pop/happy, energy 0.78) score 7.65
  3. Gym Hero (pop/intense, energy 0.93) score 6.15
  4. Hyperdrive Heartbeat (pop/energetic, energy 0.95) score 6.08
  5. Fuego en la Calle (latin/happy, energy 0.80) score 5.70
```

</details>

**What actually changed and why**

- `Sunrise City` and `Golden Hour Parade` are #1 and #2 in all seven settings. They match genre, mood and energy at once, so no single weight change can dislodge them.
- The only movement is in slots 3-5, and it comes from one tension: the baseline fills those slots with songs that match the *genre label* (pop) but not the mood or energy.
- **Surprising result:** doubling the genre weight changed *nothing* about the ranking. All five baseline picks were already pop, so a bigger genre weight just added the same 2.0 to each of them. The weight that looks most important only matters when other genres are competing.
- **Disappointing result:** the baseline's #5 is `Heartbeat Static`, a romantic pop song with energy 0.62 (0.23 below the target), while `Fuego en la Calle` (latin, happy, energy 0.80, a much better fit on mood and energy) is left out. It only gets in if genre is halved, mood is doubled, or energy is doubled. In other words, the fifth slot of the default list is decided by a single exact-label match.
- `Rooftop Lights` (indie pop, happy, energy 0.76) only enters when genre is halved or mood is doubled, and it never reaches the top two. Because the genre rule is exact-match, "indie pop" gets no credit for being close to "pop".

---

## Stretch Features

Every stretch feature is wired into the same core (`score_breakdown` / `rank_songs` in [src/recommender.py](src/recommender.py)), so the OOP and functional interfaces stay in agreement. In each subsection, "baseline" means the default settings and "experimental" means the feature switched on.

### Stretch 1: Five additional song attributes

**What:** five new columns appended after the starter's ten: `popularity` (0-100), `release_decade` (1970-2020), `instrumentalness`, `speechiness`, `liveness` (0-1), filled in for all 30 songs (illustrative values, not measurements).

**Code:**
- `OPTIONAL_COLUMNS`, `INTEGER_COLUMNS`, `FEATURE_RANGES` and `_parse_song_row` / `load_songs` in [src/recommender.py](src/recommender.py): the columns are optional in the file (a 10-column CSV still loads) but fully validated when present.
- `_CLOSENESS_FEATURES` and `ScoringWeights`: five new table rows and weights (0.5 each) feed the *same* scoring loop as energy and valence. Users opt in through the dict keys `popularity`, `decade`, `instrumentalness`, `speechiness`, `liveness`, or the new optional `UserProfile.target_*` fields.
- A user who sets none of these gets exactly the baseline score: the test `test_new_attributes_add_nothing_when_user_did_not_ask` and the unchanged baseline output above prove it.

**Evidence** (baseline vs. experimental, from `attribute_demo` in [src/experiments.py](src/experiments.py)):

<!-- OUTPUT: python3 -m src.experiments | section Stretch 1: new attributes -->
```text
Nostalgic folk listener, then also prefers the 1970s (decade=1970)
Without the new preference (genre=folk, mood=nostalgic, energy=0.4, likes_acoustic=True):
  1. Paper Planes at Dawn (Wren and Willow, folk) score 4.33
  2. Dusty Porch Light (Hollis Reed, country) score 3.70
  3. Focus Flow (LoRoom, lofi) score 2.39
  4. Coffee Shop Stories (Slow Stereo, jazz) score 2.38
  5. Blue Hour Confessions (Delta Marrow, blues) score 2.34
With decade=1970 added:
  1. Paper Planes at Dawn (Wren and Willow, folk) score 4.83
  2. Dusty Porch Light (Hollis Reed, country) score 3.90
  3. Blue Hour Confessions (Delta Marrow, blues) score 2.84
  4. Sunday Slow Dance (Slow Stereo, jazz) score 2.73
  5. Coffee Shop Stories (Slow Stereo, jazz) score 2.69
What changed: entered: Sunday Slow Dance; dropped: Focus Flow; moved: Blue Hour Confessions #5->#3, Coffee Shop Stories #4->#5

Happy pop listener, then also prefers lesser-known songs (popularity=40)
Without the new preference (genre=pop, mood=happy, energy=0.85, likes_acoustic=False):
  1. Sunrise City (Neon Echo, pop) score 5.85
  2. Golden Hour Parade (Cherry Meridian, pop) score 5.79
  3. Gym Hero (Max Pulse, pop) score 4.31
  4. Hyperdrive Heartbeat (Max Pulse, pop) score 4.28
  5. Heartbeat Static (Velvet Circuit, pop) score 3.89
With popularity=40 added:
  1. Sunrise City (Neon Echo, pop) score 5.93
  2. Golden Hour Parade (Cherry Meridian, pop) score 5.90
  3. Hyperdrive Heartbeat (Max Pulse, pop) score 4.38
  4. Gym Hero (Max Pulse, pop) score 4.33
  5. Heartbeat Static (Velvet Circuit, pop) score 4.07
What changed: moved: Hyperdrive Heartbeat #4->#3, Gym Hero #3->#4
```

Reading it: asking for the 1970s lifts `Blue Hour Confessions` (1970) from #5 to #3 and pushes `Focus Flow` (2020) out of the top 5. The popularity case is a small effect (two songs swap places), which is what a 0.5 weight is supposed to do. Not every attribute changes every ranking: in a trial run, asking the lofi listener for instrumentalness 0.9 raised scores but changed no order, because the top four were already instrumental.

**Tests:** `tests/test_stretch.py` (`test_each_new_attribute_can_decide_a_ranking` for all five attributes, `test_decade_preference_changes_real_catalog_ranking`, similarity-formula and validation tests) and `tests/test_data.py` (loading, types, ranges, a 10-column file, invalid values).

### Stretch 2: Multiple ranking modes

**What:** three strategies, selected with `--mode`:

| Mode | Weights (genre / mood / energy) | Idea |
| --- | --- | --- |
| `balanced` (default) | 2.0 / 1.5 / 2.0 | genre, mood and energy all count |
| `genre-first` | 4.0 / 1.0 / 1.0 | an exact genre match dominates |
| `mood-energy` | 0.5 / 3.0 / 3.0 | the feel of the song dominates, genre is a tie-breaker |

**Code:** `RankingMode`, `RANKING_MODES`, `DEFAULT_MODE` and `get_mode` in [src/recommender.py](src/recommender.py); `--mode` in `build_parser` in [src/main.py](src/main.py). A mode is only a named `ScoringWeights`; there is one scoring algorithm, and `Recommender(songs, weights)` / `recommend_songs(..., weights=...)` accept any of them.

**Evidence** (baseline `balanced` vs. experimental modes, `mode_comparison` in [src/experiments.py](src/experiments.py)):

<!-- OUTPUT: python3 -m src.experiments | section Stretch 2: ranking modes -->
```text
Profile: Happy high-energy pop listener
[balanced] genre, mood and energy all count (default)
  1. Sunrise City (Neon Echo, pop) score 5.85
  2. Golden Hour Parade (Cherry Meridian, pop) score 5.79
  3. Gym Hero (Max Pulse, pop) score 4.31
  4. Hyperdrive Heartbeat (Max Pulse, pop) score 4.28
  5. Heartbeat Static (Velvet Circuit, pop) score 3.89
[genre-first] an exact genre match dominates: genre 4.0, mood 1.0, energy 1.0
  1. Sunrise City (Neon Echo, pop) score 6.38
  2. Golden Hour Parade (Cherry Meridian, pop) score 6.36
  3. Gym Hero (Max Pulse, pop) score 5.39
  4. Hyperdrive Heartbeat (Max Pulse, pop) score 5.38
  5. Heartbeat Static (Velvet Circuit, pop) score 5.12
  vs balanced -> no change in the top 5
[mood-energy] mood and energy dominate, genre is a tie-breaker: genre 0.5, mood 3.0, energy 3.0
  1. Sunrise City (Neon Echo, pop) score 6.82
  2. Golden Hour Parade (Cherry Meridian, pop) score 6.71
  3. Fuego en la Calle (Luna Rivera, latin) score 6.25
  4. Rooftop Lights (Indigo Parade, indie pop) score 6.05
  5. Gym Hero (Max Pulse, pop) score 3.73
  vs balanced -> entered: Fuego en la Calle, Rooftop Lights; dropped: Hyperdrive Heartbeat, Heartbeat Static; moved: Gym Hero #3->#5

Profile: Edge case: high-energy classical fan (conflicting tastes)
[balanced] genre, mood and energy all count (default)
  1. Moonlit Sonata Sketch (Aria Voss, classical) score 4.54
  2. Glass Cathedral (Aria Voss, classical) score 3.12
  3. Storm Runner (Voltline, rock) score 2.03
  4. Laser Garden (Pulse Arcade, electronic) score 2.03
  5. Gym Hero (Max Pulse, pop) score 1.96
[genre-first] an exact genre match dominates: genre 4.0, mood 1.0, energy 1.0
  1. Moonlit Sonata Sketch (Aria Voss, classical) score 5.76
  2. Glass Cathedral (Aria Voss, classical) score 4.80
  3. Storm Runner (Voltline, rock) score 1.04
  4. Rooftop Lights (Indigo Parade, indie pop) score 1.03
  5. Laser Garden (Pulse Arcade, electronic) score 1.03
  vs balanced -> entered: Rooftop Lights; dropped: Gym Hero; moved: Laser Garden #4->#5
[mood-energy] mood and energy dominate, genre is a tie-breaker: genre 0.5, mood 3.0, energy 3.0
  1. Moonlit Sonata Sketch (Aria Voss, classical) score 4.83
  2. Laser Garden (Pulse Arcade, electronic) score 3.03
  3. Storm Runner (Voltline, rock) score 3.02
  4. Gym Hero (Max Pulse, pop) score 2.94
  5. Basement Riot (Static Youth, punk) score 2.92
  vs balanced -> entered: Basement Riot; dropped: Glass Cathedral; moved: Laser Garden #4->#2, Gym Hero #5->#4
```

Reading it: for the pop listener, `genre-first` keeps the same five songs in the same order (scores rise because genre is worth more) while `mood-energy` swaps in two non-pop songs, `Fuego en la Calle` and `Rooftop Lights`. For the classical edge case, `mood-energy` drops `Glass Cathedral` from #2 and promotes `Laser Garden`. A less flattering observation: under `genre-first`, that edge case's slots 3-5 score 1.04, 1.03 and 1.03, so the order after the genre matches is decided by tiny differences and is nearly arbitrary.

**Tests:** `tests/test_stretch.py` (mode registry, distinct weights, immutability, shared scoring rule, different rankings for the same profile, OOP/functional agreement in every mode) and `tests/test_report.py` (CLI `--mode` output differs per mode).

### Stretch 3: Diversity and fairness

**What:** an optional greedy rerank. When picking each next song, its score is reduced by `artist_penalty` for every earlier pick by the same artist, and by `genre_penalty` for every earlier pick of the same genre. The penalty is part of the final score and appears in the explanation as a negative reason, so the list and the explanation always agree. Both penalties default to 0, which is the baseline ranking.

**Code:** `DiversityConfig` and `_diversify` (called from `rank_songs`) in [src/recommender.py](src/recommender.py); `--artist-penalty` / `--genre-penalty` in [src/main.py](src/main.py); `Recommender(songs, diversity=...)` for the OOP interface. Ties still break by song `id`, `k=0` returns an empty list, `k` larger than the catalog returns every song once, and final scores never increase down the list.

**Evidence** (baseline vs. experimental, `diversity_demo` in [src/experiments.py](src/experiments.py)):

<!-- OUTPUT: python3 -m src.experiments | section Stretch 3: variety penalty -->
```text
Profile: Happy high-energy pop listener; variety penalty: artist 0.75, genre 0
Baseline (no penalty):
  1. Sunrise City (Neon Echo, pop) score 5.85
  2. Golden Hour Parade (Cherry Meridian, pop) score 5.79
  3. Gym Hero (Max Pulse, pop) score 4.31
  4. Hyperdrive Heartbeat (Max Pulse, pop) score 4.28
  5. Heartbeat Static (Velvet Circuit, pop) score 3.89
With penalty:
  1. Sunrise City (Neon Echo, pop) score 5.85
  2. Golden Hour Parade (Cherry Meridian, pop) score 5.79
  3. Gym Hero (Max Pulse, pop) score 4.31
  4. Heartbeat Static (Velvet Circuit, pop) score 3.89
  5. Fuego en la Calle (Luna Rivera, latin) score 3.80
What changed: entered: Fuego en la Calle; dropped: Hyperdrive Heartbeat; moved: Heartbeat Static #5->#4
Match quality (sum of the five songs' penalty-free scores): baseline 24.12, with penalty 23.64

Profile: Relaxed low-energy lofi listener; variety penalty: artist 0.75, genre 0
Baseline (no penalty):
  1. Library Rain (Paper Lanterns, lofi) score 5.93
  2. Midnight Coding (LoRoom, lofi) score 5.71
  3. Focus Flow (LoRoom, lofi) score 4.29
  4. Spacewalk Thoughts (Orbit Bloom, ambient) score 3.82
  5. Late Bus Home (Marlow Vance, hip hop) score 3.44
With penalty:
  1. Library Rain (Paper Lanterns, lofi) score 5.93
  2. Midnight Coding (LoRoom, lofi) score 5.71
  3. Spacewalk Thoughts (Orbit Bloom, ambient) score 3.82
  4. Focus Flow (LoRoom, lofi) score 3.54
  5. Late Bus Home (Marlow Vance, hip hop) score 3.44
  Focus Flow: variety penalty: 1 earlier pick(s) by LoRoom (-0.75)
What changed: moved: Spacewalk Thoughts #4->#3, Focus Flow #3->#4
Match quality (sum of the five songs' penalty-free scores): baseline 23.20, with penalty 23.20

Profile: Relaxed low-energy lofi listener; variety penalty: artist 0, genre 0.5
Baseline (no penalty):
  1. Library Rain (Paper Lanterns, lofi) score 5.93
  2. Midnight Coding (LoRoom, lofi) score 5.71
  3. Focus Flow (LoRoom, lofi) score 4.29
  4. Spacewalk Thoughts (Orbit Bloom, ambient) score 3.82
  5. Late Bus Home (Marlow Vance, hip hop) score 3.44
With penalty:
  1. Library Rain (Paper Lanterns, lofi) score 5.93
  2. Midnight Coding (LoRoom, lofi) score 5.21
  3. Spacewalk Thoughts (Orbit Bloom, ambient) score 3.82
  4. Late Bus Home (Marlow Vance, hip hop) score 3.44
  5. Focus Flow (LoRoom, lofi) score 3.29
  Midnight Coding: variety penalty: 1 earlier lofi pick(s) (-0.50)
  Focus Flow: variety penalty: 2 earlier lofi pick(s) (-1.00)
What changed: moved: Spacewalk Thoughts #4->#3, Late Bus Home #5->#4, Focus Flow #3->#5
Match quality (sum of the five songs' penalty-free scores): baseline 23.20, with penalty 23.20
```

Reading it: with an artist penalty of 0.75, the pop listener's second `Max Pulse` track (`Hyperdrive Heartbeat`, 4.28 before the penalty) is displaced from the top 5 by `Fuego en la Calle`; the lofi listener's second `LoRoom` track, `Focus Flow`, drops from 4.29 to 3.54 and falls behind `Spacewalk Thoughts`. With a genre penalty of 0.5, the lofi listener's second and third lofi songs are penalized 0.50 and 1.00, and `Focus Flow` falls from #3 to #5.

**The trade-off.** Variety and strict preference matching pull in opposite directions. The baseline list is the best match for the stated taste by definition; the reranked list gives up some of that match to show more artists (or genres). Every penalized song above was a *better* match than the one that replaced it. The "Match quality" lines measure the cost: for the pop listener the five songs' combined penalty-free score falls from 24.12 to 23.64 (about 2%), while for the lofi listener the same five songs appear and only their order changes (23.20 either way). The penalty size decides how much accuracy is traded away: at 0.75 it only reorders and swaps one song, at very large values the list becomes "one song per artist" regardless of fit. Who benefits: listeners who would otherwise see one artist repeated, and artists with a single song in a crowded genre. Who may lose: a listener who really does want three songs from the same artist. This is a small, deterministic rule on a 30-song fictional catalog; it is **not** a solution to fairness in any broad societal sense, and it only looks at artist and genre labels, not at who the artists are.

**Tests:** `tests/test_stretch.py` (disabled equals baseline, the penalty changes the real top 5, the final score reflects the penalty, reasons stay truthful and sum to the score, accumulation per repeat, genre penalty independent, determinism, tie-breaking, k semantics, invalid penalties, OOP/functional agreement).

### Stretch 4: Visual summary table

**What:** a standard-library-only report with rank, song, artist, final score and every scoring reason. Cells are word-wrapped, over-long words are split, and below 76 columns the layout switches from a grid to a compact one-block-per-song form.

**Code:** `format_recommendation_table` (wide grid and compact layouts) and `format_recommendation_list` in [src/report.py](src/report.py); `--width` and `--format` in [src/main.py](src/main.py). Header lines are wrapped to the same width.

**Evidence.** The lofi profile with the variety penalty on, at the default width of 100 (experimental run; note the `Focus Flow` row with its penalty and final score 3.54):

<!-- OUTPUT: python3 -m src.main --artist-penalty 0.75 | awk '/^=== Relaxed/,/^$/' -->
```text
=== Relaxed low-energy lofi listener ===
Preferences: genre=lofi, mood=chill, energy=0.35, likes_acoustic=True
Top 5 (a perfect match would score 6.00):
# | Song                  | Artist           | Score | Why (points)
--+-----------------------+------------------+-------+----------------------------------------------
1 | Library Rain          | Paper Lanterns   |  5.93 | genre match: lofi (+2.00)
  |                       |                  |       | mood match: chill (+1.50)
  |                       |                  |       | energy 0.35 vs target 0.35 (+2.00)
  |                       |                  |       | acousticness 0.86, wants acoustic (+0.43)
--+-----------------------+------------------+-------+----------------------------------------------
2 | Midnight Coding       | LoRoom           |  5.71 | genre match: lofi (+2.00)
  |                       |                  |       | mood match: chill (+1.50)
  |                       |                  |       | energy 0.42 vs target 0.35 (+1.86)
  |                       |                  |       | acousticness 0.71, wants acoustic (+0.35)
--+-----------------------+------------------+-------+----------------------------------------------
3 | Spacewalk Thoughts    | Orbit Bloom      |  3.82 | mood match: chill (+1.50)
  |                       |                  |       | energy 0.28 vs target 0.35 (+1.86)
  |                       |                  |       | acousticness 0.92, wants acoustic (+0.46)
--+-----------------------+------------------+-------+----------------------------------------------
4 | Focus Flow            | LoRoom           |  3.54 | genre match: lofi (+2.00)
  |                       |                  |       | energy 0.40 vs target 0.35 (+1.90)
  |                       |                  |       | acousticness 0.78, wants acoustic (+0.39)
  |                       |                  |       | variety penalty: 1 earlier pick(s) by LoRoom
  |                       |                  |       |   (-0.75)
--+-----------------------+------------------+-------+----------------------------------------------
5 | Late Bus Home         | Marlow Vance     |  3.44 | mood match: chill (+1.50)
  |                       |                  |       | energy 0.48 vs target 0.35 (+1.74)
  |                       |                  |       | acousticness 0.40, wants acoustic (+0.20)
--+-----------------------+------------------+-------+----------------------------------------------
```

The same profile at `--width 50`:

<!-- OUTPUT: python3 -m src.main --artist-penalty 0.75 --width 50 | awk '/^=== Relaxed/,/^$/' -->
```text
=== Relaxed low-energy lofi listener ===
Preferences: genre=lofi, mood=chill, energy=0.35,
likes_acoustic=True
Top 5 (a perfect match would score 6.00):
1. Library Rain by Paper Lanterns (score 5.93)
   - genre match: lofi (+2.00)
   - mood match: chill (+1.50)
   - energy 0.35 vs target 0.35 (+2.00)
   - acousticness 0.86, wants acoustic (+0.43)
2. Midnight Coding by LoRoom (score 5.71)
   - genre match: lofi (+2.00)
   - mood match: chill (+1.50)
   - energy 0.42 vs target 0.35 (+1.86)
   - acousticness 0.71, wants acoustic (+0.35)
3. Spacewalk Thoughts by Orbit Bloom (score 3.82)
   - mood match: chill (+1.50)
   - energy 0.28 vs target 0.35 (+1.86)
   - acousticness 0.92, wants acoustic (+0.46)
4. Focus Flow by LoRoom (score 3.54)
   - genre match: lofi (+2.00)
   - energy 0.40 vs target 0.35 (+1.90)
   - acousticness 0.78, wants acoustic (+0.39)
   - variety penalty: 1 earlier pick(s) by LoRoom
     (-0.75)
5. Late Bus Home by Marlow Vance (score 3.44)
   - mood match: chill (+1.50)
   - energy 0.48 vs target 0.35 (+1.74)
   - acousticness 0.40, wants acoustic (+0.20)
```

**Tests:** `tests/test_report.py` (required columns and values, penalties shown, no line wider than the width for widths 30-140 with very long titles and unbreakable words, nothing truncated, layout switch at 76, no trailing whitespace, every mode/width/format combination from the CLI).

---

## Limitations and Risks

These are measured on the actual catalog (`python3 -m src.experiments`):

- **Tiny, uneven catalog.** 30 songs, 19 genres. 12 of the 19 genres have exactly one song, and pop (5 songs) is the only genre that can fill a whole top 5. A rock fan gets two genre matches and then the list is filled with other loud songs (2 of the 5 rock recommendations matched neither genre nor mood).
- **Sparse moods.** 14 mood labels, 7 of which appear on a single song.
- **Energy skew.** 14 of 30 songs have energy 0.70 or higher, 8 have energy below 0.40 and 8 are in between, so high-energy listeners have more candidates than low-energy listeners.
- **Exact labels are brittle.** For the lofi/chill listener, `Late Bus Home` (hip hop/chill) ranks #5 with 3.44 while `Coffee Shop Stories` (jazz/relaxed, energy 0.37, acousticness 0.89) ranks #8 with 2.40, even though its numbers fit the listener better. The only difference is the word "chill" versus "relaxed".
- **Repetition is possible in the baseline.** The baseline pop top 5 contains `Max Pulse` twice, and the classical edge case gets `Aria Voss` in both of its top two slots. The variety rerank (Stretch 3) fixes the pop case but costs match quality, and with penalty 0.75 it does *not* change the classical edge case's top two: `Glass Cathedral` drops from 3.12 to 2.37 but still beats `Storm Runner` (2.03), so the second `Aria Voss` song stays at #2.
- **Modes can make the tail arbitrary.** Under `genre-first` the edge case's slots 3-5 differ by 0.01.
- **Extra attributes are small nudges on invented data.** They only matter when a listener asks for them, at 0.5 points each, and the values themselves are hand-written. Asking for a popularity or decade also builds popularity/recency preferences into the ranking, which a real system would need to think about carefully.
- **One genre, one mood per listener.** Real taste is rarely a single label.
- **Fictional, hand-written data.** The audio features are illustrative values, not real measurements. Nothing here was validated against real listener behavior, so "evaluation" means inspecting results and testing the code, not measuring recommendation accuracy.
- **Content-based only.** No listening history, lyrics, language, artist similarity or popularity signal from real listeners; the system cannot surprise a listener.

See the [**Model Card**](model_card.md) for the fuller discussion. The AI-assistance log for the stretch features is in [ai_interactions.md](ai_interactions.md).

---

## Reflection

The full write-up of intended use, data, evaluation and limitations is in the model card:

[**Model Card**](model_card.md)

Building this made it concrete how a recommender turns data into predictions: a "prediction" is just a sum of weighted comparisons between a song's numbers and a listener's stated preferences, and every weight is a design decision. The weight experiment showed that decision matters at the edges of the list (slots 3-5) far more than at the top, and the mode comparison showed the same thing from the other side: three strategies agree on the best song and disagree about the rest.

Bias showed up without anyone intending it. The catalog's shape (one pop-heavy genre, many single-song genres, a high-energy skew) and an exact-match genre rule mean that listeners who happen to like well-stocked genres get lists made of true matches, while listeners of thinly stocked genres get lists padded with whatever is loud or quiet enough. The variety rerank showed that "fixing" repetition is a trade, not a free improvement: each song it promoted was a worse match for the stated taste than the one it replaced. A real system with real listener data would have the same risks in a less visible form.
