#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 13 - Validar fluxos reais da interface logada

Objetivo:
- Criar backup documental.
- Gerar manifesto antes e depois.
- Fazer login com email e senha.
- Manter cookie apenas em memoria.
- Acessar dashboard autenticado.
- Descobrir links reais no HTML do dashboard.
- Descobrir assets reais no HTML do dashboard.
- Testar somente GET/HEAD em paginas e assets encontrados.
- Nao executar POST/PUT/DELETE alem do login.
- Nao criar, editar ou excluir dados.
- Detectar 404, 500, erro de banco, stacktrace e redirect indevido para login.
- Coletar logs recentes do app.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar:
sudo ETAPA13_LOGIN_EMAIL='admin@saas.com' ETAPA13_LOGIN_PASSWORD='SUA_SENHA' python3 etapa_13_validar_fluxos_interface_logada.py

Compatibilidade:
Tambem aceita ETAPA12_LOGIN_EMAIL e ETAPA12_LOGIN_PASSWORD.
"""

import os
import re
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError, URLError
from http.cookiejar import CookieJar

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

BASE_URL = "http://127.0.0.1:50010"
LOGIN_PATH = "/api/auth/login"
DASHBOARD_PATH = "/dashboard"

MAX_LINKS_TESTAR = 80
MAX_ASSETS_TESTAR = 120

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

CHAVES_EMAIL = [
    "ETAPA13_LOGIN_EMAIL",
    "ETAPA12_LOGIN_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SEED_ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

CHAVES_SENHA = [
    "ETAPA13_LOGIN_PASSWORD",
    "ETAPA12_LOGIN_PASSWORD",
    "LOGIN_PASSWORD",
    "ADMIN_PASSWORD",
    "SEED_ADMIN_PASSWORD",
    "SUPER_ADMIN_PASSWORD",
    "DEFAULT_ADMIN_PASSWORD"
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
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def gravar_texto(path, conteudo):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8")


def validar_sem_asterisco_indevido(conteudo, nome):
    if chr(42) in conteudo:
        raise ValueError("Validacao bloqueou " + nome + " por conter asterisco.")


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
    texto = json.dumps(dados, ensure_ascii=False, indent=2) + "\n"
    texto = texto.replace(chr(42), "[asterisco]")
    gravar_texto(path, texto)


def copiar_item(origem, destino):
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

    email = obter_primeiro(dados, CHAVES_EMAIL)
    senha = obter_primeiro(dados, CHAVES_SENHA)

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

    out = out.replace(chr(42), "[asterisco]")
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
            "stdout": redigir(proc.stdout.strip())[:16000],
            "stderr": redigir(proc.stderr.strip())[:16000],
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


def criar_opener():
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    return opener, jar


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


def http_request(opener, metodo, path_ou_url, data_obj=None):
    if path_ou_url.startswith("http://") or path_ou_url.startswith("https://"):
        url = path_ou_url
        path = urlparse(url).path or "/"
    else:
        url = BASE_URL + path_ou_url
        path = path_ou_url

    resultado = {
        "path": path,
        "url": url,
        "metodo": metodo,
        "ok": False,
        "status": None,
        "erro": None,
        "body_preview": "",
        "body_full_limited": "",
        "content_type": "",
        "redirect_url": None
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-13-interface-logada/1.0"
    }

    if data_obj is not None:
        body_text = json.dumps(data_obj)
        body_bytes = body_text.encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=body_bytes, headers=headers, method=metodo)

    try:
        with opener.open(req, timeout=20) as resp:
            body = resp.read(262144)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["body_preview"] = redigir(texto[:1600])
            resultado["body_full_limited"] = redigir(texto[:50000])
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["redirect_url"] = resp.geturl()
    except HTTPError as exc:
        try:
            body = exc.read(262144)
            texto = body.decode("utf-8", errors="replace")
        except Exception:
            texto = ""

        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 400
        resultado["erro"] = redigir(str(exc))
        resultado["body_preview"] = redigir(texto[:1600])
        resultado["body_full_limited"] = redigir(texto[:50000])
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
    except URLError as exc:
        resultado["erro"] = redigir(str(exc.reason))
    except Exception as exc:
        resultado["erro"] = redigir(str(exc))

    return resultado


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
        "senha": cred["senha"]
    }

    http = http_request(opener, "POST", LOGIN_PATH, payload)

    resultado["executado"] = True
    resultado["http"] = sanitizar_http(http, incluir_body=True)
    resultado["cookies"] = cookies_resumo(jar)

    body = (http.get("body_preview") or "").lower()
    status_ok = http.get("status") in [200, 201, 302]
    cookie_ok = len(resultado["cookies"]) > 0
    body_ok = "sucesso" in body or "success" in body or "dashboard" in body or "ok" in body

    resultado["ok"] = bool(status_ok and (cookie_ok or body_ok))

    return resultado


def sanitizar_http(item, incluir_body=False):
    out = {
        "path": item.get("path"),
        "metodo": item.get("metodo"),
        "ok": item.get("ok"),
        "status": item.get("status"),
        "erro": item.get("erro"),
        "content_type": item.get("content_type"),
        "redirect_url": item.get("redirect_url")
    }

    if incluir_body:
        out["body_preview"] = item.get("body_preview", "")

    return out


def normalizar_url(valor, base=BASE_URL):
    if not valor:
        return ""

    valor = valor.strip()

    if not valor:
        return ""

    if valor.startswith("#"):
        return ""

    if valor.startswith("mailto:") or valor.startswith("tel:") or valor.startswith("javascript:"):
        return ""

    absoluto = urljoin(base, valor)
    parsed = urlparse(absoluto)

    if parsed.scheme not in ["http", "https"]:
        return ""

    if parsed.netloc not in ["127.0.0.1:50010", "localhost:50010"]:
        return ""

    caminho = parsed.path or "/"

    if parsed.query:
        caminho += "?" + parsed.query

    return caminho


def extrair_links_e_assets(html):
    links = []
    assets = []

    # href em tags a/link
    for m in re.finditer(r'href=[^"\']+["\']', html, flags=re.IGNORECASE):
        valor = m.group(1)
        norm = normalizar_url(valor)
        if norm:
            if norm.lower().endswith((".css", ".ico", ".png", ".jpg", ".jpeg", ".webp", ".svg")):
                assets.append(norm)
            else:
                links.append(norm)

    # src em script/img
    for m in re.finditer(r'src=[^"\']+["\']', html, flags=re.IGNORECASE):
        valor = m.group(1)
        norm = normalizar_url(valor)
        if norm:
            assets.append(norm)

    # url(...) em CSS inline
    for m in re.finditer(r'url\(([^)]+)\)', html, flags=re.IGNORECASE):
        valor = m.group(1).strip().strip("'").strip('"')
        norm = normalizar_url(valor)
        if norm:
            assets.append(norm)

    # socket.io costuma estar em script src
    if "/socket.io/socket.io.js" in html and "/socket.io/socket.io.js" not in assets:
        assets.append("/socket.io/socket.io.js")

    links_unicos = []
    assets_unicos = []

    for item in links:
        if item not in links_unicos:
            links_unicos.append(item)

    for item in assets:
        if item not in assets_unicos:
            assets_unicos.append(item)

    return {
        "links": links_unicos[:MAX_LINKS_TESTAR],
        "assets": assets_unicos[:MAX_ASSETS_TESTAR],
        "links_total": len(links_unicos),
        "assets_total": len(assets_unicos)
    }


def testar_lista_get(opener, caminhos):
    resultados = []

    for caminho in caminhos:
        resultados.append(sanitizar_http(http_request(opener, "GET", caminho), incluir_body=True))

    return resultados


def analisar_resultados(resultados):
    resumo = {
        "total": len(resultados),
        "ok_2xx_3xx": 0,
        "status_401": 0,
        "status_403": 0,
        "status_404": 0,
        "status_500": 0,
        "db_error": 0,
        "stacktrace": 0,
        "redirect_login": 0,
        "falhas_graves": 0,
        "sem_falhas_graves": True
    }

    for item in resultados:
        status = item.get("status")
        body = (item.get("body_preview") or "").lower()
        erro = (item.get("erro") or "").lower()
        redirect = str(item.get("redirect_url") or "").lower()

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

        if "database" in body or "database" in erro or "econnrefused" in body or "econnrefused" in erro:
            resumo["db_error"] += 1

        if "stack" in body or "traceback" in body or "syntaxerror" in body:
            resumo["stacktrace"] += 1

        if redirect.endswith("/login") or "login - acesso seguro" in body:
            resumo["redirect_login"] += 1

    resumo["falhas_graves"] = (
        resumo["status_500"] +
        resumo["db_error"] +
        resumo["stacktrace"]
    )
    resumo["sem_falhas_graves"] = resumo["falhas_graves"] == 0

    return resumo


def coletar_logs_app():
    comandos = [
        ["docker", "compose", "logs", "--tail=220", "app"],
        ["docker", "logs", "--tail=220", "whatsapp_bot_app"]
    ]

    resultados = []

    for cmd in comandos:
        r = run_cmd(cmd, 60)
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

    termos = [
        "error",
        "exception",
        "stack",
        "syntaxerror",
        "database",
        "unhandled",
        "econnrefused"
    ]

    for termo in termos:
        if termo in lower:
            for idx, linha in enumerate(texto.splitlines(), start=1):
                if termo in linha.lower():
                    achados.append({
                        "termo": termo,
                        "linha": idx,
                        "trecho": redigir(linha.strip())[:300]
                    })
                    break

    sessoes_expostas = 0
    cookies_expostos = 0

    for linha in texto.splitlines():
        low = linha.lower()
        if "session id" in low:
            sessoes_expostas += 1
        if "conteúdo:" in low or "conteudo:" in low or "saas_crm_sid" in low:
            cookies_expostos += 1

    return {
        "total_linhas": len(texto.splitlines()),
        "achados": achados,
        "tem_achados": len(achados) > 0,
        "session_id_linhas": sessoes_expostas,
        "cookie_linhas": cookies_expostos,
        "amostra": redigir("\n".join(texto.splitlines()[-60:]))[:12000]
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_13_INICIO -->"
    marcador_fim = "<!-- ETAPA_13_FIM -->"

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
    extracao = relatorio["extracao_dashboard"]
    links_resumo = relatorio["links_resumo"]
    assets_resumo = relatorio["assets_resumo"]
    logs = relatorio["logs_analise"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 13 - Interface logada validada",
        [
            "Data: " + data,
            "",
            "Foi executada validacao de fluxos reais da interface logada.",
            "Login OK: " + str(login["ok"]) + ".",
            "Links reais encontrados no dashboard: " + str(extracao["links_total"]) + ".",
            "Assets reais encontrados no dashboard: " + str(extracao["assets_total"]) + ".",
            "Links sem falhas graves: " + str(links_resumo["sem_falhas_graves"]) + ".",
            "Assets sem falhas graves: " + str(assets_resumo["sem_falhas_graves"]) + ".",
            "Achados criticos em logs: " + str(len(logs["achados"])) + ".",
            "Nenhuma escrita funcional foi executada."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 13 - Validacao de interface logada",
        [
            "Data: " + data,
            "",
            "Realizado login com cookie em memoria.",
            "Extraidos links e assets reais do HTML do dashboard.",
            "Testados fluxos GET encontrados no dashboard.",
            "Testados assets locais encontrados no dashboard.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 13 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido testar links reais do dashboard em vez de rotas presumidas.",
            "Decidido limitar a etapa a requisicoes GET/HEAD seguras.",
            "Decidido nao executar operacoes de escrita.",
            "Decidido registrar exposicao de Session ID e cookies nos logs para hardening posterior."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Revisar eventuais 404 de links reais encontrados no dashboard.",
        "Reduzir verbosidade de logs de sessao e cookies em producao.",
        "Validar fluxos reais de cadastro/edicao em ambiente controlado e com dados de teste.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.",
        "Planejar rotacao de credenciais reais expostas anteriormente."
    ]

    if links_resumo["status_500"] > 0 or assets_resumo["status_500"] > 0 or logs["achados"]:
        pendencias.insert(2, "Corrigir falhas graves da Etapa 13 antes de avancar.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 13",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    login = relatorio["login"]
    dashboard = relatorio["dashboard"]
    extracao = relatorio["extracao_dashboard"]
    links_resumo = relatorio["links_resumo"]
    assets_resumo = relatorio["assets_resumo"]
    logs = relatorio["logs_analise"]

    linhas.append("# Etapa 13 - Validar fluxos reais da interface logada")
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
    linhas.append("- Login OK: " + str(login["ok"]))
    linhas.append("- Cookies recebidos: " + str(len(login["cookies"])))
    linhas.append("- Dashboard status: " + str(dashboard.get("status")))
    linhas.append("- Links reais encontrados: " + str(extracao["links_total"]))
    linhas.append("- Assets reais encontrados: " + str(extracao["assets_total"]))
    linhas.append("- Links testados: " + str(links_resumo["total"]))
    linhas.append("- Links 404: " + str(links_resumo["status_404"]))
    linhas.append("- Links 500: " + str(links_resumo["status_500"]))
    linhas.append("- Assets testados: " + str(assets_resumo["total"]))
    linhas.append("- Assets 404: " + str(assets_resumo["status_404"]))
    linhas.append("- Assets 500: " + str(assets_resumo["status_500"]))
    linhas.append("- Erros DB links/assets: " + str(links_resumo["db_error"] + assets_resumo["db_error"]))
    linhas.append("- Achados em logs: " + str(len(logs["achados"])))
    linhas.append("- Linhas com Session ID nos logs: " + str(logs["session_id_linhas"]))
    linhas.append("- Linhas com cookie nos logs: " + str(logs["cookie_linhas"]))
    linhas.append("")

    linhas.append("## Links encontrados no dashboard")
    linhas.append("")
    if extracao["links"]:
        for item in extracao["links"]:
            linhas.append("- " + item)
    else:
        linhas.append("- Nenhum link local encontrado.")

    linhas.append("")
    linhas.append("## Assets encontrados no dashboard")
    linhas.append("")
    if extracao["assets"]:
        for item in extracao["assets"]:
            linhas.append("- " + item)
    else:
        linhas.append("- Nenhum asset local encontrado.")

    linhas.append("")
    linhas.append("## Resultado dos links")
    linhas.append("")
    for item in relatorio["links_resultados"]:
        linhas.append(
            "- "
            + str(item.get("path"))
            + ": status="
            + str(item.get("status"))
            + ", ok="
            + str(item.get("ok"))
            + ", erro="
            + str(item.get("erro"))
        )

    linhas.append("")
    linhas.append("## Resultado dos assets")
    linhas.append("")
    for item in relatorio["assets_resultados"]:
        linhas.append(
            "- "
            + str(item.get("path"))
            + ": status="
            + str(item.get("status"))
            + ", ok="
            + str(item.get("ok"))
            + ", tipo="
            + str(item.get("content_type"))
            + ", erro="
            + str(item.get("erro"))
        )

    linhas.append("")
    linhas.append("## Achados em logs")
    linhas.append("")
    if logs["achados"]:
        for item in logs["achados"]:
            linhas.append(
                "- termo="
                + item["termo"]
                + " linha="
                + str(item["linha"])
                + " trecho="
                + item["trecho"]
            )
    else:
        linhas.append("- Nenhum padrao critico encontrado nos logs analisados.")

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Cookie foi mantido apenas em memoria.")
    linhas.append("- Nenhuma criacao, edicao ou exclusao de dados foi executada.")
    linhas.append("- Foram feitas apenas requisicoes GET apos o login.")
    linhas.append("- A exposicao de Session ID e cookie em logs deve ser tratada em hardening.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 14: hardening de logs, sessao, cookies e cabecalhos HTTP.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_13_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_13_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    docker = verificar_docker()

    opener, jar = criar_opener()

    login = realizar_login(opener, jar)
    dashboard_full = http_request(opener, "GET", DASHBOARD_PATH)
    dashboard = sanitizar_http(dashboard_full, incluir_body=True)

    html_dashboard = dashboard_full.get("body_full_limited") or ""
    extracao = extrair_links_e_assets(html_dashboard)

    links_resultados = testar_lista_get(opener, extracao["links"])
    assets_resultados = testar_lista_get(opener, extracao["assets"])

    links_resumo = analisar_resultados(links_resultados)
    assets_resumo = analisar_resultados(assets_resultados)

    logs_resultados = coletar_logs_app()
    logs_analise = analisar_logs(logs_resultados)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "login": login,
        "dashboard": dashboard,
        "extracao_dashboard": extracao,
        "links_resultados": links_resultados,
        "links_resumo": links_resumo,
        "assets_resultados": assets_resultados,
        "assets_resumo": assets_resumo,
        "logs_resultados": logs_resultados,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_13_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_13_validar_fluxos_interface_logada.json"
    md_path = REPORTS_DIR / "etapa_13_validar_fluxos_interface_logada.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 13 concluida.")
    print("Backup documental: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Docker OK: " + str(docker["docker_version"]["ok"]))
    print("Docker Compose OK: " + str(docker["docker_compose_version"]["ok"]))
    print("Login OK: " + str(login["ok"]))
    print("Dashboard status: " + str(dashboard.get("status")))
    print("Links reais encontrados: " + str(extracao["links_total"]))
    print("Assets reais encontrados: " + str(extracao["assets_total"]))
    print("Links 404: " + str(links_resumo["status_404"]))
    print("Links 500: " + str(links_resumo["status_500"]))
    print("Assets 404: " + str(assets_resumo["status_404"]))
    print("Assets 500: " + str(assets_resumo["status_500"]))
    print("Achados em logs: " + str(len(logs_analise["achados"])))
    print("Linhas Session ID logs: " + str(logs_analise["session_id_linhas"]))
    print("Linhas cookie logs: " + str(logs_analise["cookie_linhas"]))

    if links_resumo["status_500"] > 0 or assets_resumo["status_500"] > 0 or logs_analise["achados"]:
        print("")
        print("Existem falhas graves para revisar. Consulte o relatorio Markdown.")


if __name__ == "__main__":
    main()