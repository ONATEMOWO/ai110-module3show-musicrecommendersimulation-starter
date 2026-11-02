# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeMatch 1.0**, a small, transparent, content-based music recommender.

---

## 2. Intended Use

**Goal.** Given one listener's stated taste (a favorite genre, a favorite mood, a target energy level, and optionally an acoustic preference and a few other targets), rank the songs in a small catalog and say *exactly* why each one scored the way it did.

**What it assumes about the user.** That their taste can be summarized as one genre, one mood and a few numbers, and that they will state those preferences themselves. It has no listening history.

**Real users or classroom exploration?** Classroom exploration only. It exists to make the mechanics of a recommender visible: data in, preferences in, score out, ranking out.

**Who should use it**

- Students learning how content-based recommenders work and where their biases come from.
- Instructors who want a small system whose every score can be traced to a few readable terms.

**Who should not use it**

- Anyone who wants real music recommendations: the catalog is 30 fictional songs.
- Anyone who wants to draw conclusions about real artists or real listeners: the songs, artists and feature values are invented and illustrative, not real audio measurements, and nothing was validated against real listening behavior.
- Anyone who needs to serve listeners whose taste is mixed, shifting, or not captured by one genre label and one mood label (see the classical edge case below).

---

## 3. How the Model Works

Every song in the catalog has a genre, a mood, and a few numbers describing how it sounds (energy, tempo, valence, danceability, acousticness). A listener tells the system their favorite genre and mood and how energetic they want the music to be.

The system gives every song points:

- **Genre:** 2.0 points if the song's genre is exactly the listener's favorite, otherwise 0.
- **Mood:** 1.5 points for an exact mood match, otherwise 0.
- **Energy:** up to 2.0 points, based on how *close* the song's energy is to the listener's target. A song exactly on target gets all 2.0; one that is 0.3 away gets 1.4. High energy is not rewarded for its own sake: a relaxed listener gets quiet songs first.
- **Acoustic taste:** up to 0.5 points, higher for acoustic songs if the listener likes acoustic music and higher for non-acoustic songs if they don't.
- **Optional targets (valence, danceability, tempo):** up to 0.5 points each, but *only* if the listener provided that target.

It adds the points up, sorts every song from highest to lowest, and returns the top few. If two songs tie, the one with the lower `id` comes first, so the same input always gives the same output. Every point that went into a score is listed in the explanation, and the listed points add up to the score.

The same scoring code is used by both the functional interface (`load_songs`, `score_song`, `recommend_songs`) and the object-oriented one (`Song`, `UserProfile`, `Recommender`), so they cannot disagree about the ranking. A test checks this.

**What changed from the starter:** the starter had empty function bodies. The scoring rule, CSV loader with validation, ranking and tie-breaking, explanations, the command-line report and the experiments are all new.

---

## 4. Data

- **Size:** 30 songs by 24 artists, in `data/songs.csv`: the 10 starter songs (unchanged) plus 20 added for this project.
- **Columns:** `id, title, artist, genre, mood, energy, tempo_bpm, valence, danceability, acousticness`.
- **Genres (19):** pop 5, lofi 3, classical 2, hip hop 2, jazz 2, rock 2, synthwave 2, and one song each of ambient, blues, country, electronic, folk, indie pop, latin, metal, punk, r&b, reggae, soul. Twelve of the 19 genres have exactly one song.
- **Moods (14):** chill 4, energetic 4, happy 4, relaxed 4, romantic 3, angry 2, intense 2, and one song each of confident, focused, melancholy, moody, nostalgic, sad, uplifting.
- **Energy:** 14 songs at 0.70 or higher, 8 between 0.40 and 0.69, 8 below 0.40.
- **Fictional and illustrative.** All titles and artists are invented, and all numeric values were written by hand to be plausible. They are not Spotify or other measured data.
- **What is missing:** lyrics, language, release year, popularity, artist similarity, instrumentation, listening history, and any notion of a song being *good*. Musical taste outside these 19 genres is absent entirely.

---

## 5. Strengths

Based on the evaluation output in the README:

- **Listeners whose genre and mood are well represented get convincing top results.** The pop, lofi and rock profiles each get a #1 that matches genre, mood and energy at once (scores 5.85, 5.93 and 5.93 out of 6.00).
- **Energy behaves like a target, not a "more is better" slider.** The lofi listener's whole top 5 has energy between 0.28 and 0.48 (target 0.35); the rock listener's top 5 sits between 0.84 and 0.94 (target 0.92).
- **Fully explainable.** For any song you can see which features earned points and how many. No score is a black box.
- **Deterministic and tested.** The same input always gives the same ranking, regardless of the order songs appear in the CSV.
- **Robust at the top.** In the weight experiment, the pop listener's #1 and #2 did not change under any single-weight halving or doubling.

---

## 6. Limitations and Bias

All figures below come from the actual catalog (`python3 -m src.experiments`).

