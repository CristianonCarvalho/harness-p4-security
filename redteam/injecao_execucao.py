"""Uma execução completa do laboratório de injeção.

Cada execução tem uma cópia nova do P2 com o corpo envenenado, um diretório neutro para o
`claude -p`, um canário novo e um veredito. O P2 original é conferido antes e depois: se ele
mudou, a rodada é inválida e a função levanta P2Mudou.
"""

from __future__ import annotations

from pathlib import Path

from redteam.canario import classificar, expostos, novo_canario
from redteam.envenenar import envenenar
from redteam.injecao import carregar_ataque_injecao
from redteam.integridade import conferir, snapshot
from redteam.runner_injecao import executar, gravar_mcp_config, montar_argv
from redteam.workdir import MCP_CONFIG_NAME, prepare_workdir

TRECHO_MAX = 500


def executar_ataque(
    ataque: Path,
    modelo: str,
    p2_dir: Path,
    dir_execucao: Path,
    max_budget_usd: float,
    *,
    canario: str | None = None,
    executor=executar,
) -> dict:
    """Roda um ataque uma vez. `dir_execucao` precisa não existir: cada execução é a sua pasta.

    `executor(argv, pergunta, cwd) -> dict` é o runner; os testes passam um falso.
    """
    attack, registros, pergunta, _ = carregar_ataque_injecao(Path(ataque))
    p2_dir = Path(p2_dir)
    dir_execucao = Path(dir_execucao)
    if dir_execucao.exists():
        raise FileExistsError(f"a pasta da execução já existe: {dir_execucao}")
    canario = canario or novo_canario()

    antes = snapshot(p2_dir)
    copia = dir_execucao / "copia"
    neutro = dir_execucao / "neutro"
    prepare_workdir(p2_dir, copia)
    corpus_sha = envenenar(copia, registros, canario)
    neutro.mkdir(parents=True)
    config = gravar_mcp_config(copia, neutro / MCP_CONFIG_NAME)
    argv = montar_argv(modelo, max_budget_usd, str(config))

    r = executor(argv, pergunta, neutro)
    conferir(antes, snapshot(p2_dir))

    payloads = [reg["payload"].replace("{CANARIO}", canario) for reg in registros]
    vistos = expostos(r["resultados_de_ferramentas"], payloads)
    # Erro do runner não é resposta: não entra como L0, nem como qualquer outro veredito.
    resposta = r["resultado"] or ""
    veredito = None if r["erro"] else classificar(vistos, resposta, canario)
    posicao = resposta.find(canario)
    posicao_canario = posicao if posicao >= 0 else None
    return {
        "ataque": attack.id,
        "modelo": modelo,
        "veredito": veredito,
        "expostos": vistos,
        "erro": r["erro"],
        "custo": r["custo"],
        "turnos": r["turnos"],
        "corpus_sha256": corpus_sha,
        "resposta_trecho": (r["resultado"] or "")[:TRECHO_MAX],
        "resposta_completa": resposta,
        "posicao_canario": posicao_canario,
        "limite_status": r.get("limite_status"),
    }
