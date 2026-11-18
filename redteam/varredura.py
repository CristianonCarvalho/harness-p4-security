"""Varredura: nenhum CPF ou CNPJ com dígito verificador válido nos arquivos rastreados pelo git.

Um achado mostra caminho, linha, tipo e fingerprint, nunca o número. Falsos positivos entram
em `redteam/varredura_allow.txt` pelo fingerprint.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_ANTES = r"(?<![0-9A-Za-z])"
_DEPOIS = r"(?![0-9A-Za-z])"
_REGEX = [
    ("cpf", re.compile(_ANTES + r"[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}" + _DEPOIS)),
    ("cpf", re.compile(_ANTES + r"[0-9]{11}" + _DEPOIS)),
    ("cnpj", re.compile(_ANTES + r"[0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-[0-9]{2}" + _DEPOIS)),
    ("cnpj", re.compile(_ANTES + r"[0-9A-Z]{14}" + _DEPOIS)),
]
_SEP = re.compile(r"[./-]")
CPF_P1 = tuple(range(10, 1, -1))
CPF_P2 = tuple(range(11, 1, -1))
CNPJ_P1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
CNPJ_P2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
MAX_BYTES = 5_000_000
ALLOW_PADRAO = Path(__file__).parent / "varredura_allow.txt"


@dataclass(frozen=True)
class Hit:
    caminho: str
    linha: int
    tipo: str
    fingerprint: str


def _dv(valores: list[int], pesos: tuple[int, ...]) -> int:
    r = sum(v * p for v, p in zip(valores, pesos, strict=True)) % 11
    return 0 if r < 2 else 11 - r


def valido(tipo: str, numero: str) -> bool:
    if tipo == "cpf":
        if not re.fullmatch(r"[0-9]{11}", numero) or len(set(numero)) == 1:
            return False
        base = [int(c) for c in numero[:9]]
        d1 = _dv(base, CPF_P1)
        return numero[9:] == f"{d1}{_dv(base + [d1], CPF_P2)}"
    if not re.fullmatch(r"[0-9A-Z]{14}", numero) or len(set(numero)) == 1 or not numero[12:].isdigit():
        return False
    v = [ord(c) - 48 for c in numero[:12]]
    d1 = _dv(v, CNPJ_P1)
    return numero[12:] == f"{d1}{_dv(v + [d1], CNPJ_P2)}"


def fingerprint(numero: str) -> str:
    return hashlib.sha256(numero.encode()).hexdigest()[:12]


def scan_text(texto: str) -> list[tuple[int, str, str]]:
    achados = []
    for n_linha, linha in enumerate(texto.splitlines(), 1):
        for tipo, regex in _REGEX:
            for m in regex.finditer(linha):
                compacto = _SEP.sub("", m.group()).upper()
                if valido(tipo, compacto):
                    achados.append((n_linha, tipo, fingerprint(compacto)))
    return achados


def carregar_allow(caminho: Path = ALLOW_PADRAO) -> set[str]:
    if not caminho.exists():
        return set()
    entradas = set()
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.split("#", 1)[0].strip()
        if linha:
            entradas.add(linha)
    return entradas


def scan_file(caminho: Path, allow: set[str]) -> list[Hit]:
    try:
        if caminho.stat().st_size > MAX_BYTES:
            return []
        texto = caminho.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [Hit(str(caminho), n, tipo, fp) for n, tipo, fp in scan_text(texto) if fp not in allow]


def arquivos_rastreados(raiz: Path) -> list[Path]:
    saida = subprocess.run(["git", "-C", str(raiz), "ls-files", "-z"],
                           capture_output=True, check=True).stdout.decode()
    return [Path(raiz) / p for p in saida.split("\0") if p]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Procura CPF e CNPJ válidos nos arquivos do repositório.")
    ap.add_argument("--raiz", type=Path, default=Path("."))
    ap.add_argument("--allow", type=Path, default=ALLOW_PADRAO)
    ap.add_argument("--arquivos", nargs="*", type=Path, default=None)
    args = ap.parse_args(argv)
    allow = carregar_allow(args.allow)
    arquivos = args.arquivos if args.arquivos is not None else arquivos_rastreados(args.raiz)
    achados = [h for a in arquivos for h in scan_file(a, allow)]
    for h in achados:
        print(f"{h.caminho}:{h.linha}: {h.tipo} com dígito verificador válido (fingerprint {h.fingerprint})")
    if achados:
        print(f"{len(achados)} achado(s): remova o número ou, se for falso positivo, "
              f"acrescente o fingerprint em {args.allow.name}.", file=sys.stderr)
        return 1
    print("nenhum CPF ou CNPJ válido encontrado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
