# Laboratório HTTP do red team no P2: plano de implementação

> **Para quem executa:** REQUIRED SUB-SKILL: use superpowers:executing-plans (execução nativa) ou superpowers:subagent-driven-development. Os passos usam caixas `- [ ]`.
> **Para estudar:** cada tarefa tem um bloco **Para estudar**. Os passos marcados com **PORTÃO** dependem de você: escrever previsões, autorizar a rodada na VPS ou apagar segredos.

**Goal:** medir, na réplica local e num subconjunto autorizado na VPS, como o server HTTP do P2 responde a requisições de protocolo (autenticação, `Host`, `Origin`, tamanho de corpo, método, JSON malformado), com veredito por código e registro sem segredos.

**Architecture:** módulos novos em `redteam/http/` no repositório P4. O verificador, o cliente, o gate da VPS e a medição são funções puras ou com o transporte injetado, e a suíte padrão roda offline. A réplica sobe uma cópia do P2 (`prepare_workdir`, da base neutra) com o token gerado na hora, passado só por variável de ambiente.

**Tech Stack:** Python 3.13, `uv`, `pytest`, `httpx`, `git`.

**Spec:** [`docs/superpowers/specs/2026-11-18-red-team-p2-design.md`](../specs/2026-11-18-red-team-p2-design.md), seção "Laboratório HTTP". Este plano implementa só essa seção, no caminho 1 escolhido por você.

## Escopo deste plano

**Entra:** réplica local, cliente HTTP, verificador de veredito, validação das requisições, sete ataques de protocolo (H1, H2, H3, H4, H5, H8, H9), medição com três repetições, gate da VPS com autorização e relatório.

**Não entra, de propósito:**
- **H6 e H7** (CPF e CNPJ na requisição e formatos disfarçados): dependem do gerador de números sintéticos, que saiu do escopo. Continuam sendo sua decisão.
- **Injeção pelo texto da norma** e as **sondas do ambiente**: fora deste plano, como combinado.

## Restrições globais

- **Só o próprio servidor.** O alvo é a réplica local e a VPS `https://mcpreforma.cristianocarvalho.cloud`. Nenhum outro host.
- **Sem negação de serviço.** O ataque de token errado usa **um valor fixo de teste**, nunca tentativas em massa. A VPS recebe no máximo **30 requisições, 2 por segundo**, e para na primeira resposta 429 ou 5xx.
- **Autorização antes da VPS.** Nenhuma requisição sai para a VPS sem você ver a lista exata e devolver a assinatura dela (um hash).
- **Token só por variável de ambiente** (`TAXLAW_HTTP_TOKEN` na réplica, `TAXLAW_VPS_TOKEN` na VPS). Nunca na linha de comando, nunca em arquivo, nunca na saída. Os registros trocam o token por `<TOKEN>`.
- **O P2 não muda.** Antes e depois da medição, `git status` do P2 deve ser o mesmo da linha de base (`M meister.config.yaml` e `?? meister.config.yaml.bak`).
- **Previsão antes da medição.** Você escreve a previsão de cada ataque e faz commit antes de a medição rodar.
- **Testes padrão offline.** Os testes que sobem a réplica ficam marcados com `skipif` e só rodam com `REDTEAM_INTEGRACAO=1`. Nenhum teste padrão sai para a rede.
- Mensagens em português; identificadores de código em inglês; commits com `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>`.

## Fatos do P2 que o plano usa

Lidos de `src/taxlaw/http.py` e de `src/taxlaw/server.py` no checkout do P2:

- o server é `python -m taxlaw.http --port N`, e exige `TAXLAW_HTTP_TOKEN` com pelo menos 32 caracteres;
- o caminho do protocolo é `/mcp`, e o transporte é stateless com resposta JSON;
- sem token válido, a resposta é HTTP 401 com corpo JSON-RPC `{"error": {"code": -32001, "message": "nao_autorizado"}}`;
- o `Host` padrão aceito é `127.0.0.1:<porta>` e `localhost:<porta>`;
- o corpo tem limite de 64 KB.

**Os códigos esperados de H3, H4, H5, H8 e H9 são hipóteses**, escritas na previsão antes da medição. A medição é que confirma ou refuta cada uma.

## Revisão: entradas que a spec não cobre

1. Porta ocupada ou réplica que não sobe: erro com a causa, sem o token. *(Tarefa 4)*
2. Token aparecer em argumento de linha de comando, no log ou no registro: teste de argv e de redação. *(Tarefas 3, 4, 6 e 7)*
3. Corpo de resposta enorme: truncado no registro. *(Tarefa 3)*
4. VPS responder 429 ou 5xx no meio da rodada: a rodada para e registra o motivo. *(Tarefa 7)*
5. Lista da VPS diferente da lista autorizada: recusada antes de qualquer envio. *(Tarefa 7)*

---

## Tarefa 1: Verificador de veredito

**Para estudar:** o veredito compara o que o P2 **respondeu** com a expectativa escrita **antes**. Três resultados: **defendido** (a expectativa bate), **furou** (era para bloquear e a requisição passou) e **inesperado** (qualquer outra coisa, inclusive erro de servidor). O verificador não decide se algo é grave: ele só compara com o que foi escrito antes.

**Arquivos:** criar `redteam/http/__init__.py` (vazio) e `redteam/http/veredito.py`; teste `redteam/tests/test_veredito.py`.

