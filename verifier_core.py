"""
verifier_core.py — Paper-vs-canonical verification for NeurIPS 2026 paper #1296.

Each Check pairs:
- a paper-side extractor that pulls a numerical value from the paper's .tex
  source files at runtime, AND
- a canonical-side extractor that pulls the corresponding value from the
  reproducibility depository (CSVs / JSONs) at runtime.

Neither side hard-codes expected values. The verifier asserts that the two
extracted values agree within tolerance.

If the paper changes wording in a way that breaks a paper extractor, the
verifier reports the extraction error pointing at the .tex location. If the
canonical depository changes, the verifier reports a canonical extraction
error. If both extract cleanly but disagree, the verifier reports the mismatch
with paper_loc, source_file, and both values.

Inspect this file to see exactly what is being checked and how. Each Check has
a paper_loc (where the claim appears in the paper) and human-readable
description.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import paper_extractors as pe
import canonical_extractors as ce


# =============================================================================
# Tolerance defaults
# =============================================================================
TOL_STRICT = 0.001        # individual values where paper is precise to 3+ dp
TOL_NORMAL = 0.005        # cross-method aggregates
TOL_LOOSE  = 0.01         # "≈ X" claims, 2-dp rounding
TOL_VLOOSE = 0.05         # "≈ X" claims, 1-dp rounding
TOL_EXACT  = 0            # integers, n_pass counts


# =============================================================================
# Check spec
# =============================================================================
@dataclass
class Check:
    """A single paper-vs-canonical check.

    paper_loc:    Where the claim appears in the paper (human-readable).
    description:  What is being checked.
    paper:        Callable(paper_sources) -> value
    canonical:    Callable(depository_root) -> value
    tol:          Absolute tolerance (default TOL_STRICT).
    comparator:   "approx" (default), "lt" (paper bound, canonical < paper),
                  "lte", "exact" (==), "tuple_approx" (both sides are (lo, hi)).
    """
    paper_loc: str
    description: str
    paper: Callable
    canonical: Callable
    tol: float = TOL_STRICT
    comparator: str = "approx"


# =============================================================================
# THE CHECKS — paired paper and canonical extractors
# =============================================================================
CHECKS: list[Check] = []


# -----------------------------------------------------------------------------
# Inline claim: V-Dem-16 per-indicator AR(1) β range [0.928, 0.995]
# -----------------------------------------------------------------------------
# The paper uses this range twice: once as the calibration-tested range
# β ∈ [0.50, 0.99], once as the V-Dem empirical range β ∈ [0.928, 0.995]. We
# use a more specific anchor pattern that picks out the V-Dem one.
CHECKS.append(Check(
    paper_loc="main.tex §2.2 \"Inference\" / §4.2 \"Indicator-level diagnosis\" / appendix B",
    description="V-Dem-16 per-indicator AR(1) β range [0.928, 0.995] — minimum",
    paper=lambda src: pe.inline_range(
        "main.tex",
        r"per-indicator AR\(1\) coefficients on the 13-indicator block: "
        r"\$\\beta_i \\in \[(\d+\.\d+),\s*(\d+\.\d+)\]\$"
    )(src)[0],
    canonical=ce.csv_cell(
        "parametric_null_applications_outputs/parametric_null_applications.csv",
        {"panel": "V-Dem long_16var"},
        "fitted_beta_min",
    ),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex §4.2 \"Indicator-level diagnosis\"",
    description="V-Dem-16 per-indicator AR(1) β range [0.928, 0.995] — maximum",
    paper=lambda src: pe.inline_range(
        "main.tex",
        r"per-indicator AR\(1\) coefficients on the 13-indicator block: "
        r"\$\\beta_i \\in \[(\d+\.\d+),\s*(\d+\.\d+)\]\$"
    )(src)[1],
    canonical=ce.csv_cell(
        "parametric_null_applications_outputs/parametric_null_applications.csv",
        {"panel": "V-Dem long_16var"},
        "fitted_beta_max",
    ),
    tol=TOL_STRICT,
))


# -----------------------------------------------------------------------------
# Inline claims: R3 ρ=0.7 OLS VAR results
# -----------------------------------------------------------------------------
# "OLS VAR's ΔPR = +0.164 ± 0.035 is significant at p ≤ 0.003 across all 5 seeds"
CHECKS.append(Check(
    paper_loc="main.tex §3 \"R3 falsifies Claim B\"",
    description="R3 ρ=0.7 OLS VAR ΔPR mean = +0.164",
    paper=pe.inline_value(
        "main.tex",
        r"OLS VAR's \$\\dPR = \+(\d+\.\d+) \\pm \d+\.\d+\$ is significant at \$p \\leq",
    ),
    canonical=ce.csv_cell(
        "r3_rho07_outputs/r3_rho07_summary.csv",
        {"regime": "R3", "rho_innov": 0.7},
        "mean_dPR",
    ),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex §3 \"R3 falsifies Claim B\"",
    description="R3 ρ=0.7 OLS VAR ΔPR sd = 0.035",
    paper=pe.inline_value(
        "main.tex",
        r"OLS VAR's \$\\dPR = \+\d+\.\d+ \\pm (\d+\.\d+)\$ is significant",
    ),
    canonical=ce.csv_cell(
        "r3_rho07_outputs/r3_rho07_summary.csv",
        {"regime": "R3", "rho_innov": 0.7},
        "std_dPR",
    ),
    tol=TOL_STRICT,
))
# p ≤ 0.003 — paper bound, canonical max p across 5 seeds must be < 0.003
CHECKS.append(Check(
    paper_loc="main.tex §3",
    description="R3 ρ=0.7 OLS VAR max p across 5 seeds ≤ paper bound 0.003",
    paper=pe.inline_value(
        "main.tex",
        r"is significant at \$p \\leq (\d+\.\d+)\$ across all 5 seeds",
    ),
    canonical=ce.csv_cell(
        "r3_rho07_outputs/r3_rho07_summary.csv",
        {"regime": "R3", "rho_innov": 0.7},
        "max_p_perm",
    ),
    comparator="lte",
    tol=0,
))

# T_cov ∈ [0.684, 0.739]
CHECKS.append(Check(
    paper_loc="main.tex §3 \"R3 falsifies Claim B\"",
    description="R3 ρ=0.7 T_cov range [0.684, 0.739] — minimum",
    paper=lambda src: pe.inline_range(
        "main.tex",
        r"R3's \$\\Tcov \\in \[(\d+\.\d+),\s*(\d+\.\d+)\]\$ straddles \$\\tau = 0\.7\$",
    )(src)[0],
    canonical=ce.csv_minmax(
        "r3_rho07_outputs/r3_rho07_per_seed.csv",
        {"regime": "R3"}, "T_cov", "min",
    ),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex §3",
    description="R3 ρ=0.7 T_cov range [0.684, 0.739] — maximum",
    paper=lambda src: pe.inline_range(
        "main.tex",
        r"R3's \$\\Tcov \\in \[(\d+\.\d+),\s*(\d+\.\d+)\]\$ straddles \$\\tau = 0\.7\$",
    )(src)[1],
    canonical=ce.csv_minmax(
        "r3_rho07_outputs/r3_rho07_per_seed.csv",
        {"regime": "R3"}, "T_cov", "max",
    ),
    tol=TOL_STRICT,
))


# -----------------------------------------------------------------------------
# Table 1 (synthetic baseline) — every comparator method × regime cell
# -----------------------------------------------------------------------------
# Columns of Table 1: [method, R1, R1', R2, R2', R3, R3']
TABLE1_REGIMES = [
    (1, "R1"),
    (2, "R1'"),
    (3, "R2"),
    (4, "R2'"),
    (5, "R3"),
    (6, "R3'"),
]

# Comparator methods (these have ±sd subscripts for all 6 columns)
TABLE1_METHODS = ["lvg", "pcmci", "cmlp", "navar", "dynotears"]

for paper_method, csv_method in [
    ("lvg",       "linear_var_granger"),
    ("pcmci",     "pcmci"),
    ("cmlp",      "cmlp"),
    ("navar",     "navar"),
    ("dynotears", "dynotears"),
]:
    for col_idx, regime in TABLE1_REGIMES:
        # Mean
        CHECKS.append(Check(
            paper_loc=f"main.tex Table 1, row '{paper_method}', column '{regime}'",
            description=f"Table 1 {paper_method} {regime} mean ΔPR",
            paper=pe.table1_cell("main.tex", "tab:synthetic-baseline",
                                 paper_method, col_idx, "mean"),
            canonical=ce.csv_cell(
                "lsc_synthetic_validation_outputs/synthetic_results_aggregated.csv",
                {"regime": regime, "method": csv_method},
                "delta_PR_diag_mean",
            ),
            tol=TOL_STRICT,
        ))
        # SD
        CHECKS.append(Check(
            paper_loc=f"main.tex Table 1, row '{paper_method}', column '{regime}'",
            description=f"Table 1 {paper_method} {regime} ΔPR sd",
            paper=pe.table1_cell("main.tex", "tab:synthetic-baseline",
                                 paper_method, col_idx, "sd"),
            canonical=ce.csv_cell(
                "lsc_synthetic_validation_outputs/synthetic_results_aggregated.csv",
                {"regime": regime, "method": csv_method},
                "delta_PR_diag_sd",
            ),
            tol=TOL_STRICT,
        ))
        # n_pass — paper subscript vs canonical p_perm < 0.05 count
        CHECKS.append(Check(
            paper_loc=f"main.tex Table 1, row '{paper_method}', column '{regime}', subscript",
            description=f"Table 1 {paper_method} {regime} n_pass (count of seeds with p_perm < 0.05)",
            paper=pe.table1_cell("main.tex", "tab:synthetic-baseline",
                                 paper_method, col_idx, "n_pass"),
            canonical=ce.csv_count(
                "lsc_synthetic_validation_outputs/synthetic_results.csv",
                {"regime": regime, "method": csv_method},
                {"p_perm": (lambda v: v < 0.05)},
            ),
            comparator="exact",
            tol=0,
        ))

# OLS VAR row of Table 1 — has ±sd subscripts
for col_idx, regime in TABLE1_REGIMES:
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 1, row 'ols_var', column '{regime}'",
        description=f"Table 1 OLS VAR {regime} mean ΔPR",
        paper=pe.table1_cell("main.tex", "tab:synthetic-baseline",
                             "ols_var", col_idx, "mean"),
        canonical=ce.csv_cell(
            "lsc_synthetic_validation_outputs/ols_var_table1_aggregated.csv",
            {"regime": regime},
            "mean_dPR",
        ),
        tol=TOL_STRICT,
    ))
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 1, row 'ols_var', column '{regime}'",
        description=f"Table 1 OLS VAR {regime} sd ΔPR",
        paper=pe.table1_cell("main.tex", "tab:synthetic-baseline",
                             "ols_var", col_idx, "sd"),
        canonical=ce.csv_cell(
            "lsc_synthetic_validation_outputs/ols_var_table1_aggregated.csv",
            {"regime": regime},
            "std_dPR",
        ),
        tol=TOL_STRICT,
    ))
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 1, row 'ols_var', column '{regime}', subscript",
        description=f"Table 1 OLS VAR {regime} n_pass",
        paper=pe.table1_cell("main.tex", "tab:synthetic-baseline",
                             "ols_var", col_idx, "n_pass"),
        canonical=ce.csv_cell(
            "lsc_synthetic_validation_outputs/ols_var_table1_aggregated.csv",
            {"regime": regime},
            "n_pass",
        ),
        comparator="exact",
        tol=0,
    ))


# -----------------------------------------------------------------------------
# Table 2 (substrates): 4 rows × 3 verifiable numeric columns each
# Columns: [Substrate, N, T_cov, dPR, p, verdict, Layer 2]
# We verify N, T_cov, dPR (cols 1, 2, 3); p is a mix of "<.001" and numeric
# -----------------------------------------------------------------------------
TABLE2_ROWS = [
    # (paper row substring, canonical-source-spec for T_cov, canonical for dPR, canonical for p)
    ("WB-WPP",
     ce.csv_cell("multi_criteria_outputs/wb_wpp/multi_criteria_summary.csv",
                 {"panel": "wb_wpp", "method": "linear_var_granger"}, "T_cov"),
     ce.csv_cell("multi_criteria_outputs/wb_wpp/multi_criteria_summary.csv",
                 {"panel": "wb_wpp", "method": "linear_var_granger"}, "dPR_param"),
     None),  # p < .001 — checked separately as inequality
    ("^V-Dem-16$",  # exact match: distinguish from "V-Dem-16 after Layer 3 repair"
     ce.json_path("era_decomposed_outputs/era_decomposed_results.json",
                  ("test2_drop_regime_shifters",
                   {"block_label": "size13_full_panel (T=75) [from Test 1]"},
                   "T_cov")),
     ce.json_path("era_decomposed_outputs/era_decomposed_results.json",
                  ("test2_drop_regime_shifters",
                   {"block_label": "size13_full_panel (T=75) [from Test 1]"},
                   "delta_PR")),
     ce.json_path("era_decomposed_outputs/era_decomposed_results.json",
                  ("test2_drop_regime_shifters",
                   {"block_label": "size13_full_panel (T=75) [from Test 1]"},
                   "p_parametric"))),
    ("after Layer~3 repair",
     ce.json_path("era_decomposed_outputs/era_decomposed_results.json",
                  ("test2_drop_regime_shifters",
                   {"block_label": "size12_no_elected_officials (T=75)"},
                   "T_cov")),
     ce.json_path("era_decomposed_outputs/era_decomposed_results.json",
                  ("test2_drop_regime_shifters",
                   {"block_label": "size12_no_elected_officials (T=75)"},
                   "delta_PR")),
     ce.json_path("era_decomposed_outputs/era_decomposed_results.json",
                  ("test2_drop_regime_shifters",
                   {"block_label": "size12_no_elected_officials (T=75)"},
                   "p_parametric"))),
    ("V-Dem-60",
     ce.csv_cell("multi_criteria_outputs/vdem_indicators/multi_criteria_summary.csv",
                 {"panel": "vdem_indicators", "method": "linear_var_granger"}, "T_cov"),
     # Paper Table 2 says "ΔPR values are for OLS VAR (Layer 1 substrate diagnostic)".
     # The OLS VAR (unthresholded) baseline is in layer1_vdem_indicators.csv,
     # which differs from the linear_var_granger row in multi_criteria_summary
     # because lvg applies Granger thresholding. Appendix C Table 13 confirms
     # OLS VAR baseline ΔPR = +0.348 vs lvg ΔPR = +0.368.
     ce.csv_cell("multi_criteria_outputs/vdem_indicators/layer1_vdem_indicators.csv",
                 {"method": "ols_var"}, "dPR_param"),
     None),
]

for row_match, tcov_canon, dpr_canon, p_canon in TABLE2_ROWS:
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 2, row '{row_match.strip()}'",
        description=f"Table 2 {row_match.strip()} T_cov",
        paper=pe.table_cell("main.tex", "tab:substrates", row_match, 2),
        canonical=tcov_canon,
        tol=TOL_STRICT,
    ))
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 2, row '{row_match.strip()}'",
        description=f"Table 2 {row_match.strip()} ΔPR",
        paper=pe.table_cell("main.tex", "tab:substrates", row_match, 3),
        canonical=dpr_canon,
        tol=TOL_STRICT,
    ))
    if p_canon is not None:
        CHECKS.append(Check(
            paper_loc=f"main.tex Table 2, row '{row_match.strip()}'",
            description=f"Table 2 {row_match.strip()} p_param",
            paper=pe.table_cell("main.tex", "tab:substrates", row_match, 4),
            canonical=p_canon,
            tol=TOL_NORMAL,
        ))


# -----------------------------------------------------------------------------
# Table 3 (cross-substrate): 5 methods × 6 columns
# Columns: [Method, WB ΔPR, WB CRPS, V16 ΔPR, V16 CRPS, V60 ΔPR, V60 CRPS]
# -----------------------------------------------------------------------------
T3_METHODS = [
    ("linear_var_granger", "linear_var_granger"),
    ("pcmci",              "pcmci"),
    ("cmlp",               "cmlp"),
    ("navar",              "navar"),
    ("dynotears",          "dynotears"),
]

# Per-substrate canonical sources. V-Dem-16 uses adversary_defense_pareto (kind=honest);
# WB-WPP and V-Dem-60 use multi_criteria_outputs.
for paper_m, csv_m in T3_METHODS:
    # WB-WPP ΔPR (col 1)
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 3, WB-WPP {paper_m} ΔPR",
        description=f"Table 3 WB-WPP {paper_m} ΔPR",
        paper=pe.table_cell("main.tex", "tab:cross-substrate", paper_m, 1),
        canonical=ce.csv_cell(
            "multi_criteria_outputs/wb_wpp/multi_criteria_summary.csv",
            {"panel": "wb_wpp", "method": csv_m}, "dPR_param"),
        tol=TOL_STRICT,
    ))
    # WB-WPP CRPS (col 2)
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 3, WB-WPP {paper_m} CRPS",
        description=f"Table 3 WB-WPP {paper_m} CRPS",
        paper=pe.table_cell("main.tex", "tab:cross-substrate", paper_m, 2),
        canonical=ce.csv_cell(
            "multi_criteria_outputs/wb_wpp/multi_criteria_summary.csv",
            {"panel": "wb_wpp", "method": csv_m}, "CRPS_unc"),
        tol=TOL_STRICT,
    ))
    # V-Dem-16 ΔPR (col 3)
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 3, V-Dem-16 {paper_m} ΔPR",
        description=f"Table 3 V-Dem-16 {paper_m} ΔPR",
        paper=pe.table_cell("main.tex", "tab:cross-substrate", paper_m, 3),
        canonical=ce.csv_cell(
            "adversary_defense_pareto_block_8a_outputs/all_evaluations.csv",
            {"kind": "honest", "method": csv_m}, "parametric_delta"),
        tol=TOL_STRICT,
    ))
    # V-Dem-16 CRPS (col 4)
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 3, V-Dem-16 {paper_m} CRPS",
        description=f"Table 3 V-Dem-16 {paper_m} CRPS",
        paper=pe.table_cell("main.tex", "tab:cross-substrate", paper_m, 4),
        canonical=ce.csv_cell(
            "adversary_defense_pareto_block_8a_outputs/all_evaluations.csv",
            {"kind": "honest", "method": csv_m}, "crps_unconstrained"),
        tol=TOL_STRICT,
    ))
    # V-Dem-60 ΔPR (col 5)
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 3, V-Dem-60 {paper_m} ΔPR",
        description=f"Table 3 V-Dem-60 {paper_m} ΔPR",
        paper=pe.table_cell("main.tex", "tab:cross-substrate", paper_m, 5),
        canonical=ce.csv_cell(
            "multi_criteria_outputs/vdem_indicators/multi_criteria_summary.csv",
            {"panel": "vdem_indicators", "method": csv_m}, "dPR_param"),
        tol=TOL_STRICT,
    ))
    # V-Dem-60 CRPS (col 6)
    CHECKS.append(Check(
        paper_loc=f"main.tex Table 3, V-Dem-60 {paper_m} CRPS",
        description=f"Table 3 V-Dem-60 {paper_m} CRPS",
        paper=pe.table_cell("main.tex", "tab:cross-substrate", paper_m, 6),
        canonical=ce.csv_cell(
            "multi_criteria_outputs/vdem_indicators/multi_criteria_summary.csv",
            {"panel": "vdem_indicators", "method": csv_m}, "CRPS_unc"),
        tol=TOL_STRICT,
    ))


# -----------------------------------------------------------------------------
# Table 4 (Elected_officials drop): size-13 vs size-12
# Columns: [Block, T_cov, dPR, z-score, p_param, verdict]
# -----------------------------------------------------------------------------
T4_ROWS = [
    ("size-13", "size13_full_panel (T=75) [from Test 1]"),
    ("size-12", "size12_no_elected_officials (T=75)"),
]
for paper_block, json_block in T4_ROWS:
    for col_idx, field, label, tol in [
        (1, "T_cov",        "T_cov",   TOL_STRICT),
        (2, "delta_PR",     "ΔPR",     TOL_STRICT),
        (3, "z_score",      "z-score", TOL_NORMAL),
        (4, "p_parametric", "p_param", TOL_NORMAL),  # paper rounds to 2dp (0.34 vs 0.337)
    ]:
        CHECKS.append(Check(
            paper_loc=f"main.tex Table 4, row '{paper_block}'",
            description=f"Table 4 {paper_block} {label}",
            paper=pe.table_cell("main.tex", "tab:vdem-16-drop", paper_block, col_idx),
            canonical=ce.json_path(
                "era_decomposed_outputs/era_decomposed_results.json",
                ("test2_drop_regime_shifters", {"block_label": json_block}, field),
            ),
            tol=tol,
        ))


# -----------------------------------------------------------------------------
# Table 5 (tau-sensitivity, main): T_cov values shown in row labels
# -----------------------------------------------------------------------------
# Each row label is e.g. "WB-WPP ($\Tcov = 0.853$)" and we extract the 0.853.
# We use inline_value on the cell-label region via regex over the full table,
# matching specific row labels.
def _t_cov_in_table5(label_pattern: str) -> Callable:
    """Helper: extract the T_cov inside the parenthetical of a Table 5 row label."""
    return pe.inline_value(
        "main.tex",
        label_pattern + r"\s*\(\$\\Tcov\s*=\s*(\d+\.\d+)\$\)",
    )

CHECKS.append(Check(
    paper_loc="main.tex Table 5 row label, WB-WPP",
    description="Table 5 WB-WPP T_cov label = canonical T_cov",
    paper=_t_cov_in_table5(r"WB-WPP"),
    canonical=ce.csv_cell(
        "multi_criteria_outputs/wb_wpp/multi_criteria_summary.csv",
        {"panel": "wb_wpp", "method": "linear_var_granger"}, "T_cov"),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex Table 5 row label, V-Dem-16 pre-repair",
    description="Table 5 V-Dem-16 pre-repair T_cov label",
    paper=_t_cov_in_table5(r"V-Dem-16 pre-repair"),
    canonical=ce.json_path(
        "era_decomposed_outputs/era_decomposed_results.json",
        ("test2_drop_regime_shifters",
         {"block_label": "size13_full_panel (T=75) [from Test 1]"}, "T_cov")),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex Table 5 row label, V-Dem-16 post-repair",
    description="Table 5 V-Dem-16 post-repair T_cov label",
    paper=_t_cov_in_table5(r"V-Dem-16 post-repair"),
    canonical=ce.json_path(
        "era_decomposed_outputs/era_decomposed_results.json",
        ("test2_drop_regime_shifters",
         {"block_label": "size12_no_elected_officials (T=75)"}, "T_cov")),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex Table 5 row label, V-Dem-60",
    description="Table 5 V-Dem-60 T_cov label",
    paper=_t_cov_in_table5(r"V-Dem-60"),
    canonical=ce.csv_cell(
        "multi_criteria_outputs/vdem_indicators/multi_criteria_summary.csv",
        {"panel": "vdem_indicators", "method": "linear_var_granger"}, "T_cov"),
    tol=TOL_STRICT,
))


# -----------------------------------------------------------------------------
# §6 inline claims: Elected_officials saturation, sup-Wald, β shift
# -----------------------------------------------------------------------------
CHECKS.append(Check(
    paper_loc="main.tex §4.2 \"Indicator-level diagnosis\"",
    description="Elected_officials sup-Wald = 10.8",
    paper=pe.inline_value(
        "main.tex",
        r"sup-Wald statistic of \$(\d+\.\d+)\$ on this indicator",
    ),
    canonical=ce.csv_cell(
        "eda_verification_v2_outputs/eda_v2_per_indicator_indices.csv",
        {"indicator": "Elected_officials"}, "sup_wald"),
    tol=TOL_VLOOSE,  # paper rounds to 1dp
))
CHECKS.append(Check(
    paper_loc="main.tex §4.2 \"Indicator-level diagnosis\"",
    description="Elected_officials saturation_frac = 30.3%",
    paper=pe.inline_percent(
        "main.tex",
        r"flat-lines for \$(\d+\.\d+)\\%\$ of countries",
    ),
    canonical=ce.csv_cell(
        "eda_verification_v2_outputs/eda_v2_per_indicator_indices.csv",
        {"indicator": "Elected_officials"}, "saturation_frac"),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex §4.2 \"Indicator-level diagnosis\"",
    description="Elected_officials abs β shift = 0.042",
    paper=pe.inline_value(
        "main.tex",
        r"with absolute \$\\beta\$ shift of \$(\d+\.\d+)\$ at the optimal breakpoint",
    ),
    canonical=ce.csv_cell(
        "eda_verification_v2_outputs/eda_v2_per_indicator_indices.csv",
        {"indicator": "Elected_officials"}, "abs_beta_shift"),
    tol=TOL_STRICT,
))


# -----------------------------------------------------------------------------
# §5.3 honest cluster claims (PR and ΔPR ranges)
# -----------------------------------------------------------------------------
def _honest_pass_filter(df):
    return df[(df["kind"] == "honest") & (df["method"].isin(["pcmci", "cmlp", "navar"]))]

# PR ∈ [0.785, 0.811] — minimum
CHECKS.append(Check(
    paper_loc="main.tex §5.3 \"strong adversary\"",
    description="Honest cluster (PCMCI/cMLP/NAVAR) PR_obs minimum",
    paper=lambda src: pe.inline_range(
        "main.tex",
        r"V-Dem-16 \(\$\\PR \\in \[(\d+\.\d+),\s*(\d+\.\d+)\]\$\)",
    )(src)[0],
    canonical=ce.csv_lambda(
        "adversary_defense_pareto_block_8a_outputs/all_evaluations.csv",
        lambda df: float(_honest_pass_filter(df)["PR_obs"].min()),
    ),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex §5.3 \"strong adversary\"",
    description="Honest cluster PR_obs maximum",
    paper=lambda src: pe.inline_range(
        "main.tex",
        r"V-Dem-16 \(\$\\PR \\in \[(\d+\.\d+),\s*(\d+\.\d+)\]\$\)",
    )(src)[1],
    canonical=ce.csv_lambda(
        "adversary_defense_pareto_block_8a_outputs/all_evaluations.csv",
        lambda df: float(_honest_pass_filter(df)["PR_obs"].max()),
    ),
    tol=TOL_STRICT,
))
# ΔPR ∈ [+0.389, +0.417]
CHECKS.append(Check(
    paper_loc="main.tex §5.3 \"weak adversary\"",
    description="Honest cluster ΔPR minimum",
    paper=lambda src: pe.inline_range(
        "main.tex",
        r"\$\\dPR \\in \[\+(\d+\.\d+),\s*\+(\d+\.\d+)\]\$ for the honest cluster",
    )(src)[0],
    canonical=ce.csv_lambda(
        "adversary_defense_pareto_block_8a_outputs/all_evaluations.csv",
        lambda df: float(_honest_pass_filter(df)["parametric_delta"].min()),
    ),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex §5.3 \"weak adversary\"",
    description="Honest cluster ΔPR maximum",
    paper=lambda src: pe.inline_range(
        "main.tex",
        r"\$\\dPR \\in \[\+(\d+\.\d+),\s*\+(\d+\.\d+)\]\$ for the honest cluster",
    )(src)[1],
    canonical=ce.csv_lambda(
        "adversary_defense_pareto_block_8a_outputs/all_evaluations.csv",
        lambda df: float(_honest_pass_filter(df)["parametric_delta"].max()),
    ),
    tol=TOL_STRICT,
))

# Calibrated adversary at λ ≈ 0.25: PR = 0.806, ΔPR = +0.413
CHECKS.append(Check(
    paper_loc="main.tex §5.3 \"calibrated adversary\"",
    description="Calibrated adversary (λ=0.25) PR = 0.806",
    paper=pe.inline_value(
        "main.tex",
        r"calibrated adversary at \$\\lambda \\approx 0\.25\$ produces \$\\PR = (\d+\.\d+)\$",
    ),
    canonical=ce.csv_cell(
        "adversary_defense_pareto_block_8a_outputs/all_evaluations.csv",
        {"method": "adv_lambda_0.25", "lambda": 0.25}, "PR_obs"),
    tol=TOL_STRICT,
))
CHECKS.append(Check(
    paper_loc="main.tex §5.3 \"calibrated adversary\"",
    description="Calibrated adversary (λ=0.25) ΔPR = +0.413",
    paper=pe.inline_value(
        "main.tex",
        r"calibrated adversary at \$\\lambda \\approx 0\.25\$ produces \$\\PR = \d+\.\d+\$, "
        r"\$\\dPR = \+(\d+\.\d+)\$",
    ),
    canonical=ce.csv_cell(
        "adversary_defense_pareto_block_8a_outputs/all_evaluations.csv",
        {"method": "adv_lambda_0.25", "lambda": 0.25}, "parametric_delta"),
    tol=TOL_STRICT,
))


# -----------------------------------------------------------------------------
# Appendix B: Table 7 (rowperm calibration) — 6 columns × Type-I rate
# Header columns: β=0.00, 0.50, 0.70, 0.85, 0.95, 0.99
# -----------------------------------------------------------------------------
ROWPERM_BETAS = [
    (1, "C1_white_noise"),    # β = 0.00 (Gauss.)
    (2, "C2_ar1_beta0.50"),
    (3, "C2_ar1_beta0.70"),
    (4, "C2_ar1_beta0.85"),
    (5, "C2_ar1_beta0.95"),
    (6, "C2_ar1_beta0.99"),
]
for col_idx, condition in ROWPERM_BETAS:
    # Type-I rate row
    CHECKS.append(Check(
        paper_loc=f"appendix_B.tex Table 7 (rowperm), Type-I rate column {col_idx}",
        description=f"Rowperm Type-I rate, condition {condition}",
        paper=pe.table_cell("appendix_B.tex", "tab:rowperm-calibration",
                            "Type-I rate", col_idx),
        canonical=ce.csv_cell(
            "null_calibration_v2_outputs/null_calibration_v2_summary.csv",
            {"null": "row-permuting", "condition": condition},
            "reject_rate",
        ),
        tol=TOL_STRICT,
    ))
    # n_panels row
    CHECKS.append(Check(
        paper_loc=f"appendix_B.tex Table 7 (rowperm), n column {col_idx}",
        description=f"Rowperm n_panels, condition {condition}",
        paper=pe.table_cell("appendix_B.tex", "tab:rowperm-calibration",
                            "n", col_idx),
        canonical=ce.csv_cell(
            "null_calibration_v2_outputs/null_calibration_v2_summary.csv",
            {"null": "row-permuting", "condition": condition},
            "n_panels",
        ),
        comparator="exact",
        tol=0,
    ))


# -----------------------------------------------------------------------------
# Appendix B: Table 8 (parametric calibration)
# -----------------------------------------------------------------------------
for col_idx, condition in ROWPERM_BETAS:
    CHECKS.append(Check(
        paper_loc=f"appendix_B.tex Table 8 (parametric), Type-I column {col_idx}",
        description=f"Parametric Type-I rate, condition {condition}",
        paper=pe.table_cell("appendix_B.tex", "tab:param-calibration",
                            "Type-I rate", col_idx),
        canonical=ce.csv_cell(
            "null_calibration_v2_outputs/null_calibration_v2_summary.csv",
            {"null": "parametric_AR1", "condition": condition},
            "reject_rate",
        ),
        tol=TOL_STRICT,
    ))
    CHECKS.append(Check(
        paper_loc=f"appendix_B.tex Table 8 (parametric), n column {col_idx}",
        description=f"Parametric n_panels, condition {condition}",
        paper=pe.table_cell("appendix_B.tex", "tab:param-calibration",
                            "n", col_idx),
        canonical=ce.csv_cell(
            "null_calibration_v2_outputs/null_calibration_v2_summary.csv",
            {"null": "parametric_AR1", "condition": condition},
            "n_panels",
        ),
        comparator="exact",
        tol=0,
    ))


# -----------------------------------------------------------------------------
# Appendix B: Table 10 (sigma_lam sweep) — 6 sigma values
# -----------------------------------------------------------------------------
SIGMA_LAM_VALUES = [0.00, 0.10, 0.25, 0.50, 0.75, 1.00]
for sigma in SIGMA_LAM_VALUES:
    row_match = f"{sigma:.2f}"
    # PR (col 1)
    CHECKS.append(Check(
        paper_loc=f"appendix_B.tex Table 10 (σ_Λ sweep), σ={sigma}",
        description=f"σ_Λ={sigma} median PR (paper rounded to 2dp)",
        paper=pe.table_cell("appendix_B.tex", "tab:sigma-lam-sweep",
                            row_match, 1),
        canonical=ce.csv_cell(
            "sigma_lam_sweep_block_7_outputs/sigma_lam_sweep_aggregate.csv",
            {"sigma_lam": sigma}, "PR_obs_median"),
        tol=TOL_LOOSE,
    ))
    # ΔPR (col 2)
    CHECKS.append(Check(
        paper_loc=f"appendix_B.tex Table 10, σ={sigma}",
        description=f"σ_Λ={sigma} median ΔPR (paper rounded to 2dp)",
        paper=pe.table_cell("appendix_B.tex", "tab:sigma-lam-sweep",
                            row_match, 2),
        canonical=ce.csv_cell(
            "sigma_lam_sweep_block_7_outputs/sigma_lam_sweep_aggregate.csv",
            {"sigma_lam": sigma}, "delta_median"),
        tol=TOL_LOOSE,
    ))


# -----------------------------------------------------------------------------
# Appendix B: Table 11 (R1-dynsplit sweep) — 6 configs
# -----------------------------------------------------------------------------
DYNSPLIT_CONFIGS = [
    ("baseline_6_6",      "baseline_6_6"),
    ("split_7_6_tight",   "split_7_6_tight"),
    ("split_7_6_mid",     "split_7_6_mid"),
    ("split_7_6_vdem",    "split_7_6_vdem"),
    ("split_7_6_loose",   "split_7_6_loose"),
    ("split_7_6_extreme", "split_7_6_extreme"),
]
for csv_cfg, paper_match in DYNSPLIT_CONFIGS:
    # Column 3: mean corr; column 4: median ΔPR
    CHECKS.append(Check(
        paper_loc=f"appendix_B.tex Table 11, config '{csv_cfg}'",
        description=f"R1-dynsplit {csv_cfg} mean indicator correlation (paper 2dp)",
        paper=pe.table_cell("appendix_B.tex", "tab:dynsplit-sweep",
                            paper_match, 3),
        canonical=ce.csv_cell(
            "r1_dynsplit_sweep_block_3_outputs/r1_dynsplit_sweep_aggregate.csv",
            {"config_name": csv_cfg}, "mean_corr_median"),
        tol=TOL_LOOSE,
    ))
    CHECKS.append(Check(
        paper_loc=f"appendix_B.tex Table 11, config '{csv_cfg}'",
        description=f"R1-dynsplit {csv_cfg} median ΔPR",
        paper=pe.table_cell("appendix_B.tex", "tab:dynsplit-sweep",
                            paper_match, 4),
        canonical=ce.csv_cell(
            "r1_dynsplit_sweep_block_3_outputs/r1_dynsplit_sweep_aggregate.csv",
            {"config_name": csv_cfg}, "parametric_delta_median"),
        tol=TOL_STRICT,
    ))


# -----------------------------------------------------------------------------
# Appendix C: Table 12 (WB-WPP detail)
# Columns: [Method, nnz, CRPS, rb-beats, ΔPR, p_param, p_rowperm]
# -----------------------------------------------------------------------------
for paper_m, csv_m in T3_METHODS:
    CHECKS.append(Check(
        paper_loc=f"appendix_C.tex Table 12 (WB-WPP), {paper_m}",
        description=f"App Tab 12 WB-WPP {paper_m} nnz",
        paper=pe.table_cell("appendix_C.tex", "tab:wbwpp-full", paper_m, 1),
        canonical=ce.csv_cell(
            "multi_criteria_outputs/wb_wpp/multi_criteria_summary.csv",
            {"panel": "wb_wpp", "method": csv_m}, "nnz"),
        comparator="exact", tol=0,
    ))
    CHECKS.append(Check(
        paper_loc=f"appendix_C.tex Table 12 (WB-WPP), {paper_m}",
        description=f"App Tab 12 WB-WPP {paper_m} CRPS",
        paper=pe.table_cell("appendix_C.tex", "tab:wbwpp-full", paper_m, 2),
        canonical=ce.csv_cell(
            "multi_criteria_outputs/wb_wpp/multi_criteria_summary.csv",
            {"panel": "wb_wpp", "method": csv_m}, "CRPS_unc"),
        tol=TOL_STRICT,
    ))
    CHECKS.append(Check(
        paper_loc=f"appendix_C.tex Table 12 (WB-WPP), {paper_m}",
        description=f"App Tab 12 WB-WPP {paper_m} ΔPR",
        paper=pe.table_cell("appendix_C.tex", "tab:wbwpp-full", paper_m, 4),
        canonical=ce.csv_cell(
            "multi_criteria_outputs/wb_wpp/multi_criteria_summary.csv",
            {"panel": "wb_wpp", "method": csv_m}, "dPR_param"),
        tol=TOL_STRICT,
    ))


# -----------------------------------------------------------------------------
# Appendix C: Table 13 (V-Dem-60 detail)
# Columns: [Method, nnz, CRPS, rb-beats, ΔPR, p_param, p_rowperm]
# -----------------------------------------------------------------------------
for paper_m, csv_m in T3_METHODS:
    CHECKS.append(Check(
        paper_loc=f"appendix_C.tex Table 13 (V-Dem-60), {paper_m}",
        description=f"App Tab 13 V-Dem-60 {paper_m} nnz",
        paper=pe.table_cell("appendix_C.tex", "tab:vdem60-full", paper_m, 1),
        canonical=ce.csv_cell(
            "multi_criteria_outputs/vdem_indicators/multi_criteria_summary.csv",
            {"panel": "vdem_indicators", "method": csv_m}, "nnz"),
        comparator="exact", tol=0,
    ))
    CHECKS.append(Check(
        paper_loc=f"appendix_C.tex Table 13 (V-Dem-60), {paper_m}",
        description=f"App Tab 13 V-Dem-60 {paper_m} ΔPR",
        paper=pe.table_cell("appendix_C.tex", "tab:vdem60-full", paper_m, 4),
        canonical=ce.csv_cell(
            "multi_criteria_outputs/vdem_indicators/multi_criteria_summary.csv",
            {"panel": "vdem_indicators", "method": csv_m}, "dPR_param"),
        tol=TOL_STRICT,
    ))


# -----------------------------------------------------------------------------
# Appendix C: Table 14 (full λ adversary sweep)
# Columns: [λ, PR, ΔPR, p_param, CRPS-excess]
# -----------------------------------------------------------------------------
ADV_LAMBDAS = [0.00, 0.01, 0.05, 0.10, 0.25, 0.50, 1.00, 2.00, 5.00, 20.0]
for lam in ADV_LAMBDAS:
    if lam == 20.0:
        # row label is exactly "20.0" — use exact match to avoid colliding with
        # bolded "0.25" or other fractions
        row_match = "^20.0$"
    else:
        row_match = f"^{lam:.2f}$"
    CHECKS.append(Check(
        paper_loc=f"appendix_C.tex Table 14, λ={lam}",
        description=f"Adv sweep λ={lam}: PR",
        paper=pe.table_cell("appendix_C.tex", "tab:adversary-full", row_match, 1),
        canonical=ce.csv_cell(
            "adversary_rank1_block_8_outputs/adversary_sweep_aggregate.csv",
            {"lambda": lam}, "PR_obs"),
        tol=TOL_STRICT,
    ))
    CHECKS.append(Check(
        paper_loc=f"appendix_C.tex Table 14, λ={lam}",
        description=f"Adv sweep λ={lam}: ΔPR",
        paper=pe.table_cell("appendix_C.tex", "tab:adversary-full", row_match, 2),
        canonical=ce.csv_cell(
            "adversary_rank1_block_8_outputs/adversary_sweep_aggregate.csv",
            {"lambda": lam}, "parametric_delta"),
        tol=TOL_STRICT,
    ))
    CHECKS.append(Check(
        paper_loc=f"appendix_C.tex Table 14, λ={lam}",
        description=f"Adv sweep λ={lam}: CRPS-excess vs OLS VAR",
        paper=pe.table_cell("appendix_C.tex", "tab:adversary-full", row_match, 4),
        canonical=ce.csv_cell(
            "adversary_rank1_block_8_outputs/adversary_sweep_aggregate.csv",
            {"lambda": lam}, "crps_excess_vs_olsvar"),
        tol=TOL_STRICT,
    ))


# -----------------------------------------------------------------------------
# EDA appendix: Table 16 (condition counts)
# Columns: [Condition, V-Dem indices, V-Dem indicators, WB-WPP]
# -----------------------------------------------------------------------------
EDA_ROWS = [
    # (paper row substring, json_substrate_key, json_field, notes)
    ("Regime shift (joint",          "n_flag_regime_shift_joint", "row 1"),
    ("stat-sig only",                "n_stat_sig_regime_shift",   "row 1 sub"),
    ("Saturation",                   "n_flag_saturation",         "row 2"),
    ("Outlier flag",                 "n_flag_outlier",            "row 3a"),
    ("Outlier drop",                 "n_drop_outlier",            "row 3b"),
    ("Collinear pairs",              "n_high_corr_pairs",         "row 4"),
    ("Max cross-indicator",          "max_corr_shift",            "row 5"),
    ("Low within/total",             "n_flag_low_within",         "row 6"),
]
EDA_SUBSTRATES = [
    (1, "indices",     "V-Dem indices column"),    # column 1 = V-Dem indices
    (2, "indicators",  "V-Dem indicators column"), # column 2 = V-Dem indicators
    (3, "wbwpp",       "WB-WPP column"),           # column 3 = WB-WPP
]
for paper_row, json_field, _ in EDA_ROWS:
    if json_field == "max_corr_shift":
        # Row 5 has float values, in the eda_corr_shift CSV
        for col_idx, json_sub, _label in EDA_SUBSTRATES:
            substrate_csv = {
                "indices":    "vdem_indices_size_16",
                "indicators": "vdem_indicators_size_70_pool",
                "wbwpp":      "wbwpp_indicators_size_21_pool",
            }[json_sub]
            CHECKS.append(Check(
                paper_loc=f"eda_appendix.tex Table 16, row '{paper_row}', col {col_idx}",
                description=f"EDA {json_sub} max corr shift",
                paper=pe.table_cell("eda_appendix.tex", "tab:eda-summary",
                                    paper_row, col_idx),
                canonical=ce.csv_cell(
                    "eda_corr_shift_outputs/eda_corr_shift_summary.csv",
                    {"substrate": substrate_csv}, "max_abs_corr_shift"),
                tol=TOL_LOOSE,
            ))
    else:
        # Integer counts from eda_v2_summary.json
        for col_idx, json_sub, _label in EDA_SUBSTRATES:
            CHECKS.append(Check(
                paper_loc=f"eda_appendix.tex Table 16, row '{paper_row}', col {col_idx}",
                description=f"EDA {json_sub}: {json_field}",
                paper=pe.table_cell("eda_appendix.tex", "tab:eda-summary",
                                    paper_row, col_idx),
                canonical=ce.json_path(
                    "eda_verification_v2_outputs/eda_v2_summary.json",
                    json_sub, json_field),
                comparator="exact", tol=0,
            ))


# -----------------------------------------------------------------------------
# Appendix B: V-Dem variance ratio inline claim (≈ 4.6)
# -----------------------------------------------------------------------------
CHECKS.append(Check(
    paper_loc="appendix_B.tex §O.1 (R1-hetero rationale, V-Dem heterogeneity scale)",
    description="V-Dem size-12 ar1-resid variance ratio ≈ 4.6 (paper rounds to 1dp)",
    paper=pe.inline_value(
        "appendix_B.tex",
        r"max-to-min AR\(1\) residual variance ratio \$\\approx (\d+\.\d+)\$",
    ),
    canonical=ce.csv_cell(
        "vdem_variance_ratios_outputs/vdem_variance_ratios.csv",
        {"block": "size_12", "metric": "ar1_resid"}, "ratio_max_over_min"),
    tol=TOL_VLOOSE,
))


# =============================================================================
# Runner
# =============================================================================
@dataclass
class CheckResult:
    check: Check
    paper_value: Any = None
    canonical_value: Any = None
    status: str = "PASS"      # "PASS" | "FAIL" | "ERROR"
    message: str = ""


def _approx_equal(a, b, tol):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def run_check(check: Check, paper_sources: dict, depository_root: Path) -> CheckResult:
    # Extract paper value
    try:
        paper_val = check.paper(paper_sources)
    except Exception as e:
        return CheckResult(
            check=check, status="ERROR",
            message=f"Paper extraction failed: {type(e).__name__}: {e}",
        )

    # Extract canonical value
    try:
        canon_val = check.canonical(depository_root)
    except Exception as e:
        return CheckResult(
            check=check, paper_value=paper_val, status="ERROR",
            message=f"Canonical extraction failed: {type(e).__name__}: {e}",
        )

    # Compare
    cmp = check.comparator
    tol = check.tol
    if cmp == "approx":
        ok = _approx_equal(paper_val, canon_val, tol)
    elif cmp == "lt":
        # paper claims canonical < paper bound
        ok = float(canon_val) < float(paper_val)
    elif cmp == "lte":
        ok = float(canon_val) <= float(paper_val)
    elif cmp == "exact":
        ok = (paper_val == canon_val)
    else:
        return CheckResult(
            check=check, paper_value=paper_val, canonical_value=canon_val,
            status="ERROR", message=f"Unknown comparator: {cmp}",
        )

    return CheckResult(
        check=check,
        paper_value=paper_val,
        canonical_value=canon_val,
        status="PASS" if ok else "FAIL",
    )


def run_all(paper_sources: dict, depository_root: Path, checks=None):
    if checks is None:
        checks = CHECKS
    return [run_check(c, paper_sources, depository_root) for c in checks]


def format_result(r: CheckResult) -> str:
    c = r.check
    if r.status == "PASS":
        return f"  [PASS] {c.description}"
    elif r.status == "FAIL":
        def fmt(v):
            if isinstance(v, float):
                return f"{v:.6f}"
            return str(v)
        return (f"  [FAIL] {c.description}\n"
                f"         paper:     {fmt(r.paper_value)}\n"
                f"         canonical: {fmt(r.canonical_value)}\n"
                f"         tol: {c.tol}  comparator: {c.comparator}\n"
                f"         paper_loc: {c.paper_loc}")
    else:  # ERROR
        return (f"  [ERR ] {c.description}\n"
                f"         {r.message}\n"
                f"         paper_loc: {c.paper_loc}")


def summarize(results) -> dict:
    return {
        "total": len(results),
        "pass":  sum(1 for r in results if r.status == "PASS"),
        "fail":  sum(1 for r in results if r.status == "FAIL"),
        "error": sum(1 for r in results if r.status == "ERROR"),
    }
