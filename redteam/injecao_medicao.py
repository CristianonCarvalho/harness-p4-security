"""Medição do laboratório de injeção: ataques × modelos × repetições.

Duas paradas protegem a conta e a janela de uso: o custo acumulado não passa do teto total
(conservador: uma rodada só começa se couber o teto por execução), e a medição para quando o
limite de uso deixa de estar liberado. Quem não roda vira `nao_rodada`, nunca L0.
O P2 é conferido antes e depois; se mudar, a medição levanta P2Mudou.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from redteam.canario import novo_canario
from redteam.injecao_execucao import executar_ataque
from redteam.integridade import conferir, snapshot
from redteam.runner_injecao import executar

ATAQUES_DIR = Path(__file__).resolve().parent / "ataques"
ATAQUES = ("I1", "I2", "I3", "I4", "I5", "I6", "I7")
MODELOS = ("claude-haiku-5-5", "claude-sonnet-5-5")
REPETICOES = 5
TOTAL_MAX_USD = 3.00
POR_EXECUCAO_USD = 0.50
LIMITE_LIBERADO = "allowed"


def _nao_rodada(ataque: str, modelo: str, repeticao: int, motivo: str) -> dict:
    return {
        "ataque": ataque, "modelo": modelo, "repeticao": repeticao,
        "status": "nao_rodada", "motivo": motivo, "veredito": None, "expostos": [],
        "erro": None, "custo": None, "turnos": None, "corpus_sha256": None,
        "resposta_trecho": "", "limite_status": None,
    }


def medir(ataques_dir, p2_dir, base_dir, *, ataques=ATAQUES, modelos=MODELOS, repeticoes=REPETICOES,
          total_max=TOTAL_MAX_USD, por_execucao=POR_EXECUCAO_USD, executor=executar,
          canario_fn=novo_canario) -> dict:
    ataques_dir, p2_dir, base_dir = Path(ataques_dir), Path(p2_dir), Path(base_dir)
    antes = snapshot(p2_dir)
    registros = []
    gasto = 0.0
    parada = None
    for ataque in ataques:
        for modelo in modelos:
            for rep in range(1, repeticoes + 1):
                if parada is None and gasto + por_execucao > total_max:
                    parada = "teto de custo do total"
                if parada is not None:
                    registros.append(_nao_rodada(ataque, modelo, rep, parada))
                    continue
                dir_exec = base_dir / f"{ataque}-{modelo}-r{rep}"
                r = executar_ataque(ataques_dir / f"{ataque}.json", modelo, p2_dir, dir_exec,
                                    por_execucao, canario=canario_fn(), executor=executor)
                shutil.rmtree(dir_exec)
                r.update({"repeticao": rep, "status": "rodada", "motivo": None})
                registros.append(r)
                gasto += r["custo"] or 0.0
                if r["limite_status"] not in (None, LIMITE_LIBERADO):
                    parada = f"limite de uso: {r['limite_status']}"
    depois = snapshot(p2_dir)
    conferir(antes, depois)
    return {
        "parada": parada,
        "gasto_usd": round(gasto, 4),
        "teto_usd": total_max,
        "p2_antes": antes,
        "p2_depois": depois,
        "registros": registros,
    }


def gravar(saida: dict, destino: Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Medição do laboratório de injeção (70 rodadas por padrão).")
    ap.add_argument("--p2", type=Path, required=True)
    ap.add_argument("--base", type=Path, required=True, help="pasta nova para as cópias de cada rodada")
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--executar", action="store_true", help="sem esta flag, só mostra o plano")
    args = ap.parse_args(argv)
    total = len(ATAQUES) * len(MODELOS) * REPETICOES
    if not args.executar:
        print(f"{total} rodadas planejadas; teto total US$ {TOTAL_MAX_USD:.2f}. Sem --executar, nada roda.")
        return 0
    saida = medir(ATAQUES_DIR, args.p2, args.base)
    gravar(saida, args.saida)
    rodadas = [r for r in saida["registros"] if r["status"] == "rodada"]
    print(f"rodadas: {len(rodadas)} de {total}; gasto: US$ {saida['gasto_usd']:.4f}; parada: {saida['parada']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
