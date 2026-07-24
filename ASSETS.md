<!-- GENERATED FILE — DO NOT EDIT BY HAND.
     Source: scripts/assets-registry.json · Generator: scripts/build-assets-registry.py
     Drift-gated by `make assets` (part of `make check`): byte-parity, per-file
     sha256 match, and a coverage sweep over web/public/, site/public/,
     site/src/assets/, site/og/. -->

# ASSETS.md — asset provenance registry

Every committed binary/vector asset is recorded here with origin, license, and a
provenance statement; file hashes are drift-gated. Policy: original, hand-written
geometry only; references may be studied for direction and must be named; no
traced, copied, or auto-generated third-party geometry; no stock, no clip-art, no
AI-image imports. Fonts are the repository's licensed set only.

Project-original assets are licensed Apache-2.0 as part of the repository; see
LICENSE, NOTICE, LICENSING.md, and ADR-0028. Third-party assets retain the separate
upstream licenses recorded in their rows; this registry does not alter those terms.
`site/ASSETS.md` is a pointer to this registry.

## Reference imagery (preamble)

Design references (screenshots of third-party marketing/product sites, studied during the redesign) were used for layout/interaction conventions only and are not committed, not shipped, and not copied from; no shipped asset is derived from them. Icon design adopts Lucide's published grid conventions (24 grid, 2 px stroke, round caps) for visual compatibility; no Lucide path is reused, traced, or modified.

## 1. E1 "Convergence Seat" mark (+ favicon copy)

- **type:** mark · **origin:** original · **license:** Apache-2.0 · **date:** 2026-07-21
- **source:** in-repository vector work, 2026-07-21 redesign cycle
- **provenance:** Original vector work created in-repository; drawn from geometric primitives (original 45-degree stroke construction); no third-party vector source, no font-outline tracing (lockup text set in IBM Plex per its OFL terms). Ball-detent engineering conventions (90-degree V, seat depth, apex daylight) studied as facts, not artwork. Working history retained privately; the committed files are canonical.
- **files (sha256):**
  - `web/public/brand/e1-convergence-seat.svg` — `5e6f4fa6456a53e0ea0a3963afe801fbf541da88b082b88bb74eb5327204057d`
  - `site/public/favicon.svg` — `ac08e5eba5a0654ce522662e10243b611bd923f175d0a9c777dab740b590b196`

## 2. D1 seat mark (core geometry)

- **type:** mark · **origin:** original · **license:** Apache-2.0 · **date:** 2026-07-21
- **source:** in-repository vector work, 2026-07-21 redesign cycle
- **provenance:** Original vector work; the D1 core geometry the E1 mark builds on. Same construction posture as the E1 row.
- **files (sha256):**
  - `web/public/brand/d1-seat.svg` — `91e670620decb365661bc40d1c33c151fbee1cc02ea6f5810ebe58f69c037add`

## 3. IBM Plex Sans / Mono woff2 subsets + OFL license text

