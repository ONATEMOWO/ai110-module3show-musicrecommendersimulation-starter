# AI Interactions Log

> **Stretch features only.** This file documents the four stretch features that were attempted (extra attributes, ranking modes, variety reranking, visual table), plus the starter's two general sections. It is not required for the core project.

**How this log was produced.** One AI coding agent (Claude, via Claude Code) did the work in a single session, starting from one long assignment brief pasted by the student. The prompts quoted below are the real stretch sections of that brief, copied verbatim. The "review decisions" are things the agent actually did or found during that session (failing tests, bugs, alternatives it tried), taken from the session itself. Test counts are from the final run of `python3 -m pytest`. After implementation, the student requested an independent ChatGPT review of the committed ZIP; the verification and remaining limits are recorded below.

Final test evidence for the whole project: `python3 -m pytest` -> **210 passed** (2 original starter tests + 208 added). `python3 -m src.main`, `python3 -m src.main --mode genre-first` and `python3 -m src.main --mode mood-energy` all run and exit 0; `git diff --check` is clean.

---

## Agentic Workflow (SF8)

**What task did you give the agent?**

Complete the whole CodePath AI110 Project 3 (Music Recommender Simulation) in one session in this repository: a required core (dataset, scoring, ranking, CLI, tests), the evaluation and model card, then four stretch challenges, with commits at milestones and no pushing.

**Prompts used:**

The brief was a single message. Its main constraints, quoted:

> Work efficiently in ONE focused session using the current repository. No parallel subagents, unnecessary package installation, large exploratory research, or repeated rewriting.
>
> Do not fabricate data sources, program output, experiments, model comparisons, or personal reactions.
>
> DO NOT push or submit. I will verify before that.
>
> src/recommender.py contains BOTH: 1. OOP interface: Song, UserProfile, Recommender 2. Functional interface: load_songs, score_song, recommend_songs ... Do not delete either. Implement them consistently, sharing scoring logic instead of creating contradictory algorithms.

The stretch prompts are quoted in the sections below.

**What did the agent generate or change?**

- Milestone 1 (commit `feat: implement music recommender and profile evaluation`): `src/recommender.py` (shared scoring core, CSV loader, ranking, both interfaces), `src/main.py`, `data/songs.csv` (20 songs added), `src/__init__.py`, `pytest.ini`, `tests/test_data.py`, `tests/test_scoring.py`, README approach section.
- Milestone 2 (commit `docs: evaluate recommendations and complete model card`): `src/experiments.py`, `README.md`, `model_card.md`.
- Milestone 3 (final commit): the four stretch features below, documentation updated to match the final code and fresh program output.
- Commands run by the agent included `git remote -v`, `git status -sb`, `python3 -m src.main` (with and without flags), `python3 -m src.experiments`, `python3 -m pytest`, and `git diff --check`. Nothing was pushed.

**What was verified after implementation?**

The agent ran code and tests while implementing the features (details per stretch below). It also generated the README output blocks from actual commands and checked the accompanying descriptions against those runs.

After the implementation, the student supplied the committed ZIP for an independent ChatGPT review. That review reran all 210 tests, exercised the CLI and experiment commands, and compared all nine README command-output blocks against fresh output (all nine matched). It also inspected the dataset, shared scoring and ranking code, diversity feature, and model card. The reviewer identified a small presentation caveat: individual scoring reasons and the total are separately rounded to two decimals, so the printed figures can differ by 0.01 while the underlying components still sum correctly. This was a code-and-output audit, not a real-listener evaluation. No backend change was needed.

---

## Design Pattern (SF10)

**Which design pattern did you use?**

A lightweight **Strategy** pattern, implemented as *named weight configurations* rather than a class hierarchy.

**How did AI help you brainstorm or implement it?**

The brief allowed "named weight configurations or a lightweight Strategy class". The agent chose frozen dataclasses (`ScoringWeights` for the numbers, `RankingMode` for a name, description and weights) because every strategy here differs only in how much each feature counts. Subclasses with their own `score()` methods would have invited exactly the contradictory scoring algorithms the brief warned against.

**How does the pattern appear in your final code?**

`RankingMode`, `RANKING_MODES` (the registry), `DEFAULT_MODE` and `get_mode` in `src/recommender.py`; `--mode` in `build_parser` in `src/main.py`. Every mode flows through the same `score_breakdown` / `rank_songs`.

---

## Stretch 1: Five additional song attributes

**Real prompt (verbatim from the brief):**

> Add at least FIVE meaningful new columns beyond the existing starter fields.
> A reasonable set: popularity (0–100), release_decade, instrumentalness (0–1), speechiness (0–1), liveness (0–1)
> Preserve the original ten columns.
> Populate each new field coherently for every song, noting that invented feature values are illustrative.
> Actually incorporate these attributes into scoring. Use optional user preferences and sensible modest weights so the features affect recommendations without creating artificial defaults for users who did not request them.
> Demonstrate at least one recommendation comparison where a new attribute changes a score or ranking.
> Document the real agent prompt, files modified, test evidence and review decisions in ai_interactions.md.

