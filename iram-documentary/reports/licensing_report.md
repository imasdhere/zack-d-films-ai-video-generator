# Licensing report

Scope: everything that appears in, or was used to make, `renders/final/iram_lost_city_documentary.mp4`.
**This is not legal advice.** Before any commercial distribution, have a qualified person review the items marked ⚠.

## 1. Text sources shown or spoken

| Material | Licence / status | Use in film | Obligation |
|---|---|---|---|
| Quran Arabic text (Tanzil Uthmani v1.1) | CC BY 3.0. Tanzil terms: verbatim use, no alteration | Arabic verse cards (89:6–8; 46:24) | Credit "Tanzil" (done on the cards and in the credits). Text not modified (loaded programmatically). |
| Pickthall translation (1930) | Public domain (author d. 1936; published 1930) | Narration quotes and on-screen translation | None. Credited anyway. |
| Saheeh International (1997) | © Abul-Qasim / Al-Muntada | Two short phrases on the comparison card and in narration ("Iram — who had lofty pillars", "the likes of whom") | ⚠ Brief quotation for commentary and comparison. Normally treated as fair use / quotation right. Confirm for commercial release. |
| Tafsir al-Ṭabarī; Tafsir Ibn Kathīr (Arabic) | Classical works (public domain). Digital edition via quran.com | Short Arabic quotes plus the production's own English translations | None |
| Hadith texts (sunnah.com) | Classical Arabic: public domain. English translations on sunnah.com carry their own rights. | Short quotes (one sentence each) | ⚠ Short quotation, credited "text as published on sunnah.com" |
| Periplus (Schoff 1912); Pliny (Bostock & Riley 1855) | Public domain | Paraphrased and briefly quoted | None |
| NYT lede (5 Feb 1992); Zarins NOVA interview (1996); Bertram Thomas (1931) | © holders | One-sentence quotations with attribution | ⚠ Short quotation for criticism/reporting. Standard documentary practice. Confirm for commercial release. |

## 2. Images

| Source | Licence | Obligation |
|---|---|---|
| NASA / JPL / GSFC / JSC images (PIA01721, PIA01302, PIA11084, PIA02656, PIA21803, GSFC Archive e001903 and e001930, sts059-s-109, iss069e010867, iss069e003275) | NASA media is generally not copyrighted in the US (NASA Media Usage Guidelines). ASTER images credit METI/AIST/Japan Space Systems. ISS images were taken by astronaut Sultan Alneyadi (UAE) on a NASA mission and are published by NASA. | Credit burned in. No NASA endorsement implied. ⚠ For international-partner photographs, confirm NASA's terms if distributing commercially outside the US. |
| Wikimedia Commons photographs (only if downloaded; see `assets/archaeological_photographs/commons_licences.json`) | Per file: PD, CC BY 2.0/2.5, CC BY-SA 2.0/3.0/4.0 | Attribution burned in (author, licence). ⚠ **CC BY-SA**: an adapted image (cropped, graded, animated) must stay under CC BY-SA, and whether that extends to the whole film is debated. Keep credits and link to the licence in the description. |
| AI-generated images (SDXL base 1.0 + SDXL-Lightning) | CreativeML OpenRAIL++-M. You may use outputs commercially. The use-based restrictions (Attachment A) apply: no deception, no harm, and so on. | Disclose that AI was used (done: on-screen labels and credits). The outputs are not presented as photographs of real sites. |
| Blender renders | Your own outputs (Blender GPL does not apply to renders) | None |
| Depth maps (Depth-Anything-V2-**Small**) | Apache-2.0 | None. Do not switch to the Base/Large models without checking: those are CC-BY-NC-4.0. |
| Maps: Copernicus GLO-90 DEM | Free licence with attribution: "© DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved" | Credit on every map frame and in the credits (done) |
| Maps: Natural Earth | Public domain | None. Credited anyway. |

## 3. Audio

| Source | Licence | Notes |
|---|---|---|
| Narration: Qwen3-TTS 1.7B (VoiceDesign + Base), voice designed from a text description, **not cloned from any real person** | Apache-2.0 (code and weights) | A synthetic voice. The credits disclose it. |
| Sound effects | Procedurally synthesised from noise by `scripts/editing/sfx.py` | Original work. No third-party samples. **No music.** |

## 4. Fonts (rendered into the picture)

Amiri, Amiri Quran, Cinzel and EB Garamond: SIL Open Font License 1.1 (embedding and rendering allowed). Inter: SIL OFL 1.1.

## 5. Software

Using the tools does not impose obligations on the film. ComfyUI (GPL-3.0) and Blender (GPL-3.0) apply only if you redistribute modified versions of those programs. FFmpeg with libx264 is GPL; no redistribution happens here.

## 6. Commercial-use summary

| Item | Commercial use OK? |
|---|---|
| Qwen3-TTS, Kokoro, SDXL, SDXL-Lightning, Depth-Anything-V2-Small | Yes (Apache / OpenRAIL++, within the use restrictions) |
| Excluded: F5-TTS weights, Fish Audio weights, Depth-Anything-V2 Base/Large | No (non-commercial). Not used. |
| NASA imagery | Generally yes, without implying endorsement |
| CC BY-SA photographs | Yes, with attribution and share-alike ⚠ |
| Short third-party quotations | Normally yes as quotation ⚠ |
