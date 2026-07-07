#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 05 - Validar backend PostgreSQL

Objetivo:
- Criar backup antes de qualquer acao.
- Gerar manifesto antes e depois.
- Auditar setup_db.js, src/config/db.js, controllers, routes e src.
- Procurar padroes SQL incompativeis ou suspeitos para PostgreSQL.
- Mapear queries SQL em arquivos JS.
- Rodar node --check nos principais arquivos JS.
- Gerar relatorios JSON e Markdown em reports.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.

Escopo:
- Nao corrige queries nesta etapa.
- Nao altera regras de negocio.
- Nao altera .env real.
- Nao executa banco.
- Nao executa Docker.
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

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "setup_db.js",
    "src/config/db.js",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

DIRS_ANALISE = [
    "controllers",
    "routes",
    "src"
]

ARQUIVOS_ANALISE_DIRETA = [
    "setup_db.js",
    "server.js",
    "package.json"
]

ARQUIVOS_NODE_CHECK = [
    "server.js",
    "setup_db.js",
    "routes/api.js",
    "routes/index.js",
    "controllers/AdminController.js",
    "controllers/AdminPanelController.js",
    "controllers/AuthController.js",
    "controllers/CrmController.js",
    "controllers/ScheduleController.js",
    "controllers/WhatsAppController.js",
    "src/config/db.js",
    "src/managers/SessionManager.js",
    "src/managers/OpenAIManager.js",
    "src/middleware/auth.js",
    "src/utils/atendimento.js",
    "script/export_full.js",
    "script/backup_database.js"
]

PADROES_SQL_RISCO = [
    {
        "nome": "AUTO_INCREMENT",
        "regex": r"\bAUTO_INCREMENT\b",
        "severidade": "alta",
        "recomendacao": "Usar SERIAL, BIGSERIAL ou GENERATED AS IDENTITY no PostgreSQL."
    },
    {
        "nome": "TINYINT",
        "regex": r"\bTINYINT\b",
        "severidade": "media",
        "recomendacao": "Usar SMALLINT, INTEGER ou BOOLEAN conforme o caso."
    },
    {
        "nome": "DATETIME",
        "regex": r"\bDATETIME\b",
        "severidade": "media",
        "recomendacao": "Usar TIMESTAMP ou TIMESTAMPTZ no PostgreSQL."
    },
    {
        "nome": "ON_DUPLICATE_KEY",
        "regex": r"\bON\s+DUPLICATE\s+KEY\b",
        "severidade": "alta",
        "recomendacao": "Usar INSERT ... ON CONFLICT no PostgreSQL."
    },
    {
        "nome": "INSERT_IGNORE",
        "regex": r"\bINSERT\s+IGNORE\b",
        "severidade": "alta",
        "recomendacao": "Usar INSERT ... ON CONFLICT DO NOTHING no PostgreSQL."
    },
    {
        "nome": "LAST_INSERT_ID",
        "regex": r"\bLAST_INSERT_ID\s*\(",
        "severidade": "alta",
        "recomendacao": "Usar RETURNING id no PostgreSQL."
    },
    {
        "nome": "ENGINE_EQUALS",
        "regex": r"\bENGINE\s*=",
        "severidade": "alta",
        "recomendacao": "Remover engine de tabela, pois PostgreSQL nao usa ENGINE."
    },
    {
        "nome": "UNSIGNED",
        "regex": r"\bUNSIGNED\b",
        "severidade": "media",
        "recomendacao": "PostgreSQL nao possui UNSIGNED nativo. Validar dominio ou constraint."
    },
    {
        "nome": "BACKTICK_SQL",
        "regex": r"`[^`]+`",
        "severidade": "media",
        "recomendacao": "Usar aspas duplas para identificadores, ou remover quoting se nao necessario."
    },
    {
        "nome": "LIMIT_OFFSET_PARAM_MYSQL",
        "regex": r"\bLIMIT\s*\?\s*,\s*\?",
        "severidade": "alta",
        "recomendacao": "Usar LIMIT $1 OFFSET $2, ou adaptar parametros posicionais."
    },
    {
        "nome": "NOW_FUNCTION_OK_REVISAR",
        "regex": r"\bNOW\s*\(\s*\)",
        "severidade": "baixa",
        "recomendacao": "NOW e suportado no PostgreSQL, mas validar timezone e uso de TIMESTAMPTZ."
    },
    {
        "nome": "BOOLEAN_NUMERICO",
        "regex": r"\b(ativo|is_admin|admin|status)\s*=\s*[01]\b",
        "severidade": "baixa",
        "recomendacao": "Validar se a coluna e BOOLEAN e se o valor numerico deve virar TRUE/FALSE."
    }
]

