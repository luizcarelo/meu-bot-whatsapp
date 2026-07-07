#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess

ARQUIVO = Path("etapa_24_criar_banco_teste_superadmin_tenant.py")

BLOCO_ANTIGO = """let bcrypt;
try {
    bcrypt = require('/usr/src/app/node_modules/bcrypt');
} catch (e1) {
    try {
        bcrypt = require('/usr/src/app/node_modules/bcryptjs');
    } catch (e2) {
        throw new Error('Nao foi possivel carregar bcrypt ou bcryptjs em /usr/src/app/node_modules');
    }
}
"""

BLOCO_NOVO = """const bcrypt = require('/usr/src/app/node_modules/bcryptjs');
"""


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    backup = Path("backups") / "etapa_24_antes_hotfix_bcryptjs.py"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(texto, encoding="utf-8")

    if BLOCO_ANTIGO not in texto:
        raise SystemExit("Bloco antigo de bcrypt nao encontrado. Nao alterei o arquivo.")

    novo = texto.replace(BLOCO_ANTIGO, BLOCO_NOVO, 1)

    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Hotfix aplicado: seed agora usa somente bcryptjs.")
    print("Backup: " + str(backup))

    r = subprocess.run(
        ["python3", "-m", "py_compile", str(ARQUIVO)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    print("Py compile OK: " + str(r.returncode == 0))

    if r.stdout:
        print(r.stdout)

    if r.stderr:
        print(r.stderr)

    if r.returncode != 0:
        raise SystemExit("Falha no py_compile. Nao rode a Etapa 24 ainda.")


if __name__ == "__main__":
    main()