**Files modified:** `data/songs.csv` (five columns appended to all 30 rows), `src/recommender.py` (`OPTIONAL_COLUMNS`, `INTEGER_COLUMNS`, extended `FEATURE_RANGES`, new `Song` fields, `UserProfile.target_*` fields and `to_prefs`, new `ScoringWeights` fields, five new `_CLOSENESS_FEATURES` rows, `_parse_song_row` / `load_songs`), `src/experiments.py` (`attribute_demo`, extra `catalog_counts` lines), `tests/test_data.py`, `tests/test_stretch.py` (new), `README.md`, `model_card.md`.

**Test evidence:** `tests/test_stretch.py::test_each_new_attribute_can_decide_a_ranking` (parametrized over all five attributes), `test_new_attributes_add_nothing_when_user_did_not_ask`, `test_decade_preference_changes_real_catalog_ranking`, `test_popularity_preference_changes_real_catalog_scores_and_order`, the similarity-formula and invalid-preference tests; `tests/test_data.py` extended-column loading, type, range and invalid-value tests. Real comparison from `python3 -m src.experiments`: for a folk/nostalgic listener, adding `decade=1970` moves `Blue Hour Confessions` from #5 to #3 and drops `Focus Flow` out of the top 5.

**Review decisions:**

- The five columns are optional in the loader (a 10-column CSV still loads, so the starter test files and any earlier data keep working) but strictly validated when present. Integer columns (`popularity`, `release_decade`) reject non-whole numbers.
- Uniform 0.5 weights, with spans chosen from the catalog's spread (50 popularity points, 50 years, 0.5 for speechiness and liveness). No default target is created for a user who did not set one, and a test proves unchanged scores in that case.
- The original ten CSV columns were checked byte-for-byte against the previous commit (`cut -d, -f1-10` diff).
- Three candidate demonstrations were tried before choosing: instrumentalness 0.9 for the lofi listener only raised scores (the top four were already instrumental), `popularity=40` swapped two songs, and `decade=1970` for a folk listener changed the top 5. The README shows the last two and states the first honestly.
- A failing test was found when the new columns were added: the agent's own earlier test iterated all of `FEATURE_RANGES`, which now includes optional columns a 10-column file lacks. The agent fixed the test's scope (the five required numeric columns), not the code.

---

## Stretch 2: Multiple ranking modes

**Real prompt (verbatim from the brief):**

> Implement at least TWO genuinely different ranking strategies, preferably: Genre First, Mood/Energy First
> Use a small modular strategy design, such as named weight configurations or a lightweight Strategy class.
> Do not duplicate the entire scoring algorithm.
> Allow selection using src/main.py, ideally via argparse: python3 -m src.main --mode genre-first / python3 -m src.main --mode mood-energy
> Maintain a sensible default mode.
> Show a reproducible case where the modes produce different scores or rankings.
> Document the design choice and actual AI contribution in ai_interactions.md.

**Files modified:** `src/recommender.py` (`RankingMode`, `RANKING_MODES`, `DEFAULT_MODE`, `get_mode`), `src/main.py` (argparse `--mode`), `src/experiments.py` (`mode_comparison`), `tests/test_stretch.py`, `tests/test_report.py`, `README.md`, `model_card.md`.

**Test evidence:** `test_modes_reuse_the_same_scoring_rule` (each mode's score equals the formula applied to that mode's weights), `test_modes_produce_different_rankings_on_the_classical_edge_case`, `test_modes_change_scores_even_when_order_is_unchanged`, `test_oop_recommender_matches_functional_in_every_mode`, `test_mode_flags_change_the_output` (CLI). Real case: for the classical edge case, `balanced` and `genre-first` keep `Glass Cathedral` at #2 while `mood-energy` drops it and promotes `Laser Garden`; for the pop listener `mood-energy` brings in `Fuego en la Calle` and `Rooftop Lights`.

**Design choice and AI contribution:** all three modes are `ScoringWeights` presets (balanced 2.0/1.5/2.0, genre-first 4.0/1.0/1.0, mood-energy 0.5/3.0/3.0 for genre/mood/energy), so there is one scoring algorithm. The agent proposed the weight values; whether they are the *right* strategies is a judgment for the student to review. `balanced` is the default so every baseline result from the earlier milestones stays valid.

**Review decisions:**

- A real bug surfaced as soon as the presets were added: they instantiate `ScoringWeights()` at import time, and its validation called `_is_real`, which was defined further down the module, so importing `src.recommender` raised `NameError` and every test failed to collect. The agent moved the small helper functions above the dataclasses.
- The agent noticed, and kept in the documentation, an unflattering behavior: under `genre-first`, the edge case's slots 3-5 score 1.04, 1.03 and 1.03, so their order is nearly arbitrary.

---

## Stretch 3: Diversity and fairness

