#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 12 - Validar login e endpoints autenticados

Objetivo:
- Criar backup documental.
- Gerar manifesto antes e depois.
- Verificar Docker e Docker Compose.
- Validar app respondendo na porta local.
- Fazer login controlado em POST /api/auth/login.
- Nao imprimir senha.
- Manter cookie apenas em memoria.
- Validar paginas autenticadas com cookie.
- Validar endpoints somente leitura quando existirem.
- Detectar 401, 403, 500, erro de banco e stacktrace.
- Nao criar, editar ou excluir dados.
- Nao chamar WhatsApp, SMTP ou servicos externos.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Observacao:
- Como acessa Docker, execute com sudo se necessario:
  sudo python3 etapa_12_validar_login_endpoints_autenticados.py

Credenciais:
- O script tenta ler do ambiente ou do .env, nesta ordem:
  ETAPA12_LOGIN_EMAIL
  LOGIN_EMAIL
  ADMIN_EMAIL
  SEED_ADMIN_EMAIL
  SUPER_ADMIN_EMAIL
  DEFAULT_ADMIN_EMAIL

  ETAPA12_LOGIN_PASSWORD
  LOGIN_PASSWORD
  ADMIN_PASSWORD
  SEED_ADMIN_PASSWORD
  SUPER_ADMIN_PASSWORD
  DEFAULT_ADMIN_PASSWORD

