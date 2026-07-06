#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 04.1 - Limpar historico antigo de banco nos documentos

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Limpar rastros antigos de MySQL em documentos de controle.
- Preservar o historico de decisao sem manter termos literais antigos.
- Validar que os documentos de controle nao contem mais termos antigos.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Nao altera codigo JS.
- Nao altera Docker.
- Nao altera .env.
- Nao altera package.json.
- Nao executa banco.
- Nao executa Docker.
"""

import os
import re
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

MAX_LEITURA = 2097152

DOCS_CONTROLE = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

TERMOS_PROIBIDOS = [
    "mysql",
    "mysql2",
    "mariadb",
    "MYSQL_",
    "mysqldata",
    "mysqladmin",
    "DB_PORT=3306",
    "3306"
]

IGNORAR_MANIFESTO_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def rel(path):
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


def ler_texto(path):
    try:
        if not path.exists():
            return None
        if path.stat().st_size > MAX_LEITURA:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def gravar_texto(path, conteudo):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8")


def validar_sem_asterisco_indevido(conteudo, nome):
    if chr(42) in conteudo:
        raise ValueError(
            "Validacao bloqueou a geracao de "
            + nome
            + " por conter caractere asterisco."
        )


def sha256_arquivo(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                bloco = f.read(1048576)
                if not bloco:
                    break
                h.update(bloco)
        return h.hexdigest()
    except Exception:
        return None


def deve_ignorar_manifesto(path):
    partes = set(path.parts)
    for nome in IGNORAR_MANIFESTO_DIRS:
        if nome in partes:
            return True
    return False


def listar_arquivos_manifesto():
    arquivos = []

    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)
        novos_dirs = []

        for nome_dir in dirs:
            p = base_path / nome_dir
            if deve_ignorar_manifesto(p):
                continue
            novos_dirs.append(nome_dir)

        dirs[:] = novos_dirs

        for nome in files:
            p = base_path / nome
            if deve_ignorar_manifesto(p):
                continue
            arquivos.append(p)

    return sorted(arquivos)


def gerar_manifesto():
    itens = []

    for p in listar_arquivos_manifesto():
        try:
            st = p.stat()
            itens.append({
                "arquivo": rel(p),
                "tamanho_bytes": st.st_size,
                "sha256": sha256_arquivo(p)
            })
        except Exception as exc:
            itens.append({
                "arquivo": rel(p),
                "erro": str(exc)
            })

    return {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "total_arquivos": len(itens),
        "arquivos": itens
    }


def salvar_json(path, dados):
    gravar_texto(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def criar_backup(destino):
    destino.mkdir(parents=True, exist_ok=True)

    copiados = []
    ausentes = []
    erros = []

    for nome in DOCS_CONTROLE:
        origem = ROOT / nome
        destino_item = destino / nome

        if not origem.exists():
            ausentes.append(nome)
            continue

        try:
            destino_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino_item)
            copiados.append(nome)
        except Exception as exc:
            erros.append({
                "arquivo": nome,
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def remover_blocos_etapas_antigas(texto):
    blocos = [
        ("<!-- ETAPA_03_INICIO -->", "<!-- ETAPA_03_FIM -->"),
        ("<!-- ETAPA_03_1_INICIO -->", "<!-- ETAPA_03_1_FIM -->")
    ]

    novo = texto

    for inicio, fim in blocos:
        while True:
            pos_inicio = novo.find(inicio)
            if pos_inicio < 0:
                break

            pos_fim = novo.find(fim, pos_inicio)
            if pos_fim < 0:
                break

            pos_fim = pos_fim + len(fim)
            novo = novo[:pos_inicio] + novo[pos_fim:]

    return novo


def aplicar_limpeza_linhas(texto):
    linhas = texto.splitlines()
    novas = []
    removidas = 0
    alteradas = 0

    for linha in linhas:
        original = linha
        lower = linha.lower()

        contem_termo_antigo = False
        for termo in TERMOS_PROIBIDOS:
            if termo.lower() in lower:
                contem_termo_antigo = True
                break

        if contem_termo_antigo:
            removidas += 1
            continue

        linha = linha.replace(chr(42), "")

        if linha != original:
            alteradas += 1

        novas.append(linha)

    novo_texto = "\n".join(novas)
    if texto.endswith("\n"):
        novo_texto += "\n"

    return novo_texto, removidas, alteradas


def limpar_docs_controle():
    resultados = []

    for nome in DOCS_CONTROLE:
        path = ROOT / nome
        texto = ler_texto(path)

        if texto is None:
            resultados.append({
                "arquivo": nome,
                "existe": path.exists(),
                "alterado": False,
                "linhas_removidas": 0,
                "linhas_alteradas": 0,
                "motivo": "Arquivo ausente ou ilegivel"
            })
            continue

        texto_sem_blocos = remover_blocos_etapas_antigas(texto)
        novo, removidas, alteradas = aplicar_limpeza_linhas(texto_sem_blocos)

        if not novo.endswith("\n"):
            novo += "\n"

        if novo != texto:
            validar_sem_asterisco_indevido(novo, nome)
            gravar_texto(path, novo)

        resultados.append({
            "arquivo": nome,
            "existe": True,
            "alterado": novo != texto,
            "linhas_removidas": removidas,
            "linhas_alteradas": alteradas,
            "sha256_depois": sha256_arquivo(path)
        })

    return resultados


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_04_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_04_1_FIM -->"

    secao = []
    secao.append("")
    secao.append(marcador_inicio)
    secao.append("## " + titulo)
    secao.append("")
    secao.extend(corpo)
    secao.append(marcador_fim)
    secao.append("")

    bloco = "\n".join(secao)

    inicio = texto_atual.find(marcador_inicio)
    fim = texto_atual.find(marcador_fim)

    if inicio >= 0 and fim >= inicio:
        fim = fim + len(marcador_fim)
        novo = texto_atual[:inicio] + bloco.strip() + texto_atual[fim:]
    else:
        if not texto_atual.endswith("\n"):
            texto_atual += "\n"
        novo = texto_atual + bloco

    novo = novo.replace(chr(42), "")
    validar_sem_asterisco_indevido(novo, nome)
    gravar_texto(path, novo)


def escanear_docs_controle():
    achados = []

    for nome in DOCS_CONTROLE:
        path = ROOT / nome
        texto = ler_texto(path)

        if texto is None:
            continue

        for numero, linha in enumerate(texto.splitlines(), start=1):
            lower = linha.lower()
            termos = []

            for termo in TERMOS_PROIBIDOS:
                if termo.lower() in lower:
                    termos.append(termo)

            if termos:
                achados.append({
                    "arquivo": nome,
                    "linha": numero,
                    "termos": termos,
                    "conteudo": linha.strip()[:160]
                })

    return achados


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    restantes = str(len(relatorio["rastros_restantes"]))

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 04.1 - Historico tecnico limpo",
        [
            "Data: " + data,
            "",
            "Foram removidos rastros textuais antigos sobre banco anterior nos documentos de controle.",
            "A decisao consolidada do projeto e PostgreSQL como banco oficial.",
            "A etapa preservou os documentos de governanca e registrou a revisao de decisao.",
            "Rastros restantes nos documentos de controle: " + restantes + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 04.1 - Limpeza final de documentos",
        [
            "Data: " + data,
            "",
            "Limpos documentos de controle para remover referencias antigas de banco.",
            "Mantida a decisao consolidada de PostgreSQL como padrao oficial.",
            "Gerados backup, manifestos e relatorios da etapa.",
            "Executado scan final nos documentos de controle."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 04.1 - Decisao consolidada",
        [
            "Data: " + data,
            "",
            "PostgreSQL fica consolidado como banco oficial do projeto.",
            "Referencias antigas de banco foram removidas dos documentos de controle.",
            "Historico operacional fica preservado por backups e relatorios gerados em reports.",
            "Proximas validacoes devem focar setup_db.js, queries, rotas e fluxo funcional."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 04.1",
        [
            "Data: " + data,
            "",
            "Validar setup_db.js com PostgreSQL.",
            "Validar queries complexas em controllers, managers e rotas.",
            "Executar testes funcionais em ambiente controlado.",
            "Planejar rotacao de credenciais reais expostas anteriormente.",
            "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes."
        ]
    )

    return DOCS_CONTROLE


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 04.1 - Limpar historico antigo nos documentos")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Rastros restantes: " + str(len(relatorio["rastros_restantes"])))
    linhas.append("")

    linhas.append("## Documentos limpos")
    linhas.append("")
    for item in relatorio["limpeza_docs"]:
        linhas.append(
            "- "
            + item["arquivo"]
            + ": alterado="
            + str(item["alterado"])
            + ", linhas_removidas="
            + str(item["linhas_removidas"])
        )

    linhas.append("")
    linhas.append("## Scan final")
    linhas.append("")
    if relatorio["rastros_restantes"]:
        for item in relatorio["rastros_restantes"]:
            trecho = item["conteudo"].replace(chr(42), "[asterisco]")
            linhas.append(
                "- "
                + item["arquivo"]
                + ":"
                + str(item["linha"])
                + " termos="
                + ", ".join(item["termos"])
                + " trecho="
                + trecho
            )
    else:
        linhas.append("- Nenhum rastro antigo encontrado nos documentos de controle.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 05: validar setup_db.js, queries, rotas e fluxo funcional com PostgreSQL.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_04_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_04_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    limpeza_docs = limpar_docs_controle()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "limpeza_docs": limpeza_docs,
        "rastros_restantes": []
    }

    rastros_antes_doc = escanear_docs_controle()
    relatorio["rastros_apos_limpeza_antes_documentacao"] = rastros_antes_doc

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    rastros_finais = escanear_docs_controle()
    relatorio["rastros_restantes"] = rastros_finais

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_04_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_04_1_limpar_historico_mysql_docs.json"
    md_path = REPORTS_DIR / "etapa_04_1_limpar_historico_mysql_docs.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 04.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Rastros restantes: " + str(len(rastros_finais)))

    if rastros_finais:
        print("")
        print("Ainda existem rastros antigos nos documentos de controle.")
        for item in rastros_finais:
            print("- " + item["arquivo"] + ":" + str(item["linha"]))


if __name__ == "__main__":
    main()