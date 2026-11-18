import subprocess

import pytest

from redteam.integridade import P2Mudou, conferir, snapshot


def _git(p, *args):
    subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


@pytest.fixture
def p2(tmp_path):
    raiz = tmp_path / "p2"
    (raiz / "corpus").mkdir(parents=True)
    (raiz / "corpus" / "dispositivos.json").write_text('{"dispositivos": []}', encoding="utf-8")
    _git(raiz, "init", "-q")
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-qm", "base")
    return raiz


def test_snapshot_igual_nao_levanta(p2):
    conferir(snapshot(p2), snapshot(p2))


def test_mudanca_no_corpus_levanta_e_diz_o_que_mudou(p2):
    antes = snapshot(p2)
    (p2 / "corpus" / "dispositivos.json").write_text('{"x": 1}', encoding="utf-8")
    with pytest.raises(P2Mudou) as exc:
        conferir(antes, snapshot(p2))
    assert "corpus_sha256" in str(exc.value) and "git_status" in str(exc.value)


def test_arquivo_novo_sem_rastreio_levanta(p2):
    antes = snapshot(p2)
    (p2 / "novo.txt").write_text("x", encoding="utf-8")
    with pytest.raises(P2Mudou):
        conferir(antes, snapshot(p2))
