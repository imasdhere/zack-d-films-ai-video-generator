# Production log

All times are the container's local time on 2026-11-19.

| Time | Stage | Event / decision |
|---|---|---|
| 11:13 | 1 Audit | The environment is a Linux cloud container (4 vCPU Xeon, 15 GiB, no GPU), not a Mac. No local machine was attached. Network: allow-list proxy. |
| 11:15 | 1 Audit | Hugging Face, PyTorch CDN, Whisper, Wikimedia and Tanzil were blocked. **User approved** adding those hosts to the "AI video studio" environment. |
| 11:17 | 3 Install | ML venv: the PyTorch CPU index redirects to a blocked host, so PyPI wheels were used. Kokoro needs Python < 3.13, so Python 3.12 was used. `bpy` 5.3.0 installed on Python 3.13. |
| 11:20 | 4 Research | Quran (Uthmani) and translations downloaded from Tanzil. All 40 verses containing عاد extracted; 23 verses (24 occurrences) confirmed by script. |
| 11:21 | 4 Research | Web-reader agents could not reach research hosts. **User approved** adding the research sites (Wikipedia, UNESCO, JPL, sunnah.com, quran.com, tafsir sites, archive.org …). |
| 11:24 | 4 Research | Tafsir al-Ṭabarī and Ibn Kathīr on 89:6–8 retrieved verbatim (quran.com API). Key finding: al-Ṭabarī prefers "tent poles" and says no columned building of ʿĀd is known by authentic report. Ibn Kathīr calls the golden city a fable. |
| 11:30 | 4 Research | sunnah.com and UNESCO pages pass Cloudflare in headless Chromium. Hadith Bukhari 1035 / 4828–29 and Muslim 899b / 900a verified. |
| 11:33 | 4 Research | Wikipedia "ʿĀd" points to Al-Jallad (2025): a tribe of ʿĀd is attested in pre-Islamic northern inscriptions (Wadi Ramm). Its wording "widely accepted" was **not adopted**; the film calls it a proposal. |
| 11:38 | 4 Research | Ibn Khaldūn's Muqaddimah text could not be retrieved (scanned pages only), so it was **excluded** rather than quoted from memory. |
| 11:40 | 4 Research | PubMed: Fleitmann et al. 2003 (Science) and Zaki et al. 2025 (Commun. Earth Environ.) abstracts verified. |
| 11:42 | 3 Install | HF downloads stalled on `us.aws.cdn.hf.co`. **User approved** adding the HF CDN hosts. All weights downloaded (about 17 GB). |
| 11:45 | TTS eval | Same 145-word sample: Kokoro (6 voices plus 1 blend) and Qwen3-TTS VoiceDesign. Objective metrics (Whisper WER, Arabic terms, F0, SQUIM PESQ/STOI/SI-SDR). |
| 11:58 | TTS eval | Voice designed (seed 7) and cloned with the Qwen3 Base model: PESQ 4.33, WER 0.095, F0 about 91 Hz. **Primary: Qwen3-TTS clone. Backup: Kokoro bm_lewis.** |
| 12:01 | 8 Narration | Full narration started (75 segments, sentence by sentence, resumable). |
| 12:05 | 6 Storyboard | 144 shots planned (`storyboard/shots.yaml`), 52+ AI images defined with labels and style grammar (photo / recon / legend). |
| 12:10 | 7 Visuals | ComfyUI (CPU, bf16) was **killed for lack of memory** while loading SDXL (11 GB RSS) alongside narration. Image generation was postponed until narration finishes. |
| 12:12 | 7 Visuals | Copernicus GLO-90 DEM mosaics built (Arabia 605 tiles, Dhofar, Wadi Rum). Natural Earth vectors and OFL fonts fetched. |
| 12:20 | 7 Visuals | Typography/diagram renderer and map renderer built. Arabic shaping verified (raqm). Coordinates verified from Wikipedia page metadata. |
| 12:28 | 7 Visuals | Blender procedural dunes looked like CG, so the two dune animations were replaced by AI stills with depth parallax. Blender is kept for the column layout (guide for SDXL img2img) and the Shisr cutaway schematic. |
| 12:30 | 7 Visuals | Wikimedia Commons rate-limited (HTTP 429) the API and file downloads from this egress IP. NASA public-domain imagery added (ASTER Rubʿ al-Khālī, ISS Dhofar and dunes, Salalah, Wadi Rum, STS-59 Endeavour liftoff). Labelled fallbacks defined for every Commons photo. |
| 12:45 | 8 Narration | Found that Qwen3-TTS occasionally misses its end token and generates up to 2048 tokens (about 170 s) per sentence, costing minutes per segment. Fix: per-sentence `max_new_tokens` cap plus duration sanity check with seed retries. Narration restarted (resumable). |