- **Dataset imbalance.** 12 of 19 genres and 7 of 14 moods have a single song. A listener of a one-song genre can receive at most one genre match; the rest of their list is filled with songs that merely have a similar energy. For the rock/workout profile, 2 of the 5 recommendations matched neither genre nor mood.
- **Pop-heavy head.** Pop is the largest genre (5 of 30 songs) and the only one that can fill a whole top 5, so pop listeners get lists made entirely of genre matches while others do not.
- **Energy skew.** 14 of 30 songs have energy 0.70 or higher versus 8 below 0.40, so high-energy listeners have more candidates to choose from.
- **Exact-match labels are brittle.** "Chill" and "relaxed" mean nearly the same thing but score as a total mismatch. For the lofi/chill listener, `Late Bus Home` (hip hop/chill, energy 0.48, acousticness 0.40) ranks #5 with 3.44, while `Coffee Shop Stories` (jazz/relaxed, energy 0.37, acousticness 0.89) ranks #8 with 2.40, despite fitting the listener's numbers better. Likewise "indie pop" gets no credit as a neighbor of "pop".
- **Genre and mood can outvote the numbers.** The classical edge-case listener wants energy 0.90, but the top two results are classical songs with energy 0.18 and 0.22, because genre plus mood (3.5 points) outweighs the energy penalty (about 1.4 points). The system adds the two pulls together rather than looking for a compromise.
- **The fifth slot can rest on a single label.** In the weight experiment, the pop listener's #5 (`Heartbeat Static`, romantic, energy 0.62) beat a happy, energy-0.80 latin song purely on the pop label.
- **No variety control.** The pop listener's top 5 contains `Max Pulse` twice; the classical profile's top two are both by `Aria Voss`. Nothing in the ranking asks whether an artist has already been shown.
- **One genre and one mood per listener.** Real taste is mixed and changes with context.
- **Hand-picked weights.** They were chosen by judgment, not learned. The experiment shows they matter mostly for slots 3-5.
- **Not a measure of recommendation quality.** There is no ground truth of what listeners actually liked, so the evaluation checks internal consistency and sensible behavior, not accuracy.

---

## 7. Evaluation

**Method.**

1. Four listener profiles were run through the real code on the real catalog, top 5 each: a happy high-energy pop listener, a relaxed low-energy lofi listener, an intense rock/workout listener, and a deliberately conflicting edge case (classical, melancholy, energy 0.90). The full output is in the README.
2. For each result I looked at: does the top 5 match the stated genre, mood and energy; how many slots matched neither genre nor mood; how far the energy of each pick is from the target; and whether the listed reasons add up to the score.
3. A controlled weight experiment held the pop profile and the catalog fixed and halved and doubled genre, mood and energy one at a time (six variants plus the baseline).
4. Automated tests (`python3 -m pytest`, 83 tests) cover CSV loading and numeric types, catalog validity and unique IDs, exact genre/mood matching, energy-distance scoring, explanation consistency (listed points sum to the score), ranking order, deterministic tie-breaking and input-order independence, distinct profiles, empty catalog, `k=0`, `k` larger than the catalog, invalid CSV rows, invalid preferences, and functional/OOP agreement.

**What happened.**

| Profile | Top 5 scores | Genre matches | Mood matches | Neither |
| --- | --- | --- | --- | --- |
| Happy high-energy pop | 5.85, 5.79, 4.31, 4.28, 3.89 | 5/5 | 2/5 | 0/5 |
| Relaxed low-energy lofi | 5.93, 5.71, 4.29, 3.82, 3.44 | 3/5 | 4/5 | 0/5 |
| Intense rock/workout | 5.93, 4.26, 3.96, 2.43, 2.42 | 2/5 | 2/5 | 2/5 |
| Edge: high-energy classical | 4.54, 3.12, 2.03, 2.03, 1.96 | 2/5 | 1/5 | 3/5 |

- Only three songs appear in more than one profile's top 5: `Gym Hero` (three profiles), `Laser Garden` and `Storm Runner` (two each).
- **Weight experiment:** `Sunrise City` and `Golden Hour Parade` stayed #1 and #2 in all seven settings. The top 5 changed in three of the six perturbed settings (genre x0.5, mood x2, energy x2) and was identical in the other three (genre x2, mood x0.5, energy x0.5).
- **Surprising:** doubling the genre weight changed nothing, because all five baseline picks were already pop.
- **Disappointing:** the baseline's #5 was a mid-energy romantic pop song while a happy, high-energy latin song was left out, and only a weight change could fix it.

---

## 8. Future Work

1. **Use similarity instead of exact labels for genre and mood.** Give partial credit for neighboring genres (indie pop to pop) and near-synonym moods (chill to relaxed), for example with a small hand-built similarity table. *Why:* the measured `Coffee Shop Stories` / `Late Bus Home` inversion and the indie-pop exclusion both come from all-or-nothing matching.
2. **Rerank for variety.** Penalize repeating the same artist (and optionally genre) among the top results. *Why:* the pop profile shows `Max Pulse` twice in five slots and the classical profile shows `Aria Voss` twice in two. The trade-off is that variety can push a better match down the list.
3. **Grow and balance the catalog, then evaluate with real feedback.** Add songs for the genres with one entry and collect real listener ratings so recommendation quality can be measured against something. *Why:* the imbalance (12 of 19 genres with one song) limits what the scoring rule can achieve for most listeners, and without ground truth no accuracy claim is possible.

---

## 9. Personal Reflection

### AI assistance and human verification

An AI coding agent (Claude, working through Claude Code) wrote the implementation, tests, dataset additions and documentation from the assignment brief. Human involvement was in giving the brief, constraints and acceptance criteria; the code and documents were produced by the agent, not hand-written by the student.

What was checked, and how:

- **Tests.** The original two starter tests pass unchanged, alongside 81 added tests (83 total), run with `python3 -m pytest`.
- **Outputs.** The output blocks in the README come from running `python3 -m src.main` and `python3 -m src.experiments`; the prose describing them was checked against that output.
- **Things the agent got to decide that deserve a human look:** the weights (2.0 / 1.5 / 2.0 / 0.5), the choice of exact-match genre and mood, the invented song records, and the four listener profiles.
- **Not verified:** whether the recommendations are *good* for real listeners. Nothing here involved real listeners.

### Your own reflection

*To be written by the student before submitting: what you learned about recommenders, anything that surprised you, and how this changes how you think about music apps. This part is personal judgment and is intentionally not filled in.*
