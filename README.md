# Reproducibility code & data — NeurIPS 2026 paper #1296

> **When Classical Inference Fails: A Multi-Criteria Diagnostic for Causal Discovery on Latent-Factor Panels**

This repository contains everything needed to reproduce or verify the numerical claims in the paper.

## What's in here

| File / Dir                              | What it is                                                                                       | Size   |
| --------------------------------------- | ------------------------------------------------------------------------------------------------ | ------:|
| `README.md`                             | This file.                                                                                       | small  |
| `verify_paper_numbers.py`               | **Verifier (CLI).** Loads the tarball and asserts every paper number against canonical CSVs.     | small  |
| `verify_paper_numbers.ipynb`            | **Verifier (Colab notebook).** Same as the script, formatted for one-click Colab execution.      | small  |
| `verifier_core.py`                      | Hard-coded `CHECKS` list (paper-claim → canonical-CSV mapping) and runner. Imported by both above. | small |
| `requirements.txt`                      | Minimal pip dependencies for the verifier (`pandas`, `numpy`).                                   | small  |
| `NeurIPS2026_1296_pipeline.ipynb`       | The full analysis pipeline, identical to the copy inside the tarball. Re-run this to regenerate every CSV. | medium |
| `BUNDLE_README.md`                      | Copy of the README inside the tarball. Read this without extracting if you want re-run instructions. | small |
| `neurips_1296_bundle.tar.gz`            | **Reproducibility tarball.** Data files, canonical outputs (CSVs/JSONs), source code, internal README, SHA-256 manifest. | ~72 MB |

There are two ways to use this repo, depending on what you want to do.

---

## Path A: Verify the paper without re-running anything (~30 seconds)

This is what reviewers will typically want. The verifier loads the tarball, walks a hard-coded list of every numerical claim in the paper, and asserts each one against the corresponding canonical CSV / JSON value within tolerance.

### From the command line

```bash
git clone <this repo>
cd <this repo>
pip install -r requirements.txt    # only pandas + numpy
python verify_paper_numbers.py --tarball neurips_1296_bundle.tar.gz
```

Expected output (truncated):

```
================================================================
  NeurIPS 2026 paper #1296 — paper-number verifier
================================================================
  Extracting tarball to: /tmp/verify_1296_xxxxxx
  Depository root:   /tmp/verify_1296_xxxxxx/NeurIPS2026_1296
  Total checks:      317
================================================================

================================================================
  SUMMARY
================================================================
  Total checks:  317
  Passed:        317
  Failed:        0
  Errors:        0
================================================================
```

**Optional flags:**
- `--strict` — exit code 1 if any FAIL (default: exit 0 with summary).
- `--verbose` — list every PASS line, not just FAILs.
- `--depository /path/to/extracted/dir` — skip extraction (use an already-unpacked dir).
- `--no-color` — disable ANSI color codes.

The script needs only the standard library plus `pandas` and `numpy`. No GPU, no project-specific dependencies.

### On Colab (no local install)

Open `verify_paper_numbers.ipynb` directly in Colab (File → Upload notebook, or click the badge below if you publish the repo on GitHub):

```
https://colab.research.google.com/github/<anon>/<repo>/blob/main/verify_paper_numbers.ipynb
```

The notebook will prompt you to upload `neurips_1296_bundle.tar.gz` and `verifier_core.py`. Then run all cells. Total runtime: ~1 minute (most of which is uploading the tarball).

### What the verifier checks

All 317 individual paper claims:

- **Tables 1–5** (main paper): every cell value (ΔPR, std, CRPS, T_cov, p-values, n_pass counts).
- **Tables 6–13** (appendices B and C): every cell.
- **Table 15** (EDA appendix): condition counts and correlation-shift values.
- **Inline numerical claims**: β-range on V-Dem-16, R3 ρ=0.7 (ΔPR, T_cov), Elected_officials saturation / sup-Wald / β-shift, honest-cluster PR/ΔPR ranges, calibrated-adversary trajectory, V-Dem variance ratio.

Tolerances follow the convention "strict where the paper is precise; lenient where it says ≈":

| Tolerance | Used for                                                  |
| --------: | :-------------------------------------------------------- |
|   ±0.001  | individual values where paper is precise to 3 decimals    |
|   ±0.005  | cross-method aggregates                                   |
|   ±0.01   | "≈ X" claims rounded to 2 decimal places                  |
|   ±0.05   | "≈ X" claims rounded to 1 decimal place                   |
|  `< X`    | p-values stated as `p < X` (checked as inequality)        |

The full mapping is in `verifier_core.py` as a `CHECKS` list. **That file is the canonical audit trail — open it to see exactly what each check does.**

---

## Path B: Re-run the full pipeline (~14–18 hours on Colab T4)

If you want to regenerate every CSV from the data, follow the instructions in `BUNDLE_README.md` (which is also inside the tarball at `NeurIPS2026_1296/README.md`). The short version:

1. Extract `neurips_1296_bundle.tar.gz` to your Google Drive at `MyDrive/NeurIPS2026_1296/`.
2. Open `NeurIPS2026_1296_pipeline.ipynb` in Colab (or use the copy inside the tarball — they are identical).
3. Runtime → Run all.
4. After completion, point the verifier at your re-generated tree:
   ```bash
   python verify_paper_numbers.py --depository /content/drive/MyDrive/NeurIPS2026_1296
   ```
   You should still see 317/317 PASS, modulo small Monte-Carlo drift on stochastic methods (cMLP / NAVAR / DYNOTEARS). The paper's tolerances are loose enough to absorb that drift.

A full re-run requires:
- GPU (T4 or better; cMLP and NAVAR are GPU-trained).
- ~16 GB RAM.
- ~80 GB disk (intermediate panels and `W_hats/` accumulate).

---

## Repository layout (tree)

```
.
├── README.md                          ← this file
├── requirements.txt                   ← pandas + numpy (verifier deps only)
├── verify_paper_numbers.py            ← CLI verifier
├── verify_paper_numbers.ipynb         ← Colab verifier notebook
├── verifier_core.py                   ← shared CHECKS list + runner
├── NeurIPS2026_1296_pipeline.ipynb    ← full analysis notebook (90 cells)
├── BUNDLE_README.md                   ← copy of the README inside the tarball
└── neurips_1296_bundle.tar.gz         ← canonical tarball (~72 MB)
    └── NeurIPS2026_1296/
        ├── README.md                  ← internal README
        ├── MANIFEST.sha256            ← SHA-256 of every file
        ├── data/                      ← input panels (3 CSVs)
        ├── src/                       ← Python modules (NAVAR, DYNOTEARS, etc.)
        ├── analysis/                  ← analysis scripts
        ├── NeurIPS2026_1296_pipeline.ipynb   ← copy of the notebook
        └── <31 *_outputs/ directories>
```

---

## License

- **Code** (under `src/`, `analysis/`, the notebook, and the verifier): **MIT License** for purposes of NeurIPS 2026 reproducibility review.
- **Vendored third-party code** (e.g., DYNOTEARS optimizer adapted from causalnex): retains its original Apache 2.0 license; see file headers.
- **Data** (the three CSVs in `data/`): derived from publicly available sources (V-Dem v15, World Bank WDI, UN World Population Prospects, KOF Globalization Index) and released under the same terms as their underlying sources.

---

## Contact

This repository accompanies an anonymous NeurIPS 2026 submission. For correspondence please use the OpenReview thread for paper #1296.
