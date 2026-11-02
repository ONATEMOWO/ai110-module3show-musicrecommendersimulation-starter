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

### Reproducing the evaluation

Every number and output block in this README was produced by these commands (nothing is typed in by hand):

```bash
python3 -m src.main          # the four listener profiles
python3 -m src.experiments   # catalog counts, weight sensitivity, profile comparison
```

---

## Sample Recommendation Output

Output of `python3 -m src.main` (30 songs, four listener profiles, top 5 each). A perfect match would score 6.00 for these profiles. Each bullet is a real term in the score, and the bullets add up to the score shown.

<!-- OUTPUT: python3 -m src.main -->
```text
Loaded 30 songs from data/songs.csv

=== Happy high-energy pop listener ===
Preferences: genre=pop, mood=happy, energy=0.85, likes_acoustic=False
Top 5 (a perfect match would score 6.00):
1. Sunrise City by Neon Echo - score 5.85
     - genre match: pop (+2.00)
     - mood match: happy (+1.50)
     - energy 0.82 vs target 0.85 (+1.94)
     - acousticness 0.18 suits a taste for non-acoustic music (+0.41)
2. Golden Hour Parade by Cherry Meridian - score 5.79
     - genre match: pop (+2.00)
     - mood match: happy (+1.50)
     - energy 0.78 vs target 0.85 (+1.86)
     - acousticness 0.15 suits a taste for non-acoustic music (+0.42)
3. Gym Hero by Max Pulse - score 4.31
     - genre match: pop (+2.00)
     - energy 0.93 vs target 0.85 (+1.84)
     - acousticness 0.05 suits a taste for non-acoustic music (+0.47)
4. Hyperdrive Heartbeat by Max Pulse - score 4.28
     - genre match: pop (+2.00)
     - energy 0.95 vs target 0.85 (+1.80)
     - acousticness 0.04 suits a taste for non-acoustic music (+0.48)
5. Heartbeat Static by Velvet Circuit - score 3.89
     - genre match: pop (+2.00)
     - energy 0.62 vs target 0.85 (+1.54)
     - acousticness 0.30 suits a taste for non-acoustic music (+0.35)

=== Relaxed low-energy lofi listener ===
Preferences: genre=lofi, mood=chill, energy=0.35, likes_acoustic=True
Top 5 (a perfect match would score 6.00):
1. Library Rain by Paper Lanterns - score 5.93
     - genre match: lofi (+2.00)
     - mood match: chill (+1.50)
     - energy 0.35 vs target 0.35 (+2.00)
     - acousticness 0.86 suits a taste for acoustic music (+0.43)
2. Midnight Coding by LoRoom - score 5.71
     - genre match: lofi (+2.00)
     - mood match: chill (+1.50)
     - energy 0.42 vs target 0.35 (+1.86)
     - acousticness 0.71 suits a taste for acoustic music (+0.35)
3. Focus Flow by LoRoom - score 4.29
     - genre match: lofi (+2.00)
     - energy 0.40 vs target 0.35 (+1.90)
     - acousticness 0.78 suits a taste for acoustic music (+0.39)
4. Spacewalk Thoughts by Orbit Bloom - score 3.82
     - mood match: chill (+1.50)
     - energy 0.28 vs target 0.35 (+1.86)
     - acousticness 0.92 suits a taste for acoustic music (+0.46)
5. Late Bus Home by Marlow Vance - score 3.44
     - mood match: chill (+1.50)
     - energy 0.48 vs target 0.35 (+1.74)
     - acousticness 0.40 suits a taste for acoustic music (+0.20)

=== Intense rock/workout listener ===
Preferences: genre=rock, mood=intense, energy=0.92, likes_acoustic=False
Top 5 (a perfect match would score 6.00):
1. Storm Runner by Voltline - score 5.93
     - genre match: rock (+2.00)
     - mood match: intense (+1.50)
     - energy 0.91 vs target 0.92 (+1.98)
     - acousticness 0.10 suits a taste for non-acoustic music (+0.45)
2. Rust Belt Anthem by The Gravel Roads - score 4.26
     - genre match: rock (+2.00)
     - energy 0.84 vs target 0.92 (+1.84)
     - acousticness 0.15 suits a taste for non-acoustic music (+0.42)
3. Gym Hero by Max Pulse - score 3.96
     - mood match: intense (+1.50)
     - energy 0.93 vs target 0.92 (+1.98)
     - acousticness 0.05 suits a taste for non-acoustic music (+0.47)
4. Laser Garden by Pulse Arcade - score 2.43
     - energy 0.90 vs target 0.92 (+1.96)
     - acousticness 0.06 suits a taste for non-acoustic music (+0.47)
5. Basement Riot by Static Youth - score 2.42
     - energy 0.94 vs target 0.92 (+1.96)
     - acousticness 0.08 suits a taste for non-acoustic music (+0.46)

=== Edge case: high-energy classical fan (conflicting tastes) ===
Preferences: genre=classical, mood=melancholy, energy=0.9, likes_acoustic=True
Top 5 (a perfect match would score 6.00):
1. Moonlit Sonata Sketch by Aria Voss - score 4.54
     - genre match: classical (+2.00)
     - mood match: melancholy (+1.50)
     - energy 0.18 vs target 0.90 (+0.56)
     - acousticness 0.97 suits a taste for acoustic music (+0.48)
2. Glass Cathedral by Aria Voss - score 3.12
     - genre match: classical (+2.00)
     - energy 0.22 vs target 0.90 (+0.64)
     - acousticness 0.96 suits a taste for acoustic music (+0.48)
3. Storm Runner by Voltline - score 2.03
     - energy 0.91 vs target 0.90 (+1.98)
     - acousticness 0.10 suits a taste for acoustic music (+0.05)
4. Laser Garden by Pulse Arcade - score 2.03
     - energy 0.90 vs target 0.90 (+2.00)
     - acousticness 0.06 suits a taste for acoustic music (+0.03)
5. Gym Hero by Max Pulse - score 1.96
     - energy 0.93 vs target 0.90 (+1.94)
     - acousticness 0.05 suits a taste for acoustic music (+0.03)
```