**Produz:** `@dataclass(frozen=True) Resposta(status: int, corpo: str)` e `julgar(esperado: dict, observado: Resposta) -> str`, que devolve `"defendido"`, `"furou"` ou `"inesperado"`. As chaves de `esperado` são `status` (lista de inteiros), `erro_mcp` (mensagem do erro JSON-RPC) e `sem_stacktrace` (booleano).

- [ ] **Passo 1.1: testes**

`redteam/tests/test_veredito.py`:

```python
import json

from redteam.http.veredito import Resposta, julgar

ESPERADO_401 = {"status": [401], "erro_mcp": "nao_autorizado", "sem_stacktrace": True}
CORPO_401 = json.dumps({"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32001, "message": "nao_autorizado"}})


def test_defendido_quando_todas_as_expectativas_batem():
    assert julgar(ESPERADO_401, Resposta(401, CORPO_401)) == "defendido"


def test_furou_quando_bloqueio_esperado_recebe_sucesso():
    assert julgar({"status": [401]}, Resposta(200, "{}")) == "furou"


def test_inesperado_para_erro_de_servidor():
    assert julgar({"status": [401]}, Resposta(500, "")) == "inesperado"


def test_inesperado_quando_a_mensagem_do_erro_nao_bate():
    corpo = json.dumps({"error": {"message": "outra coisa"}})
    assert julgar(ESPERADO_401, Resposta(401, corpo)) == "inesperado"


def test_traceback_no_corpo_reprova_mesmo_com_status_certo():
    assert julgar({"status": [400], "sem_stacktrace": True},
                  Resposta(400, "Traceback (most recent call last)")) == "inesperado"


def test_corpo_que_nao_e_json_nao_bate_com_erro_mcp():
    assert julgar(ESPERADO_401, Resposta(401, "texto puro")) == "inesperado"
```

- [ ] **Passo 1.2: ver falhar e implementar**

Rode `uv run pytest redteam/tests/test_veredito.py -q` e confirme a falha por módulo inexistente. Depois crie `redteam/http/veredito.py`:

```python
"""Veredito de uma requisição HTTP: compara o que o P2 respondeu com a expectativa escrita antes."""

from __future__ import annotations

import json
from dataclasses import dataclass

# Códigos que, quando esperados, significam "bloqueio": uma resposta 2xx nesse caso é furo.
BLOQUEIOS = {400, 401, 403, 404, 405, 406, 413, 421}


@dataclass(frozen=True)
class Resposta:
    status: int
    corpo: str


def _mensagem_erro(corpo: str):
    try:
        return json.loads(corpo)["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return None


def julgar(esperado: dict, observado: Resposta) -> str:
    checks = [observado.status in esperado.get("status", [])]
    if "erro_mcp" in esperado:
        checks.append(_mensagem_erro(observado.corpo) == esperado["erro_mcp"])
    if esperado.get("sem_stacktrace"):
        checks.append("Traceback" not in observado.corpo)
    if all(checks):
        return "defendido"
    if set(esperado.get("status", [])) & BLOQUEIOS and 200 <= observado.status < 300:
        return "furou"
    return "inesperado"
```

- [ ] **Passo 1.3: rodar e commitar**

```bash
uv run pytest redteam/tests/test_veredito.py -q
uv run pytest -q && uv run pytest -q
git add redteam/http redteam/tests/test_veredito.py
git commit -m "Veredito de requisicoes HTTP: defendido, furou ou inesperado" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 2: Validação das requisições e carregador do ataque HTTP

**Para estudar:** o catálogo é dado, e o esquema comum da base neutra só valida os campos comuns. Esta tarefa valida o bloco `entrada` e o bloco `criterio` de um ataque HTTP. A autenticação não entra como cabeçalho escrito no arquivo: o campo `autenticacao` escolhe entre `correta`, `ausente` e `errada`, e assim o token nunca vai para o catálogo.

**Arquivos:** criar `redteam/http/requisicoes.py`; teste `redteam/tests/test_requisicoes.py`.

**Consome:** `load_attack` e `Attack` (base neutra, `redteam/esquema.py`).
**Produz:** `validar_requisicoes(entrada) -> list[dict]`, `validar_criterio(criterio) -> dict`, `carregar_ataque_http(caminho) -> tuple[Attack, list[dict], dict]`.

- [ ] **Passo 2.1: testes**

`redteam/tests/test_requisicoes.py`:

```python
import json

import pytest

from redteam.http.requisicoes import carregar_ataque_http, validar_criterio, validar_requisicoes

