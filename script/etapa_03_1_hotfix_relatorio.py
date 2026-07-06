#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hotfix da Etapa 03.1

Objetivo:
- Corrigir a geracao do relatorio Markdown da Etapa 03.1.
- Nao altera Docker, env, controllers ou banco.
- Apenas ajusta o script etapa_03_1_padronizar_postgres.py.
- Cria backup do script antes da alteracao.
"""

from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path.cwd()
SCRIPT = ROOT / "etapa_03_1_padronizar_postgres.py"
BACKUPS = ROOT / "backups"


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def falhar(msg):
    print("ERRO: " + msg)
    raise SystemExit(1)


def main():
    if not SCRIPT.exists():
        falhar("Arquivo etapa_03_1_padronizar_postgres.py nao encontrado.")

    texto = SCRIPT.read_text(encoding="utf-8", errors="replace")

    marcador = 'conteudo = conteudo.replace(chr(42), "[asterisco]")'
    if marcador in texto:
        print("Hotfix ja estava aplicado.")
        return

    alvo = 'validar_sem_asterisco_indevido(conteudo, "relatorio markdown")'
    if alvo not in texto:
        falhar("Linha alvo nao encontrada no script.")

    BACKUPS.mkdir(exist_ok=True)
    backup_path = BACKUPS / ("hotfix_etapa_03_1_script_" + agora_stamp() + ".py")
    shutil.copy2(SCRIPT, backup_path)

    substituto = (
        'conteudo = conteudo.replace(chr(42), "[asterisco]")\n'
        '    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")'
    )

    texto_novo = texto.replace(alvo, substituto, 1)

    SCRIPT.write_text(texto_novo, encoding="utf-8")

    print("Hotfix aplicado com sucesso.")
    print("Backup do script: " + str(backup_path))


if __name__ == "__main__":
    main()