PADROES_QUERY = [
    r"\bSELECT\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bCREATE\s+TABLE\b",
    r"\bALTER\s+TABLE\b",
    r"\bDROP\s+TABLE\b",
    r"\bTRUNCATE\b"
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
                "arquivo": nome,
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def listar_arquivos_js_para_analise():
    arquivos = []

    for nome in ARQUIVOS_ANALISE_DIRETA:
        p = ROOT / nome
        if p.exists() and p.is_file():
            arquivos.append(p)

    for nome_dir in DIRS_ANALISE:
        base = ROOT / nome_dir
        if not base.exists():
            continue

        for p in base.rglob("*.js"):
            if "node_modules" in set(p.parts):
                continue
            arquivos.append(p)

    unicos = {}
    for p in arquivos:
        unicos[rel(p)] = p

    return [unicos[k] for k in sorted(unicos.keys())]


def linha_redigida(linha):
    texto = linha.strip()

    if "=" not in texto:
        return texto[:220]

    esquerda = texto.split("=", 1)[0].strip()
    esquerda_upper = esquerda.upper()

    for termo in ["PASS", "PASSWORD", "SECRET", "TOKEN", "KEY", "SENHA"]:
        if termo in esquerda_upper:
            return esquerda + "=<REDIGIDO>"

    return texto[:220]


def analisar_padroes_sql():
    achados = []

    for path in listar_arquivos_js_para_analise():
        texto = ler_texto(path)
        if texto is None:
            continue

        linhas = texto.splitlines()
        for numero, linha in enumerate(linhas, start=1):
            for padrao in PADROES_SQL_RISCO:
                if re.search(padrao["regex"], linha, flags=re.IGNORECASE):
                    achados.append({
                        "arquivo": rel(path),
                        "linha": numero,
                        "padrao": padrao["nome"],
                        "severidade": padrao["severidade"],
                        "recomendacao": padrao["recomendacao"],
                        "trecho": linha_redigida(linha)
                    })

    return achados


def linha_tem_query(linha):
    for padrao in PADROES_QUERY:
        if re.search(padrao, linha, flags=re.IGNORECASE):
            return True
    return False


def mapear_queries():
    queries = []

    for path in listar_arquivos_js_para_analise():
        texto = ler_texto(path)
        if texto is None:
            continue

        linhas = texto.splitlines()
        for numero, linha in enumerate(linhas, start=1):
            if linha_tem_query(linha):
                queries.append({
                    "arquivo": rel(path),
                    "linha": numero,
                    "trecho": linha_redigida(linha)
                })

    return queries


def analisar_config_db():
    path = ROOT / "src/config/db.js"
    texto = ler_texto(path)

    resultado = {
        "arquivo": "src/config/db.js",
        "existe": path.exists(),
        "ok_basico": False,
        "achados": []
    }

    if texto is None:
        resultado["achados"].append({
            "tipo": "erro",
            "mensagem": "Arquivo ausente ou ilegivel"
        })
        return resultado

    checks_obrigatorios = [
        ("require_pg", "require('pg')"),
        ("pool_pg", "new Pool"),
        ("db_host", "process.env.DB_HOST"),
        ("db_port", "process.env.DB_PORT"),
        ("db_name", "process.env.DB_NAME")
    ]

    faltantes = []

    for nome, termo in checks_obrigatorios:
        if termo not in texto:
            faltantes.append(nome)

    if faltantes:
        resultado["achados"].append({
            "tipo": "faltantes",
            "mensagem": "Elementos esperados ausentes: " + ", ".join(faltantes)
        })
    else:
        resultado["ok_basico"] = True

    if "mysql" in texto.lower():
        resultado["achados"].append({
            "tipo": "comentario_ou_legado",
            "mensagem": "Texto ainda contem termo antigo relacionado a banco anterior"
        })

    if "?" in texto and "$1" in texto:
        resultado["achados"].append({
            "tipo": "compatibilidade_parametros",
            "mensagem": "Arquivo parece conter adaptacao de parametros legados para PostgreSQL"
        })

    return resultado


def analisar_setup_db():
    path = ROOT / "setup_db.js"
    texto = ler_texto(path)

    resultado = {
        "arquivo": "setup_db.js",
        "existe": path.exists(),
        "ok_basico": False,
        "achados": []
    }

    if texto is None:
        resultado["achados"].append({
            "tipo": "erro",
            "mensagem": "Arquivo ausente ou ilegivel"
        })
        return resultado

    texto_lower = texto.lower()

    if "require('pg')" in texto or 'require("pg")' in texto:
        resultado["achados"].append({
            "tipo": "pg_detectado",
            "mensagem": "Dependencia pg encontrada no setup"
        })
    else:
        resultado["achados"].append({
            "tipo": "pg_nao_detectado",
            "mensagem": "Nao foi detectado require de pg no setup"
        })

    if "create table" in texto_lower:
        resultado["achados"].append({
            "tipo": "ddl_detectado",
            "mensagem": "setup_db.js contem criacao de tabelas"
        })

    if "serial" in texto_lower or "identity" in texto_lower:
        resultado["achados"].append({
            "tipo": "id_postgres_detectado",
            "mensagem": "Encontrado padrao de ID compativel com PostgreSQL"
        })

    if "auto_increment" in texto_lower:
        resultado["achados"].append({
            "tipo": "risco",
            "mensagem": "Encontrado AUTO_INCREMENT no setup"
        })

    resultado["ok_basico"] = True
    return resultado


def validar_package_json():
    path = ROOT / "package.json"
    texto = ler_texto(path)

    if texto is None:
        return {
            "ok": False,
            "erros": ["package.json ausente ou ilegivel"],
            "avisos": []
        }

    try:
        pkg = json.loads(texto)
    except Exception as exc:
        return {
            "ok": False,
            "erros": ["package.json invalido: " + str(exc)],
            "avisos": []
        }

    deps = {}
    deps.update(pkg.get("dependencies", {}))
    deps.update(pkg.get("devDependencies", {}))

    erros = []
    avisos = []

    if "pg" not in deps:
        erros.append("Dependencia pg nao encontrada")

    for dep_antiga in ["mysql", "mysql2"]:
        if dep_antiga in deps:
            erros.append("Dependencia antiga encontrada: " + dep_antiga)

    return {
        "ok": len(erros) == 0,
        "erros": erros,
        "avisos": avisos,
        "pg_version": deps.get("pg"),
        "total_dependencias": len(deps)
    }


def node_disponivel():
    try:
        result = subprocess.run(
            ["node", "--version"],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception:
        return False, None


def node_check():
    disponivel, versao = node_disponivel()

    resultado = {
        "node_disponivel": disponivel,
        "node_versao": versao,
        "arquivos": []
    }

    if not disponivel:
        resultado["aviso"] = "Node nao disponivel"
        return resultado

    for nome in ARQUIVOS_NODE_CHECK:
        path = ROOT / nome

        if not path.exists():
            resultado["arquivos"].append({
                "arquivo": nome,
                "existe": False,
                "ok": False,
                "erro": "Arquivo ausente"
            })
            continue

        try:
            proc = subprocess.run(
                ["node", "--check", str(path)],
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=40
            )

            resultado["arquivos"].append({
                "arquivo": nome,
                "existe": True,
                "ok": proc.returncode == 0,
                "stdout": proc.stdout.strip()[:500],
                "stderr": proc.stderr.strip()[:1000]
            })
        except Exception as exc:
            resultado["arquivos"].append({
                "arquivo": nome,
                "existe": True,
                "ok": False,
                "erro": str(exc)
            })

    return resultado


def resumo_node_check(resultado):
    total = 0
    ok = 0
    falhas = 0
    ausentes = 0

    for item in resultado.get("arquivos", []):
        total += 1
        if not item.get("existe"):
            ausentes += 1
        elif item.get("ok"):
            ok += 1
        else:
            falhas += 1

    return {
        "total": total,
        "ok": ok,
        "falhas": falhas,
        "ausentes": ausentes
    }


def resumir_severidade(achados):
    resumo = {
        "alta": 0,
        "media": 0,
        "baixa": 0
    }

    for item in achados:
        sev = item.get("severidade", "baixa")
        if sev not in resumo:
            resumo[sev] = 0
        resumo[sev] += 1

    return resumo


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_05_INICIO -->"
    marcador_fim = "<!-- ETAPA_05_FIM -->"

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
    achados = relatorio["resumo_severidade"]
    total_queries = str(len(relatorio["queries_mapeadas"]))

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 05 - Auditoria backend PostgreSQL",
        [
            "Data: " + data,
            "",
            "Foi executada auditoria estatica do backend com foco em PostgreSQL.",
            "Foram analisados setup_db.js, src/config/db.js, controllers, routes e src.",
            "Queries mapeadas: " + total_queries + ".",
            "Achados de alta severidade: " + str(achados.get("alta", 0)) + ".",
            "Achados de media severidade: " + str(achados.get("media", 0)) + ".",
            "Achados de baixa severidade: " + str(achados.get("baixa", 0)) + ".",
            "Nenhuma correcao de query foi aplicada nesta etapa."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 05 - Auditoria PostgreSQL",
        [
            "Data: " + data,
            "",
            "Adicionado relatorio de auditoria de compatibilidade PostgreSQL.",
            "Mapeadas queries SQL em arquivos JS.",
            "Analisados setup_db.js e src/config/db.js.",
            "Executado node --check nos principais arquivos JS.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 05 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido auditar antes de corrigir queries para reduzir risco.",
            "Decidido tratar setup_db.js e queries suspeitas em etapa posterior.",
            "Decidido manter esta etapa sem execucao de banco ou Docker.",
            "Decidido usar severidade para priorizar correcoes futuras."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 05",
        [
            "Data: " + data,
            "",
            "Corrigir achados de alta severidade apontados no relatorio.",
            "Revisar achados de media severidade apontados no relatorio.",
            "Validar setup_db.js com PostgreSQL em ambiente controlado.",
            "Executar testes funcionais de rotas e controllers.",
            "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.",
            "Planejar rotacao de credenciais reais expostas anteriormente."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 05 - Validar backend PostgreSQL")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivos analisados: " + str(len(relatorio["arquivos_analisados"])))
    linhas.append("- Queries mapeadas: " + str(len(relatorio["queries_mapeadas"])))
    linhas.append("- Achados SQL suspeitos: " + str(len(relatorio["achados_sql"])))
    linhas.append("- Validacao package.json OK: " + str(relatorio["validacao_package_json"]["ok"]))
    linhas.append("")

    linhas.append("## Severidade")
    linhas.append("")
    for chave in ["alta", "media", "baixa"]:
        linhas.append("- " + chave + ": " + str(relatorio["resumo_severidade"].get(chave, 0)))

    linhas.append("")
    linhas.append("## Analise src/config/db.js")
    linhas.append("")
    db = relatorio["analise_config_db"]
    linhas.append("- Existe: " + str(db["existe"]))
    linhas.append("- OK basico: " + str(db["ok_basico"]))
    for item in db["achados"]:
        linhas.append("- " + item["tipo"] + ": " + item["mensagem"])

    linhas.append("")
    linhas.append("## Analise setup_db.js")
    linhas.append("")
    setup = relatorio["analise_setup_db"]
    linhas.append("- Existe: " + str(setup["existe"]))
    linhas.append("- OK basico: " + str(setup["ok_basico"]))
    for item in setup["achados"]:
        linhas.append("- " + item["tipo"] + ": " + item["mensagem"])

    linhas.append("")
    linhas.append("## Package JSON")
    linhas.append("")
    vp = relatorio["validacao_package_json"]
    linhas.append("- OK: " + str(vp["ok"]))
    linhas.append("- pg: " + str(vp.get("pg_version")))
    if vp["erros"]:
        linhas.append("- Erros:")
        for erro in vp["erros"]:
            linhas.append("  - " + erro)
    else:
        linhas.append("- Erros: nenhum")

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    resumo_node = relatorio["resumo_node_check"]
    linhas.append("- Node disponivel: " + str(relatorio["node_check"]["node_disponivel"]))
    linhas.append("- Node versao: " + str(relatorio["node_check"].get("node_versao")))
    linhas.append("- Arquivos verificados: " + str(resumo_node["total"]))
    linhas.append("- OK: " + str(resumo_node["ok"]))
    linhas.append("- Falhas: " + str(resumo_node["falhas"]))
    linhas.append("- Ausentes: " + str(resumo_node["ausentes"]))

    falhas = []
    for item in relatorio["node_check"].get("arquivos", []):
        if item.get("existe") and not item.get("ok"):
            falhas.append(item)

    if falhas:
        linhas.append("")
        linhas.append("### Falhas node --check")
        linhas.append("")
        for item in falhas:
            detalhe = item.get("stderr") or item.get("erro") or "Falha sem detalhe"
            detalhe = detalhe.replace(chr(42), "[asterisco]")
            linhas.append("- " + item["arquivo"] + ": " + detalhe[:300])

    linhas.append("")
    linhas.append("## Achados SQL suspeitos")
    linhas.append("")
    if relatorio["achados_sql"]:
        limite = 120
        for item in relatorio["achados_sql"][:limite]:
            trecho = item["trecho"].replace(chr(42), "[asterisco]")
            linhas.append(
                "- "
                + item["arquivo"]
                + ":"
                + str(item["linha"])
                + " severidade="
                + item["severidade"]
                + " padrao="
                + item["padrao"]
                + " trecho="
                + trecho
            )
            linhas.append("  - recomendacao: " + item["recomendacao"])
        if len(relatorio["achados_sql"]) > limite:
            linhas.append("- Lista truncada no Markdown. Consulte o JSON completo.")
    else:
        linhas.append("- Nenhum padrao SQL suspeito encontrado.")

    linhas.append("")
    linhas.append("## Queries mapeadas")
    linhas.append("")
    if relatorio["queries_mapeadas"]:
        limite_q = 120
        for item in relatorio["queries_mapeadas"][:limite_q]:
            trecho = item["trecho"].replace(chr(42), "[asterisco]")
            linhas.append("- " + item["arquivo"] + ":" + str(item["linha"]) + " trecho=" + trecho)
        if len(relatorio["queries_mapeadas"]) > limite_q:
            linhas.append("- Lista truncada no Markdown. Consulte o JSON completo.")
    else:
        linhas.append("- Nenhuma query mapeada.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 06: corrigir setup_db.js e queries suspeitas priorizando severidade alta.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_05_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_05_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    arquivos_analisados = [rel(p) for p in listar_arquivos_js_para_analise()]
    achados_sql = analisar_padroes_sql()
    queries = mapear_queries()
    analise_db = analisar_config_db()
    analise_setup = analisar_setup_db()
    validacao_pkg = validar_package_json()
    node_resultado = node_check()
    resumo_node = resumo_node_check(node_resultado)
    resumo_sev = resumir_severidade(achados_sql)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "arquivos_analisados": arquivos_analisados,
        "achados_sql": achados_sql,
        "queries_mapeadas": queries,
        "analise_config_db": analise_db,
        "analise_setup_db": analise_setup,
        "validacao_package_json": validacao_pkg,
        "node_check": node_resultado,
        "resumo_node_check": resumo_node,
        "resumo_severidade": resumo_sev
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_05_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_05_validar_postgres_backend.json"
    md_path = REPORTS_DIR / "etapa_05_validar_postgres_backend.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 05 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Arquivos analisados: " + str(len(arquivos_analisados)))
    print("Queries mapeadas: " + str(len(queries)))
    print("Achados SQL: " + str(len(achados_sql)))
    print("Alta severidade: " + str(resumo_sev.get("alta", 0)))
    print("Media severidade: " + str(resumo_sev.get("media", 0)))
    print("Baixa severidade: " + str(resumo_sev.get("baixa", 0)))
    print("Package JSON OK: " + str(validacao_pkg["ok"]))
    print("Node check falhas: " + str(resumo_node["falhas"]))

    if not validacao_pkg["ok"]:
        print("")
        print("Erros em package.json:")
        for erro in validacao_pkg["erros"]:
            print("- " + erro)

    if resumo_node["falhas"] > 0:
        print("")
        print("Falhas em node --check. Consulte o relatorio Markdown.")

    if not validacao_pkg["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()