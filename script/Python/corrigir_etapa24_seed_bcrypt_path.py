#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess

ARQUIVO = Path("etapa_24_criar_banco_teste_superadmin_tenant.py")

ANTIGO = "const bcrypt = require('bcrypt');"

NOVO = """let bcrypt;
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

ANTIGO_EXEC = '"node", destino'
NOVO_EXEC = '"sh", "-lc", "cd /usr/src/app && node " + destino'


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    backup = Path("backups") / "etapa_24_antes_hotfix_bcrypt_path.py"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(texto, encoding="utf-8")

    novo = texto.replace(ANTIGO, NOVO)

    if ANTIGO_EXEC in novo:
        novo = novo.replace(ANTIGO_EXEC, NOVO_EXEC)
    else:
        print("Aviso: trecho de execucao node nao encontrado para troca. Verifique se ja foi alterado.")

    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Hotfix aplicado.")
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
