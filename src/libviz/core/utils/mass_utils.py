import re
from pyteomics.mass import calculate_mass
from pyteomics.auxiliary.structures import PyteomicsError
PROTON = 1.007276466812

def infer_precursor_delta(name: str) -> tuple[int, float]:
    """
    Infer (charge, delta_mass) from a precursor string like:
    [M+H]+
    [M-2H]2-
    [M+2Na-H]-
    Returns: (charge, delta_mass)
    """

    # ---------- Extract charge ----------
    charge_match = re.search(r'(\d*)([+-])$', name)
    if not charge_match:
        raise ValueError(f"Cannot infer charge from precursor: {name}")
    magnitude = int(charge_match.group(1) or 1)
    sign = 1 if charge_match.group(2) == '+' else -1
    charge = sign * magnitude

    # ---------- Extract content inside brackets ----------
    inner_match = re.search(r'\[(\d*)M([^\]]+)\]', name)
    if not inner_match:
        raise ValueError(f"Cannot extract modifications from precursor: {name}")
    multiplication_factor = int(inner_match.group(1)) if inner_match.group(1) else 1
    content = inner_match.group(2)  # e.g., "+H", "+2Na-H"
    content = content.replace("FA-H", "HCOO").replace("Hac", "CH3COOH")

    # ---------- Parse all modifications ----------
    delta = 0.0
    # matches sign (+/-), optional count (\d*), then formula ([A-Za-z0-9]+)
    for mod in re.finditer(r'([+-])(\d*)([A-Za-z][A-Za-z0-9]*)', content):
        mod_sign = 1 if mod.group(1) == '+' else -1
        count = int(mod.group(2) or 1)
        formula = mod.group(3)
        # compute mass
        delta += mod_sign * count * calculate_mass(formula=formula)

    return charge, delta, multiplication_factor


def calculate_exact_mass(formula: str, n_decimals: int = 4) -> float | None:
    if not formula:
        return None
    try:
        return round(calculate_mass(formula=formula), n_decimals)
    except Exception:
        return None

def calculate_exact_mass_formula_adduct(formula: str, delta: float, n_decimals: int = 4) -> float | None:
    if not formula:
        return None
    try:
        return round(calculate_mass(formula=formula) + delta, n_decimals)
    except PyteomicsError as e:
        raise e


ELECTRON = 0.000548579909065


def adduct_mz(neutral_mass: float, adduct: str) -> float:
    """m/z of ``adduct`` (e.g. "[M+H]+", "[2M+Na]+", "[M-2H]2-") of a
    neutral monoisotopic mass. ``infer_precursor_delta`` sums *atom*
    masses, so the ion's missing/extra electrons are corrected here."""
    charge, delta, multiplier = infer_precursor_delta(adduct)
    return (multiplier * neutral_mass + delta - charge * ELECTRON) / abs(charge)


def neutral_mass(mz: float, adduct: str) -> float:
    """Inverse of :func:`adduct_mz`: the neutral mass whose ``adduct`` ion has m/z ``mz``."""
    charge, delta, multiplier = infer_precursor_delta(adduct)
    return (mz * abs(charge) - delta + charge * ELECTRON) / multiplier
