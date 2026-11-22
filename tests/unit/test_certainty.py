from engine.certainty import combine, combine_all, penalize, propagate


def test_combine_positivos():
    assert combine(0.6, 0.5) == 0.8


def test_combine_opostos():
    assert abs(combine(0.6, -0.4) - (0.2 / 0.6)) < 1e-9


def test_combine_all_comutativo():
    assert abs(combine_all([0.3, 0.5, 0.2]) - combine_all([0.2, 0.3, 0.5])) < 1e-9


def test_propagate_e_penalize():
    assert propagate(0.9, [0.5, 0.8]) == 0.45
    assert penalize(0.9, [0.4]) == 0.9 * 0.4
