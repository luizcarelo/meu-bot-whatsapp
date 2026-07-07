#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess
from datetime import datetime

ROOT = Path.cwd()
ARQUIVO = ROOT / "routes" / "index.js"
BACKUPS = ROOT / "backups"

LINHA_DB = "const db = require('../src/config/db');"
LINHA_REQUIRE = "const AdminPanelController = require('../controllers/AdminPanelController');"
LINHA_INSTANCIA = "const adminPanelController = new AdminPanelController(db);"


def stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    BACKUPS.mkdir(exist_ok=True)
    backup = BACKUPS / ("etapa_21_1_ordem_admin_controller_" + stamp() + ".js")
    backup.write_text(texto, encoding="utf-8")

    linhas = texto.splitlines()

    novas = []
    for linha in linhas:
        limpa = linha.strip()
        if limpa == LINHA_REQUIRE:
            continue
        if limpa == LINHA_INSTANCIA:
            continue
        novas.append(linha)

    texto_limpo = "\n".join(novas) + "\n"

    pos = texto_limpo.find(LINHA_DB)
    if pos < 0:
        raise SystemExit("Linha do db nao encontrada em routes/index.js")

    fim_linha = texto_limpo.find("\n", pos)
    if fim_linha < 0:
        fim_linha = pos + len(LINHA_DB)

    bloco = LINHA_REQUIRE + "\n" + LINHA_INSTANCIA + "\n"

    novo = texto_limpo[:fim_linha + 1] + bloco + texto_limpo[fim_linha + 1:]

    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Correcao aplicada em routes/index.js")
    print("Backup criado em: " + str(backup))
    print("")
    print("Trecho esperado:")
    print(LINHA_DB)
    print(LINHA_REQUIRE)
    print(LINHA_INSTANCIA)
    print("")

    r = subprocess.run(
        ["node", "--check", "routes/index.js"],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    print("Node check OK: " + str(r.returncode == 0))

    if r.stdout:
        print(r.stdout)

    if r.stderr:
        print(r.stderr)

    if r.returncode != 0:
        raise SystemExit("node --check falhou. Nao reinicie ainda.")


if __name__ == "__main__":
    main()
