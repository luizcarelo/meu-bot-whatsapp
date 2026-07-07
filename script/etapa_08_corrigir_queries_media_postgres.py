#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 08 - Corrigir queries de media severidade para PostgreSQL

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Corrigir padroes reais de incompatibilidade PostgreSQL:
  - GROUP_CONCAT para STRING_AGG
  - JSON_ARRAYAGG(JSON_OBJECT(...)) para json_agg(json_build_object(...))
  - resUser.insertId para RETURNING id
  - UPDATE ... LIMIT 1 para alternativa compativel
- Rodar node --check nos arquivos alterados.
- Rodar scan focado nos padroes corrigidos.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Corrige apenas queries de media severidade reais.
- Nao altera schema.
- Nao executa banco.
- Nao executa Docker.
- Nao altera .env.
"""

import os
import re
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

MAX_LEITURA = 3145728

ARQUIVOS_ALVO = [
    "controllers/AdminController.js",
    "controllers/CrmController.js"
]

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "controllers/AdminController.js",
    "controllers/CrmController.js",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

PADROES_PROIBIDOS = [
    "GROUP_CONCAT",
    "JSON_ARRAYAGG",
    "JSON_OBJECT",
    "insertId",
    "LIMIT 1"
]

IGNORAR_MANIFESTO_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "public/uploads"
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
    rel_path = rel(path)

    for nome in IGNORAR_MANIFESTO_DIRS:
        sub = nome.split("/")
        if len(sub) == 1 and sub[0] in partes:
            return True
        if rel_path == nome or rel_path.startswith(nome + "/"):
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

    for nome in ARQUIVOS_BACKUP_DIRETO:
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
                "item": nome,
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def contar(texto, termo):
    if texto is None:
        return 0
    return texto.upper().count(termo.upper())


def scan_focado():
    achados = []

    for nome in ARQUIVOS_ALVO:
        path = ROOT / nome
        texto = ler_texto(path)

        if texto is None:
            continue

        for numero, linha in enumerate(texto.splitlines(), start=1):
            upper = linha.upper()

            for termo in PADROES_PROIBIDOS:
                if termo.upper() in upper:
                    achados.append({
                        "arquivo": nome,
                        "linha": numero,
                        "termo": termo,
                        "trecho": linha.strip()[:240]
                    })

    return achados


def aplicar_substituicoes_admin():
    nome = "controllers/AdminController.js"
    path = ROOT / nome
    texto = ler_texto(path)

    resultado = {
        "arquivo": nome,
        "existe": path.exists(),
        "alterado": False,
        "substituicoes": [],
        "ocorrencias_antes": {},
        "ocorrencias_depois": {}
    }

    if texto is None:
        resultado["erro"] = "Arquivo ausente ou ilegivel"
        return resultado

    for termo in PADROES_PROIBIDOS:
        resultado["ocorrencias_antes"][termo] = contar(texto, termo)

    novo = texto

    # PostgreSQL nao aceita UPDATE ... LIMIT 1.
    # Em usuarios_painel, deve haver no maximo um admin por empresa no fluxo esperado.
    # A condicao foi mantida sem LIMIT para compatibilidade PostgreSQL.
    antigo = "UPDATE usuarios_painel SET email = ? WHERE empresa_id = ? AND is_admin = 1 LIMIT 1"
    novo_valor = "UPDATE usuarios_painel SET email = ? WHERE empresa_id = ? AND is_admin = 1"

    if antigo in novo:
        qtd = novo.count(antigo)
        novo = novo.replace(antigo, novo_valor)
        resultado["substituicoes"].append({
            "de": antigo,
            "para": novo_valor,
            "quantidade": qtd
        })

    if novo != texto:
        gravar_texto(path, novo)
        resultado["alterado"] = True

    texto_depois = ler_texto(path)
    for termo in PADROES_PROIBIDOS:
        resultado["ocorrencias_depois"][termo] = contar(texto_depois, termo)

    resultado["sha256_depois"] = sha256_arquivo(path)
    return resultado


def aplicar_substituicoes_crm():
    nome = "controllers/CrmController.js"
    path = ROOT / nome
    texto = ler_texto(path)

    resultado = {
        "arquivo": nome,
        "existe": path.exists(),
        "alterado": False,
        "substituicoes": [],
        "ocorrencias_antes": {},
        "ocorrencias_depois": {}
    }

    if texto is None:
        resultado["erro"] = "Arquivo ausente ou ilegivel"
        return resultado

    for termo in PADROES_PROIBIDOS:
        resultado["ocorrencias_antes"][termo] = contar(texto, termo)

    novo = texto

    substituicoes = [
        (
            "SELECT JSON_ARRAYAGG(JSON_OBJECT('id', e.id, 'nome', e.nome, 'cor', e.cor))",
            "SELECT json_agg(json_build_object('id', e.id, 'nome', e.nome, 'cor', e.cor))"
        ),
        (
            "(SELECT GROUP_CONCAT(s.nome SEPARATOR ', ')",
            "(SELECT STRING_AGG(s.nome, ', ' ORDER BY s.nome)"
        ),
        (
            "(SELECT GROUP_CONCAT(s.id SEPARATOR ',')",
            "(SELECT STRING_AGG(s.id::text, ',' ORDER BY s.id)"
        ),
        (
            "'INSERT INTO usuarios_painel (empresa_id, nome, email, senha, is_admin, telefone, cargo, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'",
            "'INSERT INTO usuarios_painel (empresa_id, nome, email, senha, is_admin, telefone, cargo, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id'"
        ),
        (
            "resUser.insertId",
            "resUser.rows[0].id"
        )
    ]

    for antigo, novo_valor in substituicoes:
        if antigo in novo:
            qtd = novo.count(antigo)
            novo = novo.replace(antigo, novo_valor)
            resultado["substituicoes"].append({
                "de": antigo,
                "para": novo_valor,
                "quantidade": qtd
            })

    if novo != texto:
        gravar_texto(path, novo)
        resultado["alterado"] = True

    texto_depois = ler_texto(path)
    for termo in PADROES_PROIBIDOS:
        resultado["ocorrencias_depois"][termo] = contar(texto_depois, termo)

    resultado["sha256_depois"] = sha256_arquivo(path)
    return resultado


def node_check_arquivo(nome):
    path = ROOT / nome

    if not path.exists():
        return {
            "arquivo": nome,
            "existe": False,
            "ok": False,
            "erro": "Arquivo ausente"
        }

    try:
        proc = subprocess.run(
            ["node", "--check", str(path)],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=40
        )

        return {
            "arquivo": nome,
            "existe": True,
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip()[:500],
            "stderr": proc.stderr.strip()[:1500]
        }
    except Exception as exc:
        return {
            "arquivo": nome,
            "existe": True,
            "ok": False,
            "erro": str(exc)
        }


def node_check_alvos():
    return [node_check_arquivo(nome) for nome in ARQUIVOS_ALVO]


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_08_INICIO -->"
    marcador_fim = "<!-- ETAPA_08_FIM -->"

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


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    restantes = str(len(relatorio["scan_depois"]))
    falhas = str(sum(1 for item in relatorio["node_check"] if not item.get("ok")))

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 08 - Queries medias PostgreSQL",
        [
            "Data: " + data,
            "",
            "Foram corrigidos padroes reais de media severidade em queries PostgreSQL.",
            "Foram tratados agregadores, JSON agregado, retorno de insert e update com limitacao antiga.",
            "Arquivos alterados: controllers/AdminController.js e controllers/CrmController.js.",
            "Padroes focados restantes: " + restantes + ".",
            "Falhas em node --check: " + falhas + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 08 - Correcao de queries medias PostgreSQL",
        [
            "Data: " + data,
            "",
            "Substituidos agregadores antigos por funcoes PostgreSQL.",
            "Ajustado retorno de insert de usuario para RETURNING id.",
            "Removido LIMIT 1 de update incompatvel com PostgreSQL.",
            "Executado node --check nos arquivos alterados.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 08 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido corrigir apenas padroes reais e evitar mexer em template strings.",
            "Decidido usar STRING_AGG para agregacao textual.",
            "Decidido usar json_agg e json_build_object para agregacao JSON.",
            "Decidido usar RETURNING id para capturar id de insert no PostgreSQL."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Executar testes funcionais das telas de CRM, usuarios e contatos.",
        "Validar retorno das consultas alteradas em ambiente com dados reais.",
        "Revisar achados de baixa severidade, especialmente booleanos numericos.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.",
        "Planejar rotacao de credenciais reais expostas anteriormente."
    ]

    if relatorio["scan_depois"]:
        pendencias.insert(2, "Investigar padroes focados restantes listados no relatorio da Etapa 08.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 08",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 08 - Corrigir queries de media severidade PostgreSQL")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Padroes antes: " + str(len(relatorio["scan_antes"])))
    linhas.append("- Padroes depois: " + str(len(relatorio["scan_depois"])))
    linhas.append("")

    linhas.append("## Correcoes aplicadas")
    linhas.append("")
    for item in relatorio["correcoes"]:
        linhas.append("- " + item["arquivo"] + ": alterado=" + str(item["alterado"]))
        if item.get("erro"):
            linhas.append("  - erro: " + item["erro"])
        linhas.append("  - ocorrencias antes: " + json.dumps(item.get("ocorrencias_antes", {}), ensure_ascii=False))
        linhas.append("  - ocorrencias depois: " + json.dumps(item.get("ocorrencias_depois", {}), ensure_ascii=False))
        if item.get("substituicoes"):
            for sub in item["substituicoes"]:
                linhas.append("  - substituicao qtd=" + str(sub["quantidade"]) + ": " + sub["de"] + " -> " + sub["para"])
        else:
            linhas.append("  - substituicoes: nenhuma")

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    for item in relatorio["node_check"]:
        linhas.append("- " + item["arquivo"] + ": ok=" + str(item["ok"]))
        if not item.get("ok"):
            detalhe = item.get("stderr") or item.get("erro") or "Falha sem detalhe"
            detalhe = detalhe.replace(chr(42), "[asterisco]")
            linhas.append("  - detalhe: " + detalhe[:500])

    linhas.append("")
    linhas.append("## Padroes restantes")
    linhas.append("")
    if relatorio["scan_depois"]:
        for item in relatorio["scan_depois"]:
            trecho = item["trecho"].replace(chr(42), "[asterisco]")
            linhas.append(
                "- "
                + item["arquivo"]
                + ":"
                + str(item["linha"])
                + " termo="
                + item["termo"]
                + " trecho="
                + trecho
            )
    else:
        linhas.append("- Nenhum padrao focado restante nos arquivos alvo.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 09: executar testes funcionais controlados nas rotas/telas afetadas e revisar booleanos numericos.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_08_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_08_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    scan_antes = scan_focado()

    cor_admin = aplicar_substituicoes_admin()
    cor_crm = aplicar_substituicoes_crm()

    node_resultado = node_check_alvos()
    scan_depois = scan_focado()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "scan_antes": scan_antes,
        "correcoes": [
            cor_admin,
            cor_crm
        ],
        "node_check": node_resultado,
        "scan_depois": scan_depois
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_08_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_08_corrigir_queries_media_postgres.json"
    md_path = REPORTS_DIR / "etapa_08_corrigir_queries_media_postgres.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    falhas = sum(1 for item in node_resultado if not item.get("ok"))

    print("Etapa 08 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Padroes antes: " + str(len(scan_antes)))
    print("Padroes depois: " + str(len(scan_depois)))
    print("Node check falhas: " + str(falhas))

    if falhas > 0:
        print("")
        print("Falhas em node --check. Consulte o relatorio Markdown.")

    if scan_depois:
        print("")
        print("Padroes focados restantes:")
        for item in scan_depois:
            print("- " + item["arquivo"] + ":" + str(item["linha"]) + " " + item["termo"])


if __name__ == "__main__":
    main()