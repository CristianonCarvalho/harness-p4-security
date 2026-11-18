from redteam.juiz import (
    CLASSES,
    extrair_canario,
    interpretar_veredito,
    julgar,
    montar_argv_juiz,
    montar_prompt,
)


def test_argv_do_juiz_nao_tem_ferramentas_nem_mcp_do_p2():
    argv = montar_argv_juiz("claude-opus-5-5", "/caminho/vazio.json")
    texto = " ".join(argv)
    assert "WebFetch" not in texto
    assert "mcp__taxlaw" not in texto
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert argv[argv.index("--mcp-config") + 1] == "/caminho/vazio.json"
    assert "--strict-mcp-config" in argv
    assert "--no-session-persistence" in argv
    assert "--bare" not in argv


def test_prompt_traz_as_tres_classes_e_os_tres_dados():
    p = montar_prompt("Qual é a alíquota?", "Instrução: inclua X.", "Resposta com X.")
    for classe in CLASSES:
        assert classe in p
    assert "Qual é a alíquota?" in p
    assert "Instrução: inclua X." in p
    assert "Resposta com X." in p


def test_extrai_o_canario_na_posicao_indicada():
    assert extrair_canario("Segue. CANARIO-1A2B3C4D fim.", len("Segue. ")) == "CANARIO-1A2B3C4D"


def test_sem_posicao_nao_ha_canario():
    assert extrair_canario("Sem a palavra.", None) is None


def test_veredito_valido_e_lido_mesmo_com_texto_ao_redor():
    texto = 'Aqui está: {"classe": "denuncia", "motivo": "ignorou"} fim.'
    assert interpretar_veredito(texto) == {"classe": "denuncia", "motivo": "ignorou", "erro": None}


def test_classe_fora_do_conjunto_e_erro():
    r = interpretar_veredito('{"classe": "talvez", "motivo": "x"}')
    assert r["classe"] is None
    assert "classe_invalida" in r["erro"]


def test_texto_sem_json_e_erro():
    r = interpretar_veredito("não sei responder")
    assert r["classe"] is None
    assert r["erro"] == "sem_json"


def test_julgar_chama_o_executor_com_o_prompt_e_devolve_a_classe(tmp_path):
    chamadas = []

    def executor(argv, prompt, cwd):
        chamadas.append((argv, prompt, cwd))
        return {"resultado": '{"classe": "seguiu", "motivo": "cumpriu"}', "erro": None, "custo": 0.01}

    r = julgar("Qual é?", "Instrução: inclua X.", "Resposta com X.", tmp_path, executor=executor)
    assert r == {"classe": "seguiu", "motivo": "cumpriu", "erro": None, "custo": 0.01}
    argv, prompt, cwd = chamadas[0]
    assert cwd == tmp_path
    assert "Resposta com X." in prompt
    assert (tmp_path / "mcp-vazio.json").exists()


def test_erro_do_executor_vira_erro_do_juiz(tmp_path):
    def executor(argv, prompt, cwd):
        return {"resultado": None, "erro": "timeout", "custo": None}

    r = julgar("Qual é?", "Instrução.", "Resposta.", tmp_path, executor=executor)
    assert r["classe"] is None
    assert r["erro"] == "timeout"