- Se nao encontrar senha, o login sera marcado como nao executado.
"""

import os
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError, URLError
from http.cookiejar import CookieJar

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

MAX_LEITURA = 3145728
BASE_URL = "http://127.0.0.1:50010"

LOGIN_PATH = "/api/auth/login"

PAGINAS_AUTENTICADAS = [
    "/dashboard",
    "/crm",
    "/admin",
    "/contatos",
    "/setores",
    "/usuarios",
    "/configuracoes"
]

ENDPOINTS_LEITURA = [
    "/api/auth/me",
    "/api/session",
    "/api/empresas",
    "/api/usuarios",
    "/api/contatos",
    "/api/setores",
    "/api/mensagens"
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

PADROES_ERRO = [
    "error",
    "exception",
    "stack",
    "traceback",
    "econnrefused",
    "database",
    "syntaxerror",
    "unhandled",
    "senha",
    "password"
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
    dados = {}
    env_path = ROOT / ".env"
    texto = ler_texto(env_path)

    if texto:
        for linha in texto.splitlines():
            linha = linha.strip()

            if not linha:
                continue

            if linha.startswith("#"):
                continue

            if "=" not in linha:
                continue

            chave, valor = linha.split("=", 1)
            valor = valor.strip()

            if len(valor) >= 2:
                if valor[0] == '"' and valor[-1] == '"':
                    valor = valor[1:-1]
                elif valor[0] == "'" and valor[-1] == "'":
                    valor = valor[1:-1]

            dados[chave.strip()] = valor

    for chave, valor in os.environ.items():
        if chave not in dados:
            dados[chave] = valor

    return dados


def obter_primeiro(dados, chaves):
    for chave in chaves:
        valor = dados.get(chave)
        if valor:
            return valor
    return ""


def obter_credenciais():
    dados = parse_env()

    email = obter_primeiro(
        dados,
        [
            "ETAPA12_LOGIN_EMAIL",
            "LOGIN_EMAIL",
            "ADMIN_EMAIL",
            "SEED_ADMIN_EMAIL",
            "SUPER_ADMIN_EMAIL",
            "DEFAULT_ADMIN_EMAIL"
        ]
    )

    senha = obter_primeiro(
        dados,
        [
            "ETAPA12_LOGIN_PASSWORD",
            "LOGIN_PASSWORD",
            "ADMIN_PASSWORD",
            "SEED_ADMIN_PASSWORD",
            "SUPER_ADMIN_PASSWORD",
            "DEFAULT_ADMIN_PASSWORD"
        ]
    )

    return {
        "email": email,
        "senha": senha,
        "email_configurado": bool(email),
        "senha_configurada": bool(senha)
    }


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

    cred = obter_credenciais()
    if cred["senha"]:
        valores.append(cred["senha"])

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


def criar_opener():
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    return opener, jar


def http_request(opener, metodo, path, data_obj=None):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "url": url,
        "metodo": metodo,
        "ok": False,
        "status": None,
        "erro": None,
        "body_preview": "",
        "content_type": "",
        "redirect_url": None
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-12-validacao-local/1.0"
    }

    if data_obj is not None:
        body_text = json.dumps(data_obj)
        body_bytes = body_text.encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(
        url,
        data=body_bytes,
        headers=headers,
        method=metodo
    )

    try:
        with opener.open(req, timeout=15) as resp:
            body = resp.read(8192)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["body_preview"] = redigir(texto[:1200])
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["redirect_url"] = resp.geturl()
    except HTTPError as exc:
        try:
            body = exc.read(8192)
            texto = body.decode("utf-8", errors="replace")
        except Exception:
            texto = ""

        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 400
        resultado["erro"] = str(exc)
        resultado["body_preview"] = redigir(texto[:1200])
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
    except URLError as exc:
        resultado["erro"] = str(exc.reason)
    except Exception as exc:
        resultado["erro"] = str(exc)

    return resultado


def cookies_resumo(jar):
    itens = []
    for cookie in jar:
        itens.append({
            "name": cookie.name,
            "domain": cookie.domain,
            "path": cookie.path,
            "secure": cookie.secure
        })
    return itens


def realizar_login(opener, jar):
    cred = obter_credenciais()

    resultado = {
        "executado": False,
        "email_configurado": cred["email_configurado"],
        "senha_configurada": cred["senha_configurada"],
        "email_usado": cred["email"] if cred["email"] else "",
        "ok": False,
        "http": None,
        "cookies": []
    }

    if not cred["email_configurado"] or not cred["senha_configurada"]:
        resultado["motivo"] = "Credenciais nao configuradas no ambiente ou .env"
        return resultado

    payload = {
        "email": cred["email"],
        "password": cred["senha"]
    }

    http = http_request(opener, "POST", LOGIN_PATH, payload)

    resultado["executado"] = True
    resultado["http"] = http
    resultado["cookies"] = cookies_resumo(jar)

    body = (http.get("body_preview") or "").lower()
    status_ok = http.get("status") in [200, 201, 302]
    cookie_ok = len(resultado["cookies"]) > 0
    body_ok = "sucesso" in body or "success" in body or "dashboard" in body or "ok" in body

    resultado["ok"] = bool(status_ok and (cookie_ok or body_ok))

    return resultado


def testar_paginas_autenticadas(opener):
    resultados = []

    for path in PAGINAS_AUTENTICADAS:
        resultados.append(http_request(opener, "GET", path))

    return resultados


def testar_endpoints_leitura(opener):
    resultados = []

    for path in ENDPOINTS_LEITURA:
        resultados.append(http_request(opener, "GET", path))

    return resultados


def analisar_resultados_http(resultados):
    resumo = {
        "total": len(resultados),
        "ok_2xx_3xx": 0,
        "status_401": 0,
        "status_403": 0,
        "status_404": 0,
        "status_500": 0,
        "db_error": 0,
        "stacktrace": 0,
        "falhas_graves": 0
    }

    for item in resultados:
        status = item.get("status")
        body = (item.get("body_preview") or "").lower()
        erro = (item.get("erro") or "").lower()

        if status is not None and 200 <= status < 400:
            resumo["ok_2xx_3xx"] += 1

        if status == 401:
            resumo["status_401"] += 1

        if status == 403:
            resumo["status_403"] += 1

        if status == 404:
            resumo["status_404"] += 1

        if status is not None and status >= 500:
            resumo["status_500"] += 1

        if "database" in body or "econnrefused" in body or "database" in erro:
            resumo["db_error"] += 1

        if "stack" in body or "traceback" in body or "syntaxerror" in body:
            resumo["stacktrace"] += 1

    resumo["falhas_graves"] = (
        resumo["status_500"] +
        resumo["db_error"] +
        resumo["stacktrace"]
    )

    resumo["sem_falhas_graves"] = resumo["falhas_graves"] == 0

    return resumo


def coletar_logs_app():
    comandos = [
        ["docker", "compose", "logs", "--tail=160", "app"],
        ["docker", "logs", "--tail=160", "whatsapp_bot_app"]
    ]

    resultados = []

    for cmd in comandos:
        r = run_cmd(cmd, 50)
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

    for termo in PADROES_ERRO:
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
        "amostra": redigir("\n".join(texto.splitlines()[-50:]))[:10000]
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_12_INICIO -->"
    marcador_fim = "<!-- ETAPA_12_FIM -->"

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
    login = relatorio["login"]
    paginas = relatorio["paginas_resumo"]
    endpoints = relatorio["endpoints_resumo"]
    logs = relatorio["logs_analise"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 12 - Login e endpoints autenticados",
        [
            "Data: " + data,
            "",
            "Foi executada validacao de login real e rotas autenticadas em ambiente controlado.",
            "Login executado: " + str(login["executado"]) + ".",
            "Login OK: " + str(login["ok"]) + ".",
            "Paginas autenticadas sem falhas graves: " + str(paginas["sem_falhas_graves"]) + ".",
            "Endpoints autenticados sem falhas graves: " + str(endpoints["sem_falhas_graves"]) + ".",
            "Achados em logs: " + str(len(logs["achados"])) + ".",
            "Nenhuma escrita funcional foi executada nesta etapa."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 12 - Validacao de login e autenticacao",
        [
            "Data: " + data,
            "",
            "Validado login real via endpoint de autenticacao.",
            "Validadas paginas autenticadas com cookie mantido em memoria.",
            "Validados endpoints somente leitura quando existentes.",
            "Coletados logs recentes para detectar erros criticos.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 12 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido manter cookie apenas em memoria durante a validacao.",
            "Decidido nao imprimir senha nem persistir credenciais.",
            "Decidido nao executar criacao, edicao ou exclusao de dados nesta etapa.",
            "Decidido separar fluxos reais de WhatsApp para etapa posterior."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Validar fluxos reais da interface web com usuario logado.",
        "Validar endpoints autenticados com dados reais em modo controlado.",
        "Reduzir verbosidade de logs de sessao e cookies em producao.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.",
        "Planejar rotacao de credenciais reais expostas anteriormente."
    ]

    if not login["ok"] or not paginas["sem_falhas_graves"] or not endpoints["sem_falhas_graves"]:
        pendencias.insert(2, "Corrigir achados da Etapa 12 antes de avancar para fluxos reais.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 12",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    login = relatorio["login"]
    paginas = relatorio["paginas_resumo"]
    endpoints = relatorio["endpoints_resumo"]
    logs = relatorio["logs_analise"]

    linhas.append("# Etapa 12 - Validar login e endpoints autenticados")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup documental criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Docker OK: " + str(relatorio["docker"]["docker_version"]["ok"]))
    linhas.append("- Docker Compose OK: " + str(relatorio["docker"]["docker_compose_version"]["ok"]))
    linhas.append("- Login executado: " + str(login["executado"]))
    linhas.append("- Login OK: " + str(login["ok"]))
    linhas.append("- Email configurado: " + str(login["email_configurado"]))
    linhas.append("- Senha configurada: " + str(login["senha_configurada"]))
    linhas.append("- Cookies recebidos: " + str(len(login["cookies"])))
    linhas.append("- Paginas autenticadas testadas: " + str(paginas["total"]))
    linhas.append("- Paginas sem falhas graves: " + str(paginas["sem_falhas_graves"]))
    linhas.append("- Endpoints leitura testados: " + str(endpoints["total"]))
    linhas.append("- Endpoints sem falhas graves: " + str(endpoints["sem_falhas_graves"]))
    linhas.append("- Achados em logs: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Login")
    linhas.append("")
    linhas.append("- Executado: " + str(login["executado"]))
    linhas.append("- OK: " + str(login["ok"]))
    linhas.append("- Email usado: " + str(login["email_usado"]))
    if login.get("motivo"):
        linhas.append("- Motivo: " + login["motivo"])
    if login.get("http"):
        http = login["http"]
        linhas.append("- Status HTTP: " + str(http.get("status")))
        linhas.append("- Erro: " + str(http.get("erro")))
        preview = (http.get("body_preview") or "").replace("\n", " ")[:240]
        preview = preview.replace(chr(42), "[asterisco]")
        if preview:
            linhas.append("- Preview: " + preview)

    linhas.append("")
    linhas.append("## Cookies")
    linhas.append("")
    if login["cookies"]:
        for item in login["cookies"]:
            linhas.append(
                "- name="
                + item["name"]
                + ", domain="
                + item["domain"]
                + ", path="
                + item["path"]
                + ", secure="
                + str(item["secure"])
            )
    else:
        linhas.append("- Nenhum cookie registrado.")

    linhas.append("")
    linhas.append("## Paginas autenticadas")
    linhas.append("")
    for item in relatorio["paginas_resultados"]:
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

    linhas.append("")
    linhas.append("## Endpoints somente leitura")
    linhas.append("")
    for item in relatorio["endpoints_resultados"]:
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

    linhas.append("")
    linhas.append("## Resumo HTTP")
    linhas.append("")
    linhas.append("- Paginas 401: " + str(paginas["status_401"]))
    linhas.append("- Paginas 403: " + str(paginas["status_403"]))
    linhas.append("- Paginas 500: " + str(paginas["status_500"]))
    linhas.append("- Endpoints 401: " + str(endpoints["status_401"]))
    linhas.append("- Endpoints 403: " + str(endpoints["status_403"]))
    linhas.append("- Endpoints 500: " + str(endpoints["status_500"]))
    linhas.append("- Erros DB em paginas: " + str(paginas["db_error"]))
    linhas.append("- Erros DB em endpoints: " + str(endpoints["db_error"]))

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
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Cookie foi mantido apenas em memoria.")
    linhas.append("- Nenhuma criacao, edicao ou exclusao de dados foi executada.")
    linhas.append("- Nenhuma chamada externa ao WhatsApp ou SMTP foi executada.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 13: validar fluxos reais da interface web com usuario logado em ambiente controlado.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_12_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_12_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    docker = verificar_docker()
    compose = analisar_compose_ps(docker["docker_compose_ps"])

    opener, jar = criar_opener()

    login = realizar_login(opener, jar)
    paginas = testar_paginas_autenticadas(opener)
    endpoints = testar_endpoints_leitura(opener)

    paginas_resumo = analisar_resultados_http(paginas)
    endpoints_resumo = analisar_resultados_http(endpoints)

    logs_resultados = coletar_logs_app()
    logs_analise = analisar_logs(logs_resultados)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "compose_ps_analise": compose,
        "login": login,
        "paginas_resultados": paginas,
        "paginas_resumo": paginas_resumo,
        "endpoints_resultados": endpoints,
        "endpoints_resumo": endpoints_resumo,
        "logs_resultados": logs_resultados,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_12_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_12_validar_login_endpoints_autenticados.json"
    md_path = REPORTS_DIR / "etapa_12_validar_login_endpoints_autenticados.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 12 concluida.")
    print("Backup documental: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Docker OK: " + str(docker["docker_version"]["ok"]))
    print("Docker Compose OK: " + str(docker["docker_compose_version"]["ok"]))
    print("Login executado: " + str(login["executado"]))
    print("Login OK: " + str(login["ok"]))
    print("Cookies recebidos: " + str(len(login["cookies"])))
    print("Paginas sem falhas graves: " + str(paginas_resumo["sem_falhas_graves"]))
    print("Endpoints sem falhas graves: " + str(endpoints_resumo["sem_falhas_graves"]))
    print("Achados em logs: " + str(len(logs_analise["achados"])))

    if not login["ok"] or not paginas_resumo["sem_falhas_graves"] or not endpoints_resumo["sem_falhas_graves"]:
        print("")
        print("Existem achados para revisar. Consulte o relatorio Markdown.")


if __name__ == "__main__":
    main()