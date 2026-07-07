#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hotfix de indentacao da Etapa 04

Objetivo:
- Corrigir IndentationError no script etapa_04_limpar_mysql_e_validar_postgres.py.
- Reescrever funcoes afetadas com indentacao limpa.
- Criar backup antes da alteracao.
- Nao alterar arquivos do sistema, documentacao, JS, Docker ou env.
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


def substituir_bloco(texto, inicio, proximo_inicio, novo_bloco):
    pos_inicio = texto.find(inicio)
    if pos_inicio < 0:
        falhar("Inicio do bloco nao encontrado: " + inicio)

    pos_fim = texto.find(proximo_inicio, pos_inicio)
    if pos_fim < 0:
        falhar("Fim do bloco nao encontrado antes de: " + proximo_inicio)

    return texto[:pos_inicio] + novo_bloco + "\n\n" + texto[pos_fim:]


def bloco_limpar_documentacao():
    return '''def limpar_documentacao():
    resultados = []

    replaces = [
        ("MySQL ≥ 5.7", "PostgreSQL 15 ou superior"),
        ("MySQL >= 5.7", "PostgreSQL 15 ou superior"),
        ("MariaDB ≥ 10.3", "PostgreSQL 15 ou superior"),
        ("MariaDB >= 10.3", "PostgreSQL 15 ou superior"),
        ("Conexão MySQL", "Conexao PostgreSQL"),
        ("Conexao MySQL", "Conexao PostgreSQL"),
        ("pool MySQL", "pool PostgreSQL"),
        ("Pool de conexão MySQL", "Pool de conexao PostgreSQL"),
        ("Pool de conexao MySQL", "Pool de conexao PostgreSQL"),
        ("MySQL/SMTP/SUPER_ADMIN_PASS", "PostgreSQL/SMTP/SUPER_ADMIN_PASS"),
        ("MySQL e helpers", "PostgreSQL e helpers"),
        ("MySQL via config/db.js", "PostgreSQL via src/config/db.js"),
        ("MySQL", "PostgreSQL"),
        ("mysql", "postgres"),
        ("MariaDB", "PostgreSQL"),
        ("mariadb", "postgres")
    ]

    for nome in ARQUIVOS_DOC_LIMPEZA:
        path = ROOT / nome
        texto = ler_texto(path)

        if texto is None:
            resultados.append({
                "arquivo": nome,
                "existe": path.exists(),
                "alterado": False,
                "alteracoes": 0,
                "motivo": "Arquivo ausente ou ilegivel"
            })
            continue

        novo, alteracoes = aplicar_replaces(texto, replaces)
        novo = novo.replace(chr(42), "")

        if novo != texto:
            validar_sem_asterisco_indevido(novo, nome)
            gravar_texto(path, novo)

        resultados.append({
            "arquivo": nome,
            "existe": True,
            "alterado": novo != texto,
            "alteracoes": alteracoes
        })

    return resultados'''


def bloco_acrescentar_secao_documento():
    return '''def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\\n"

    marcador_inicio = "<!-- ETAPA_04_INICIO -->"
    marcador_fim = "<!-- ETAPA_04_FIM -->"

    secao = []
    secao.append("")
    secao.append(marcador_inicio)
    secao.append("## " + titulo)
    secao.append("")
    secao.extend(corpo)
    secao.append(marcador_fim)
    secao.append("")

    bloco = "\\n".join(secao)
    inicio = texto_atual.find(marcador_inicio)
    fim = texto_atual.find(marcador_fim)

    if inicio >= 0 and fim >= inicio:
        fim = fim + len(marcador_fim)
        novo = texto_atual[:inicio] + bloco.strip() + texto_atual[fim:]
    else:
        if not texto_atual.endswith("\\n"):
            texto_atual += "\\n"
        novo = texto_atual + bloco

    novo = novo.replace(chr(42), "")
    validar_sem_asterisco_indevido(novo, nome)
    gravar_texto(path, novo)'''


def main():
    if not SCRIPT.exists():
        falhar("Arquivo etapa_04_limpar_mysql_e_validar_postgres.py nao encontrado.")

    texto = SCRIPT.read_text(encoding="utf-8", errors="replace")

    BACKUPS.mkdir(exist_ok=True)
    backup_path = BACKUPS / ("hotfix_etapa_04_indentacao_" + agora_stamp() + ".py")
    shutil.copy2(SCRIPT, backup_path)

    texto = substituir_bloco(
        texto,
        "def limpar_documentacao():",
        "def limpar_comentarios_js():",
        bloco_limpar_documentacao()
    )

    texto = substituir_bloco(
        texto,
        "def acrescentar_secao_documento(nome, titulo, corpo):",
        "def atualizar_documentacao(relatorio):",
        bloco_acrescentar_secao_documento()
    )

    SCRIPT.write_text(texto, encoding="utf-8")

    print("Hotfix de indentacao aplicado com sucesso.")
    print("Backup do script: " + str(backup_path))


if __name__ == "__main__":
    main()