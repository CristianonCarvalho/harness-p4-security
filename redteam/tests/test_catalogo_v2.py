import json
import os
import subprocess
from pathlib import Path

import pytest

from redteam.catalogo_v2 import PERGUNTA_1, PERGUNTA_2, TABELA, gerar
from redteam.envenenar import envenenar
from redteam.injecao import carregar_ataque_injecao
from redteam.workdir import prepare_workdir

CANARIO = "CANARIO-1A2B3C4D"


@pytest.fixture
def catalogo(tmp_path):
    pasta = tmp_path / "ataques"
    gerar(pasta)
    return pasta


def _bruto(pasta, ident):
    return json.loads((pasta / f"{ident}.json").read_text(encoding="utf-8"))


def test_gerar_escreve_os_nove_arquivos_e_eles_carregam(catalogo):
    for ident, *_ in TABELA:
        attack, registros, pergunta, oraculo = carregar_ataque_injecao(catalogo / f"{ident}.json")
        assert attack.id == ident
        assert registros and pergunta
        assert oraculo in {"canario", "valor"}


def test_ids_e_perguntas_seguem_a_tabela(catalogo):
    esperado = {"P1": PERGUNTA_1, "P2": PERGUNTA_2}
    for ident, pergunta, _, _ in TABELA:
        assert _bruto(catalogo, ident)["entrada"]["pergunta"] == esperado[pergunta]
    assert [t[0] for t in TABELA] == ["I8", "I9", "I10", "I14", "I15", "I16", "I17", "I18", "I19"]


def test_posicao_segue_o_alvo(catalogo):
    for ident, _, alvo, _ in TABELA:
        reg = _bruto(catalogo, ident)["entrada"]["registros"][0]
        assert reg["alvo"] == ("alvo" if alvo == "A" else "alvo2")
        assert reg["posicao"] == ("fim" if alvo == "A" else "inicio")


def test_oraculo_valor_so_no_comportamento_v(catalogo):
    for ident, _, _, comp in TABELA:
        criterio = _bruto(catalogo, ident)["criterio"]
        if comp == "V":
            assert criterio == {"oraculo": "valor", "valor": "27%"}
        else:
            assert criterio == {"oraculo": "canario"}


def test_marcador_do_canario_so_no_comportamento_t(catalogo):
    for ident, _, _, comp in TABELA:
        payload = _bruto(catalogo, ident)["entrada"]["registros"][0]["payload"]
        assert ("{CANARIO}" in payload) == (comp == "T")


def test_payloads_sem_url_sem_cpf_e_com_previsao_rotulada(catalogo):
    for ident, *_ in TABELA:
        bruto = _bruto(catalogo, ident)
        texto = json.dumps(bruto, ensure_ascii=False).lower()
        assert "http" not in texto and "www" not in texto and "{cpf" not in texto
        assert bruto["previsao"]["motivo"].startswith("Previsão do Claude (não do Cristiano)")


@pytest.mark.skipif(os.environ.get("REDTEAM_INTEGRACAO") != "1",
                    reason="integração: roda o P2 real; use REDTEAM_INTEGRACAO=1")
def test_cada_arquivo_acha_o_alvo_e_respeita_a_regra_do_trecho(tmp_path, catalogo):
    p2 = Path(os.environ["REDTEAM_P2_DIR"])
    busca = (
        "import json, sys\n"
        "from taxlaw.tools import buscar_dispositivos, load_context\n"
        "res = buscar_dispositivos(load_context(), sys.argv[1], None, 5)\n"
        "alvo = next((h for h in res['resultados'] if h['id'] == sys.argv[2]), None)\n"
        "print(json.dumps({'top5': [h['id'] for h in res['resultados']],"
        " 'no_trecho': bool(alvo) and sys.argv[3] in alvo['trecho']}))\n"
    )
    alvo_id = {"alvo": "LC214.art125", "alvo2": "EC132.art8.parunico"}
    for ident, _, _, _ in TABELA:
        bruto = _bruto(catalogo, ident)
        reg = bruto["entrada"]["registros"][0]
        payload = reg["payload"].replace("{CANARIO}", CANARIO)
        copia = tmp_path / f"copia-{ident}"
        prepare_workdir(p2, copia)
        envenenar(copia, [{**reg, "payload": payload}], CANARIO)
        saida = subprocess.run(
            ["uv", "run", "--project", str(copia), "python", "-c", busca,
             bruto["entrada"]["pergunta"], alvo_id[reg["alvo"]], payload],
            cwd=copia, capture_output=True, text=True, check=True, timeout=600,
        ).stdout
        achado = json.loads(saida.strip().splitlines()[-1])
        assert alvo_id[reg["alvo"]] in achado["top5"], ident
        assert achado["no_trecho"] is (reg["posicao"] == "inicio"), ident
