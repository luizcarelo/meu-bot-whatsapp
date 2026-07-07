#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess

ARQUIVO = Path("etapa_21_1_registrar_rota_admin_panel.py")

NOVA_FUNCAO = '''def parece_email(token):
    token = str(token or "").strip().strip(".;:,()[]{}<>")

    if "@" not in token:
        return False

    partes = token.split("@")

    if len(partes) != 2:
        return False

    usuario = partes[0]
    dominio = partes[1]

    if not usuario:
        return False

    if "." not in dominio:
        return False

    if len(dominio) < 4:
        return False

    if dominio.replace(".", "").isdigit():
        return False

    return True
'''


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    inicio = texto.find("def parece_email(token):")
    if inicio < 0:
        raise SystemExit("Funcao parece_email nao encontrada.")

    proximo = texto.find("\ndef ", inicio + 1)
    if proximo < 0:
        raise SystemExit("Nao foi possivel localizar fim da funcao parece_email.")

    novo = texto[:inicio] + NOVA_FUNCAO + texto[proximo + 1:]

    backup = Path("backups") / "etapa_21_1_syntax_email_backup.py"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(texto, encoding="utf-8")

    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Correcao aplicada.")
    print("Backup criado em: " + str(backup))

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
        raise SystemExit("Falha no py_compile. Nao execute a etapa ainda.")

    print("Agora execute:")
    print("sudo ETAPA21_1_RESTART_APP=true ETAPA21_1_LOGIN_EMAIL='admin@saas.com' ETAPA21_1_LOGIN_PASSWORD='123456' python3 etapa_21_1_registrar_rota_admin_panel.py")


if __name__ == "__main__":
    main()
