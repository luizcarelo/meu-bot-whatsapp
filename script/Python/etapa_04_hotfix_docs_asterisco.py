#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hotfix da Etapa 04

Objetivo:
- Corrigir bloqueio em arquivos de documentacao com enfase Markdown antiga.
- Criar backup do script etapa_04_limpar_mysql_e_validar_postgres.py.
- Ajustar somente a validacao de documentacao.
- Nao alterar README, MELHORIAS, codigo JS, Docker ou .env neste hotfix.
"""

from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path.cwd()
SCRIPT = ROOT / "etapa_04_limpar_mysql_e_validar_postgres.py"
BACKUPS = ROOT / "backups"


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def falhar(msg):
    print("ERRO: " + msg)
    raise SystemExit(1)


def main():
    if not SCRIPT.exists():
        falhar("Arquivo etapa_04_limpar_mysql_e_validar_postgres.py nao encontrado.")

    texto = SCRIPT.read_text(encoding="utf-8", errors="replace")

    marcador = "novo = novo.replace(chr(42), \"\")"
    if marcador in texto:
        print("Hotfix ja estava aplicado.")
        return

    BACKUPS.mkdir(exist_ok=True)
    backup_path = BACKUPS / ("hotfix_etapa_04_script_" + agora_stamp() + ".py")
    shutil.copy2(SCRIPT, backup_path)

    alvo_doc = "            validar_sem_asterisco_indevido(novo, nome)"
    novo_doc = (
        "            novo = novo.replace(chr(42), \"\")\n"
        "            validar_sem_asterisco_indevido(novo, nome)"
    )

    alvo_secao = "    validar_sem_asterisco_indevido(novo, nome)"
    novo_secao = (
        "    novo = novo.replace(chr(42), \"\")\n"
        "    validar_sem_asterisco_indevido(novo, nome)"
    )

    alteracoes = 0

    if alvo_doc in texto:
        texto = texto.replace(alvo_doc, novo_doc)
        alteracoes += 1

    if alvo_secao in texto:
        texto = texto.replace(alvo_secao, novo_secao)
        alteracoes += 1

    if alteracoes == 0:
        falhar("Nenhuma linha alvo foi encontrada para aplicar hotfix.")

    SCRIPT.write_text(texto, encoding="utf-8")

    print("Hotfix aplicado com sucesso.")
    print("Backup do script: " + str(backup_path))
    print("Alteracoes aplicadas: " + str(alteracoes))


if __name__ == "__main__":
    main()