#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 15.2 - Auditar CORS, cookie e headers sem alterar arquivos

Objetivo:
- Nao alterar codigo da aplicacao.
- Nao alterar banco.
- Nao reiniciar app.
- Rodar node --check server.js.
- Auditar server.js estaticamente.
- Validar headers em runtime:
  - X-Powered-By
  - X-Content-Type-Options
  - X-Frame-Options
  - Referrer-Policy
  - Permissions-Policy
  - Cross-Origin-Opener-Policy
  - Access-Control-Allow-Origin
  - Access-Control-Allow-Credentials
  - Set-Cookie
- Testar sem Origin, Origin local permitido e Origin externo nao permitido.
- Validar login e dashboard.
- Validar cookie recebido.
- Coletar logs novos e confirmar ausencia de Session ID, cookie e email.
- Atualizar documentacao obrigatoria.
- Gerar relatorios JSON e Markdown em reports.

Como executar:
sudo ETAPA15_2_LOGIN_EMAIL='admin@saas.com' ETAPA15_2_LOGIN_PASSWORD='123456' python3 etapa_15_2_auditar_cors_cookie_headers_sem_alterar.py
"""

import os
import json
import hashlib
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError, URLError
from http.cookiejar import CookieJar

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"

SERVER_JS = ROOT / "server.js"
BASE_URL = "http://127.0.0.1:50010"
LOGIN_PATH = "/api/auth/login"
DASHBOARD_PATH = "/dashboard"

DOCS_OBRIGATORIOS = [
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
    "ETAPA15_2_LOGIN_EMAIL",
    "ETAPA15_1_LOGIN_EMAIL",
    "ETAPA15_LOGIN_EMAIL",
    "ETAPA14_2_LOGIN_EMAIL",
    "ETAPA14_1_LOGIN_EMAIL",
    "ETAPA14_LOGIN_EMAIL",
    "ETAPA13_LOGIN_EMAIL",
    "ETAPA12_LOGIN_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SEED_ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

CHAVES_SENHA = [
    "ETAPA15_2_LOGIN_PASSWORD",
    "ETAPA15_1_LOGIN_PASSWORD",
    "ETAPA15_LOGIN_PASSWORD",
    "ETAPA14_2_LOGIN_PASSWORD",
    "ETAPA14_1_LOGIN_PASSWORD",
    "ETAPA14_LOGIN_PASSWORD",
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


def agora_logs_since():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def rel(path):
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)


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
            "stdout": redigir(proc.stdout.strip())[:20000],
            "stderr": redigir(proc.stderr.strip())[:20000],
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


def node_check_server():
    if not SERVER_JS.exists():
        return {
            "ok": False,
            "stderr": "server.js ausente",
            "stdout": "",
            "returncode": None
        }

    return run_cmd(["node", "--check", "server.js"], 40)


def auditar_server_js():
    texto = ler_texto(SERVER_JS)
    estrela = chr(42)

    resultado = {
        "existe": SERVER_JS.exists(),
        "sha256": sha256_arquivo(SERVER_JS),
        "cors_require": False,
        "cors_app_use": False,
        "access_control_origin_star": False,
        "access_control_credentials_true": False,
        "etapa15_cors": False,
        "x_powered_disable": False,
        "headers_etapa14": False,
        "headers_etapa15": False,
        "cookie_http_only": False,
        "cookie_same_site": False,
        "cookie_secure": False,
        "cookie_name_saas": False,
        "cookie_name_connect": False,
        "console_session_id": 0,
        "console_cookie": 0,
        "console_email": 0
    }

    if texto is None:
        resultado["erro"] = "server.js ausente ou ilegivel"
        return resultado

    lower = texto.lower()

    resultado["cors_require"] = "require('cors')" in texto or 'require("cors")' in texto
    resultado["cors_app_use"] = "app.use(cors" in texto
    resultado["access_control_origin_star"] = (
        "access-control-allow-origin" in lower and estrela in texto
    )
    resultado["access_control_credentials_true"] = (
        "access-control-allow-credentials" in lower and "true" in lower
    )
    resultado["etapa15_cors"] = "ETAPA15_CORS_SEGURO" in texto
    resultado["x_powered_disable"] = "app.disable('x-powered-by')" in texto or 'app.disable("x-powered-by")' in texto
    resultado["headers_etapa14"] = "ETAPA14_SECURITY_HEADERS" in texto
    resultado["headers_etapa15"] = "ETAPA15_SECURITY_HEADERS" in texto
    resultado["cookie_http_only"] = "httponly" in lower
    resultado["cookie_same_site"] = "samesite" in lower
    resultado["cookie_secure"] = "secure" in lower
    resultado["cookie_name_saas"] = "saas_crm_sid" in texto
    resultado["cookie_name_connect"] = "connect.sid" in texto

    for linha in texto.splitlines():
        low = linha.lower()
        if "console.log" not in low:
            continue

        if "session id" in low:
            resultado["console_session_id"] += 1

        if "saas_crm_sid" in low or "header cookie" in low or "conteúdo:" in low or "conteudo:" in low:
            resultado["console_cookie"] += 1

        if "user.email" in low or "req.session.user.email" in low:
            resultado["console_email"] += 1

    return resultado


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
            "secure": cookie.secure,
            "expires": cookie.expires,
            "discard": cookie.discard,
            "httponly_detectado": bool(
                cookie.has_nonstandard_attr("HttpOnly") or
                cookie.has_nonstandard_attr("httponly")
            )
        })

    return itens


def http_request(opener, metodo, path, data_obj=None, origin=None, timeout=15):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "metodo": metodo,
        "ok": False,
        "status": None,
        "erro": None,
        "body_preview": "",
        "content_type": "",
        "redirect_url": None,
        "headers": {}
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-15-2-auditoria/1.0"
    }

    if origin:
        headers["Origin"] = origin

    if data_obj is not None:
        body_text = json.dumps(data_obj)
        body_bytes = body_text.encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=body_bytes, headers=headers, method=metodo)

    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(8192)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["body_preview"] = redigir(texto[:1200])
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["redirect_url"] = resp.geturl()
            resultado["headers"] = dict(resp.headers.items())
    except HTTPError as exc:
        try:
            body = exc.read(8192)
            texto = body.decode("utf-8", errors="replace")
        except Exception:
            texto = ""

        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 400
        resultado["erro"] = redigir(str(exc))
        resultado["body_preview"] = redigir(texto[:1200])
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
        resultado["headers"] = dict(exc.headers.items()) if exc.headers else {}
    except URLError as exc:
        resultado["erro"] = redigir(str(exc.reason))
    except Exception as exc:
        resultado["erro"] = redigir(str(exc))

    return resultado


def headers_lower(item):
    lower = {}
    headers = item.get("headers") or {}
    for k, v in headers.items():
        lower[str(k).lower()] = v
    return lower


def extrair_headers_interesse(item):
    h = headers_lower(item)

    return {
        "status": item.get("status"),
        "erro": item.get("erro"),
        "x_powered_by": h.get("x-powered-by"),
        "x_content_type_options": h.get("x-content-type-options"),
        "x_frame_options": h.get("x-frame-options"),
        "referrer_policy": h.get("referrer-policy"),
        "permissions_policy": h.get("permissions-policy"),
        "cross_origin_opener_policy": h.get("cross-origin-opener-policy"),
        "access_control_allow_origin": h.get("access-control-allow-origin"),
        "access_control_allow_credentials": h.get("access-control-allow-credentials"),
        "vary": h.get("vary"),
        "set_cookie": redigir(h.get("set-cookie"))
    }


def validar_headers_runtime():
    opener, jar = criar_opener()

    normal = http_request(opener, "GET", "/")
    origem_local = http_request(opener, "GET", "/", origin="http://127.0.0.1:50010")
    origem_evil = http_request(opener, "GET", "/", origin="http://evil.example")

    normal_h = extrair_headers_interesse(normal)
    local_h = extrair_headers_interesse(origem_local)
    evil_h = extrair_headers_interesse(origem_evil)

    estrela = chr(42)

    ok_sem_x_powered = normal_h["x_powered_by"] is None
    ok_headers_basicos = bool(
        normal_h["x_content_type_options"] and
        normal_h["x_frame_options"] and
        normal_h["referrer_policy"]
    )
    ok_cors_sem_estrela = (
        normal_h["access_control_allow_origin"] != estrela and
        local_h["access_control_allow_origin"] != estrela and
        evil_h["access_control_allow_origin"] != estrela
    )
    ok_evil_bloqueado = evil_h["access_control_allow_origin"] is None

    return {
        "sem_origin": normal_h,
        "origin_local": local_h,
        "origin_evil": evil_h,
        "ok_sem_x_powered_by": ok_sem_x_powered,
        "ok_headers_basicos": ok_headers_basicos,
        "ok_cors_sem_estrela": ok_cors_sem_estrela,
        "ok_origin_evil_bloqueado": ok_evil_bloqueado
    }


def validar_login_dashboard():
    cred = obter_credenciais()

    resultado = {
        "executado": False,
        "email_configurado": cred["email_configurado"],
        "senha_configurada": cred["senha_configurada"],
        "home_ok": False,
        "login_ok": False,
        "dashboard_ok": False,
        "cookies": [],
        "home": None,
        "login": None,
        "dashboard": None
    }

    opener, jar = criar_opener()

    home = http_request(opener, "GET", "/")
    resultado["home"] = {
        "status": home.get("status"),
        "ok": home.get("ok"),
        "erro": home.get("erro"),
        "content_type": home.get("content_type")
    }
    resultado["home_ok"] = home.get("status") in [200, 302, 404]

    if not cred["email_configurado"] or not cred["senha_configurada"]:
        resultado["motivo"] = "Credenciais nao configuradas"
        return resultado

    payload = {
        "email": cred["email"],
        "senha": cred["senha"]
    }

    login = http_request(opener, "POST", LOGIN_PATH, payload)
    resultado["executado"] = True
    resultado["login"] = {
        "status": login.get("status"),
        "ok": login.get("ok"),
        "erro": login.get("erro"),
        "content_type": login.get("content_type"),
        "headers": extrair_headers_interesse(login),
        "body_preview": login.get("body_preview")
    }
    resultado["cookies"] = cookies_resumo(jar)

    body = (login.get("body_preview") or "").lower()
    status_ok = login.get("status") in [200, 201, 302]
    cookie_ok = len(resultado["cookies"]) > 0
    body_ok = "sucesso" in body or "success" in body or "dashboard" in body or "ok" in body

    resultado["login_ok"] = bool(status_ok and (cookie_ok or body_ok))

    dashboard = http_request(opener, "GET", DASHBOARD_PATH)
    resultado["dashboard"] = {
        "status": dashboard.get("status"),
        "ok": dashboard.get("ok"),
        "erro": dashboard.get("erro"),
        "content_type": dashboard.get("content_type"),
        "headers": extrair_headers_interesse(dashboard)
    }
    resultado["dashboard_ok"] = bool(
        dashboard.get("status") == 200 and
        "crm enterprise" in (dashboard.get("body_preview") or "").lower()
    )

    return resultado


def coletar_logs_novos(since):
    r = run_cmd(["docker", "compose", "logs", "--since", since, "app"], 80)

    if not r.get("ok") or not (r.get("stdout") or r.get("stderr")):
        r2 = run_cmd(["docker", "logs", "--since", since, "whatsapp_bot_app"], 80)
        return {
            "principal": r,
            "fallback": r2,
            "texto": (r2.get("stdout") or "") + "\n" + (r2.get("stderr") or "")
        }

    return {
        "principal": r,
        "fallback": None,
        "texto": (r.get("stdout") or "") + "\n" + (r.get("stderr") or "")
    }


def parece_email_token(token):
    if "@" not in token:
        return False
    if "." not in token:
        return False
    if len(token) < 5:
        return False
    return True


def analisar_logs_texto(texto):
    session_id = 0
    cookie = 0
    email = 0
    achados = []

    for idx, linha in enumerate(str(texto or "").splitlines(), start=1):
        low = linha.lower()

        if "session id" in low:
            session_id += 1

        if "saas_crm_sid" in low or "connect.sid" in low or "header cookie" in low or "conteúdo:" in low or "conteudo:" in low:
            cookie += 1

        tokens = linha.replace("(", " ").replace(")", " ").replace(",", " ").split()
        for token in tokens:
            if parece_email_token(token):
                email += 1
                break

        if "error" in low or "exception" in low or "syntaxerror" in low or "database" in low or "econnrefused" in low:
            achados.append({
                "linha": idx,
                "trecho": redigir(linha.strip())[:300]
            })

    return {
        "total_linhas": len(str(texto or "").splitlines()),
        "linhas_session_id": session_id,
        "linhas_cookie": cookie,
        "linhas_email": email,
        "achados": achados,
        "amostra": redigir("\n".join(str(texto or "").splitlines()[-80:]))[:16000]
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_15_2_INICIO -->"
    marcador_fim = "<!-- ETAPA_15_2_FIM -->"

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
    node = relatorio["node_check"]
    headers = relatorio["headers_runtime"]
    validacao = relatorio["validacao_login_dashboard"]
    logs = relatorio["logs_analise"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 15.2 - Auditoria sem alteracao de CORS, cookie e headers",
        [
            "Data: " + data,
            "",
            "Foi executada auditoria sem alteracao de codigo, banco ou container.",
            "Node check OK: " + str(node["ok"]) + ".",
            "Home OK: " + str(validacao["home_ok"]) + ".",
            "Login OK: " + str(validacao["login_ok"]) + ".",
            "Dashboard OK: " + str(validacao["dashboard_ok"]) + ".",
            "Headers basicos OK: " + str(headers["ok_headers_basicos"]) + ".",
            "Sem X-Powered-By: " + str(headers["ok_sem_x_powered_by"]) + ".",
            "CORS sem estrela: " + str(headers["ok_cors_sem_estrela"]) + ".",
            "Origin externo bloqueado: " + str(headers["ok_origin_evil_bloqueado"]) + ".",
            "Logs novos com Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs novos com cookie: " + str(logs["linhas_cookie"]) + ".",
            "Logs novos com email: " + str(logs["linhas_email"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 15.2 - Auditoria de seguranca HTTP sem alteracao",
        [
            "Data: " + data,
            "",
            "Auditados CORS, cookies e headers em runtime.",
            "Executado node --check em server.js.",
            "Validado login e dashboard.",
            "Coletados logs novos para verificar sanitizacao.",
            "Nenhum arquivo de codigo foi alterado pela auditoria."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 15.2 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido auditar antes de nova alteracao em CORS e headers.",
            "Decidido nao reiniciar app nesta etapa.",
            "Decidido usar teste com Origin local e Origin externo nao permitido.",
            "Decidido manter esta etapa como baseline de seguranca HTTP."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Se algum header ou CORS ainda estiver inadequado, propor correcao pequena e especifica.",
        "Definir CORS_ORIGINS no ambiente final com dominio real HTTPS.",
        "Definir COOKIE_SECURE=true apenas com HTTPS valido.",
        "Validar ambiente externo com HTTPS.",
        "Planejar rate limit e politica CSP dedicada."
    ]

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 15.2",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    node = relatorio["node_check"]
    static = relatorio["auditoria_static_server"]
    headers = relatorio["headers_runtime"]
    validacao = relatorio["validacao_login_dashboard"]
    logs = relatorio["logs_analise"]

    linhas.append("# Etapa 15.2 - Auditar CORS, cookie e headers sem alterar")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Node check OK: " + str(node["ok"]))
    linhas.append("- Home OK: " + str(validacao["home_ok"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("- Headers basicos OK: " + str(headers["ok_headers_basicos"]))
    linhas.append("- Sem X-Powered-By: " + str(headers["ok_sem_x_powered_by"]))
    linhas.append("- CORS sem origem aberta: " + str(headers["ok_cors_sem_estrela"]))
    linhas.append("- Origin externo bloqueado: " + str(headers["ok_origin_evil_bloqueado"]))
    linhas.append("- Logs novos Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos email: " + str(logs["linhas_email"]))
    linhas.append("- Achados criticos logs: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Node check")
    linhas.append("")
    linhas.append("- OK: " + str(node["ok"]))
    if node.get("stderr"):
        linhas.append("- stderr: " + node["stderr"][:1000])

    linhas.append("")
    linhas.append("## Auditoria estatica server.js")
    linhas.append("")
    for chave in sorted(static.keys()):
        if chave != "erro":
            linhas.append("- " + chave + ": " + str(static[chave]))
    if static.get("erro"):
        linhas.append("- erro: " + static["erro"])

    linhas.append("")
    linhas.append("## Headers runtime - sem Origin")
    linhas.append("")
    for chave, valor in headers["sem_origin"].items():
        linhas.append("- " + chave + ": " + str(valor))

    linhas.append("")
    linhas.append("## Headers runtime - Origin local")
    linhas.append("")
    for chave, valor in headers["origin_local"].items():
        linhas.append("- " + chave + ": " + str(valor))

    linhas.append("")
    linhas.append("## Headers runtime - Origin externo")
    linhas.append("")
    for chave, valor in headers["origin_evil"].items():
        linhas.append("- " + chave + ": " + str(valor))

    linhas.append("")
    linhas.append("## Validacao login e dashboard")
    linhas.append("")
    linhas.append("- Executada: " + str(validacao["executado"]))
    linhas.append("- Email configurado: " + str(validacao["email_configurado"]))
    linhas.append("- Senha configurada: " + str(validacao["senha_configurada"]))
    linhas.append("- Home OK: " + str(validacao["home_ok"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("- Cookies recebidos: " + str(len(validacao["cookies"])))
    for cookie in validacao["cookies"]:
        linhas.append(
            "- Cookie: name="
            + str(cookie["name"])
            + ", secure="
            + str(cookie["secure"])
            + ", httponly_detectado="
            + str(cookie["httponly_detectado"])
        )

    linhas.append("")
    linhas.append("## Logs novos")
    linhas.append("")
    linhas.append("- Linhas analisadas: " + str(logs["total_linhas"]))
    linhas.append("- Linhas Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Linhas cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Linhas email: " + str(logs["linhas_email"]))
    linhas.append("- Achados: " + str(len(logs["achados"])))

    linhas.append("")
    linhas.append("## Amostra logs")
    linhas.append("")
    amostra = logs.get("amostra") or ""
    if amostra:
        for linha in amostra.splitlines()[-60:]:
            linhas.append("- " + linha[:240])
    else:
        linhas.append("- Sem logs novos.")

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhum codigo de aplicacao foi alterado.")
    linhas.append("- Nenhum banco foi alterado.")
    linhas.append("- Nenhum container foi reiniciado.")
    linhas.append("- Esta etapa serve como baseline para proxima correcao pequena, se necessaria.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Se necessario, aplicar correcao minima apenas no ponto que a auditoria indicar.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_15_2_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    node = node_check_server()
    auditoria_static = auditar_server_js()

    since = agora_logs_since()
    headers = validar_headers_runtime()
    validacao = validar_login_dashboard()
    time.sleep(2)

    logs_coleta = coletar_logs_novos(since)
    logs_analise = analisar_logs_texto(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "manifesto_antes": rel(manifesto_antes_path),
        "node_check": node,
        "auditoria_static_server": auditoria_static,
        "headers_runtime": headers,
        "logs_since": since,
        "validacao_login_dashboard": validacao,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_15_2_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_15_2_auditar_cors_cookie_headers_sem_alterar.json"
    md_path = REPORTS_DIR / "etapa_15_2_auditar_cors_cookie_headers_sem_alterar.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 15.2 concluida.")
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Node check OK: " + str(node["ok"]))
    print("Home OK: " + str(validacao["home_ok"]))
    print("Login OK: " + str(validacao["login_ok"]))
    print("Dashboard OK: " + str(validacao["dashboard_ok"]))
    print("Headers basicos OK: " + str(headers["ok_headers_basicos"]))
    print("Sem X-Powered-By: " + str(headers["ok_sem_x_powered_by"]))
    print("CORS sem origem aberta: " + str(headers["ok_cors_sem_estrela"]))
    print("Origin externo bloqueado: " + str(headers["ok_origin_evil_bloqueado"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not node["ok"]:
        print("")
        print("Aviso: node --check falhou. Nao aplicar novas mudancas antes de corrigir.")

    if not headers["ok_headers_basicos"] or not headers["ok_cors_sem_estrela"]:
        print("")
        print("Aviso: auditoria encontrou pontos pendentes em headers/CORS. Consulte o relatorio.")


if __name__ == "__main__":
    main()