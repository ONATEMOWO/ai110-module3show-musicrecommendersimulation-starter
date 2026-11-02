# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeMatch 1.0**, a small, transparent, content-based music recommender with selectable ranking modes and optional variety reranking.

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
- Anyone who wants a fairness guarantee: the variety rerank is a small, label-based rule, not a fairness solution.

---

## 3. How the Model Works

Every song in the catalog has a genre, a mood, and a few numbers describing how it sounds (energy, tempo, valence, danceability, acousticness) plus five extra attributes (popularity, release decade, instrumentalness, speechiness, liveness). A listener tells the system their favorite genre and mood and how energetic they want the music to be.

The system gives every song points (default `balanced` mode):

- **Genre:** 2.0 points if the song's genre is exactly the listener's favorite, otherwise 0.
- **Mood:** 1.5 points for an exact mood match, otherwise 0.
- **Energy:** up to 2.0 points, based on how *close* the song's energy is to the listener's target. A song exactly on target gets all 2.0; one that is 0.3 away gets 1.4. High energy is not rewarded for its own sake: a relaxed listener gets quiet songs first.
- **Acoustic taste:** up to 0.5 points, higher for acoustic songs if the listener likes acoustic music and higher for non-acoustic songs if they don't.
- **Optional targets (valence, danceability, tempo, popularity, decade, instrumentalness, speechiness, liveness):** up to 0.5 points each, but *only* if the listener provided that target. Nobody is given a hidden default.

It adds the points up, sorts every song from highest to lowest, and returns the top few. If two songs tie, the one with the lower `id` comes first, so the same input always gives the same output. Every scoring component is listed in the explanation. The unrounded components add up to the exact score; because each term and the total are displayed to two decimal places, the displayed figures may differ by 0.01 from rounding.

**Ranking modes.** A mode is just a different set of weights for the same rule: `balanced` (genre 2.0, mood 1.5, energy 2.0), `genre-first` (4.0, 1.0, 1.0), and `mood-energy` (0.5, 3.0, 3.0). There is only one scoring algorithm.

**Variety reranking (optional, off by default).** When switched on, the system picks songs one at a time and subtracts a penalty from a song's score for every earlier pick by the same artist (and, if configured, the same genre). The penalized score is the final score, and the explanation lists the penalty as a negative reason.

The same code is used by both the functional interface (`load_songs`, `score_song`, `recommend_songs`) and the object-oriented one (`Song`, `UserProfile`, `Recommender`), so they cannot disagree about the ranking. Tests check this in every mode and with variety reranking on.

**What changed from the starter:** the starter had empty function bodies. The scoring rule, CSV loader with validation, ranking and tie-breaking, explanations, command-line report, ranking modes, variety reranking, table formatter and experiments are all new.

---

## 4. Data

- **Size:** 30 songs by 24 artists, in `data/songs.csv`: the 10 starter songs (original ten columns unchanged) plus 20 added for this project.
- **Columns (15):** `id, title, artist, genre, mood, energy, tempo_bpm, valence, danceability, acousticness` (the original ten) plus `popularity, release_decade, instrumentalness, speechiness, liveness`.
- **Genres (19):** pop 5, lofi 3, classical 2, hip hop 2, jazz 2, rock 2, synthwave 2, and one song each of ambient, blues, country, electronic, folk, indie pop, latin, metal, punk, r&b, reggae, soul. Twelve of the 19 genres have exactly one song.
- **Moods (14):** chill 4, energetic 4, happy 4, relaxed 4, romantic 3, angry 2, intense 2, and one song each of confident, focused, melancholy, moody, nostalgic, sad, uplifting.
- **Energy:** 14 songs at 0.70 or higher, 8 between 0.40 and 0.69, 8 below 0.40.
- **Extra attributes:** release decades 1970s 3, 1980s 2, 1990s 2, 2000s 5, 2010s 8, 2020s 10; popularity from 28 to 88 (9 songs at 70 or above); instrumentalness 0.00 to 0.97 (11 songs at 0.50 or above); speechiness 0.03 to 0.34 (no song reaches 0.50); liveness 0.07 to 0.62 (3 songs at 0.50 or above).
- **Fictional and illustrative.** All titles and artists are invented, and all numeric values were written by hand to be plausible. They are not Spotify or other measured data.
- **What is missing:** lyrics, language, artist similarity, instrumentation, listening history, and any notion of a song being *good*. Musical taste outside these 19 genres is absent entirely.

