import re
from pyteomics.mass import calculate_mass
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
    inner_match = re.search(r'\[M([^\]]+)\]', name)
    if not inner_match:
        raise ValueError(f"Cannot extract modifications from precursor: {name}")
    content = inner_match.group(1)  # e.g., "+H", "+2Na-H"

    # ---------- Parse all modifications ----------
    delta = 0.0
    # matches sign (+/-), optional count (\d*), then formula ([A-Za-z0-9]+)
    for mod in re.finditer(r'([+-])(\d*)([A-Za-z][A-Za-z0-9]*)', content):
        mod_sign = 1 if mod.group(1) == '+' else -1
        count = int(mod.group(2) or 1)
        formula = mod.group(3)
        # compute mass
        delta += mod_sign * count * calculate_mass(formula=formula)

    return charge, delta


def calculate_exact_mass(formula: str) -> float | None:
    if not formula:
        return None
    try:
        return calculate_mass(formula=formula)
    except Exception:
        return None