REQ = {"nome": "sem_autenticacao", "metodo": "POST", "caminho": "/mcp", "autenticacao": "ausente",
       "cabecalhos": {}, "corpo": {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
       "alvos": ["replica"]}


def test_requisicao_valida_passa():
    assert validar_requisicoes({"requisicoes": [REQ]}) == [REQ]


@pytest.mark.parametrize("alteracao", [
    {"metodo": "PUT"},
    {"caminho": "mcp"},
    {"autenticacao": "talvez"},
    {"cabecalhos": {"Authorization": "Bearer x"}},
    {"cabecalhos": {"authorization": "Bearer x"}},
    {"alvos": ["lua"]},
    {"alvos": []},
    {"nome": ""},
])
def test_requisicao_invalida_e_recusada(alteracao):
    with pytest.raises(ValueError):
        validar_requisicoes({"requisicoes": [{**REQ, **alteracao}]})


def test_lista_de_requisicoes_vazia_e_recusada():
    with pytest.raises(ValueError):
        validar_requisicoes({"requisicoes": []})


def test_criterio_aceita_so_as_chaves_conhecidas():
    assert validar_criterio({"esperado": {"status": [401]}}) == {"status": [401]}
    with pytest.raises(ValueError):
        validar_criterio({"esperado": {"magia": 1}})
    with pytest.raises(ValueError):
        validar_criterio({"esperado": {}})


def test_carrega_ataque_http_completo(tmp_path):
    ataque = {"id": "H1", "superficie": "http", "nome": "exemplo", "nucleo": True,
              "rotulos": {"classe": "autenticação"},
              "previsao": {"resultado_esperado": "defendido", "confianca": 80, "motivo": "teste"},
              "entrada": {"requisicoes": [REQ]},
              "criterio": {"esperado": {"status": [401]}}}
    caminho = tmp_path / "H1.json"
    caminho.write_text(json.dumps(ataque), encoding="utf-8")
    attack, reqs, esperado = carregar_ataque_http(caminho)
    assert attack.id == "H1" and reqs == [REQ] and esperado == {"status": [401]}
```

- [ ] **Passo 2.2: implementar**

`redteam/http/requisicoes.py`:

```python
"""Validação do bloco `entrada` e `criterio` de um ataque HTTP, além dos campos comuns."""

from __future__ import annotations

import json
from pathlib import Path

from redteam.esquema import Attack, load_attack

METODOS = {"GET", "POST", "DELETE"}
ALVOS = {"replica", "vps"}
AUTENTICACOES = {"correta", "ausente", "errada"}
CHAVES_ESPERADO = {"status", "erro_mcp", "sem_stacktrace"}


def validar_requisicoes(entrada: dict) -> list[dict]:
    reqs = entrada.get("requisicoes")
    if not isinstance(reqs, list) or not reqs:
        raise ValueError("entrada.requisicoes não pode ser vazia")
    for r in reqs:
        if not isinstance(r.get("nome"), str) or not r["nome"]:
            raise ValueError("requisição sem nome")
        if r.get("metodo") not in METODOS:
            raise ValueError(f"método inválido: {r.get('metodo')!r}")
        caminho = r.get("caminho")
        if not isinstance(caminho, str) or not caminho.startswith("/") or len(caminho) > 200:
            raise ValueError(f"caminho inválido: {caminho!r}")
        if r.get("autenticacao", "correta") not in AUTENTICACOES:
            raise ValueError(f"autenticacao inválida: {r.get('autenticacao')!r}")
        cabecalhos = r.get("cabecalhos", {})
        if not isinstance(cabecalhos, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in cabecalhos.items()):
            raise ValueError("cabecalhos deve ser um objeto de texto para texto")
        if "authorization" in {k.lower() for k in cabecalhos}:
            raise ValueError("use o campo autenticacao, não o cabeçalho Authorization")
        alvos = r.get("alvos")
        if not isinstance(alvos, list) or not alvos or not set(alvos) <= ALVOS:
            raise ValueError(f"alvos inválidos: {alvos!r}")
    return reqs


def validar_criterio(criterio: dict) -> dict:
    esperado = criterio.get("esperado")
    if not isinstance(esperado, dict) or not esperado or not set(esperado) <= CHAVES_ESPERADO:
        raise ValueError(f"criterio.esperado inválido: {esperado!r}")
    return esperado


def carregar_ataque_http(caminho: Path) -> tuple[Attack, list[dict], dict]:
    caminho = Path(caminho)
    attack = load_attack(caminho)
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    return attack, validar_requisicoes(bruto["entrada"]), validar_criterio(bruto["criterio"])
```

- [ ] **Passo 2.3: rodar e commitar**

```bash
uv run pytest redteam/tests/test_requisicoes.py -q
uv run pytest -q && uv run pytest -q
git add redteam/http/requisicoes.py redteam/tests/test_requisicoes.py
git commit -m "Validacao das requisicoes e do criterio do ataque HTTP" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 3: Cliente HTTP com redação do token

**Para estudar:** o cliente é o único lugar que envia o token. Ele monta o cabeçalho a partir de `autenticacao`, e toda saída passa por `redigir`, que troca o token por `<TOKEN>`. O transporte é injetado, então os testes usam um transporte falso, sem rede. O corpo da resposta é truncado, porque uma resposta grande não deve virar um registro gigante.

**Arquivos:** criar `redteam/http/cliente.py`; teste `redteam/tests/test_cliente.py`.

**Produz:** `TOKEN_ERRADO` (valor fixo de teste, com mais de 32 caracteres), `montar_cabecalhos(autenticacao, token, extras) -> dict`, `montar_corpo(corpo) -> bytes | None`, `redigir(texto, token) -> str`, `enviar(base_url, token, req, *, cliente) -> Resposta`.

- [ ] **Passo 3.1: testes (com `httpx.MockTransport`)**

`redteam/tests/test_cliente.py`:

```python
import httpx

from redteam.http.cliente import TOKEN_ERRADO, enviar, montar_cabecalhos, montar_corpo, redigir

TOKEN = "t" * 40
REQ = {"nome": "x", "metodo": "POST", "caminho": "/mcp", "autenticacao": "correta",
       "cabecalhos": {}, "corpo": {"a": 1}, "alvos": ["replica"]}


def test_autenticacao_correta_errada_e_ausente():
    assert montar_cabecalhos("correta", TOKEN, {})["Authorization"] == f"Bearer {TOKEN}"
    assert montar_cabecalhos("errada", TOKEN, {})["Authorization"] == f"Bearer {TOKEN_ERRADO}"
    assert "Authorization" not in montar_cabecalhos("ausente", TOKEN, {})


def test_token_errado_de_teste_tem_mais_de_32_caracteres_e_difere_do_real():
    assert len(TOKEN_ERRADO) >= 32 and TOKEN_ERRADO != TOKEN


def test_corpo_texto_vai_cru_e_objeto_vira_json():
    assert montar_corpo("abc") == b"abc"
    assert montar_corpo({"a": 1}) == b'{"a": 1}'
    assert montar_corpo(None) is None


def test_redigir_troca_o_token():
    assert redigir(f"x {TOKEN} y", TOKEN) == "x <TOKEN> y"


def test_enviar_devolve_resposta_sem_o_token_e_trunca_o_corpo():
    def responder(request):
        return httpx.Response(401, text=TOKEN + "a" * 10000)

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        r = enviar("http://teste.invalid", TOKEN, REQ, cliente=cliente)
    assert r.status == 401
    assert TOKEN not in r.corpo and len(r.corpo) <= 4000
```

- [ ] **Passo 3.2: implementar**

`redteam/http/cliente.py`:

```python
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
    return json.dumps(corpo, ensure_ascii=False).encode("utf-8")


def redigir(texto: str, token: str) -> str:
    return texto.replace(token, "<TOKEN>") if token else texto


def enviar(base_url: str, token: str, req: dict, *, cliente: httpx.Client) -> Resposta:
    resposta = cliente.request(
        req["metodo"], base_url + req["caminho"],
        headers=montar_cabecalhos(req.get("autenticacao", "correta"), token, req.get("cabecalhos", {})),
        content=montar_corpo(req.get("corpo")),
        timeout=10.0,
    )
    return Resposta(resposta.status_code, redigir(resposta.text[:MAX_CORPO_REGISTRADO], token))
```

- [ ] **Passo 3.3: rodar e commitar**

```bash
uv run pytest redteam/tests/test_cliente.py -q
uv run pytest -q && uv run pytest -q
git add redteam/http/cliente.py redteam/tests/test_cliente.py
git commit -m "Cliente HTTP com redacao do token" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 4: Réplica local do server do P2

**Para estudar:** a réplica é o mesmo `taxlaw.http` do P2, rodando numa **cópia** (`prepare_workdir`), nunca no original. O token é gerado na hora e entra só pela variável de ambiente. A porta é escolhida pelo sistema. Quando o bloco `with` termina, o processo é encerrado. Os testes padrão checam a montagem do comando e do ambiente, sem subir nada; o teste de subida real só roda com `REDTEAM_INTEGRACAO=1`.

**Arquivos:** criar `redteam/http/replica.py`; testes `redteam/tests/test_replica.py`.

**Consome:** `prepare_workdir` (base neutra, `redteam/workdir.py`).
**Produz:** `TOKEN_ENV = "TAXLAW_HTTP_TOKEN"`, `porta_livre() -> int`, `montar_comando(workdir, porta) -> list[str]`, `montar_ambiente(token) -> dict`, `class ReplicaNaoSobe(Exception)`, e o gerenciador de contexto `replica(workdir, token, *, timeout_s=90.0)`, que devolve a URL base.

- [ ] **Passo 4.1: testes**

`redteam/tests/test_replica.py`:

```python
import os
import socket
from pathlib import Path

import pytest

from redteam.http.replica import TOKEN_ENV, montar_ambiente, montar_comando, porta_livre

TOKEN = "s" * 40


def test_porta_livre_pode_ser_amarrada():
    porta = porta_livre()
    assert 1024 <= porta <= 65535
    with socket.socket() as s:
        s.bind(("127.0.0.1", porta))


def test_comando_nao_carrega_o_token():
    comando = montar_comando(Path("/tmp/copia"), 8123)
    assert TOKEN not in " ".join(comando)
    assert "--port" in comando and "8123" in comando


def test_ambiente_leva_o_token_e_preserva_o_resto():
    ambiente = montar_ambiente(TOKEN)
    assert ambiente[TOKEN_ENV] == TOKEN
    assert ambiente.get("PATH") == os.environ.get("PATH")


@pytest.mark.skipif(os.environ.get("REDTEAM_INTEGRACAO") != "1",
                    reason="integração: sobe o P2 real; use REDTEAM_INTEGRACAO=1")
def test_replica_sobe_responde_401_sem_token_e_nao_grava_o_token(tmp_path):
    import httpx

    from redteam.http.replica import replica
    from redteam.workdir import prepare_workdir

    dest = tmp_path / "copia"
    prepare_workdir(Path(os.environ["REDTEAM_P2_DIR"]), dest)
    with replica(dest, TOKEN) as base:
        assert httpx.post(base + "/mcp", json={}).status_code == 401
    assert TOKEN not in (dest / "replica.log").read_text(encoding="utf-8")
```

- [ ] **Passo 4.2: implementar**

`redteam/http/replica.py`:

```python
"""Réplica local: sobe o `taxlaw.http` do P2 numa cópia, com token por variável de ambiente."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

TOKEN_ENV = "TAXLAW_HTTP_TOKEN"


class ReplicaNaoSobe(Exception):
    """A réplica não respondeu: a causa está no log, nunca no token."""


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def montar_comando(workdir: Path, porta: int) -> list[str]:
    return ["uv", "run", "--quiet", "--project", str(workdir), "python", "-m", "taxlaw.http",
            "--port", str(porta)]


def montar_ambiente(token: str) -> dict:
    return {**os.environ, TOKEN_ENV: token}


@contextmanager
def replica(workdir: Path, token: str, *, timeout_s: float = 90.0):
    porta = porta_livre()
    base = f"http://127.0.0.1:{porta}"
    with open(Path(workdir) / "replica.log", "w", encoding="utf-8") as log:
        proc = subprocess.Popen(montar_comando(workdir, porta), cwd=workdir,
                                env=montar_ambiente(token), stdout=log, stderr=subprocess.STDOUT)
        try:
            limite = time.monotonic() + timeout_s
            while True:
                if proc.poll() is not None:
                    raise ReplicaNaoSobe(f"o processo saiu com código {proc.returncode}; veja replica.log")
                try:
                    httpx.get(base + "/mcp", timeout=2.0)
                    break
                except httpx.TransportError:
                    if time.monotonic() > limite:
                        raise ReplicaNaoSobe("a réplica não respondeu no prazo; veja replica.log")
                    time.sleep(0.5)
            yield base
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
```

- [ ] **Passo 4.3: rodar os testes padrão e, com o P2 disponível, o de integração**

```bash
uv run pytest redteam/tests/test_replica.py -q
REDTEAM_INTEGRACAO=1 REDTEAM_P2_DIR=/Users/cristianocarvalho/Documents/harness/projeto02 uv run pytest redteam/tests/test_replica.py -q
git -C /Users/cristianocarvalho/Documents/harness/projeto02 status --porcelain
```

Esperado: os testes padrão passam; o de integração passa; e o `git status` do P2 mostra as **mesmas duas linhas** da linha de base.

```bash
uv run pytest -q && uv run pytest -q
git add redteam/http/replica.py redteam/tests/test_replica.py
git commit -m "Replica local do server HTTP do P2 numa copia" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 5: Catálogo HTTP em dados

**Para estudar:** cada ataque de protocolo é um arquivo JSON. A tabela abaixo diz o que cada um testa e qual defesa a spec espera. Os códigos são **hipóteses**: o arquivo nasce com a expectativa da spec, e a sua previsão (Tarefa 6) fica registrada como "o que eu acho que vai acontecer".

**Arquivos:** criar `redteam/ataques/H1.json`, `H2.json`, `H3.json`, `H4.json`, `H5.json`, `H8.json`, `H9.json`; teste `redteam/tests/test_catalogo_http.py`.

| ID | Requisição | Alvos | Defesa esperada (hipótese) |
|---|---|---|---|
| H1 | `POST /mcp` sem cabeçalho de autenticação, corpo JSON-RPC válido | replica, vps | `status` 401, `erro_mcp` `nao_autorizado`, sem traceback |
| H2 | `POST /mcp` com `autenticacao` `errada` (valor fixo de teste) | replica, vps | `status` 401, `erro_mcp` `nao_autorizado`, sem traceback |
| H3 | `POST /mcp` com cabeçalho `Host` fora da lista permitida | replica | `status` 421 (verificar) |
| H4 | `POST /mcp` com cabeçalho `Origin` de navegador e token correto | replica | `status` 403 (verificar) |
| H5 | `POST /mcp` com corpo de 70 000 caracteres e token correto | replica, vps | `status` 413 (verificar) |
| H8 | `GET /mcp` e `DELETE /mcp` com token correto | replica | `status` 404 ou 405 (verificar) |
| H9 | `POST /mcp` com JSON malformado | replica | `status` 400 ou 200, sem traceback |

H1, completo:

```json
{
  "id": "H1",
  "superficie": "http",
  "nome": "sem cabeçalho de autenticação",
  "nucleo": true,
  "rotulos": {"owasp_llm": [], "indirect_type": null, "classe": "autenticação"},
  "previsao": {"resultado_esperado": "defendido", "confianca": 0, "motivo": ""},
  "entrada": {"requisicoes": [{
    "nome": "sem_autenticacao", "metodo": "POST", "caminho": "/mcp",
    "autenticacao": "ausente", "cabecalhos": {},
    "corpo": {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    "alvos": ["replica", "vps"]}]},
  "criterio": {"esperado": {"status": [401], "erro_mcp": "nao_autorizado", "sem_stacktrace": true}}
}
```

O campo `previsao` nasce com `confianca` 0 e `motivo` vazio. **A medição recusa rodar enquanto o motivo estiver vazio**, de propósito: a previsão é sua, e ela precisa existir antes.

- [ ] **Passo 5.1: teste que valida o catálogo inteiro**

`redteam/tests/test_catalogo_http.py`:

```python
from pathlib import Path

from redteam.esquema import CATALOGO_DIR
from redteam.http.requisicoes import carregar_ataque_http

IDS = ["H1", "H2", "H3", "H4", "H5", "H8", "H9"]


def test_todos_os_ataques_http_carregam_e_tem_expectativa():
    for i in IDS:
        attack, reqs, esperado = carregar_ataque_http(Path(CATALOGO_DIR) / f"{i}.json")
        assert attack.id == i and attack.superficie == "http"
        assert reqs and esperado


def test_nenhum_ataque_http_carrega_token_no_arquivo():
    for i in IDS:
        texto = (Path(CATALOGO_DIR) / f"{i}.json").read_text(encoding="utf-8")
        assert "Bearer" not in texto
```

- [ ] **Passo 5.2: criar os arquivos, rodar e commitar**

Crie os sete arquivos seguindo a tabela e o exemplo do H1. Depois:

```bash
uv run pytest redteam/tests/test_catalogo_http.py -q
uv run pytest -q && uv run pytest -q
git add redteam/ataques redteam/tests/test_catalogo_http.py
git commit -m "Catalogo HTTP: sete ataques de protocolo como dados" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 6: Medição na réplica (com a sua previsão antes)

**Para estudar:** a medição roda cada requisição **três vezes** na réplica e registra o veredito de cada repetição. Se as três repetições não concordam, o comportamento é **instável**: a ficha dirá isso, e o resultado não é confiável. O registro sai com o token trocado por `<TOKEN>`.

**Arquivos:** criar `redteam/http/medicao.py`, `redteam/http/__main__.py`; teste `redteam/tests/test_medicao.py`; saída em `docs/redteam/medicao-replica.json`.

**Consome:** `carregar_ataque_http` (Tarefa 2), `enviar` e `redigir` (Tarefa 3), `julgar` (Tarefa 1), `replica` (Tarefa 4).
**Produz:** `exigir_previsao(attack) -> None`, `rodar_ataque(attack, reqs, esperado, base_url, token, *, cliente, repeticoes=3) -> list[dict]`, `gravar(registros, destino, token) -> None`, e a execução `python -m redteam.http`.

- [ ] **Passo 6.1: PORTÃO, a sua previsão**

Antes de qualquer medição, você escreve, para cada um dos sete ataques, o resultado que acha que vai acontecer, com um número de confiança de 0 a 100 e um motivo curto. Edite o campo `previsao` de cada arquivo em `redteam/ataques/`, faça um commit separado só com as previsões, e só então siga para o passo 6.2. O commit é o carimbo.

- [ ] **Passo 6.2: testes com um transporte falso**

`redteam/tests/test_medicao.py`:

```python
import json

import httpx
import pytest

from redteam.esquema import Attack
from redteam.http.medicao import exigir_previsao, gravar, rodar_ataque

TOKEN = "u" * 40
REQ = {"nome": "r", "metodo": "POST", "caminho": "/mcp", "autenticacao": "ausente",
       "cabecalhos": {}, "corpo": {"a": 1}, "alvos": ["replica"]}
ESPERADO = {"status": [401]}


def _attack(motivo="previsão escrita"):
    return Attack(id="H1", superficie="http", nome="x", nucleo=True, rotulos={},
                  previsao={"resultado_esperado": "defendido", "confianca": 80, "motivo": motivo})


def test_previsao_vazia_recusa_a_medicao():
    with pytest.raises(ValueError):
        exigir_previsao(_attack(motivo=""))


def test_tres_repeticoes_com_veredito_por_repeticao():
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, text="{}")))
    registros = rodar_ataque(_attack(), [REQ], ESPERADO, "http://teste.invalid", TOKEN,
                             cliente=cliente, repeticoes=3)
    assert [r["repeticao"] for r in registros] == [1, 2, 3]
    assert all(r["veredito"] == "defendido" for r in registros)


def test_registro_gravado_nao_contem_o_token(tmp_path):
    destino = tmp_path / "medicao.json"
    registros = [{"ataque": "H1", "requisicao": "r", "repeticao": 1, "status": 401,
                  "veredito": "defendido", "trecho": f"ecoou {TOKEN}"}]
    gravar(registros, destino, TOKEN)
    texto = destino.read_text(encoding="utf-8")
    assert TOKEN not in texto and "<TOKEN>" in texto
    assert json.loads(texto)[0]["status"] == 401
```

- [ ] **Passo 6.3: implementar a medição**

`redteam/http/medicao.py`:

```python
"""Medição das requisições na réplica: três repetições, veredito por código, registro sem segredo."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from redteam.esquema import Attack
from redteam.http.cliente import enviar, redigir
from redteam.http.veredito import julgar

REPETICOES_PADRAO = 3


def exigir_previsao(attack: Attack) -> None:
    if not attack.previsao.get("motivo"):
        raise ValueError(f"{attack.id}: previsão vazia; escreva a sua antes de medir")


def rodar_ataque(attack: Attack, reqs: list[dict], esperado: dict, base_url: str, token: str, *,
                 cliente: httpx.Client, repeticoes: int = REPETICOES_PADRAO) -> list[dict]:
    exigir_previsao(attack)
    registros = []
    for req in reqs:
        for n in range(1, repeticoes + 1):
            observado = enviar(base_url, token, req, cliente=cliente)
            registros.append({
                "ataque": attack.id, "requisicao": req["nome"], "repeticao": n,
                "status": observado.status, "veredito": julgar(esperado, observado),
                "trecho": observado.corpo[:200],
            })
    return registros


def gravar(registros: list[dict], destino: Path, token: str) -> None:
    texto = json.dumps(registros, ensure_ascii=False, indent=2)
    Path(destino).write_text(redigir(texto, token), encoding="utf-8")
```

- [ ] **Passo 6.4: implementar a execução `python -m redteam.http`**

`redteam/http/__main__.py`:

```python
"""Executa a medição na réplica: `REDTEAM_P2_DIR=<caminho do P2> python -m redteam.http`."""

from __future__ import annotations

import os
import secrets
import tempfile
from pathlib import Path

import httpx

from redteam.esquema import CATALOGO_DIR
from redteam.http.medicao import gravar, rodar_ataque
from redteam.http.replica import replica
from redteam.http.requisicoes import carregar_ataque_http
from redteam.workdir import prepare_workdir

IDS = ["H1", "H2", "H3", "H4", "H5", "H8", "H9"]
SAIDA = Path("docs/redteam/medicao-replica.json")


def main() -> int:
    p2 = Path(os.environ["REDTEAM_P2_DIR"])
    token = secrets.token_urlsafe(32)
    registros = []
    with tempfile.TemporaryDirectory() as tmp:
        copia = prepare_workdir(p2, Path(tmp) / "p2")
        with replica(copia, token) as base, httpx.Client() as cliente:
            for i in IDS:
                attack, reqs, esperado = carregar_ataque_http(Path(CATALOGO_DIR) / f"{i}.json")
                registros += rodar_ataque(attack, reqs, esperado, base, token, cliente=cliente)
    gravar(registros, SAIDA, token)
    print(f"{len(registros)} registros em {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Passo 6.5: rodar a medição na réplica e commitar**

```bash
uv run pytest -q
REDTEAM_P2_DIR=/Users/cristianocarvalho/Documents/harness/projeto02 uv run python -m redteam.http
git -C /Users/cristianocarvalho/Documents/harness/projeto02 status --porcelain
uv run python -m redteam.varredura
```

Esperado: o `git status` do P2 mostra as **mesmas duas linhas** da linha de base, e a varredura não acha nada no JSON gravado. Confira o resultado com a sua previsão, e depois commite:

```bash
uv run pytest -q && uv run pytest -q
git add redteam/http/medicao.py redteam/http/__main__.py redteam/tests/test_medicao.py docs/redteam/medicao-replica.json
git commit -m "Medicao dos ataques HTTP na replica, tres repeticoes" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 7: Gate da VPS (com autorização sua)

**Para estudar:** a VPS é do dono, mas é um serviço público, e a rodada precisa ser pequena e reversível. O gate faz três coisas: monta a lista **exata** das requisições que sairiam, calcula a assinatura dela (um hash), e só envia se você devolver essa mesma assinatura. Durante o envio, o limite de 30 requisições e 2 por segundo é aplicado no código, e a rodada para na primeira resposta 429 ou 5xx.

A lista mostra a requisição completa, porque é isso que você autoriza. O token nunca aparece nela: ele não está no catálogo, e entra só pela variável de ambiente.

**Arquivos:** criar `redteam/http/vps.py`; teste `redteam/tests/test_vps.py`.

**Consome:** `enviar` (Tarefa 3), `carregar_ataque_http` (Tarefa 2), `CATALOGO_DIR` (base neutra).
**Produz:** `listar(catalogo: list[tuple[str, list[dict]]]) -> list[dict]`, `assinatura(lista) -> str`, `executar(lista, base_url, token, *, cliente, confirmacao, max_requisicoes=30, intervalo_s=0.5, sleep=time.sleep) -> list[dict]`, e a linha de comando `python -m redteam.http.vps --listar` ou `--executar --confirmacao <assinatura>`.

- [ ] **Passo 7.1: testes**

`redteam/tests/test_vps.py`:

```python
import httpx
import pytest

from redteam.http.vps import assinatura, executar, listar

TOKEN = "v" * 40


def _req(nome, alvos=("vps",)):
    return {"ataque": "H1", "nome": nome, "metodo": "POST", "caminho": "/mcp",
            "autenticacao": "ausente", "cabecalhos": {}, "corpo": {"a": 1}, "alvos": list(alvos)}


def _lista(n):
    return [_req(f"r{i}") for i in range(n)]


def _cliente(status, texto="{}"):
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, text=texto)))