---

## 5. Strengths

Based on the evaluation output in the README:

- **Listeners whose genre and mood are well represented get convincing top results.** The pop, lofi and rock profiles each get a #1 that matches genre, mood and energy at once (scores 5.85, 5.93 and 5.93 out of 6.00).
- **Energy behaves like a target, not a "more is better" slider.** The lofi listener's whole top 5 has energy between 0.28 and 0.48 (target 0.35); the rock listener's top 5 sits between 0.84 and 0.94 (target 0.92).
- **Fully explainable.** For any song you can see which features earned points (or lost them to a variety penalty) and how many. No score is a black box.
- **Deterministic and tested.** The same input always gives the same ranking, regardless of the order songs appear in the CSV.
- **Robust at the top.** In the weight experiment, the pop listener's #1 and #2 did not change under any single-weight halving or doubling.
- **Opt-in extras behave modestly.** A listener who does not ask for popularity, decade, instrumentalness, speechiness or liveness gets exactly the same scores as before those columns existed; a listener who does ask sees small, explained shifts (for example, asking for the 1970s moved `Blue Hour Confessions` from #5 to #3).

---

## 6. Limitations and Bias

All figures below come from the actual catalog (`python3 -m src.experiments`).

- **Dataset imbalance.** 12 of 19 genres and 7 of 14 moods have a single song. A listener of a one-song genre can receive at most one genre match; the rest of their list is filled with songs that merely have a similar energy. For the rock/workout profile, 2 of the 5 recommendations matched neither genre nor mood.
- **Pop-heavy head.** Pop is the largest genre (5 of 30 songs) and the only one that can fill a whole top 5, so pop listeners get lists made entirely of genre matches while others do not.
- **Energy skew.** 14 of 30 songs have energy 0.70 or higher versus 8 below 0.40, so high-energy listeners have more candidates to choose from.
- **Recency skew in the catalog.** 18 of 30 songs are from the 2010s or 2020s, so a listener who asks for the 1970s has only 3 songs to match.
- **Exact-match labels are brittle.** "Chill" and "relaxed" mean nearly the same thing but score as a total mismatch. For the lofi/chill listener, `Late Bus Home` (hip hop/chill, energy 0.48, acousticness 0.40) ranks #5 with 3.44, while `Coffee Shop Stories` (jazz/relaxed, energy 0.37, acousticness 0.89) ranks #8 with 2.40, despite fitting the listener's numbers better. Likewise "indie pop" gets no credit as a neighbor of "pop".
- **Genre and mood can outvote the numbers.** The classical edge-case listener wants energy 0.90, but the top two results are classical songs with energy 0.18 and 0.22, because genre plus mood (3.5 points) outweighs the energy penalty (about 1.4 points). The system adds the two pulls together rather than looking for a compromise.
- **The fifth slot can rest on a single label.** In the weight experiment, the pop listener's #5 (`Heartbeat Static`, romantic, energy 0.62) beat a happy, energy-0.80 latin song purely on the pop label.
- **Modes can make the tail arbitrary.** Under `genre-first`, the classical edge case's slots 3-5 score 1.04, 1.03 and 1.03, so their order is decided by differences of 0.01. Under `mood-energy`, the same profile's slots 2-5 span only 3.03 to 2.92.
- **The extra attributes sit on invented numbers.** They only matter if a listener asks, at 0.5 points each, and the values are hand-written. Speechiness never exceeds 0.34 in this catalog, so a listener who targets 0.9 gets no meaningful match.
- **One genre and one mood per listener.** Real taste is mixed and changes with context.
- **Hand-picked weights.** They were chosen by judgment, not learned. The experiments show they matter mostly for slots 3-5.
- **Not a measure of recommendation quality.** There is no ground truth of what listeners actually liked, so the evaluation checks internal consistency and sensible behavior, not accuracy.

### Variety reranking: impact on fairness and accuracy

What the variety rule does: it stops one artist (or genre) from filling the list by penalizing repeats. What it was measured to do on this catalog, with an artist penalty of 0.75 (baseline = no penalty):

| Profile | Baseline top 5 | With variety penalty | Match quality (sum of the five songs' penalty-free scores) |
| --- | --- | --- | --- |
| Happy pop listener | `Max Pulse` twice (`Gym Hero`, `Hyperdrive Heartbeat`) | `Hyperdrive Heartbeat` replaced by `Fuego en la Calle` | 24.12 to 23.64 (about 2% lower) |
| Relaxed lofi listener | `LoRoom` twice (`Midnight Coding`, `Focus Flow`) | `Focus Flow` falls from 4.29 to 3.54 and from #3 to #4 | 23.20 to 23.20 (same five songs, reordered) |
| Classical edge case | `Aria Voss` twice | no change: `Glass Cathedral` falls 3.12 to 2.37 but stays #2 | unchanged |

- **Who benefits:** a listener who would otherwise see one artist repeated, and artists who have a single song competing with a prolific artist in the same genre. The explanation shows the penalty, so the reason for the reordering is visible.
- **How it can hurt accuracy:** every song the rule demotes was a better match for the stated taste than the song that replaced it. A listener who genuinely wants several songs by one artist is served worse, and a large penalty turns the list into "one song per artist" regardless of fit. The penalty is configurable (`--artist-penalty`, `--genre-penalty`) and off by default so the baseline stays available for fair comparison.
- **What it does not do:** it does not address the catalog imbalances above (single-song genres, label brittleness), and it only sees artist and genre labels, so it says nothing about who the artists are or how listeners are treated. It is **not** a solution to fairness in a broad societal sense; it is a small, transparent variety rule evaluated on 30 fictional songs.

---

## 7. Evaluation

**Method.**

1. Four listener profiles were run through the real code on the real catalog, top 5 each, using the baseline settings (`balanced` mode, no variety penalty): a happy high-energy pop listener, a relaxed low-energy lofi listener, an intense rock/workout listener, and a deliberately conflicting edge case (classical, melancholy, energy 0.90). The full output is in the README.
2. For each result, the evaluation checked: does the top 5 match the stated genre, mood and energy; how many slots matched neither genre nor mood; how far the energy of each pick is from the target; and whether the unrounded explanation components add up to the score (allowing for two-decimal display rounding).
3. A controlled weight experiment held the pop profile and the catalog fixed and halved and doubled genre, mood and energy one at a time (six variants plus the baseline).
4. Stretch features were each compared against the baseline: a new-attribute preference added to a profile (decade for a folk listener, popularity for the pop listener), the two non-default modes on the pop and classical profiles, and the variety penalty on the pop and lofi profiles, including a measured match-quality cost.
5. Automated tests (`python3 -m pytest`, 210 tests) cover CSV loading and numeric types, catalog validity and unique IDs, the extra columns, exact genre/mood matching, energy-distance scoring, explanation consistency (unrounded scoring components sum to the score), ranking order, deterministic tie-breaking and input-order independence, distinct profiles, empty catalog, `k=0`, `k` larger than the catalog, invalid CSV rows, invalid preferences, ranking modes, variety reranking (effect, truthful explanations, determinism, top-k semantics), table formatting at many widths, the command-line options, and functional/OOP agreement.

**What happened (baseline).**

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

**What happened (experimental settings).**

- **Modes:** for the pop listener, `genre-first` keeps the same five songs in the same order and `mood-energy` swaps in `Fuego en la Calle` and `Rooftop Lights`; for the classical edge case, `mood-energy` drops `Glass Cathedral` from #2 for `Laser Garden`.
- **New attributes:** `decade=1970` lifts `Blue Hour Confessions` from #5 to #3 for the folk listener; `popularity=40` swaps `Gym Hero` and `Hyperdrive Heartbeat` for the pop listener; instrumentalness 0.9 for the lofi listener raised scores without changing the order.
- **Variety:** see the table in section 6.

---

## 8. Future Work

1. **Use similarity instead of exact labels for genre and mood.** Give partial credit for neighboring genres (indie pop to pop) and near-synonym moods (chill to relaxed), for example with a small hand-built similarity table. *Why:* the measured `Coffee Shop Stories` / `Late Bus Home` inversion, the indie-pop exclusion and the near-tied tails under `genre-first` all come from all-or-nothing matching.
2. **Make the variety rule relevance-aware.** Replace the flat per-repeat penalty with one that scales with how similar a candidate is to what has already been picked (for example comparing energy, mood and tempo, not only artist and genre labels), and choose its strength by testing against listener feedback. *Why:* the current flat penalty trades about 2% of match quality for the pop listener and changes nothing for the classical listener, so it is a blunt tool.
3. **Grow and balance the catalog, then evaluate with real feedback.** Add songs for the genres with one entry and collect real listener ratings so recommendation quality can be measured against something. *Why:* the imbalance (12 of 19 genres with one song, 18 of 30 songs from the 2010s-2020s) limits what the scoring rule can achieve for most listeners, and without ground truth no accuracy claim is possible.

---

## 9. Personal Reflection

### AI assistance and human verification

An AI coding agent (Claude, working through Claude Code) wrote the implementation, tests, dataset additions and documentation from the assignment brief. Human involvement was in giving the brief, constraints and acceptance criteria; the code and documents were produced by the agent, not hand-written by the student. [ai_interactions.md](ai_interactions.md) records the stretch-feature prompts, files, test evidence and the bugs found along the way.

What was checked, and how:

- **Tests.** The original two starter tests pass unchanged, alongside 208 added tests (210 total), run with `python3 -m pytest`.
- **Outputs.** The output blocks in the README come from running `python3 -m src.main` and `python3 -m src.experiments`; the prose describing them was checked against that output.
- **Bugs the checks caught during development:** a test that assumed a diversity penalty would change a list whose artists were already all different (the code was right, the test was wrong); an import-time error when ranking-mode presets were added before a helper function was defined; and CLI header lines that overflowed the requested width, found by a width test and fixed in the code rather than by loosening the test.
- **Things the agent got to decide that deserve a human look:** the weights (2.0 / 1.5 / 2.0 / 0.5 and the 0.5 for each optional attribute), the choice of exact-match genre and mood, the penalty size used in the demos (0.75), the invented song records and their extra-attribute values, and the four listener profiles.
- **Independent source review:** after implementation, the student requested a separate ChatGPT audit of the committed ZIP. The reviewer reran all 210 tests and compared all nine README output blocks against actual program output; every block matched. That review also identified the two-decimal display rounding caveat explained above.
- **Not verified:** whether the recommendations are *good* for real listeners. Nothing here involved real listeners.

### My reflection

My main takeaway from the results is that a recommendation can look personalized even when it comes from a fairly simple set of rules. Every score can be traced back to genre, mood, energy and optional preferences, rather than being a black box. In the weight experiment, doubling the genre weight did not change the pop top five at all, while some mood and energy changes brought different songs into the list. This makes a good case for checking actual rankings instead of assuming a weight will behave a certain way.

I used Claude Code to implement and test the project from a detailed brief, then requested an independent ChatGPT review of the committed source. That review reran the tests and CLI outputs and caught a small presentation detail: independently rounded explanation terms can differ from the displayed total by 0.01, even though the underlying math is consistent. This also reinforced an important limitation: passing tests means the program follows its rules, not that real people would enjoy the music it recommends. The next thing I would want is real listener feedback and a larger, better-balanced song catalog.
