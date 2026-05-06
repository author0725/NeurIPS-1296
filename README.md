# Reproducibility code & data — NeurIPS 2026 paper #1296

> **When Classical Inference Fails: A Multi-Criteria Diagnostic for Causal Discovery on Latent-Factor Panels**

This repository contains everything needed to reproduce or verify the numerical claims in the paper.

## What's in here

| File / Dir                          | What it is                                                                                                   |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `README.md`                         | This file.                                                                                                   |
| `verify_paper_numbers.py`           | **Verifier (CLI).** Extracts numbers from the paper's `.tex` sources at runtime and asserts each against the canonical CSV/JSON. |
| `verify_paper_numbers.ipynb`        | **Verifier (Colab notebook).** Same as the script, formatted for one-click Colab execution.                  |
| `paper_extractors.py`               | Module: extracts numerical values from the paper's `.tex` sources at runtime. Imported by the verifier.      |
| `canonical_extractors.py`           | Module: extracts numerical values from the canonical CSVs/JSONs at runtime. Imported by the verifier.        |
| `verifier_core.py`                  | Defines all 304 paper-extractor / canonical-extractor pairs (`CHECKS` list) and the runner.                  |
| `requirements.txt`                  | Minimal pip dependencies for the verifier (`pandas`, `numpy`).                                               |
| `NeurIPS2026_1296_pipeline.ipynb`   | The full analysis pipeline, identical to the copy inside the tarball. Re-run this to regenerate every CSV.   |
| `BUNDLE_README.md`                  | Copy of the README inside the tarball. Read this without extracting if you want re-run instructions.         |

The **reproducibility tarball** itself (`neurips_1296_bundle.tar.gz`, ~73 MB) is too large for the repo's flat tree, so it is published under [Releases](../../releases) instead. See instructions below.

---

## Path A: Verify the paper without re-running anything (~30 seconds)

This is what reviewers will typically want. The verifier does two things at runtime for every numerical claim:

1. **Extracts the value from the paper's `.tex` sources** (e.g., a cell of Table 2, an inline value like `sup-Wald = 10.8`).
2. **Extracts the corresponding canonical value from the depository's CSV/JSON** outputs.

Then it compares the two within tolerance. **Neither side hard-codes expected values.** The mapping between paper claims and canonical sources is defined by paired extractor functions in `verifier_core.py`.

### From the command line

```bash
# 1. Clone the repo and install verifier dependencies
git clone https://github.com/author0725/NeurIPS-1296.git
cd NeurIPS-1296
pip install -r requirements.txt          # only pandas + numpy

# 2. Download the tarball from Releases (look for neurips_1296_bundle.tar.gz)
#    https://github.com/author0725/NeurIPS-1296/releases/latest
#    Place the downloaded file in this directory.

# 3. Run the verifier
python verify_paper_numbers.py --tarball neurips_1296_bundle.tar.gz
```

The paper sources are auto-resolved from the tarball's `paper/` subdirectory — no extra arguments needed.

If you prefer to download the tarball directly from the command line:

```bash
# Replace v1.0 with the latest release tag if it has changed
curl -L -o neurips_1296_bundle.tar.gz \
    https://github.com/author0725/NeurIPS-1296/releases/download/v1.0/neurips_1296_bundle.tar.gz
```

Expected output (truncated):

```
==============================================================================
  NeurIPS 2026 paper #1296 — paper-vs-canonical verifier
==============================================================================
  Extracting tarball to: /tmp/verify_1296_xxxxxx
  Depository:  /tmp/verify_1296_xxxxxx/NeurIPS2026_1296
  Paper dir:   /tmp/verify_1296_xxxxxx/NeurIPS2026_1296/paper
  Paper files: appendix_A.tex, appendix_B.tex, appendix_C.tex, checklist.tex,
               eda_appendix.tex, lsc_appendix.tex, main.tex
  Total checks:      304
==============================================================================

==============================================================================
  SUMMARY
==============================================================================
  Total checks:  304
  Passed:        304
  Failed:        0
  Errors:        0
==============================================================================
```

**Optional flags:**

- `--strict` — exit code 1 if any FAIL (default: exit 0 with summary).
- `--verbose` — list every PASS line, not just FAILs.
- `--depository /path/to/extracted/dir` — skip extraction (use an already-unpacked dir). Pair with `--paper /path/to/paper` if your paper is elsewhere.
- `--paper /path/to/paper` — override the paper-source location (defaults to `<depository>/paper/`).
- `--no-color` — disable ANSI color codes.

The script needs only the standard library plus `pandas` and `numpy`. No GPU, no project-specific dependencies.

### On Colab (no local install)

Open `verify_paper_numbers.ipynb` directly in Colab (File → Upload notebook).

The notebook prompts you to upload four files:
- `neurips_1296_bundle.tar.gz` — download from the [Releases](../../releases/latest) page first
- `paper_extractors.py`
- `canonical_extractors.py`
- `verifier_core.py`

Then run all cells. Total runtime: ~1 minute (most of which is uploading the tarball).

### What the verifier checks

All 304 individual paper claims:

