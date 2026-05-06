# NeurIPS 2026 paper #1296 — reproducibility bundle

> **When Classical Inference Fails: A Multi-Criteria Diagnostic for Causal Discovery on Latent-Factor Panels**

This is the canonical depository for paper #1296. It contains everything required to (a) re-run the full analysis pipeline from scratch, (b) verify the paper's numerical claims against the canonical CSV / JSON outputs without re-running anything, or (c) rebuild the paper PDF from `.tex` sources.

If you only want to verify, **you do not need this bundle's contents directly** — the standalone `verify_paper_numbers.py` / `.ipynb` script (outside this tarball) takes the bundle as input, extracts the paper sources from `paper/`, and does the verification automatically. The contents here are for re-runners and reviewers who want to inspect the canonical outputs directly.

---

## Contents

```
NeurIPS2026_1296/
├── README.md                                  ← this file
├── MANIFEST.sha256                            ← SHA-256 of every file
├── NeurIPS2026_1296_pipeline.ipynb            ← full analysis pipeline (re-run with this)
├── data/                                      ← input panels (CSV)
│   ├── my_data_75_years.csv                   ← V-Dem long_16var (89 countries × 75 years)
│   ├── my_data_VDem_Ind.csv                   ← V-Dem indicator pool (152 countries × 56 years)
│   └── my_data_WB.csv                         ← WB-WPP modernization (173 countries × 56 years)
├── src/                                       ← Python modules (data loaders, NAVAR, DYNOTEARS, etc.)
├── analysis/                                  ← analysis scripts referenced by the notebook
├── paper/                                     ← paper sources (LaTeX + compiled PDF)
│   ├── main.tex                               ← main paper body
│   ├── appendix_A.tex … checklist.tex         ← appendices
│   ├── neurips_2026.sty, references.bib       ← LaTeX support files
│   └── main.pdf                               ← compiled PDF
└── <31 *_outputs/ directories>                ← canonical CSVs / JSONs / PKLs
```

The `*_outputs/` directories contain every CSV and JSON cited in the paper. Each output directory is named after the analysis section that produces it. The most-cited ones are:

| Directory                                            | Used for                                                        |
| ---------------------------------------------------- | --------------------------------------------------------------- |
| `lsc_synthetic_validation_outputs/`                  | Table 1 (synthetic regimes) and the panel pickles for re-run    |
| `multi_criteria_outputs/{wb_wpp,vdem_indicators,long_16var}/` | Tables 2, 3, 12, 13 (real substrates)                  |
| `era_decomposed_outputs/`                            | Tables 2, 4 (V-Dem-16 size-13 / size-12 era decomposition)      |
| `adversary_rank1_block_8_outputs/`                   | Table 14 (full λ sweep adversary)                               |
| `adversary_defense_pareto_block_8a_outputs/`         | V-Dem-16 honest-method evaluation (used in Table 3 V-Dem-16 col)|
| `null_calibration_v2_outputs/`                       | Tables 7, 8 (Type-I rates for both nulls)                       |
| `parametric_null_applications_outputs/`              | β-range claim ([0.928, 0.995] on V-Dem-16)                      |
| `r3_rho07_outputs/`                                  | R3 ρ=0.7 OLS VAR claims (ΔPR, T_cov range)                      |
| `vdem_variance_ratios_outputs/`                      | V-Dem heterogeneity claim (ratio ≈ 4.6)                         |
| `eda_corr_shift_outputs/`                            | Table 16 row 5 (max correlation shift)                          |
| `eda_verification_v2_outputs/`                       | Table 16 EDA condition counts                                   |
| `r1_dynsplit_sweep_block_3_outputs/`                 | Table 11 (R1-dynsplit correlation sweep)                        |
| `sigma_lam_sweep_block_7_outputs/`                   | Table 10 (σ_Λ sweep on R1-heterogen)                            |

The full paper-claim-to-CSV mapping is defined by paired paper-extractor and canonical-extractor functions in the verifier's `CHECKS` list (in `verifier_core.py`, outside this tarball). That is the canonical audit trail.

---

## Re-running the full pipeline

### What you'll need

- **Google Colab** (recommended; the notebook was developed and tested there) — or a local environment with Python 3.10+, ~16 GB RAM, and a CUDA-capable GPU (required by NAVAR and cMLP; CPU-only will be ~10× slower).
- Approximately **14–18 hours** of contiguous runtime on a Colab T4 instance to execute every cell.
- Approximately **80 GB** of disk under your Drive directory after a full re-run (most of which is intermediate panel pickles and `W_hats/` outputs).

### Setup (on Colab)

1. Upload this bundle to your Google Drive at `MyDrive/NeurIPS2026_1296_bundle/` and extract it there:
   ```bash
   tar xzf neurips_1296_bundle.tar.gz -C /content/drive/MyDrive/
   ```
   (Or extract locally first and upload the resulting folder.)

2. The notebook expects the depository at:
   ```
   /content/drive/MyDrive/NeurIPS2026_1296/
   ```
   If you extracted to a different path, update `DRIVE_DIR` in cells 7, 82, and 84 of the notebook (these are the three audit cells; the earlier cells use a notebook-wide constant).

