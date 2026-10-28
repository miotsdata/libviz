import numpy as np
import pytest

from libviz.core.similarity import cosine, parse_peak_list


def test_identical_spectra_score_one():
    m = cosine([100, 200, 300], [10, 50, 100], [100, 200, 300], [10, 50, 100])
    assert m.score == pytest.approx(1.0)
    assert m.n_matched == 3


def test_tolerance_and_disjoint():
    assert cosine([100.0], [1], [100.005], [1], tolerance=0.01).score == pytest.approx(1.0)
    assert cosine([100.0], [1], [100.05], [1], tolerance=0.01).score == 0.0
    assert cosine([], [], [1.0], [1.0]).score == 0.0


def test_greedy_uses_each_peak_once():
    # Two query peaks near one library peak: only the heavier pair counts.
    m = cosine([100.0, 100.008], [1, 10], [100.004], [1], tolerance=0.01)
    assert m.n_matched == 1
    assert m.pairs == [(1, 0)]
    assert m.score == pytest.approx(10 / np.sqrt(101))


def test_known_value():
    # a = (3, 4), b = (4, 3) on the same m/z: cos = 24 / 25
    assert cosine([100, 200], [3, 4], [100, 200], [4, 3]).score == pytest.approx(0.96)


def test_modified_cosine_matches_shifted_fragments():
    a_mz, b_mz = [50.0, 150.0, 250.0], [50.0, 164.0, 264.0]  # b is a + CH2 on two fragments
    intensities = [1.0, 1.0, 1.0]
    plain = cosine(a_mz, intensities, b_mz, intensities)
    modified = cosine(a_mz, intensities, b_mz, intensities, precursor_a=300.0, precursor_b=314.0, modified=True)
    assert plain.n_matched == 1 and modified.n_matched == 3
    assert modified.score == pytest.approx(1.0)
    with pytest.raises(ValueError):
        cosine(a_mz, intensities, b_mz, intensities, modified=True)


def test_parse_peak_list():
    mz, inten = parse_peak_list("138.0662 100\n110.0713\t20\nNum Peaks: 2\n50,0\n")
    assert mz.tolist() == [110.0713, 138.0662] and inten.tolist() == [20.0, 100.0]
    mz, _ = parse_peak_list("100:1 200:2 300:3")
    assert mz.tolist() == [100.0, 200.0, 300.0]
