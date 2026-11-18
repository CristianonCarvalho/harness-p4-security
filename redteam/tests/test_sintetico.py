import random

from redteam.sintetico import Sintetico, fingerprint, gerar_cnpj, gerar_cpf, novo
from redteam.varredura import valido


def test_cpf_gerado_tem_dv_valido():
    rng = random.Random(1)
    for _ in range(200):
        n = gerar_cpf(rng)
        assert len(n) == 11 and valido("cpf", n)


def test_cnpj_numerico_e_alfanumerico_tem_dv_valido():
    rng = random.Random(2)
    for _ in range(200):
        assert valido("cnpj", gerar_cnpj(rng))
        assert valido("cnpj", gerar_cnpj(rng, alfanumerico=True))


def test_alfanumerico_tem_letra_em_alguma_amostra():
    rng = random.Random(3)
    assert any(any(c.isalpha() for c in gerar_cnpj(rng, alfanumerico=True)) for _ in range(30))


def test_repr_e_str_nao_mostram_o_numero():
    s = novo("cpf", random.Random(4))
    assert isinstance(s, Sintetico)
    assert s.numero not in repr(s) and s.numero not in str(s)
    assert s.fingerprint in repr(s)


def test_fingerprints_diferentes_para_numeros_diferentes():
    rng = random.Random(5)
    assert novo("cpf", rng).fingerprint != novo("cpf", rng).fingerprint


def test_fingerprint_tem_12_caracteres():
    assert len(fingerprint(gerar_cpf(random.Random(6)))) == 12