3. Open `NeurIPS2026_1296_pipeline.ipynb` in Colab.

4. **Runtime → Run all** (or run cell by cell to inspect intermediate outputs).

### What the pipeline produces

Each cell that produces output saves CSVs / JSONs / PKLs to one of the `*_outputs/` directories. **Re-running overwrites these files with freshly computed values from the same RNG seeds** — the canonical depository was produced this same way. Differences you might see:

- **Identical bit-for-bit** for purely deterministic computations (CSV merges, EDA flag counts).
- **Within ~5–6 decimal places** for numerical computations seeded with NumPy / PyTorch RNGs that are deterministic on a fixed CUDA / CPU stack but may drift slightly on a different stack.
- **Within Monte-Carlo noise** (~0.01 on ΔPR; ~0.005 on T-cov) for procedures where the seed only fixes the panel realization but the optimizer has its own non-determinism (cMLP/NAVAR/DYNOTEARS training).

### Required Python packages

The notebook installs everything it needs in early cells (`!pip install ...`). For reference, the full set is approximately:

```
numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib, seaborn,
torch (CUDA), causalnex, tigramite, properscoring,
```

Versions are pinned in the notebook's first install cell. The notebook works on Colab's default Python (currently 3.10–3.11) without modification.

### The DYNOTEARS parametric null caveat (Appendix M of the paper)

The full DYNOTEARS parametric null requires multi-day compute and is **not regenerated** by the canonical run. The paper transparently uses OLS VAR's null distribution as a proxy reference for DYNOTEARS, and DYNOTEARS binary verdicts use the row-permuting null instead. The verifier will not check DYNOTEARS-parametric numbers as binary claims (they're descriptive only).

### The three audit-residue cells (cells 7, 82, 84)

The canonical notebook has three cells that were added during the final paper audit. They produce output to `r3_rho07_outputs/`, `vdem_variance_ratios_outputs/`, and `eda_corr_shift_outputs/`. These cells are integrated into the main notebook and run in order with everything else. Their outputs are referenced by the paper's inline numerical claims and by Table 16 row 5.

---

## Verifying without re-running

The standalone `verify_paper_numbers.py` (CLI) and `verify_paper_numbers.ipynb` (Colab notebook) — both shipped **outside this tarball** — load the tarball, extract the paper sources from `paper/`, and run **304 paired checks**. For each check the verifier:

1. Extracts a numerical value from the paper's `.tex` source files at runtime (e.g., a cell of Table 2, an inline value like `sup-Wald = 10.8`).
2. Extracts the corresponding canonical value from this depository's CSV/JSON outputs at runtime.
3. Compares the two within tolerance.

Neither side hard-codes expected values. The mapping between paper claims and canonical sources is defined by paired extractor functions in `verifier_core.py` — open that file to see exactly what each check is doing.

```bash
# CLI — paper sources auto-resolved from the tarball's paper/ subdir
python verify_paper_numbers.py --tarball /path/to/this/bundle.tar.gz
```

No re-computation, no GPU, runs in well under a minute on any laptop.

---

## File integrity

`MANIFEST.sha256` lists the SHA-256 hash of every file in this bundle. To verify on Linux / macOS:

```bash
cd NeurIPS2026_1296
sha256sum -c MANIFEST.sha256 --quiet
```

If any file has been modified post-release, the corresponding line will fail.

---

## Naming note

Three output directories were named with the suffix `_audit` during the paper audit phase (`r3_rho07_audit`, `vdem_variance_ratios_audit`, `eda_corr_shift_audit`). They have been renamed to `_outputs` in this bundle to match the notebook's `OUT_DIR` constants. Re-running the corresponding notebook cells will overwrite these directories with freshly computed contents.

---

## Compute environment used to generate the canonical depository

- Google Colab (T4 instance), 2025-04 → 2025-05.
- Python 3.10, NumPy 1.26, PyTorch 2.x (CUDA 12).
- Total compute: approximately 14–18 hours wall-clock time across all cells.
- All RNG seeds are fixed in the notebook (the seed for synthetic-regime panels is per-seed-loop; the seed for null distributions is `B`-dependent only).

---

## License

The data files (`my_data_*.csv`) are derived from publicly available sources (V-Dem v14, World Bank WDI, UN World Population Prospects, KOF Globalization Index). The compiled CSVs in this bundle are released under the same terms as their underlying sources; please cite the original databases for any derived work.

The Python source code (under `src/`, `analysis/`, and the notebook) is released under the **MIT License** for the purposes of NeurIPS 2026 reproducibility review. Vendored code from third-party libraries (e.g., DYNOTEARS optimizer from causalnex) retains its original Apache 2.0 license — see file headers.

The paper sources under `paper/` (LaTeX, PDF) are the submission-ready materials. The `neurips_2026.sty` style file is from the official NeurIPS 2026 author kit.

---

## Contact

This bundle accompanies the NeurIPS 2026 anonymous submission. For correspondence, please use the OpenReview thread for paper #1296.
