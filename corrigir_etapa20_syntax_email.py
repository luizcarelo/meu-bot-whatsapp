#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

ARQUIVO = Path("etapa_20_aplicar_visual_crm.py")

NOVA_FUNCAO = '''def parece_email_token(token):
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

    return True
'''


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    inicio = texto.find("def parece_email_token(token):")
    if inicio < 0:
        raise SystemExit("Funcao parece_email_token nao encontrada.")

    proximo = texto.find("\ndef ", inicio + 1)
    if proximo < 0:
        raise SystemExit("Nao foi possivel localizar fim da funcao.")

    novo = texto[:inicio] + NOVA_FUNCAO + texto[proximo + 1:]

    backup = Path("backups") / "etapa_20_syntax_email_backup.py"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(texto, encoding="utf-8")

    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Correcao aplicada.")
    print("Backup criado em: " + str(backup))
    print("Agora execute:")
    print("sudo ETAPA20_LOGIN_EMAIL='admin@saas.com' ETAPA20_LOGIN_PASSWORD='123456' python3 etapa_20_aplicar_visual_crm.py")


if __name__ == "__main__":
    main()
