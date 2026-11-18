import random

from redteam.formas import formas, formas_no_texto
from redteam.sintetico import novo


def test_todas_as_formas_do_cpf_existem():
    s = novo("cpf", random.Random(10))
    assert set(formas(s)) == {"pura", "pontuada", "espacada", "largura_total", "invisivel"}


def test_cada_forma_e_achada_pelo_nome_certo():
    s = novo("cpf", random.Random(11))
    for nome, texto in formas(s).items():
        assert formas_no_texto(f"antes {texto} depois", s) == [nome], nome


def test_texto_sem_o_numero_nao_acha_nada():
    s = novo("cpf", random.Random(12))
    assert formas_no_texto("Art. 125. Ficam reduzidas a zero as alíquotas do IBS e da CBS.", s) == []


def test_pontuada_de_cnpj_tem_a_estrutura_certa():
    s = novo("cnpj", random.Random(13))
    p = formas(s)["pontuada"]
    assert p[2] == "." and p[6] == "." and p[10] == "/" and p[15] == "-"


def test_largura_total_de_cnpj_alfanumerico_nao_tem_letra_ascii():
    s = novo("cnpj", random.Random(14), alfanumerico=True)
    largura = formas(s)["largura_total"]
    assert not any("A" <= c <= "Z" for c in largura)
