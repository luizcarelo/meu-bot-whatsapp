#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hotfix da Etapa 10 - corrigir erro de sintaxe

Objetivo:
- Criar backup do script etapa_10_testes_funcionais_escrita_postgres.py.
- Corrigir typo que causou SyntaxError.
- Validar sintaxe do script com py_compile.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Nao alterar banco.
- Nao executar Docker.
- Nao executar a Etapa 10 automaticamente.
"""

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()
SCRIPT = ROOT / "etapa_10_testes_funcionais_escrita_postgres.py"
BACKUPS = ROOT / "backups"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def falhar(msg):
    print("ERRO: " + msg)
    raise SystemExit(1)


def ler(path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def gravar(path, texto):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def validar_sem_asterisco_indevido(texto, nome):
    if chr(42) in texto:
        falhar("Validacao bloqueou " + nome + " por conter asterisco.")


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    texto = ler(path)

    if texto is None:
        texto = "# " + nome.replace(".md", "") + "\n"

    inicio = "<!-- ETAPA_10_HOTFIX_INICIO -->"
    fim = "<!-- ETAPA_10_HOTFIX_FIM -->"

    bloco_linhas = []
    bloco_linhas.append("")
    bloco_linhas.append(inicio)
    bloco_linhas.append("## " + titulo)
    bloco_linhas.append("")
    bloco_linhas.extend(linhas)
    bloco_linhas.append(fim)
    bloco_linhas.append("")

    bloco = "\n".join(bloco_linhas)

    pos_inicio = texto.find(inicio)
    pos_fim = texto.find(fim)

    if pos_inicio >= 0 and pos_fim >= pos_inicio:
        pos_fim = pos_fim + len(fim)
        novo = texto[:pos_inicio] + bloco.strip() + texto[pos_fim:]
    else:
        if not texto.endswith("\n"):
            texto += "\n"
        novo = texto + bloco

    novo = novo.replace(chr(42), "")
    validar_sem_asterisco_indevido(novo, nome)
    gravar(path, novo)


def atualizar_documentacao():
    data = agora_iso()

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Hotfix Etapa 10 - Sintaxe corrigida",
        [
            "Data: " + data,
            "",
            "Foi corrigido erro de sintaxe no script da Etapa 10.",
            "A correcao ajustou a validacao de checks de schema minimo.",
            "Nenhuma alteracao foi aplicada ao banco.",
            "A Etapa 10 deve ser executada novamente apos este hotfix."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Hotfix Etapa 10 - Correcao de script",
        [
            "Data: " + data,
            "",
            "Corrigido SyntaxError no script etapa_10_testes_funcionais_escrita_postgres.py.",
            "Validada sintaxe do script com py_compile.",
            "Criado backup do script antes da alteracao."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Hotfix Etapa 10 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido aplicar hotfix minimo e localizado.",
            "Decidido nao executar banco ou Docker durante o hotfix.",
            "Decidido validar sintaxe antes de liberar nova execucao da Etapa 10."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Hotfix Etapa 10",
        [
            "Data: " + data,
            "",
            "Executar novamente a Etapa 10.",
            "Enviar o relatorio Markdown da Etapa 10 apos a nova execucao."
        ]
    )


def main():
    if not SCRIPT.exists():
        falhar("Script da Etapa 10 nao encontrado.")

    texto = ler(SCRIPT)

    alvo = '            if not r.get("ok") or not checksok = False'
    correcao = (
        '            if (not r.get("ok")) or (not checks[nome]):\n'
        '                ok = False'
    )

    if alvo not in texto:
        if 'checksok' not in texto:
            print("Hotfix parece ja estar aplicado. Validando sintaxe.")
        else:
            falhar("Padrao com erro foi encontrado de forma inesperada. Revisao manual necessaria.")
    else:
        BACKUPS.mkdir(exist_ok=True)
        backup_path = BACKUPS / ("hotfix_etapa_10_syntax_" + agora_stamp() + ".py")
        shutil.copy2(SCRIPT, backup_path)

        novo = texto.replace(alvo, correcao, 1)
        gravar(SCRIPT, novo)

        print("Hotfix aplicado.")
        print("Backup do script: " + str(backup_path))

    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(SCRIPT)],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        print(result.stderr)
        falhar("Validacao de sintaxe falhou.")

    atualizar_documentacao()

    print("Sintaxe validada com sucesso.")
    print("Documentacao obrigatoria atualizada.")
    print("Agora execute novamente:")
    print("sudo python3 etapa_10_testes_funcionais_escrita_postgres.py")


if __name__ == "__main__":
    main()