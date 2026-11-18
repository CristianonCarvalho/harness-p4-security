"""Gate da VPS: lista exata, assinatura, limite de 30 requisições e 2 por segundo, para em 429 ou 5xx."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import httpx

from redteam.esquema import CATALOGO_DIR
from redteam.http.cliente import enviar
from redteam.http.requisicoes import carregar_ataque_http

MAX_REQUISICOES = 30
LIMITE_TAXA = 429
IDS_HTTP = ["H1", "H2", "H3", "H4", "H5", "H8", "H9"]
SAIDA = Path("docs/redteam/medicao-vps.json")


def listar(catalogo: list[tuple[str, list[dict]]]) -> list[dict]:
    """As requisições que sairiam para a VPS. O token não está no catálogo, então não aparece aqui."""
    lista = []
    for ataque_id, reqs in catalogo:
        for req in reqs:
            if "vps" in req["alvos"]:
                lista.append({"ataque": ataque_id, **req})
    return lista


def assinatura(lista: list[dict]) -> str:
    return hashlib.sha256(json.dumps(lista, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def executar(lista: list[dict], base_url: str, token: str, *, cliente: httpx.Client, confirmacao: str,
             max_requisicoes: int = MAX_REQUISICOES, intervalo_s: float = 0.5,
             sleep=time.sleep) -> list[dict]:
    if len(lista) > max_requisicoes:
        raise ValueError(f"{len(lista)} requisições; o limite é {max_requisicoes}")
    if confirmacao != assinatura(lista):
        raise ValueError("a assinatura não bate com a lista; nada foi enviado")
    resultados = []
    for i, req in enumerate(lista):
        if i:
            sleep(intervalo_s)
        try:
            observado = enviar(base_url, token, req, cliente=cliente)
        except Exception as exc:  # noqa: BLE001 - registrar e parar; a mensagem não entra, pode conter o token
            resultados.append({"ataque": req["ataque"], "requisicao": req["nome"], "status": None,
                               "parada": f"erro de execução: {type(exc).__name__}"})
            break
        registro = {"ataque": req["ataque"], "requisicao": req["nome"], "status": observado.status,
                    "trecho": observado.corpo[:200]}
        if observado.status == LIMITE_TAXA or 500 <= observado.status < 600:
            registro["parada"] = "limite de taxa" if observado.status == LIMITE_TAXA else "erro do servidor"
            resultados.append(registro)
            break
        resultados.append(registro)
    return resultados


def _catalogo_vps() -> list[tuple[str, list[dict]]]:
    catalogo = []
    for i in IDS_HTTP:
        attack, reqs, _ = carregar_ataque_http(Path(CATALOGO_DIR) / f"{i}.json")
        catalogo.append((attack.id, reqs))
    return catalogo


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gate da VPS: liste e depois execute com a assinatura.")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--executar", action="store_true")
    ap.add_argument("--confirmacao", default="")
    args = ap.parse_args(argv)
    lista = listar(_catalogo_vps())
    if args.listar:
        print(json.dumps(lista, ensure_ascii=False, indent=2))
        print(f"assinatura: {assinatura(lista)}")
        return 0
    if args.executar:
        base = os.environ["TAXLAW_VPS_BASE"]
        token = os.environ["TAXLAW_VPS_TOKEN"]
        with httpx.Client() as cliente:
            resultados = executar(lista, base, token, cliente=cliente, confirmacao=args.confirmacao)
        SAIDA.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{len(resultados)} registros em {SAIDA}")
        return 0
    ap.error("use --listar ou --executar")


if __name__ == "__main__":
    raise SystemExit(main())