- **type:** font · **origin:** third-party-verbatim · **license:** OFL-1.1 · **date:** 2026-07-21
- **source:** @ibm/plex-sans@1.1.0 / @ibm/plex-mono@2.5.0 (npm)
- **provenance:** Upstream-built Latin1 subsets copied byte-identically by fonts:sync (drift-checked in web-check/site-check); NOT locally modified or re-subsetted, so the 'Plex' Reserved Font Name clause for Modified Versions is not triggered. OFL.txt must always travel adjacent to the font files. Local re-subsetting is prohibited without a registry + counsel revisit.
- **files (sha256):**
  - `web/public/fonts/ibm-plex-sans-400.woff2` — `b5ad7bd39f996144915f0ad9849a90183b27d8c28ad97ed98af5b1bebc51f6b1`
  - `web/public/fonts/ibm-plex-sans-500.woff2` — `b5610af04d0d4b5a14a621d96d974b993e945a065db1a8861918f69ef9321934`
  - `web/public/fonts/ibm-plex-sans-600.woff2` — `fff0ab3a88b0b4aa0b693e4f0201359a15183b08e3fa5696d1918d8f0ade8ad5`
  - `web/public/fonts/ibm-plex-mono-400.woff2` — `e8993d946649b9d01abb1ed06d574b19d8ea3e66b5c3948602db335c44c18e56`
  - `web/public/fonts/ibm-plex-mono-500.woff2` — `41201b658a328b9d00368215c2f1102770f80b15952ab82631e4006255e6365d`
  - `web/public/fonts/ibm-plex-mono-600.woff2` — `b7acd05041ab65f3b7039e218ddd893065e11a07e85ea85019473152a51b6b7d`
  - `web/public/fonts/OFL.txt` — `7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da`
  - `site/src/assets/fonts/ibm-plex-sans-400.woff2` — `b5ad7bd39f996144915f0ad9849a90183b27d8c28ad97ed98af5b1bebc51f6b1`
  - `site/src/assets/fonts/ibm-plex-sans-500.woff2` — `b5610af04d0d4b5a14a621d96d974b993e945a065db1a8861918f69ef9321934`
  - `site/src/assets/fonts/ibm-plex-sans-600.woff2` — `fff0ab3a88b0b4aa0b693e4f0201359a15183b08e3fa5696d1918d8f0ade8ad5`
  - `site/src/assets/fonts/ibm-plex-mono-400.woff2` — `e8993d946649b9d01abb1ed06d574b19d8ea3e66b5c3948602db335c44c18e56`
  - `site/src/assets/fonts/ibm-plex-mono-500.woff2` — `41201b658a328b9d00368215c2f1102770f80b15952ab82631e4006255e6365d`
  - `site/src/assets/fonts/OFL.txt` — `7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da`

## 4. Domain icon set (16 glyphs)

- **type:** icon-source · **origin:** original · **license:** Apache-2.0 · **date:** 2026-07-21
- **source:** identity cycle (N4 design), 2026-07-21
- **provenance:** Original hand-written paths. Lucide's published grid conventions (24 grid, 2 px stroke, round caps) adopted for compatibility; no Lucide path reused, traced, or modified. seat-settle derives from the in-house D1 geometry. Per-file provenance comment embedded in each SVG; call sites always pair an icon with a visible text label.
- **files (sha256):**
  - `site/src/assets/icons/intent.svg` — `74fcafd9f36a53f516b6d6c6d0856f5306871f5aaa91bd34ad37b067074d6b05`
  - `site/src/assets/icons/stable-id.svg` — `173b02f264b679017c1ca06f5305b365926e6072e6d86611633fe68b320d4ff4`
  - `site/src/assets/icons/persist.svg` — `82a38440c0968ebe608c5ed3f827a785427357fa6a7b8c13a8bead754107d95e`
  - `site/src/assets/icons/gate-allow.svg` — `bf3400e2211e870c8e6fe960d4037d69bfe4d595785e80334758dbdf9ea8fad7`
  - `site/src/assets/icons/gate-deny.svg` — `526fd3f177d9bb9c7d02f93a0495ad9bab24af2da0b2a54b107acd044c22c02c`
  - `site/src/assets/icons/boundary.svg` — `f43d6d9cc910b244c1e5a17a054de6469103510b735041d37582bc96ce0d5063`
  - `site/src/assets/icons/seat-settle.svg` — `e5992a0bf41adc8dcd23f40106d91733c8c62245fd6a8242f018900e597f2603`
  - `site/src/assets/icons/ambiguous.svg` — `e430ce513ae17da91f3582dca3e9654d19f0282b7efca49e5266459edd0d7018`
  - `site/src/assets/icons/probe.svg` — `2f1c20a724619f5bb620cb7f6ecf845f149f66126eb79cc5929d4b290abeba01`
  - `site/src/assets/icons/evidence.svg` — `c982e38a8ca6dced2423d93ec2dcbd03f00411216c4173957ef89e6da71c803f`
  - `site/src/assets/icons/duplicate-reject.svg` — `67dba10ebeb2a3eabe2350b92b053d36085bc4e17e6d9f1554918d6e7e6cbc11`
  - `site/src/assets/icons/orphan-absence.svg` — `e07d6f6a59cae9ec936fa8627b6a28be1bd8e3414a68b7867e7dc7f198d48fad`
  - `site/src/assets/icons/crash-seam.svg` — `d541f3726ce4c9f07b646d7bd1c26dabfb1b700194a20c6561b2d2987c86c78b`
  - `site/src/assets/icons/recovery.svg` — `c59b151331990c93ad038515ab8de7a3fe75c82a1d40b5cc781c9fd80c475b39`
  - `site/src/assets/icons/ledger.svg` — `68c8316bfa7ccaf782259b9c1b13b02c468620dced0503539c6e77651c54d453`
  - `site/src/assets/icons/adapter-tier.svg` — `69a3bb09f5f5eb599df1260a3560c67aa6ea621452efb271dc93e1b2d4da7edc`

