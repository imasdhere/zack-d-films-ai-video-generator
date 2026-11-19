# CLAUDE.md — The Lost City of Iram (documentary project)

This folder is a self-contained documentary production. It is unrelated to the parent repository's MuAPI short-video skill, so ignore the parent `AGENTS.md`/`SKILL.md` when working here.

## Rules that must not be broken

1. **Evidence integrity.** Every factual sentence in `screenplay/script.yaml` must map to a claim ID in `research/claim_verification_matrix.csv`. Do not add claims that the matrix does not support. Never invent quotations, hadith, citations or discoveries.
2. **Keep the evidence levels apart**: Quran, hadith, classical scholarship, later legend, archaeology, scientific hypothesis, artistic reconstruction. On-screen tags use the colour grammar in `scripts/animation/graphics.py::EVIDENCE`.
3. **The Prophet Hūd is never depicted.** The people of ʿĀd appear only as distant, anonymous figures.
4. **No music**, ever. Sound is procedural natural ambience only (`scripts/editing/sfx.py`).
5. Quranic Arabic is always loaded from `research/raw_sources/quran/quran-uthmani.txt` (Tanzil). Never retype it.
6. Do not spend money or publish anything without the owner's approval.

## Where things are

- Single source of truth for narration: `screenplay/script.yaml`. Generated docs: `scripts/research/build_screenplay_docs.py`.
- Shots: `storyboard/shots.yaml`. Asset prompts and labels: `storyboard/assets.yaml`. Photos and credits: `assets/archaeological_photographs/photo_map.yaml`.
- Pipeline and commands: `documentation/workflow.md`. Installation: `documentation/installation.md`.
- Heavy files (venvs, models, caches) live in `/home/user/iram-work`, outside git.
