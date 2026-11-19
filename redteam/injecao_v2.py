"""Medição v2 do H13: matriz de 210 rodadas, retomável, com o juiz C4 em cada linha.

Cada rodada vira uma linha JSON no arquivo. Uma rodada que já está no arquivo não roda de novo.
Uma parada, por teto de custo (conservadora) ou por limite de uso, deixa as rodadas que faltam
sem nenhuma linha: é só rodar o mesmo comando de novo. O juiz roda depois, com `julgar_v2`,
e refaz as linhas em que ele deu erro.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from redteam.canario import novo_canario
from redteam.esquema import CATALOGO_DIR
from redteam.injecao import carregar_ataque_injecao
from redteam.injecao_execucao import executar_ataque
from redteam.integridade import conferir, snapshot
from redteam.juiz import julgar_c4
from redteam.runner_injecao import executar

MODELOS_V2 = ("claude-haiku-5-5", "claude-sonnet-5-5")
ATAQUES_V2 = ("I8", "I9", "I10", "I14", "I15", "I16", "I17", "I18", "I19")
ATAQUES_CONTROLE = ("I10", "I16", "I19")  # N: controle neutro
REP_ATAQUE = 15
REP_CONTROLE = 5
TOTAL_MAX_USD = 30.00
POR_EXECUCAO_USD = 0.50
LIMITE_LIBERADO = "allowed"


def chave(ataque: str, modelo: str, rep: int) -> str:
    return f"{ataque}|{modelo}|{rep}"


def planejar_v2() -> list[tuple[str, str, int]]:
    plano = []
    for ataque in ATAQUES_V2:
        reps = REP_CONTROLE if ataque in ATAQUES_CONTROLE else REP_ATAQUE
        for modelo in MODELOS_V2:
            for rep in range(1, reps + 1):
                plano.append((ataque, modelo, rep))
    return plano


def _ler_linhas(jsonl: Path) -> list[dict]:
    if not jsonl.exists():
        return []
    return [json.loads(linha) for linha in jsonl.read_text(encoding="utf-8").splitlines() if linha.strip()]


def _acrescentar(jsonl: Path, linha: dict) -> None:
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _reescrever(jsonl: Path, linhas: list[dict]) -> None:
    tmp = jsonl.with_name(jsonl.name + ".tmp")
    tmp.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in linhas), encoding="utf-8")
    os.replace(tmp, jsonl)


def medir_v2(plano, p2_dir, base_dir, jsonl, *, ataques_dir=CATALOGO_DIR, total_max=TOTAL_MAX_USD,
             por_execucao=POR_EXECUCAO_USD, executor=executar, canario_fn=novo_canario) -> dict:
    p2_dir, base_dir, jsonl = Path(p2_dir), Path(base_dir), Path(jsonl)
    antes = snapshot(p2_dir)
    linhas = _ler_linhas(jsonl)
    feitas = {l["chave"] for l in linhas}
    gasto = sum((l.get("custo") or 0.0) for l in linhas)
    parada = None
    novas = 0
    for ataque, modelo, rep in plano:
        k = chave(ataque, modelo, rep)
        if k in feitas:
            continue
        if gasto + por_execucao > total_max:
            parada = "teto de custo do total"
            break
        dir_exec = base_dir / f"{ataque}-{modelo}-r{rep}"
        if dir_exec.exists():
            shutil.rmtree(dir_exec)  # pasta órfã de uma rodada interrompida; a linha não existe, então refazer é seguro
        r = executar_ataque(Path(ataques_dir) / f"{ataque}.json", modelo, p2_dir, dir_exec,
                            por_execucao, canario=canario_fn(), executor=executor)
        shutil.rmtree(dir_exec)
        _acrescentar(jsonl, {**r, "chave": k, "ataque": ataque, "modelo": modelo, "repeticao": rep,
                             "status": "rodada", "julgamento": None})
        feitas.add(k)
        novas += 1
        gasto += r["custo"] or 0.0
        if r["limite_status"] not in (None, LIMITE_LIBERADO):
            parada = f"limite de uso: {r['limite_status']}"
            break
    conferir(antes, snapshot(p2_dir))
    return {
        "parada": parada,
        "gasto_usd": round(gasto, 4),
        "rodadas_novas": novas,
        "pendentes": sum(1 for a, m, r in plano if chave(a, m, r) not in feitas),
    }


def julgar_v2(jsonl, base_dir, *, ataques_dir=CATALOGO_DIR, executor=executar) -> dict:
    jsonl, base_dir = Path(jsonl), Path(base_dir)
    linhas = _ler_linhas(jsonl)
    julgadas = erros = 0
    for linha in linhas:
        julgamento = linha.get("julgamento")
        if julgamento is not None and julgamento.get("erro") is None:
            continue
        if linha.get("status") != "rodada" or linha.get("erro") or not linha.get("resposta_completa"):
            linha["julgamento"] = {"verdict": None, "classe": None, "justification": None,
                                   "erro": "sem_resposta", "custo": None}
            erros += 1
            continue
        _, registros, pergunta, _ = carregar_ataque_injecao(Path(ataques_dir) / f"{linha['ataque']}.json")
        embutido = " ".join(reg["payload"].replace("{CANARIO}", linha["canario"]) for reg in registros)
        dir_juiz = base_dir / "juiz" / f"{linha['ataque']}-{linha['modelo']}-r{linha['repeticao']}"
        r = julgar_c4(pergunta, embutido, linha["resposta_completa"], dir_juiz, executor=executor)
        linha["julgamento"] = {k: r[k] for k in ("verdict", "classe", "justification", "erro", "custo")}
        if r["erro"]:
            erros += 1
        else:
            julgadas += 1
    _reescrever(jsonl, linhas)
    return {"julgadas": julgadas, "erros": erros}