- **Tables 1–5** (main paper): every cell value (ΔPR, std, CRPS, T_cov, p-values, n_pass counts).
- **Tables 7–14** (appendices B and C): every cell — calibration tables, σ_Λ sweep, dynsplit sweep, WB-WPP / V-Dem-60 detail, λ adversary sweep.
- **Table 16** (EDA appendix): condition counts and correlation-shift values.
- **Inline numerical claims**: β-range on V-Dem-16, R3 ρ=0.7 (ΔPR, T_cov), Elected_officials saturation / sup-Wald / β-shift, honest-cluster PR/ΔPR ranges, calibrated-adversary trajectory, V-Dem variance ratio.

Tolerances follow the convention "strict where the paper is precise; lenient where it says ≈":

| Tolerance | Used for                                                  |
| --------- | --------------------------------------------------------- |
|   ±0.001  | individual values where paper is precise to 3+ decimals   |
|   ±0.005  | cross-method aggregates                                   |
|   ±0.01   | "≈ X" claims rounded to 2 decimal places                  |
|   ±0.05   | "≈ X" claims rounded to 1 decimal place                   |
|  `≤` only | p-values stated as `p ≤ X` (checked as inequality)        |

Each Check in `verifier_core.py` carries a `paper_loc` (e.g., `"main.tex Table 2, row 'V-Dem-16'"`) that gets printed on FAIL — so if the paper and canonical disagree, the FAIL line tells you exactly where in the `.tex` source to look.

### Why "extract at runtime" rather than "hard-code"?

This way, the verifier itself is auditable. Each check has two callables — one that pulls a value from the paper, one that pulls a value from a CSV — and you can read them in `verifier_core.py` to see exactly what is being compared, against what, with what tolerance. If the paper text changes in a way that breaks an extractor's regex, the verifier reports the extraction error pointing at the `.tex` location, rather than silently matching a stale hard-coded value.

The full mapping is in `verifier_core.py` as the `CHECKS` list. **That file is the canonical audit trail — open it to see exactly what each check does.**

---

## Path B: Re-run the full pipeline (~14–18 hours on Colab T4)

If you want to regenerate every CSV from the data, follow the instructions in `BUNDLE_README.md` (which is also inside the tarball at `NeurIPS2026_1296/README.md`). The short version:

1. Download `neurips_1296_bundle.tar.gz` from the [Releases](../../releases/latest) page.
2. Extract it to your Google Drive at `MyDrive/NeurIPS2026_1296/`.
3. Open `NeurIPS2026_1296_pipeline.ipynb` in Colab (or use the copy inside the tarball — they are identical).
4. Runtime → Run all.
5. After completion, point the verifier at your re-generated tree:

   ```bash
   python verify_paper_numbers.py \
       --depository /content/drive/MyDrive/NeurIPS2026_1296 \
       --paper      /content/drive/MyDrive/NeurIPS2026_1296/paper
   ```

You should still see 304/304 PASS, modulo small Monte-Carlo drift on stochastic methods (cMLP / NAVAR / DYNOTEARS). The paper's tolerances are loose enough to absorb that drift.

A full re-run requires:

- GPU (T4 or better; cMLP and NAVAR are GPU-trained).
- ~16 GB RAM.
- ~80 GB disk (intermediate panels and `W_hats/` accumulate).

---

## Repository layout

```
.
├── README.md                          ← this file
├── requirements.txt                   ← pandas + numpy (verifier deps only)
├── verify_paper_numbers.py            ← CLI verifier
├── verify_paper_numbers.ipynb         ← Colab verifier notebook
├── paper_extractors.py                ← paper-side runtime extractor module
├── canonical_extractors.py            ← canonical-side runtime extractor module
├── verifier_core.py                   ← CHECKS list + runner
├── NeurIPS2026_1296_pipeline.ipynb    ← full analysis notebook
└── BUNDLE_README.md                   ← copy of the README inside the tarball

Releases (downloaded separately, ~73 MB):
└── neurips_1296_bundle.tar.gz
    └── NeurIPS2026_1296/
        ├── README.md                  ← internal README (same as BUNDLE_README.md)
        ├── MANIFEST.sha256            ← SHA-256 of every file
        ├── data/                      ← input panels (3 CSVs)
        ├── src/                       ← Python modules (NAVAR, DYNOTEARS, etc.)
        ├── analysis/                  ← analysis scripts
        ├── paper/                     ← paper sources (.tex, .pdf, .sty, .bib)
        ├── NeurIPS2026_1296_pipeline.ipynb   ← copy of the notebook
        └── <31 *_outputs/ directories>
```

---

## License

- **Code** (under `src/`, `analysis/`, the notebook, and the verifier): **MIT License** for purposes of NeurIPS 2026 reproducibility review.
- **Vendored third-party code** (e.g., DYNOTEARS optimizer adapted from causalnex): retains its original Apache 2.0 license; see file headers.
- **Data** (the three CSVs in `data/`): derived from publicly available sources (V-Dem v14, World Bank WDI, UN World Population Prospects, KOF Globalization Index) and released under the same terms as their underlying sources.
- **Paper sources** (under `paper/`): submission materials. The `neurips_2026.sty` style file is from the official NeurIPS 2026 author kit.

---

## Contact

This repository accompanies an anonymous NeurIPS 2026 submission. For correspondence please use the OpenReview thread for paper #1296.
