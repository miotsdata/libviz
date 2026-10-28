"""Spectrum similarity: greedy (modified) cosine, as in matchms' CosineGreedy
/ ModifiedCosine (ADR 6). Pure numpy, no DB. MSIAnalyzer is meant to import
this instead of its own copy (see the reminder in ADR 6)."""
from dataclasses import dataclass

import numpy as np


@dataclass
class Match:
    score: float
    n_matched: int
    pairs: list[tuple[int, int]]  # (index in a, index in b)


def _candidate_pairs(mz_a, mz_b, tolerance: float, shift: float):
    """All (i, j) with |mz_a[i] - (mz_b[j] + shift)| <= tolerance; both sorted."""
    pairs = []
    lo = 0
    for i, m in enumerate(mz_a):
        while lo < len(mz_b) and mz_b[lo] + shift < m - tolerance:
            lo += 1
        j = lo
        while j < len(mz_b) and mz_b[j] + shift <= m + tolerance:
            pairs.append((i, j))
            j += 1
    return pairs


def cosine(mz_a, int_a, mz_b, int_b, *, tolerance: float = 0.01, mz_power: float = 0.0,
           intensity_power: float = 1.0, precursor_a: float | None = None,
           precursor_b: float | None = None, modified: bool = False) -> Match:
    """Greedy cosine between two centroided spectra.

    Peaks pair up within ``tolerance`` (Da), each peak used at most once,
    highest intensity products first. ``modified=True`` (needs both
    precursors) also pairs peaks shifted by the precursor difference, which
    is what makes analog search work. Weights are ``mz**mz_power *
    intensity**intensity_power``.
    """
    mz_a, int_a = np.asarray(mz_a, dtype=float), np.asarray(int_a, dtype=float)
    mz_b, int_b = np.asarray(mz_b, dtype=float), np.asarray(int_b, dtype=float)
    if not len(mz_a) or not len(mz_b):
        return Match(0.0, 0, [])
    order_a, order_b = np.argsort(mz_a), np.argsort(mz_b)
    mz_a, int_a, mz_b, int_b = mz_a[order_a], int_a[order_a], mz_b[order_b], int_b[order_b]
    w_a = mz_a ** mz_power * np.clip(int_a, 0, None) ** intensity_power
    w_b = mz_b ** mz_power * np.clip(int_b, 0, None) ** intensity_power
    norm = np.sqrt((w_a ** 2).sum() * (w_b ** 2).sum())
    if norm == 0:
        return Match(0.0, 0, [])

    pairs = _candidate_pairs(mz_a, mz_b, tolerance, 0.0)
    if modified:
        if precursor_a is None or precursor_b is None:
            raise ValueError("modified cosine needs both precursor m/z values")
        shift = precursor_a - precursor_b
        if abs(shift) > tolerance:
            pairs += _candidate_pairs(mz_a, mz_b, tolerance, shift)
    if not pairs:
        return Match(0.0, 0, [])

    products = np.array([w_a[i] * w_b[j] for i, j in pairs])
    used_a, used_b, chosen, total = set(), set(), [], 0.0
    for k in np.argsort(-products, kind="stable"):
        i, j = pairs[k]
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        chosen.append((int(order_a[i]), int(order_b[j])))
        total += products[k]
    return Match(float(min(total / norm, 1.0)), len(chosen), chosen)


def parse_peak_list(text: str) -> tuple[np.ndarray, np.ndarray]:
    """Peaks pasted by a user: one ``m/z intensity`` pair per line (space,
    tab, comma, semicolon or colon separated), or MoNA's one-line
    ``mz:int mz:int`` form. Lines that aren't two numbers are ignored."""
    text = text.replace(":", " ").replace(";", " ").replace(",", " ")
    tokens = []
    for line in text.splitlines():
        parts = line.split()
        nums = []
        for part in parts:
            try:
                nums.append(float(part))
            except ValueError:
                nums = []
                break
        tokens.extend(nums if len(nums) % 2 == 0 else [])
    values = np.array(tokens, dtype=float).reshape(-1, 2) if tokens else np.empty((0, 2))
    values = values[values[:, 1] > 0]
    order = np.argsort(values[:, 0])
    return values[order, 0], values[order, 1]