## 5. OG social card template (1200x630)

- **type:** illustration · **origin:** original · **license:** Apache-2.0 · **date:** 2026-07-21
- **source:** identity cycle (N4 design), 2026-07-21
- **provenance:** Original composition of the E1 mark + the One-Way Seat sequence strip; text slots are template variables; colors from the ratified token set.
- **files (sha256):**
  - `site/og/template.svg` — `4692d45421777117e6692a07de3da315c407917cc2f223932d60978224d4a421`

## 6. OG rendered cards (8 files)

- **type:** illustration · **origin:** self-generated · **license:** Apache-2.0 · **date:** 2026-07-21
- **source:** rendered from site/og/template.svg by site/scripts/build-og.mjs
- **provenance:** Mechanical render of the template via pinned Playwright Chromium with the repo's IBM Plex subsets; hashes additionally pinned in site/og/manifest.json and drift-gated by build-og.mjs --check.
- **files (sha256):**
  - `site/public/og/og-default.png` — `d52afd75163307c52fa6d76069a82a8abbf5366063ccb4eed92615754e5abb1e`
  - `site/public/og/og-platform.png` — `3772864fb442376f69693cc2de310540480d27c1cc6a6b62ab19d793bb29323b`
  - `site/public/og/og-how-it-works.png` — `611f0b40eec7b2ec1ff29eee1238b2cd482cd15d5520424f7438a3da79040673`
  - `site/public/og/og-benchmark.png` — `dd3810799887e708aff806d3ba4a061c726478b79c5952989c236d7a8351afe6`
  - `site/public/og/og-demo.png` — `7e878bc8e6110af304cd0de64cecf86ae0609dda8e8b60e617b1641ac0422596`
  - `site/public/og/og-docs.png` — `6837b8de23d48056dac5e78388672df0120a6da86330f8117442a4bf72940527`
  - `site/public/og/og-research.png` — `04f363dac183548a18ff1fa00fd628ebf2d068d09511ab585345df08abe15fa9`
  - `site/public/og/og-install.png` — `401190017999c68967bbdd6738ec173cf1da2171205995b59da9d1a39276a249`

## 7. Workbench screenshots (4 files)

- **type:** screenshot · **origin:** self-generated · **license:** Apache-2.0 · **date:** 2026-07-21
- **source:** site/scripts/capture-workbench.mjs (Playwright shots project)
- **provenance:** Captured from the running fixture-backed web/ app at 1440x900 (2x DPR), both themes, SYNTHETIC FIXTURE banner deliberately in frame (synthetic data, engine capture seed 777); no third-party content. Re-capture after any workbench visual change.
- **files (sha256):**
  - `site/public/images/workbench-effects-dark.png` — `7da12a5e74b8bbb35d1112077ffca6161c22a0d2e34f7d6f1f7c3640440629a8`
  - `site/public/images/workbench-effects-light.png` — `018f068570acbf03b8f6b0f6668b82691b5ff3e3848a4c15e6716e56cfe3ea19`
  - `site/public/images/workbench-inspect-dark.png` — `82d12fa2e10a48e1953e4e8ee06dc3c5eec406f5f973c72dfaa07d2493969594`
  - `site/public/images/workbench-inspect-light.png` — `fb0e61defb4ec8c99511c6fbd54c8f46b7436fc5e0fb110eabc5af4d81fd9d6a`

## 8. MSW service worker (generated vendor file)

- **type:** icon-source · **origin:** third-party-verbatim · **license:** MIT · **date:** 2026-07-21
- **source:** msw@2.15.0 (generated by `msw init`; dev/test/review builds only)
- **provenance:** Generated verbatim by the msw CLI; never part of a live/production bundle (mock mode is refused in production builds). Recorded here because it is a committed third-party file under web/public/.
- **files (sha256):**
  - `web/public/mockServiceWorker.js` — `26171599d94d5445297303f3a1f1cedec26835ea3d0057dcfa92ec520cb35cca`