def test_listar_so_inclui_requisicoes_da_vps():
    catalogo = [("H1", [_req("para_vps"), _req("so_replica", alvos=("replica",))])]
    lista = listar(catalogo)
    assert [r["nome"] for r in lista] == ["para_vps"]


def test_mais_de_30_requisicoes_sao_recusadas():
    with pytest.raises(ValueError):
        executar(_lista(31), "https://teste.invalid", TOKEN, cliente=_cliente(401),
                 confirmacao=assinatura(_lista(31)), sleep=lambda s: None)


def test_assinatura_errada_nao_envia_nada():
    chamadas = []
    cliente = httpx.Client(transport=httpx.MockTransport(
        lambda r: chamadas.append(r) or httpx.Response(401)))
    with pytest.raises(ValueError):
        executar(_lista(2), "https://teste.invalid", TOKEN, cliente=cliente,
                 confirmacao="errada", sleep=lambda s: None)
    assert chamadas == []


def test_para_na_primeira_resposta_429():
    respostas = iter([401, 429, 401])
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(next(respostas))))
    resultados = executar(_lista(3), "https://teste.invalid", TOKEN, cliente=cliente,
                          confirmacao=assinatura(_lista(3)), sleep=lambda s: None)
    assert [r["status"] for r in resultados] == [401, 429]
    assert resultados[-1]["parada"] == "limite de taxa"


