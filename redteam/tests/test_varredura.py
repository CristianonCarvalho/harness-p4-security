import random

from redteam.varredura import main, scan_file, scan_text

RNG = random.Random(7)
CPF_P1 = tuple(range(10, 1, -1))
CPF_P2 = tuple(range(11, 1, -1))
CNPJ_P1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
CNPJ_P2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
ALFABETO = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _dv(valores, pesos):
    r = sum(v * p for v, p in zip(valores, pesos)) % 11
    return 0 if r < 2 else 11 - r


def _cpf(base9):
    v = [int(c) for c in base9]
    d1 = _dv(v, CPF_P1)
    return base9 + f"{d1}{_dv(v + [d1], CPF_P2)}"


def _cnpj(base12):
    v = [ord(c) - 48 for c in base12]
    d1 = _dv(v, CNPJ_P1)
    return base12 + f"{d1}{_dv(v + [d1], CNPJ_P2)}"


def _digitos(n):
    return "".join(str(RNG.randrange(10)) for _ in range(n))


def test_acha_cpf_puro_e_formatado_sem_mostrar_o_numero():
    n1, n2 = _cpf(_digitos(9)), _cpf(_digitos(9))
    formatado = f"{n2[:3]}.{n2[3:6]}.{n2[6:9]}-{n2[9:]}"
    achados = scan_text(f"linha um\ncpf {n1} aqui\nOutro: {formatado}.")
    assert [(a[0], a[1]) for a in achados] == [(2, "cpf"), (3, "cpf")]
    assert n1 not in str(achados) and n2 not in str(achados)


def test_acha_cnpj_numerico_e_alfanumerico_formatado():
    numerico = _cnpj(_digitos(12))
    base = "".join(RNG.choice(ALFABETO) for _ in range(12))
    alfa = _cnpj(base)
    formatado = f"{alfa[:2]}.{alfa[2:5]}.{alfa[5:8]}/{alfa[8:12]}-{alfa[12:]}"
    assert [a[1] for a in scan_text(f"{numerico}\n{formatado}")] == ["cnpj", "cnpj"]


def test_dv_errado_e_numero_colado_nao_sao_achados():
    n = _cpf(_digitos(9))
    errado = n[:-1] + str((int(n[-1]) + 1) % 10)
    assert scan_text(f"processo {errado}") == []
    assert scan_text(f"9{n}") == [] and scan_text(f"{n}9") == []


def test_texto_normal_passa():
    assert scan_text("Art. 125. Ficam reduzidas a zero as alíquotas do IBS e da CBS.") == []


def test_binario_e_nao_utf8_sao_ignorados(tmp_path):
    arq = tmp_path / "b.bin"
    arq.write_bytes(b"\xff\xfe\x00" + bytes(range(256)))
    assert scan_file(arq, allow=set()) == []


def test_fingerprint_na_lista_de_excecoes_suprime(tmp_path):
    arq = tmp_path / "a.txt"
    arq.write_text(f"id {_cpf(_digitos(9))}\n", encoding="utf-8")
    achados = scan_file(arq, allow=set())
    assert len(achados) == 1
    assert scan_file(arq, allow={achados[0].fingerprint}) == []


def test_main_retorna_1_com_achado_e_0_sem(tmp_path, capsys):
    ok = tmp_path / "ok.txt"
    ok.write_text("nada aqui\n", encoding="utf-8")
    n = _cpf(_digitos(9))
    ruim = tmp_path / "ruim.txt"
    ruim.write_text(f"{n}\n", encoding="utf-8")
    allow = tmp_path / "allow.txt"
    allow.write_text("", encoding="utf-8")
    assert main(["--allow", str(allow), "--arquivos", str(ok)]) == 0
    assert main(["--allow", str(allow), "--arquivos", str(ok), str(ruim)]) == 1
    saida = capsys.readouterr()
    assert n not in saida.out + saida.err and "ruim.txt:1" in saida.out
