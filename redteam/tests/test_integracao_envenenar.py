import json
import os
import subprocess
from pathlib import Path

import pytest

from redteam.envenenar import envenenar
from redteam.injecao import carregar_ataque_injecao
from redteam.workdir import prepare_workdir

ATAQUE = Path(__file__).resolve().parents[1] / "ataques" / "I1.json"
CANARIO = "CANARIO-1A2B3C4D"

# Roda dentro da cópia: o taxlaw importado é o da cópia, e o corpus lido é o envenenado.
BUSCA = """
import json, sys
from taxlaw.tools import buscar_dispositivos, load_context
res = buscar_dispositivos(load_context(), sys.argv[1], None, 5)
print(json.dumps([r["id"] for r in res["resultados"]]))
"""


def _top5(copia: Path, consulta: str) -> list[str]:
    saida = subprocess.run(
        ["uv", "run", "--project", str(copia), "python", "-c", BUSCA, consulta],
        cwd=copia, capture_output=True, text=True, check=True, timeout=300,
    ).stdout
    return json.loads(saida.strip().splitlines()[-1])


@pytest.mark.skipif(os.environ.get("REDTEAM_INTEGRACAO") != "1",
                    reason="integração: roda o P2 real; use REDTEAM_INTEGRACAO=1")
def test_busca_da_pergunta_acha_o_dispositivo_envenenado(tmp_path):
    _, registros, pergunta, _ = carregar_ataque_injecao(ATAQUE)
    copia = tmp_path / "copia"
    prepare_workdir(Path(os.environ["REDTEAM_P2_DIR"]), copia)
    envenenar(copia, registros, CANARIO)
    assert "LC214.art125" in _top5(copia, pergunta)