def test_respeita_o_intervalo_entre_requisicoes():
    pausas = []
    executar(_lista(3), "https://teste.invalid", TOKEN, cliente=_cliente(401),
             confirmacao=assinatura(_lista(3)), intervalo_s=0.5, sleep=pausas.append)
    assert pausas == [0.5, 0.5]


def test_resultado_nao_contem_o_token_mesmo_se_o_servidor_ecoar_o_token():
    resultados = executar(_lista(1), "https://teste.invalid", TOKEN,
                          cliente=_cliente(401, texto=f"ecoou {TOKEN}"),
                          confirmacao=assinatura(_lista(1)), sleep=lambda s: None)
    assert TOKEN not in str(resultados)
```

- [ ] **Passo 7.2: implementar**

`redteam/http/vps.py`:

```python
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
        observado = enviar(base_url, token, req, cliente=cliente)
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
```

- [ ] **Passo 7.3: rodar e commitar**

```bash
uv run pytest redteam/tests/test_vps.py -q
uv run pytest -q && uv run pytest -q
git add redteam/http/vps.py redteam/tests/test_vps.py
git commit -m "Gate da VPS: lista exata, assinatura e limites" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 8: Rodada na VPS — PORTÃO

**Para estudar:** o gate da Tarefa 7 só envia se a assinatura bater. Aqui você é quem autoriza: vê a lista exata e devolve a assinatura. Se a lista mudar depois, a assinatura muda, e a rodada não sai. Pelo catálogo atual, a rodada tem três requisições (H1, H2 e H5), bem abaixo do limite de 30.

