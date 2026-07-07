#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 11 - Validar endpoints e interface em ambiente controlado

Objetivo:
- Criar backup documental.
- Gerar manifesto antes e depois.
- Verificar Docker e Docker Compose.
- Verificar containers via docker compose ps.
- Coletar logs recentes do servico app.
- Testar porta exposta http://127.0.0.1:50010.
- Testar endpoints HTTP basicos sem login real e sem escrita.
- Detectar erros comuns:
  - HTTP 500
  - Cannot GET
  - erro de conexao DB
  - stacktrace nos logs
  - exceptions
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Nao altera codigo JS.
- Nao altera banco.
- Nao executa migrations.
- Nao faz login real.
- Nao chama WhatsApp, SMTP ou servicos externos.

Observacao:
- Como acessa Docker, execute com sudo se necessario:
  sudo python3 etapa_11_validar_endpoints_interface.py
"""

import os
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

MAX_LEITURA = 3145728

BASE_URL = "http://127.0.0.1:50010"

ENDPOINTS_TESTE = [
    "/",
    "/login",
    "/dashboard",
    "/api",
    "/api/health",
    "/health"
]

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

IGNORAR_MANIFESTO_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "public/uploads"
]

PADROES_LOG_ERRO = [
    "error",
    "exception",
    "stack",
    "econnrefused",
    "cannot connect",
    "database",
    "syntaxerror",
    "unhandled",
    "traceback"
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


def copiar_item(origem, destino):
    if origem.is_dir():
        shutil.copytree(origem, destino, dirs_exist_ok=True)
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)


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
            copiar_item(origem, destino_item)
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


def parse_env():
    env_path = ROOT / ".env"
    texto = ler_texto(env_path)
    dados = {}

    if texto is None:
        return dados

    for linha in texto.splitlines():
        linha = linha.strip()

        if not linha or linha.startswith("#") or "=" not in linha:
            continue

        chave, valor = linha.split("=", 1)
        valor = valor.strip()

        if len(valor) >= 2:
            if valor[0] == '"' and valor[-1] == '"':
                valor = valor[1:-1]
            elif valor[0] == "'" and valor[-1] == "'":
                valor = valor[1:-1]

        dados[chave.strip()] = valor

    return dados


def valores_sensiveis_env():
    dados = parse_env()
    valores = []

    for chave, valor in dados.items():
        upper = chave.upper()
        sensivel = False

        for termo in ["PASS", "PASSWORD", "SECRET", "TOKEN", "KEY", "SENHA"]:
            if termo in upper:
                sensivel = True

        if sensivel and valor:
            valores.append(valor)

    return valores


def redigir(texto):
    if texto is None:
        return texto

    out = str(texto)

    for valor in valores_sensiveis_env():
        if valor:
            out = out.replace(valor, "<REDIGIDO>")

    return out


def run_cmd(cmd, timeout=60):
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )

        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": redigir(proc.stdout.strip())[:12000],
            "stderr": redigir(proc.stderr.strip())[:12000],
            "ok": proc.returncode == 0
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "returncode": None,
            "stdout": "",
            "stderr": redigir(str(exc)),
            "ok": False
        }


def verificar_docker():
    return {
        "docker_version": run_cmd(["docker", "--version"], 20),
        "docker_compose_version": run_cmd(["docker", "compose", "version"], 20),
        "docker_compose_ps": run_cmd(["docker", "compose", "ps"], 30)
    }


def analisar_compose_ps(resultado_ps):
    texto = (resultado_ps.get("stdout") or "") + "\n" + (resultado_ps.get("stderr") or "")
    lower = texto.lower()

    return {
        "app_mencionado": "app" in lower or "whatsapp_bot_app" in lower,
        "db_mencionado": "db" in lower or "whatsapp_bot_db" in lower,
        "redis_mencionado": "redis" in lower or "whatsapp_bot_redis" in lower,
        "parece_rodando": "up" in lower or "running" in lower,
        "db_healthy": "healthy" in lower,
        "texto_redigido": texto[:12000]
    }


def coletar_logs_app():
    comandos = [
        ["docker", "compose", "logs", "--tail=120", "app"],
        ["docker", "logs", "--tail=120", "whatsapp_bot_app"]
    ]

    resultados = []

    for cmd in comandos:
        r = run_cmd(cmd, 40)
        resultados.append(r)
        if r.get("ok") and (r.get("stdout") or r.get("stderr")):
            break

    return resultados


def analisar_logs(resultados_logs):
    texto = ""

    for item in resultados_logs:
        texto += "\n" + (item.get("stdout") or "")
        texto += "\n" + (item.get("stderr") or "")

    lower = texto.lower()

    achados = []

    for termo in PADROES_LOG_ERRO:
        if termo in lower:
            linhas = texto.splitlines()
            for idx, linha in enumerate(linhas, start=1):
                if termo in linha.lower():
                    achados.append({
                        "termo": termo,
                        "linha": idx,
                        "trecho": redigir(linha.strip())[:300]
                    })
                    break

    return {
        "total_linhas": len(texto.splitlines()),
        "achados": achados,
        "tem_achados": len(achados) > 0,
        "amostra": redigir("\n".join(texto.splitlines()[-40:]))[:8000]
    }


def testar_http_endpoint(path):
    url = BASE_URL + path

    resultado = {
        "url": url,
        "path": path,
        "ok": False,
        "status": None,
        "erro": None,
        "body_preview": "",
        "headers": {}
    }

    req = Request(
        url,
        headers={
            "User-Agent": "etapa-11-validacao-local/1.0"
        },
        method="GET"
    )

    try:
        with urlopen(req, timeout=12) as resp:
            body = resp.read(4096)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 500
            resultado["body_preview"] = redigir(texto[:1000])
            resultado["headers"] = dict(resp.headers.items())
    except HTTPError as exc:
        try:
            body = exc.read(4096)
            texto = body.decode("utf-8", errors="replace")
        except Exception:
            texto = ""

        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 500
        resultado["erro"] = str(exc)
        resultado["body_preview"] = redigir(texto[:1000])
        resultado["headers"] = dict(exc.headers.items()) if exc.headers else {}
    except URLError as exc:
        resultado["erro"] = str(exc.reason)
    except Exception as exc:
        resultado["erro"] = str(exc)

    return resultado


def testar_http():
    resultados = []

    for endpoint in ENDPOINTS_TESTE:
        resultados.append(testar_http_endpoint(endpoint))

    return resultados


def analisar_http(resultados):
    resumo = {
        "total": len(resultados),
        "ok": 0,
        "falhas": 0,
        "status_500": 0,
        "cannot_get": 0,
        "db_error": 0,
        "paths_com_falha": []
    }

    for item in resultados:
        if item.get("ok"):
            resumo["ok"] += 1
        else:
            resumo["falhas"] += 1
            resumo["paths_com_falha"].append(item["path"])

        status = item.get("status")
        if status and status >= 500:
            resumo["status_500"] += 1

        body = (item.get("body_preview") or "").lower()
        erro = (item.get("erro") or "").lower()

        if "cannot get" in body:
            resumo["cannot_get"] += 1

        if "database" in body or "database" in erro or "econnrefused" in body or "econnrefused" in erro:
            resumo["db_error"] += 1

    resumo["sem_erros_graves"] = (
        resumo["status_500"] == 0 and
        resumo["db_error"] == 0
    )

    return resumo


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_11_INICIO -->"
    marcador_fim = "<!-- ETAPA_11_FIM -->"

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
    http = relatorio["http_resumo"]
    logs = relatorio["logs_analise"]
    ps = relatorio["compose_ps_analise"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 11 - Endpoints e interface",
        [
            "Data: " + data,
            "",
            "Foi executada validacao de containers, logs e endpoints HTTP basicos.",
            "Servico app mencionado no compose: " + str(ps["app_mencionado"]) + ".",
            "Servico db healthy: " + str(ps["db_healthy"]) + ".",
            "Endpoints testados: " + str(http["total"]) + ".",
            "Endpoints sem erro grave: " + str(http["sem_erros_graves"]) + ".",
            "Achados em logs: " + str(len(logs["achados"])) + ".",
            "Nenhuma escrita foi executada nesta etapa."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 11 - Validacao de endpoints e interface",
        [
            "Data: " + data,
            "",
            "Verificados containers Docker Compose.",
            "Coletados logs recentes do servico app.",
            "Testados endpoints HTTP basicos em porta local.",
            "Detectados status HTTP e padroes de erro comuns.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 11 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido validar disponibilidade antes de testar login real.",
            "Decidido nao fazer escrita nem chamadas externas nesta etapa.",
            "Decidido separar login e fluxos reais para etapa posterior.",
            "Decidido registrar achados de logs para triagem posterior."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Validar login real em etapa separada.",
        "Validar endpoints autenticados em ambiente controlado.",
        "Validar fluxo real de WhatsApp somente apos login e sessoes estarem estaveis.",
        "Revisar achados de logs, se houver.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes."
    ]

    if not http["sem_erros_graves"] or logs["achados"]:
        pendencias.insert(2, "Corrigir achados da Etapa 11 antes de avancar para login real.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 11",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    docker = relatorio["docker"]
    ps = relatorio["compose_ps_analise"]
    logs = relatorio["logs_analise"]
    http_resumo = relatorio["http_resumo"]

    linhas.append("# Etapa 11 - Validar endpoints e interface")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup documental criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Docker OK: " + str(docker["docker_version"]["ok"]))
    linhas.append("- Docker Compose OK: " + str(docker["docker_compose_version"]["ok"]))
    linhas.append("- App mencionado no compose: " + str(ps["app_mencionado"]))
    linhas.append("- DB healthy: " + str(ps["db_healthy"]))
    linhas.append("- Endpoints testados: " + str(http_resumo["total"]))
    linhas.append("- Endpoints OK: " + str(http_resumo["ok"]))
    linhas.append("- Endpoints falhas: " + str(http_resumo["falhas"]))
    linhas.append("- HTTP 500 encontrados: " + str(http_resumo["status_500"]))
    linhas.append("- Erros DB detectados em HTTP: " + str(http_resumo["db_error"]))
    linhas.append("- Achados em logs: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Docker Compose")
    linhas.append("")
    linhas.append("- app mencionado: " + str(ps["app_mencionado"]))
    linhas.append("- db mencionado: " + str(ps["db_mencionado"]))
    linhas.append("- redis mencionado: " + str(ps["redis_mencionado"]))
    linhas.append("- parece rodando: " + str(ps["parece_rodando"]))
    linhas.append("- db healthy: " + str(ps["db_healthy"]))

    linhas.append("")
    linhas.append("## Endpoints HTTP")
    linhas.append("")
    for item in relatorio["http_resultados"]:
        linhas.append(
            "- "
            + item["path"]
            + ": status="
            + str(item["status"])
            + ", ok="
            + str(item["ok"])
            + ", erro="
            + str(item["erro"])
        )
        preview = item.get("body_preview") or ""
        if preview:
            preview_linha = preview.replace("\n", " ")[:240]
            preview_linha = preview_linha.replace(chr(42), "[asterisco]")
            linhas.append("  - preview: " + preview_linha)

    linhas.append("")
    linhas.append("## Achados em logs")
    linhas.append("")
    if logs["achados"]:
        for item in logs["achados"]:
            trecho = item["trecho"].replace(chr(42), "[asterisco]")
            linhas.append(
                "- termo="
                + item["termo"]
                + " linha="
                + str(item["linha"])
                + " trecho="
                + trecho
            )
    else:
        linhas.append("- Nenhum padrao critico encontrado nos logs analisados.")

    linhas.append("")
    linhas.append("## Amostra final dos logs")
    linhas.append("")
    if logs.get("amostra"):
        for linha in logs["amostra"].splitlines()[-20:]:
            limpa = linha.replace(chr(42), "[asterisco]")[:240]
            linhas.append("- " + limpa)
    else:
        linhas.append("- Sem amostra de logs.")

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhuma escrita foi executada no banco.")
    linhas.append("- Nenhum login real foi executado.")
    linhas.append("- Nenhuma chamada externa ao WhatsApp ou SMTP foi executada.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 12: validar login real e endpoints autenticados em ambiente controlado.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_11_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_11_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    docker = verificar_docker()
    ps_analise = analisar_compose_ps(docker["docker_compose_ps"])
    logs_resultados = coletar_logs_app()
    logs_analise = analisar_logs(logs_resultados)
    http_resultados = testar_http()
    http_resumo = analisar_http(http_resultados)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "compose_ps_analise": ps_analise,
        "logs_resultados": logs_resultados,
        "logs_analise": logs_analise,
        "http_resultados": http_resultados,
        "http_resumo": http_resumo
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_11_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_11_validar_endpoints_interface.json"
    md_path = REPORTS_DIR / "etapa_11_validar_endpoints_interface.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 11 concluida.")
    print("Backup documental: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Docker OK: " + str(docker["docker_version"]["ok"]))
    print("Docker Compose OK: " + str(docker["docker_compose_version"]["ok"]))
    print("App mencionado: " + str(ps_analise["app_mencionado"]))
    print("DB healthy: " + str(ps_analise["db_healthy"]))
    print("Endpoints testados: " + str(http_resumo["total"]))
    print("Endpoints OK: " + str(http_resumo["ok"]))
    print("HTTP 500: " + str(http_resumo["status_500"]))
    print("Erros DB em HTTP: " + str(http_resumo["db_error"]))
    print("Achados em logs: " + str(len(logs_analise["achados"])))

    if http_resumo["status_500"] > 0 or http_resumo["db_error"] > 0 or logs_analise["achados"]:
        print("")
        print("Existem achados para revisar. Consulte o relatorio Markdown.")


if __name__ == "__main__":
    main()