---

## Comparing the Profiles

The same scoring code gave four very different lists. `python3 -m src.experiments` summarizes how each top 5 was earned:

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

**Design:** the profile (Happy high-energy pop listener) and the 30-song catalog were held fixed. Starting from the baseline (genre 2.0, mood 1.5, energy 2.0), one weight at a time was halved and then doubled, with every other weight unchanged. Reproduce with `python3 -m src.experiments`.

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

**What actually changed and why**

- `Sunrise City` and `Golden Hour Parade` are #1 and #2 in all seven settings. They match genre, mood and energy at once, so no single weight change can dislodge them.
- The only movement is in slots 3-5, and it comes from one tension: the baseline fills those slots with songs that match the *genre label* (pop) but not the mood or energy.
- **Surprising result:** doubling the genre weight changed *nothing* about the ranking. All five baseline picks were already pop, so a bigger genre weight just added the same 2.0 to each of them. The weight that looks most important only matters when other genres are competing.
- **Disappointing result:** the baseline's #5 is `Heartbeat Static`, a romantic pop song with energy 0.62 (0.23 below the target), while `Fuego en la Calle` (latin, happy, energy 0.80, a much better fit on mood and energy) is left out. It only gets in if genre is halved, mood is doubled, or energy is doubled. In other words, the fifth slot of the default list is decided by a single exact-label match.
- `Rooftop Lights` (indie pop, happy, energy 0.76) only enters when genre is halved or mood is doubled, and it never reaches the top two. Because the genre rule is exact-match, "indie pop" gets no credit for being close to "pop".

---

## Limitations and Risks

These are measured on the actual catalog (`python3 -m src.experiments`):

- **Tiny, uneven catalog.** 30 songs, 19 genres. 12 of the 19 genres have exactly one song, and pop (5 songs) is the only genre that can fill a whole top 5. A rock fan gets two genre matches and then the list is filled with other loud songs (2 of the 5 rock recommendations matched neither genre nor mood).
- **Sparse moods.** 14 mood labels, 7 of which appear on a single song.
- **Energy skew.** 14 of 30 songs have energy 0.70 or higher, 8 have energy below 0.40 and 8 are in between, so high-energy listeners have more candidates than low-energy listeners.
- **Exact labels are brittle.** For the lofi/chill listener, `Late Bus Home` (hip hop/chill) ranks #5 with 3.44 while `Coffee Shop Stories` (jazz/relaxed, energy 0.37, acousticness 0.89) ranks #8 with 2.40, even though its numbers fit the listener better. The only difference is the word "chill" versus "relaxed".
- **No built-in variety.** The pop listener's top 5 contains `Max Pulse` twice, and the classical edge-case profile gets `Aria Voss` in both of its top two slots. The ranking only asks "how good is each song?", never "have we already shown this artist?".
- **One genre, one mood per listener.** Real taste is rarely a single label.
- **Fictional, hand-written data.** The audio features are illustrative values, not real measurements. Nothing here was validated against real listener behavior, so "evaluation" means inspecting results and testing the code, not measuring recommendation accuracy.
- **Content-based only.** No listening history, lyrics, language, artist similarity or popularity; the system cannot surprise a listener.

See the [**Model Card**](model_card.md) for the fuller discussion.

---

## Reflection

The full write-up of intended use, data, evaluation and limitations is in the model card:

[**Model Card**](model_card.md)

Building this made it concrete how a recommender turns data into predictions: a "prediction" is just a sum of weighted comparisons between a song's numbers and a listener's stated preferences, and every weight is a design decision. The weight experiment showed that decision matters at the edges of the list (slots 3-5) far more than at the top.

Bias showed up without anyone intending it. The catalog's shape (one pop-heavy genre, many single-song genres, a high-energy skew) and an exact-match genre rule mean that listeners who happen to like well-stocked genres get lists made of true matches, while listeners of thinly stocked genres get lists padded with whatever is loud or quiet enough. A real system with real listener data would have the same risk in a less visible form.