- [ ] **Passo 8.1: gerar a lista e a assinatura, sem enviar nada**

```bash
uv run python -m redteam.http.vps --listar
```

Esperado: a lista das requisições que sairiam para a VPS e uma assinatura de 64 caracteres. Nenhum envio acontece nesse passo.

- [ ] **Passo 8.2: você autoriza**

Revise a lista. Se estiver de acordo, responda com a assinatura. Sem a assinatura, nada é enviado.

- [ ] **Passo 8.3: rodar com a assinatura autorizada**

```bash
TAXLAW_VPS_BASE=https://mcpreforma.cristianocarvalho.cloud TAXLAW_VPS_TOKEN="$(pbpaste)" uv run python -m redteam.http.vps --executar --confirmacao ASSINATURA_AQUI
```

Troque `ASSINATURA_AQUI` pela assinatura que você autorizou. O token vem da área de transferência, sem aparecer na tela nem no histórico do shell. Depois confira que o P2 não mudou.

- [ ] **Passo 8.4: commit**

```bash
uv run pytest -q && uv run pytest -q
git add docs/redteam/medicao-vps.json
git commit -m "Medicao dos ataques HTTP na VPS, com autorizacao" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 9: Relatório e fechamento

**Para estudar:** a ficha de cada ataque junta três coisas: a sua previsão, o que a réplica mostrou nas três repetições e o que a VPS mostrou. A recomendação de mitigação é escrita, **não aplicada**: o P2 continua intacto.

**Arquivos:** criar `docs/redteam/relatorio-http.md`.

- [ ] **Passo 9.1: escrever o relatório**

Para cada um dos sete ataques, uma ficha com: id e nome, requisição (sem o token), sua previsão (valor e confiança), resultado da réplica nas três repetições, resultado da VPS (se a rodada alcançou aquele ataque), veredito, estabilidade, recomendação de mitigação e risco residual. No fim, um quadro de previsão contra resultado, os limites (sete ataques, uma versão do P2, uma data) e "o que deu errado".

- [ ] **Passo 9.2: confirmações finais**

```bash
uv run python -m redteam.varredura
uv run pytest -q && uv run pytest -q
git -C /Users/cristianocarvalho/Documents/harness/projeto02 status --porcelain
```

Esperado: varredura sem achados, suíte verde nas duas rodadas, e o P2 com as mesmas duas linhas de antes.

```bash
git add docs/redteam/relatorio-http.md
git commit -m "Relatorio do laboratorio HTTP" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Autoavaliação do plano

**Cobertura:** verificador (Tarefa 1), validação (Tarefa 2), cliente com redação (Tarefa 3), réplica (Tarefa 4), catálogo de sete ataques (Tarefa 5), medição com previsão e três repetições (Tarefa 6), gate da VPS com autorização e limites (Tarefas 7 e 8), relatório (Tarefa 9).

**Fora deste plano, de propósito:** H6 e H7 (CPF e CNPJ, dependem do gerador de números sintéticos), a injeção pelo texto da norma e as sondas do ambiente.

**Pontos que a execução confirma:** os códigos esperados de H3, H4, H5, H8 e H9 (hipóteses, verificadas pela medição); o cabeçalho `Accept` necessário para o transporte MCP (confirmado na primeira execução da réplica); e o comportamento do server na primeira subida.

## Escolha de execução

Este plano tem nove tarefas, com dependências claras (verificador e cliente antes da réplica, réplica antes da medição, medição antes da VPS). Recomendo a **execução nativa**, como na base neutra. O risco principal é a rodada na VPS, que tem um portão seu antes de qualquer envio.
