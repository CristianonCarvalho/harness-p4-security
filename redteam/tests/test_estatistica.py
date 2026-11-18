import pytest

from redteam.estatistica import taxa, wilson


def test_zero_de_cinco():
    a, b = wilson(0, 5)
    assert a == pytest.approx(0.0, abs=1e-6)
    assert b == pytest.approx(0.4345, abs=0.001)


def test_dois_de_cinco():
    a, b = wilson(2, 5)
    assert a == pytest.approx(0.1176, abs=0.001)
    assert b == pytest.approx(0.7692, abs=0.001)


def test_cinco_de_cinco():
    a, b = wilson(5, 5)
    assert a == pytest.approx(0.5654, abs=0.001)
    assert b == pytest.approx(1.0, abs=0.001)


def test_sem_execucao_nao_divide_por_zero():
    assert wilson(0, 0) == (0.0, 1.0)
    assert taxa(0, 0) == "0/0 (sem execuções)"


@pytest.mark.parametrize("k,n", [(-1, 5), (6, 5), (0, -1)])
def test_valores_invalidos_sao_recusados(k, n):
    with pytest.raises(ValueError):
        wilson(k, n)


def test_texto_da_taxa():
    assert taxa(2, 5) == "2/5 = 40% (IC 95%: 12% a 77%)"
    assert taxa(0, 5) == "0/5 = 0% (IC 95%: 0% a 43%)"
    assert taxa(5, 5) == "5/5 = 100% (IC 95%: 57% a 100%)"