**Real prompt (verbatim from the brief):**

> Implement deterministic reranking that discourages too many tracks from the same artist, and optionally the same genre.
> Do not merely add a decorative diversity label.
> The final ranking should reflect the applied penalty. Show an example where the diversity rule changes the top results.
> Make the penalty configurable and preserve the ability to disable it for a fair baseline comparison.
> Explain the tradeoff: variety versus strict preference matching.
> Make explanations truthful about any score adjustments. Preserve stable tie-breaking and top-k semantics.
> Add tests to prove the effect.
> Document the impact in the Model Card, including who benefits and how diversity might hurt accuracy.
> Do not claim this solves fairness in a broad societal sense.

**Files modified:** `src/recommender.py` (`DiversityConfig`, `_diversify`, `rank_songs`, `Recommender`, `recommend_songs`), `src/main.py` (`--artist-penalty`, `--genre-penalty`), `src/experiments.py` (`diversity_demo` with a measured match-quality line), `tests/test_stretch.py`, `tests/test_report.py`, `README.md`, `model_card.md` (new "Variety reranking" subsection).

**Test evidence:** `test_disabled_diversity_equals_the_baseline_exactly`, `test_artist_penalty_changes_the_top_results` (real catalog: `Hyperdrive Heartbeat` leaves the pop top 5, `Fuego en la Calle` enters), `test_final_score_reflects_the_penalty` (`Focus Flow` 4.29 -> 3.54), `test_explanations_state_the_penalty_truthfully`, `test_reasons_still_sum_to_score_with_penalties`, `test_penalty_accumulates_per_repeat`, `test_genre_penalty_is_configurable_and_independent`, `test_diverse_scores_are_non_increasing`, `test_top_k_semantics_hold_with_diversity`, `test_diversity_is_deterministic_and_input_order_independent`, `test_ties_under_diversity_break_by_id`, `test_invalid_penalties_raise`, `test_oop_recommender_applies_the_same_diversity`.

**Design choice and AI contribution:** a greedy rerank picks the next song after subtracting repeat penalties for what is already chosen, and each penalty is added to the score breakdown as a negative component, so the displayed score, the order and the explanation come from the same numbers. It is off by default, so the baseline stays available. The impact, who benefits and the accuracy cost are written up in the model card; the measured cost is about 2% of combined match quality for the pop listener and zero for the lofi listener (same five songs, reordered).

**Review decisions:**

- The penalty size was explored before documenting an example: 0.5, 0.75 and 1.0 gave the same pop top 5, but 0.5 wins by only 0.02 (3.78 vs 3.80), so 0.75 was used for the demos because its margin is larger.
- A failing test was the agent's mistake, not the code's: it asserted that variety would change the pop listener's top 5 under `mood-energy`, but those five songs already have five different artists, so there is nothing to penalize. The agent rewrote the test (a `genre-first` case where `Max Pulse` does repeat, plus an explicit "nothing repeats, nothing changes" test).
- A claim in the README (that the classical edge case's top two do not change at 0.75) was verified with a real run before being written down: `Glass Cathedral` 3.12 -> 2.37, still above `Storm Runner` at 2.03.

---

## Stretch 4: Visual summary table

**Real prompt (verbatim from the brief):**

> Implement a clear, readable CLI summary using Python standard-library formatting if practical.
> Include: rank, song, artist, final score, scoring reasons
> Keep it readable with long song names and narrow terminal widths.
> Demonstrate real output in README.md.
> No screenshots or external UI libraries are necessary.

**Files modified:** `src/report.py` (new: `format_recommendation_table`, `format_recommendation_list`), `src/main.py` (`--format`, `--width`, wrapped header lines), `tests/test_report.py` (new), `README.md`.

**Test evidence:** `tests/test_report.py`: required columns and values, penalty reasons and final scores shown, no line wider than the width for widths 30-140 with very long titles and unbreakable words, nothing truncated, layout switch at 76 columns, no trailing whitespace, and a CLI test over every combination of mode, width (30, 50, 76, 100) and format. Real output (wide and `--width 50`) is in the README.

**Design choice and AI contribution:** the standard library only (`textwrap`). Below 76 columns the grid would be unreadable, so the layout switches to one compact block per song. The agent proposed the thresholds and column proportions.

**Review decisions:**

- A width test found a real bug: the table obeyed `--width`, but the profile titles and mode description printed by `main.py` did not (a 65-character profile title at `--width 50`). The agent fixed `main.py` rather than loosening the test.
- The agent first made that test skip the plain list format at narrow widths (6 skipped tests), then reversed that: it made `format_recommendation_list` width-aware so every combination is genuinely tested, and the suite now has no skipped tests.
- The acousticness reason was reworded to "acousticness 0.18, wants non-acoustic" so it fits on one line in the default-width table.
- Two overly convoluted assertions in the agent's own tests (an `or` fallback and a `.replace` workaround) were rewritten as precise checks, since they could have passed for the wrong reason.
