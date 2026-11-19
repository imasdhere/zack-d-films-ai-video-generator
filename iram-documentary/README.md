# THE LOST CITY OF IRAM
### In Search of the People of the Pillars

A **21:01** historical investigation documentary (1920×1080, 24 fps, H.264 High, AAC stereo, −16 LUFS, **no music**; 17/17 automated QC checks pass). It covers Iram Dhāt al-ʿImād (Quran 89:6–8), the people of ʿĀd, the classical exegetical debate, the search for "Ubar" at Shisr in Oman, and a recent epigraphic proposal that points to Wadi Ramm in Jordan. The film keeps seven evidence levels visibly apart: Quranic text, authentic hadith, classical scholarship, later legend, archaeology, scientific hypothesis and artistic reconstruction.

## Deliverables

| # | Deliverable | Location |
|---|---|---|
| — | **Main documentary** | `renders/final/iram_lost_city_documentary.mp4` (3.7 GB, not in git: too large; regenerate with `documentation/workflow.md`) |
| 1 | Final screenplay | `screenplay/final_fact_checked_script.md` (source: `screenplay/script.yaml`) |
| 2 | Chapter-by-chapter narration | `screenplay/chapter_00_cold_open.md` … `chapter_06.md`; audio in `assets/narration/raw/` |
| 3 | Bibliography | `research/bibliography.md` |
| 4 | Claim verification matrix | `research/claim_verification_matrix.csv` |
| 5 | Storyboard | `storyboard/master_storyboard.csv`, `storyboard/scene_list.md`, `storyboard/shots.yaml` |
| 6 | Subtitles (SRT) | `assets/subtitles/iram_lost_city_documentary.en.srt` |
| 7 | Visual generation prompts | `storyboard/assets.yaml`; per-image records `assets/images/*.json` (prompt, seed, full ComfyUI workflow) |
| 8 | TTS configuration | `configuration/tts_config.yaml`, `configuration/pronunciation_lexicon.yaml`, `workflows/tts/eval/README.md` |
| 9 | Dependency register | `reports/dependency_register.md` |
| 10 | Licensing report | `reports/licensing_report.md` |
| 11 | Hardware audit | `reports/system_hardware_audit.md` |
| 12 | Cost report | `reports/cost_report.md` |
| 13 | Installation documentation | `documentation/installation.md`, `documentation/workflow.md`, `documentation/troubleshooting.md` |
| 14 | Quality-control report | `reports/quality_control_report.md` (+ `reports/qc_metrics.json`) |
| 15 | Thumbnail | `renders/final/thumbnail.jpg` |
| 16 | Lower-resolution review copy | `renders/final/iram_lost_city_documentary_review_540p.mp4` |

## Research in one paragraph

The Quran names Iram once (89:7) and describes it as *dhāt al-ʿimād*. Al-Ṭabarī (d. 923) reports earlier views (Iram as Alexandria, Damascus, a nation, a clan or an ancestor) and prefers "a tribe of ʿĀd". He reads *ʿimād* as the poles of a travelling people's tents, adding that "no building of theirs with columns is known through any authentic report". Ibn Kathīr (d. 1373) agrees, and calls the golden-city and Ibn Qilāba stories fables of the *Israʾīliyyāt* with unsound chains. In 1992, Landsat-guided fieldwork at Shisr (Dhofar) uncovered a real caravan fortress, partly collapsed into a sinkhole, and it was hailed as "Ubar". Its excavators themselves argued that Ubar was a region and people (Ptolemy's Iobaritae). UNESCO lists Shisr as "the caravan oasis of Shisr/Wubar", and scholars do not accept Shisr = Iram. In 2025 Ahmad Al-Jallad surveyed pre-Islamic inscriptions by members of a tribe called ʿĀd in the north and proposed a link with Wadi Ramm, whose ancient name was ʾrm. See `research/`.

## Reproduce

See `documentation/workflow.md`. Heavy files (Python environments, about 17 GB of model weights, caches) live outside git, in `/home/user/iram-work`.
