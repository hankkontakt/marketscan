"""
evidence_loop.py — Purged walk-forward + embargo för evidensloopen (ROND 9).

Problem: master_rank reweight jämför block-poäng mot 90/180/365-dagars framtida
avkastning. Dessa fönster överlappar kraftigt (en akties 180-dagsavkastning
delar 179 dagar med nästa dags) → observationerna är INTE oberoende, vilket
gör Rank-IC optimistisk. López de Prado (Advances in Financial ML): purga
träningsobservationer vars etikett-fönster överlappar testperioden, och lägg
en embargo-period efter testet innan nästa träningsobservation får användas.

Användning (ren, testbar, ingen DB):
    folds = purged_walk_forward(df, horizon=90, embargo=5)
    # df behöver: ticker, scan_date, factor-value, forward_return.

Dessutom: `deflated_sharpe_correction(ic, n_tests)` — multipel
testning-korrigering (förenklad Bonferroni/DSR-gate).
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Optional

import numpy as np


def purged_walk_forward(
    rows: list[dict],
    horizon: int = 90,
    embargo: int = 5,
    min_train: int = 50,
    min_test: int = 10,
) -> list[tuple[list[dict], list[dict]]]:
    """Skapa (train, test)-folds med purge + embargo.

    rows: [{ticker, scan_date (date), value, fwd}]. Sorteras på scan_date.
    Varje train-data purgas: alla rader vars etikett-fönster (scan_date +
    horizon) överlappar test-fönstret tas bort. Embargo: 5 dagars tystnad
    efter test-slut innan nästa träningsobservation tillåts.

    Returns: [(train_rows, test_rows), ...] — minst 1 fold om data räcker.
    """
    if not rows or horizon <= 0:
        return []
    rows_sorted = sorted(rows, key=lambda r: r["scan_date"])
    dates = [r["scan_date"] for r in rows_sorted]
    min_d, max_d = dates[0], dates[-1]

    folds: list[tuple[list[dict], list[dict]]] = []
    # Testfönster: glidande, steg = horizon/2. `min_train` = ANTAL RADER.
    # Starta testfönstret så tidigt att purge ändå ger min_train rader:
    # första foldens cutoff = start - horizon - embargo; kräv cutoff >= min_train dagar.
    step = max(1, horizon // 2)
    # min_train rader med 1 rad/dag ≈ min_train dagar före cutoff
    t_start = min_d + timedelta(days=min_train + horizon + embargo)
    while t_start + timedelta(days=horizon) <= max_d:
        t_end = t_start + timedelta(days=horizon)
        test = [r for r in rows_sorted if t_start <= r["scan_date"] <= t_end]
        if len(test) < min_test:
            t_start += timedelta(days=step)
            continue
        # Purge: träning endast fram till test_start - horizon; embargo efter test.
        train_cutoff = t_start - timedelta(days=horizon + embargo)
        train = [r for r in rows_sorted if r["scan_date"] <= train_cutoff]
        if len(train) < min_train:
            t_start += timedelta(days=step)
            continue
        folds.append((train, test))
        t_start += timedelta(days=step)
    return folds


def ic_with_purge(folds: list[tuple[list[dict], list[dict]]], value_key="value",
                  fwd_key="fwd") -> Optional[float]:
    """Weighted IC: beräkna Spearman IC per fold och medelvärde (reweight)."""
    if not folds:
        return None
    ics: list[float] = []
    for train, test in folds:
        xs = [float(r[value_key]) for r in test]
        ys = [float(r[fwd_key]) for r in test]
        if len(xs) < 2:
            continue
        ic = _spearman(xs, ys)
        if ic == ic:  # not NaN
            ics.append(ic)
    if not ics:
        return None
    return float(np.mean(ics))


def _spearman(x: list[float], y: list[float]) -> float:
    """Rank-korrelation (Pearson på ranks). Numpy-only."""
    if len(x) < 2 or len(y) < 2:
        return float("nan")
    rx = np.empty(len(x))
    ry = np.empty(len(y))

    def rank(a):
        order = np.argsort(a, kind="mergesort")
        r = np.empty(len(a))
        r[order] = np.arange(len(a))
        return r

    rx = rank(np.array(x))
    ry = rank(np.array(y))
    if float(np.std(rx)) == 0 or float(np.std(ry)) == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def deflated_sharpe_correction(ic: Optional[float], n_tests: int,
                               n_obs: int) -> Optional[float]:
    """Förenklad DSR/Bonferroni-gate: höjer kravet när fler faktorer testas.

    IC måste överstiga 1.96/sqrt(n_obs * adjustment) för att inte vara brus;
    adjustment = sqrt(ln(n_tests)) (fler tester → högre strap).
    """
    if ic is None or n_obs <= 1:
        return None
    if n_tests <= 1:
        return ic
    z_required = NOISE_Z * math.sqrt(max(1.0, math.log(n_tests))) / math.sqrt(n_obs)
    return ic - z_required   # positivt restvärde = signifikant


NOISE_Z = 1.96
