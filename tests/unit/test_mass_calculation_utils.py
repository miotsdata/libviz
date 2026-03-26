import pytest

from libviz.core.utils import infer_precursor_delta, PROTON


def test_infer_precursor_delta_proton():
    charge, delta, multiplication_factor = infer_precursor_delta("[M+H]+")
    assert charge == 1
    assert abs(delta - PROTON) < 0.01
    assert multiplication_factor == 1


def test_infer_precursor_delta_double_deprotonation():
    charge, delta, multiplication_factor = infer_precursor_delta("[M-2H]2-")
    assert charge == -2
    assert delta < 0
    assert multiplication_factor == 1


def test_infer_precursor_delta_complex():
    charge, delta, multiplication_factor = infer_precursor_delta("[M+2Na-H]+")
    assert charge == 1
    assert delta > 0
    assert multiplication_factor == 1

def test_infer_precursor_delta_complex_multiplication():
    charge, delta, multiplication_factor = infer_precursor_delta("[3M+2Na-H]+")
    assert charge == 1
    assert delta > 0
    assert multiplication_factor == 3


def test_infer_precursor_delta_invalid():
    with pytest.raises(ValueError):
        infer_precursor_delta("invalid_string")