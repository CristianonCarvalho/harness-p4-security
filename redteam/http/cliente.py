"""Cliente HTTP do laboratório. É o único lugar que envia o token, e toda saída é redigida."""

from __future__ import annotations

import json

import httpx

from redteam.http.veredito import Resposta

TOKEN_ERRADO = "token-errado-de-teste-0000000000000000"  # valor fixo de teste, nunca o real
MAX_CORPO_REGISTRADO = 4000


def montar_cabecalhos(autenticacao: str, token: str, extras: dict) -> dict:
    cabecalhos = {"Content-Type": "application/json",
                  "Accept": "application/json, text/event-stream", **extras}
    if autenticacao == "correta":
        cabecalhos["Authorization"] = f"Bearer {token}"
    elif autenticacao == "errada":
        cabecalhos["Authorization"] = f"Bearer {TOKEN_ERRADO}"
    return cabecalhos


def montar_corpo(corpo) -> bytes | None:
    if corpo is None:
        return None
    if isinstance(corpo, str):
        return corpo.encode("utf-8")
    if isinstance(corpo, dict) and "texto_repetido" in corpo:
        rep = corpo["texto_repetido"]
        return (rep["caractere"] * rep["vezes"]).encode("utf-8")
    return json.dumps(corpo, ensure_ascii=False).encode("utf-8")


def redigir(texto: str, token: str) -> str:
    return texto.replace(token, "<TOKEN>") if token else texto


STATUS_SEM_RESPOSTA = 0  # não é um código HTTP: marca que o servidor não respondeu no prazo


def enviar(base_url: str, token: str, req: dict, *, cliente: httpx.Client) -> Resposta:
    try:
        resposta = cliente.request(
            req["metodo"], base_url + req["caminho"],
            headers=montar_cabecalhos(req.get("autenticacao", "correta"), token, req.get("cabecalhos", {})),
            content=montar_corpo(req.get("corpo")),
            timeout=10.0,
        )
    except httpx.TimeoutException as exc:
        # Um fluxo que não termina (por exemplo, um SSE aberto por GET) não pode derrubar a medição.
        return Resposta(STATUS_SEM_RESPOSTA, redigir(str(exc)[:MAX_CORPO_REGISTRADO], token))
    return Resposta(resposta.status_code, redigir(resposta.text[:MAX_CORPO_REGISTRADO], token))
