#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 15 - Hardening de CORS, cookie de sessao e headers finais

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Auditar server.js.
- Remover CORS permissivo com origem aberta quando localizado.
- Inserir middleware CORS seguro controlado por CORS_ORIGINS ou APP_URL.
- Garantir headers HTTP basicos.
- Ajustar cookie de sessao com httpOnly, sameSite e secure condicionado.
- Rodar node --check em server.js.
- Reiniciar app somente se ETAPA15_RESTART_APP=true.
- Validar login, dashboard e headers HTTP quando credenciais forem fornecidas.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar sem restart:
sudo ETAPA15_LOGIN_EMAIL='admin@saas.com' ETAPA15_LOGIN_PASSWORD='123456' python3 etapa_15_hardening_cors_cookie_headers.py

Como executar com restart:
sudo ETAPA15_RESTART_APP=true ETAPA15_LOGIN_EMAIL='admin@saas.com' ETAPA15_LOGIN_PASSWORD='123456' python3 etapa_15_hardening_cors_cookie_headers.py
"""

import os
import re
import json
import shutil
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
BACKUPS_DIR = ROOT / "backups"

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

ARQUIVOS_BACKUP_DIRETO = [
    "server.js",
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


def auditar_server_js():
    texto = ler_texto(SERVER_JS)
    estrela = chr(42)

    resultado = {
        "existe": SERVER_JS.exists(),
        "cors_require": False,
        "cors_app_use": False,
        "access_control_origin_star": False,
        "access_control_credentials_true": False,
        "etapa15_cors": False,
        "x_powered_disable": False,
        "headers_etapa14": False,
        "headers_etapa15": False,
        "session_cookie_block": False,
        "cookie_http_only": False,
        "cookie_same_site": False,
        "cookie_secure": False,
        "cookie_name_saas": False,
        "cookie_name_connect": False
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
    resultado["session_cookie_block"] = "cookie:" in lower and "express-session" in lower
    resultado["cookie_http_only"] = "httponly" in lower
    resultado["cookie_same_site"] = "samesite" in lower
    resultado["cookie_secure"] = "secure" in lower
    resultado["cookie_name_saas"] = "saas_crm_sid" in texto
    resultado["cookie_name_connect"] = "connect.sid" in texto

    return resultado


def encontrar_fim_linha(texto, pos):
    idx = texto.find("\n", pos)
    if idx < 0:
        return len(texto)
    return idx + 1


def remover_cors_permissivo(texto, alteracoes):
    estrela = chr(42)
    original = texto

    padroes = [
        r"app\.use\(\s*cors\s*\(\s*\)\s*\)\s*;?",
        r"app\.use\(\s*cors\s*\(\s*\{\s*origin\s*:\s*['\"]" + re.escape(estrela) + r"['\"][\s\S]*?\}\s*\)\s*\)\s*;?"
    ]

    for padrao in padroes:
        texto, total = re.subn(
            padrao,
            "// ETAPA15: CORS permissivo removido",
            texto,
            flags=re.MULTILINE
        )
        if total > 0:
            alteracoes.append("Removido CORS permissivo: " + str(total))

    linhas = []
    removidas = 0

    for linha in texto.splitlines():
        low = linha.lower()

        if "access-control-allow-origin" in low and estrela in linha:
            linhas.append("// ETAPA15: header Access-Control-Allow-Origin aberto removido")
            removidas += 1
            continue

        if "access-control-allow-credentials" in low and "true" in low:
            linhas.append("// ETAPA15: header credentials antigo removido")
            removidas += 1
            continue

        linhas.append(linha)

    texto = "\n".join(linhas)
    if original.endswith("\n"):
        texto += "\n"

    if removidas:
        alteracoes.append("Removidos headers CORS manuais permissivos: " + str(removidas))

    return texto


def localizar_pos_app(texto):
    candidatos = [
        "const app = express();",
        "const app = require('express')();",
        'const app = require("express")();'
    ]

    for candidato in candidatos:
        pos = texto.find(candidato)
        if pos >= 0:
            return pos + len(candidato)

    return -1


def garantir_x_powered(texto, alteracoes):
    if "app.disable('x-powered-by')" in texto or 'app.disable("x-powered-by")' in texto:
        return texto

    pos = localizar_pos_app(texto)
    if pos < 0:
        alteracoes.append("Nao foi possivel inserir app.disable x-powered-by")
        return texto

    texto = texto[:pos] + "\napp.disable('x-powered-by');" + texto[pos:]
    alteracoes.append("Adicionado app.disable x-powered-by")
    return texto


def bloco_cors_seguro():
    linhas = []
    linhas.append("")
    linhas.append("// ETAPA15_CORS_SEGURO_INICIO")
    linhas.append("const etapa15Origins = (process.env.CORS_ORIGINS || process.env.APP_URL || '')")
    linhas.append("    .split(',')")
    linhas.append("    .map((item) => item.trim())")
    linhas.append("    .filter(Boolean);")
    linhas.append("")
    linhas.append("const etapa15DevOrigins = [")
    linhas.append("    'http://127.0.0.1:50010',")
    linhas.append("    'http://localhost:50010'")
    linhas.append("];")
    linhas.append("")
    linhas.append("app.use((req, res, next) => {")
    linhas.append("    const origin = req.headers.origin;")
    linhas.append("    const permitidas = etapa15Origins.length > 0 ? etapa15Origins : etapa15DevOrigins;")
    linhas.append("    if (origin && permitidas.includes(origin)) {")
    linhas.append("        res.setHeader('Access-Control-Allow-Origin', origin);")
    linhas.append("        res.setHeader('Vary', 'Origin');")
    linhas.append("        res.setHeader('Access-Control-Allow-Credentials', 'true');")
    linhas.append("        res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS');")
    linhas.append("        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');")
    linhas.append("    }")
    linhas.append("    if (req.method === 'OPTIONS') {")
    linhas.append("        return res.sendStatus(204);")
    linhas.append("    }")
    linhas.append("    next();")
    linhas.append("});")
    linhas.append("// ETAPA15_CORS_SEGURO_FIM")
    linhas.append("")
    return "\n".join(linhas)


def adicionar_cors_seguro(texto, alteracoes):
    if "ETAPA15_CORS_SEGURO" in texto:
        return texto

    pos = texto.find("app.disable('x-powered-by');")
    if pos >= 0:
        fim = pos + len("app.disable('x-powered-by');")
        texto = texto[:fim] + bloco_cors_seguro() + texto[fim:]
        alteracoes.append("Adicionado middleware CORS seguro")
        return texto

    pos = localizar_pos_app(texto)
    if pos >= 0:
        texto = texto[:pos] + bloco_cors_seguro() + texto[pos:]
        alteracoes.append("Adicionado middleware CORS seguro")
        return texto

    alteracoes.append("Nao foi possivel inserir middleware CORS seguro")
    return texto


def bloco_headers_finais():
    linhas = []
    linhas.append("")
    linhas.append("// ETAPA15_SECURITY_HEADERS_INICIO")
    linhas.append("app.use((req, res, next) => {")
    linhas.append("    res.setHeader('X-Content-Type-Options', 'nosniff');")
    linhas.append("    res.setHeader('X-Frame-Options', 'SAMEORIGIN');")
    linhas.append("    res.setHeader('Referrer-Policy', 'no-referrer');")
    linhas.append("    res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');")
    linhas.append("    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');")
    linhas.append("    next();")
    linhas.append("});")
    linhas.append("// ETAPA15_SECURITY_HEADERS_FIM")
    linhas.append("")
    return "\n".join(linhas)


def adicionar_headers_finais(texto, alteracoes):
    if "ETAPA15_SECURITY_HEADERS" in texto:
        return texto

    pos = texto.find("// ETAPA15_CORS_SEGURO_FIM")
    if pos >= 0:
        fim = texto.find("\n", pos)
        if fim < 0:
            fim = pos + len("// ETAPA15_CORS_SEGURO_FIM")
        texto = texto[:fim] + bloco_headers_finais() + texto[fim:]
        alteracoes.append("Adicionados headers finais de seguranca")
        return texto

    pos = localizar_pos_app(texto)
    if pos >= 0:
        texto = texto[:pos] + bloco_headers_finais() + texto[pos:]
        alteracoes.append("Adicionados headers finais de seguranca")
        return texto

    alteracoes.append("Nao foi possivel inserir headers finais")
    return texto


def achar_bloco_cookie(texto):
    idx = texto.find("cookie:")
    if idx < 0:
        return None

    chave_abre = texto.find("{", idx)
    if chave_abre < 0:
        return None

    nivel = 0
    for i in range(chave_abre, len(texto)):
        ch = texto[i]
        if ch == "{":
            nivel += 1
        elif ch == "}":
            nivel -= 1
            if nivel == 0:
                return (idx, chave_abre, i)

    return None


def atualizar_propriedade_cookie(bloco, nome, valor):
    padrao = re.compile(r"(\b" + re.escape(nome) + r"\s*:\s*)([^,\n}]+)")
    if padrao.search(bloco):
        return padrao.sub(r"\1" + valor, bloco, count=1)

    pos = bloco.rfind("}")
    if pos < 0:
        return bloco

    antes = bloco[:pos].rstrip()
    depois = bloco[pos:]
    if antes.endswith("{"):
        insercao = "\n        " + nome + ": " + valor + "\n"
    else:
        insercao = ",\n        " + nome + ": " + valor + "\n"

    return antes + insercao + depois


def ajustar_cookie_sessao(texto, alteracoes):
    bloco_info = achar_bloco_cookie(texto)

    if bloco_info is None:
        alteracoes.append("Bloco cookie da sessao nao localizado automaticamente")
        return texto

    inicio, chave_abre, fim = bloco_info
    bloco = texto[chave_abre:fim + 1]
    bloco_original = bloco

    bloco = atualizar_propriedade_cookie(bloco, "httpOnly", "true")
    bloco = atualizar_propriedade_cookie(bloco, "sameSite", "'lax'")
    bloco = atualizar_propriedade_cookie(
        bloco,
        "secure",
        "process.env.NODE_ENV === 'production' && process.env.COOKIE_SECURE === 'true'"
    )

    if bloco != bloco_original:
        texto = texto[:chave_abre] + bloco + texto[fim + 1:]
        alteracoes.append("Cookie de sessao ajustado com httpOnly, sameSite e secure condicionado")
    else:
        alteracoes.append("Cookie de sessao ja parecia ajustado")

    return texto


def aplicar_hardening_server():
    resultado = {
        "arquivo": "server.js",
        "existe": SERVER_JS.exists(),
        "alterado": False,
        "alteracoes": [],
        "sha256_antes": sha256_arquivo(SERVER_JS) if SERVER_JS.exists() else None,
        "sha256_depois": None
    }

    texto = ler_texto(SERVER_JS)
    if texto is None:
        resultado["erro"] = "server.js ausente ou ilegivel"
        return resultado

    novo = texto
    alteracoes = []

    novo = remover_cors_permissivo(novo, alteracoes)
    novo = garantir_x_powered(novo, alteracoes)
    novo = adicionar_cors_seguro(novo, alteracoes)
    novo = adicionar_headers_finais(novo, alteracoes)
    novo = ajustar_cookie_sessao(novo, alteracoes)

    if novo != texto:
        gravar_texto(SERVER_JS, novo)
        resultado["alterado"] = True

    resultado["alteracoes"] = alteracoes
    resultado["sha256_depois"] = sha256_arquivo(SERVER_JS)
    return resultado


def node_check_server():
    if not SERVER_JS.exists():
        return {
            "ok": False,
            "erro": "server.js ausente"
        }

    return run_cmd(["node", "--check", "server.js"], 40)


def reiniciar_app_se_solicitado():
    valor = os.environ.get("ETAPA15_RESTART_APP", "").strip().lower()

    if valor not in ["true", "1", "sim", "yes"]:
        return {
            "solicitado": False,
            "executado": False,
            "ok": None,
            "resultado": None
        }

    r = run_cmd(["docker", "compose", "restart", "app"], 120)

    return {
        "solicitado": True,
        "executado": True,
        "ok": r.get("ok"),
        "resultado": r
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
        "User-Agent": "etapa-15-hardening/1.0"
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


def aguardar_app():
    inicio = time.time()
    tentativas = []

    while time.time() - inicio < 90:
        opener, jar = criar_opener()
        r = http_request(opener, "GET", "/", None, timeout=6)
        tentativas.append({
            "status": r.get("status"),
            "ok": r.get("ok"),
            "erro": r.get("erro")
        })

        if r.get("status") in [200, 302, 404]:
            return {
                "ok": True,
                "tentativas": tentativas,
                "segundos": int(time.time() - inicio)
            }

        time.sleep(3)

    return {
        "ok": False,
        "tentativas": tentativas,
        "segundos": int(time.time() - inicio)
    }


def validar_login_dashboard():
    cred = obter_credenciais()

    resultado = {
        "executado": False,
        "email_configurado": cred["email_configurado"],
        "senha_configurada": cred["senha_configurada"],
        "login_ok": False,
        "dashboard_ok": False,
        "cookies": [],
        "login": None,
        "dashboard": None
    }

    if not cred["email_configurado"] or not cred["senha_configurada"]:
        resultado["motivo"] = "Credenciais nao configuradas"
        return resultado

    opener, jar = criar_opener()

    payload = {
        "email": cred["email"],
        "senha": cred["senha"]
    }

    login = http_request(opener, "POST", LOGIN_PATH, payload)
    resultado["executado"] = True
    resultado["login"] = login
    resultado["cookies"] = cookies_resumo(jar)

    body = (login.get("body_preview") or "").lower()
    status_ok = login.get("status") in [200, 201, 302]
    cookie_ok = len(resultado["cookies"]) > 0
    body_ok = "sucesso" in body or "success" in body or "dashboard" in body or "ok" in body

    resultado["login_ok"] = bool(status_ok and (cookie_ok or body_ok))

    dashboard = http_request(opener, "GET", DASHBOARD_PATH)
    resultado["dashboard"] = dashboard
    resultado["dashboard_ok"] = bool(
        dashboard.get("status") == 200 and
        "crm enterprise" in (dashboard.get("body_preview") or "").lower()
    )

    return resultado


def validar_headers():
    opener, jar = criar_opener()
    normal = http_request(opener, "GET", "/", None)
    origem_permitida = http_request(opener, "GET", "/", None, origin="http://127.0.0.1:50010")
    origem_nao_permitida = http_request(opener, "GET", "/", None, origin="http://evil.example")

    def extrair(item):
        headers = item.get("headers") or {}
        lower = {}
        for k, v in headers.items():
            lower[k.lower()] = v

        return {
            "status": item.get("status"),
            "x_powered_by": lower.get("x-powered-by"),
            "x_content_type_options": lower.get("x-content-type-options"),
            "x_frame_options": lower.get("x-frame-options"),
            "referrer_policy": lower.get("referrer-policy"),
            "permissions_policy": lower.get("permissions-policy"),
            "cross_origin_opener_policy": lower.get("cross-origin-opener-policy"),
            "access_control_allow_origin": lower.get("access-control-allow-origin"),
            "access_control_allow_credentials": lower.get("access-control-allow-credentials"),
            "set_cookie": lower.get("set-cookie")
        }

    normal_h = extrair(normal)
    permitida_h = extrair(origem_permitida)
    negada_h = extrair(origem_nao_permitida)

    estrela = chr(42)
    ok_sem_powered = normal_h["x_powered_by"] is None
    ok_headers = bool(
        normal_h["x_content_type_options"] and
        normal_h["x_frame_options"] and
        normal_h["referrer_policy"]
    )
    ok_cors_sem_estrela = (
        normal_h["access_control_allow_origin"] != estrela and
        permitida_h["access_control_allow_origin"] != estrela and
        negada_h["access_control_allow_origin"] != estrela
    )
    ok_origem_negada = negada_h["access_control_allow_origin"] is None

    return {
        "normal": normal_h,
        "origem_permitida": permitida_h,
        "origem_nao_permitida": negada_h,
        "ok_sem_x_powered_by": ok_sem_powered,
        "ok_headers_basicos": ok_headers,
        "ok_cors_sem_estrela": ok_cors_sem_estrela,
        "ok_origem_nao_permitida": ok_origem_negada
    }


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

        if "@" in linha and "." in linha:
            email += 1

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

    marcador_inicio = "<!-- ETAPA_15_INICIO -->"
    marcador_fim = "<!-- ETAPA_15_FIM -->"

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
    antes = relatorio["auditoria_antes"]
    depois = relatorio["auditoria_depois"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    headers = relatorio["validacao_headers"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 15 - CORS, cookie e headers finais",
        [
            "Data: " + data,
            "",
            "Foi aplicado hardening de CORS, cookie de sessao e headers HTTP finais.",
            "CORS seguro antes: " + str(antes["etapa15_cors"]) + ".",
            "CORS seguro depois: " + str(depois["etapa15_cors"]) + ".",
            "SameSite depois: " + str(depois["cookie_same_site"]) + ".",
            "Node check OK: " + str(node["ok"]) + ".",
            "Restart executado: " + str(restart["executado"]) + ".",
            "Headers basicos OK em runtime: " + str(headers["ok_headers_basicos"]) + ".",
            "CORS sem origem aberta em runtime: " + str(headers["ok_cors_sem_estrela"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 15 - Hardening de CORS e cookies",
        [
            "Data: " + data,
            "",
            "Removida configuracao CORS permissiva quando localizada.",
            "Adicionado middleware CORS controlado por CORS_ORIGINS ou APP_URL.",
            "Ajustado cookie de sessao com httpOnly, sameSite e secure condicionado.",
            "Validados headers HTTP basicos.",
            "Executado node --check em server.js.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 15 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido bloquear origem aberta em CORS quando houver sessao e cookie.",
            "Decidido usar CORS_ORIGINS ou APP_URL como origem permitida em ambiente configurado.",
            "Decidido usar origens locais somente como fallback de desenvolvimento.",
            "Decidido condicionar secure do cookie a NODE_ENV production e COOKIE_SECURE true.",
            "Decidido manter restart dependente de ETAPA15_RESTART_APP=true."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Se o app nao foi reiniciado, reiniciar em janela controlada com ETAPA15_RESTART_APP=true.",
        "Definir CORS_ORIGINS no ambiente final com dominio real HTTPS.",
        "Definir COOKIE_SECURE=true apenas com HTTPS valido.",
        "Validar ambiente externo com HTTPS.",
        "Planejar rate limit e politica CSP dedicada."
    ]

    if restart["executado"] and headers["ok_headers_basicos"] and headers["ok_cors_sem_estrela"]:
        pendencias = [
            "Data: " + data,
            "",
            "Definir CORS_ORIGINS no ambiente final com dominio real HTTPS.",
            "Definir COOKIE_SECURE=true apenas com HTTPS valido.",
            "Validar ambiente externo com HTTPS.",
            "Planejar rate limit e politica CSP dedicada."
        ]

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 15",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    antes = relatorio["auditoria_antes"]
    depois = relatorio["auditoria_depois"]
    correcao = relatorio["correcao_server"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    validacao = relatorio["validacao_login_dashboard"]
    headers = relatorio["validacao_headers"]
    logs = relatorio["logs_novos_analise"]

    linhas.append("# Etapa 15 - Hardening de CORS, cookie e headers finais")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- server.js alterado: " + str(correcao["alterado"]))
    linhas.append("- Node check OK: " + str(node["ok"]))
    linhas.append("- Restart solicitado: " + str(restart["solicitado"]))
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("- Headers basicos OK: " + str(headers["ok_headers_basicos"]))
    linhas.append("- Sem X-Powered-By: " + str(headers["ok_sem_x_powered_by"]))
    linhas.append("- CORS sem origem aberta: " + str(headers["ok_cors_sem_estrela"]))
    linhas.append("- Origem nao permitida bloqueada: " + str(headers["ok_origem_nao_permitida"]))
    linhas.append("- Logs novos Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos email: " + str(logs["linhas_email"]))
    linhas.append("")

    linhas.append("## Auditoria antes")
    linhas.append("")
    for chave in sorted(antes.keys()):
        if chave != "erro":
            linhas.append("- " + chave + ": " + str(antes[chave]))

    linhas.append("")
    linhas.append("## Alteracoes aplicadas")
    linhas.append("")
    if correcao["alteracoes"]:
        for item in correcao["alteracoes"]:
            linhas.append("- " + item)
    else:
        linhas.append("- Nenhuma alteracao aplicada.")

    linhas.append("")
    linhas.append("## Auditoria depois")
    linhas.append("")
    for chave in sorted(depois.keys()):
        if chave != "erro":
            linhas.append("- " + chave + ": " + str(depois[chave]))

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    linhas.append("- OK: " + str(node["ok"]))
    if node.get("stderr"):
        linhas.append("- stderr: " + node["stderr"][:500])

    linhas.append("")
    linhas.append("## Validacao headers runtime")
    linhas.append("")
    linhas.append("- Sem X-Powered-By: " + str(headers["ok_sem_x_powered_by"]))
    linhas.append("- Headers basicos OK: " + str(headers["ok_headers_basicos"]))
    linhas.append("- CORS sem origem aberta: " + str(headers["ok_cors_sem_estrela"]))
    linhas.append("- Origem nao permitida bloqueada: " + str(headers["ok_origem_nao_permitida"]))
    linhas.append("- ACAO origem permitida: " + str(headers["origem_permitida"]["access_control_allow_origin"]))
    linhas.append("- ACAO origem nao permitida: " + str(headers["origem_nao_permitida"]["access_control_allow_origin"]))
    linhas.append("- X-Content-Type-Options: " + str(headers["normal"]["x_content_type_options"]))
    linhas.append("- X-Frame-Options: " + str(headers["normal"]["x_frame_options"]))
    linhas.append("- Referrer-Policy: " + str(headers["normal"]["referrer_policy"]))

    linhas.append("")
    linhas.append("## Validacao login e dashboard")
    linhas.append("")
    linhas.append("- Executada: " + str(validacao["executado"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("- Cookies recebidos: " + str(len(validacao["cookies"])))
    for cookie in validacao["cookies"]:
        linhas.append("- Cookie: name=" + cookie["name"] + ", secure=" + str(cookie["secure"]))

    linhas.append("")
    linhas.append("## Logs novos")
    linhas.append("")
    linhas.append("- Linhas analisadas: " + str(logs["total_linhas"]))
    linhas.append("- Linhas Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Linhas cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Linhas email: " + str(logs["linhas_email"]))
    linhas.append("- Achados criticos: " + str(len(logs["achados"])))

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhuma alteracao foi aplicada ao banco.")
    linhas.append("- Restart so foi executado se ETAPA15_RESTART_APP=true.")
    linhas.append("- secure do cookie foi condicionado para evitar quebrar HTTP local.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Definir CORS_ORIGINS e COOKIE_SECURE no ambiente final HTTPS.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_15_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_15_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    auditoria_antes = auditar_server_js()
    correcao_server = aplicar_hardening_server()
    auditoria_depois = auditar_server_js()
    node = node_check_server()

    restart = reiniciar_app_se_solicitado()
    aguardar = aguardar_app()

    since = agora_logs_since()
    validacao = validar_login_dashboard()
    headers = validar_headers()
    time.sleep(2)

    logs_coleta = coletar_logs_novos(since)
    logs_analise = analisar_logs_texto(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "auditoria_antes": auditoria_antes,
        "correcao_server": correcao_server,
        "auditoria_depois": auditoria_depois,
        "node_check": node,
        "restart_app": restart,
        "aguardar_app": aguardar,
        "logs_since": since,
        "validacao_login_dashboard": validacao,
        "validacao_headers": headers,
        "logs_coleta": logs_coleta,
        "logs_novos_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_15_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_15_hardening_cors_cookie_headers.json"
    md_path = REPORTS_DIR / "etapa_15_hardening_cors_cookie_headers.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 15 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("server.js alterado: " + str(correcao_server["alterado"]))
    print("Node check OK: " + str(node["ok"]))
    print("Restart solicitado: " + str(restart["solicitado"]))
    print("Restart executado: " + str(restart["executado"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(validacao["login_ok"]))
    print("Dashboard OK: " + str(validacao["dashboard_ok"]))
    print("Headers basicos OK: " + str(headers["ok_headers_basicos"]))
    print("Sem X-Powered-By: " + str(headers["ok_sem_x_powered_by"]))
    print("CORS sem origem aberta: " + str(headers["ok_cors_sem_estrela"]))
    print("Origem nao permitida bloqueada: " + str(headers["ok_origem_nao_permitida"]))
    print("Auditoria depois CORS seguro: " + str(auditoria_depois["etapa15_cors"]))
    print("Auditoria depois sameSite: " + str(auditoria_depois["cookie_same_site"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not restart["executado"]:
        print("")
        print("Aviso: app nao foi reiniciado. Para aplicar em runtime, execute com ETAPA15_RESTART_APP=true.")

    if not node["ok"]:
        print("")
        print("Falha no node --check. Consulte o relatorio.")

    if not headers["ok_cors_sem_estrela"]:
        print("")
        print("Aviso: CORS ainda aparenta permitir origem aberta em runtime.")


if __name__ == "__main__":
    main()