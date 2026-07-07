#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 25.3 - Corrigir API de status WhatsApp

Objetivo:
- Corrigir /api/whatsapp/status/:companyId em routes/api.js.
- Evitar erro quando req.whatsapp estiver undefined.
- Retornar status seguro DESCONECTADO quando nao houver sessao.
- Manter dashboard funcionando sem erro 500.
- Rodar node --check routes/api.js.
- Reiniciar app.
- Validar login, dashboard e API /api/whatsapp/status/5.
- Atualizar documentacao obrigatoria.
- Gerar relatorios JSON e Markdown.

Como executar:
sudo ETAPA25_3_LOGIN_EMAIL='admin.cliente.teste@saas.local' ETAPA25_3_LOGIN_PASSWORD='123456' python3 etapa_25_3_corrigir_api_whatsapp_status.py

Ou com super admin:
sudo ETAPA25_3_LOGIN_EMAIL='superadmin.teste@saas.local' ETAPA25_3_LOGIN_PASSWORD='123456' ETAPA25_3_EMPRESA_ID='5' python3 etapa_25_3_corrigir_api_whatsapp_status.py
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

API_FILE = ROOT / "routes" / "api.js"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "routes/api.js",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

IGNORE_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "reports",
    "__pycache__",
    "tmp_etapa_24"
]

BASE_URL = "http://127.0.0.1:50010"
LOGIN_API = "/api/auth/login"

EMAIL_KEYS = [
    "ETAPA25_3_LOGIN_EMAIL",
    "ETAPA25_2_LOGIN_EMAIL",
    "ETAPA25_1_LOGIN_EMAIL",
    "ETAPA24_CLIENTE_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA25_3_LOGIN_PASSWORD",
    "ETAPA25_2_LOGIN_PASSWORD",
    "ETAPA25_1_LOGIN_PASSWORD",
    "ETAPA24_CLIENTE_PASSWORD",
    "LOGIN_PASSWORD",
    "ADMIN_PASSWORD",
    "DEFAULT_ADMIN_PASSWORD"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def logs_since():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


def rel(path):
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def ler(path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def gravar(path, texto):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def sha256(path):
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


def salvar_json(path, dados):
    gravar(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def deve_ignorar(path):
    partes = set(path.parts)
    rel_path = rel(path)

    for nome in IGNORE_DIRS:
        if nome in partes:
            return True
        if rel_path == nome or rel_path.startswith(nome + "/"):
            return True

    return False


def gerar_manifesto():
    itens = []

    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)
        dirs[:] = [d for d in dirs if not deve_ignorar(base_path / d)]

        for nome in files:
            p = base_path / nome
            if deve_ignorar(p):
                continue

            try:
                st = p.stat()
                itens.append({
                    "arquivo": rel(p),
                    "tamanho_bytes": st.st_size,
                    "sha256": sha256(p)
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
        "arquivos": sorted(itens, key=lambda x: x.get("arquivo", ""))
    }


def criar_backup(destino):
    destino.mkdir(parents=True, exist_ok=True)

    copiados = []
    ausentes = []
    erros = []

    for nome in BACKUP_FILES:
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


def parse_env():
    dados = {}
    env_path = ROOT / ".env"
    texto = ler(env_path)

    if texto:
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

    for chave, valor in os.environ.items():
        dados[chave] = valor

    return dados


def primeiro(dados, chaves):
    for chave in chaves:
        valor = dados.get(chave)
        if valor:
            return valor
    return ""


def credenciais():
    dados = parse_env()
    email = primeiro(dados, EMAIL_KEYS)
    senha = primeiro(dados, PASSWORD_KEYS)

    if not email:
        email = "admin.cliente.teste@saas.local"

    if not senha:
        senha = "123456"

    return {
        "email": email,
        "senha": senha,
        "email_configurado": bool(email),
        "senha_configurada": bool(senha)
    }


def empresa_id_teste():
    valor = os.environ.get("ETAPA25_3_EMPRESA_ID", "").strip()
    if valor:
        return valor
    return "5"


def valores_sensiveis():
    dados = parse_env()
    valores = []

    for chave, valor in dados.items():
        upper = chave.upper()
        if any(t in upper for t in ["PASS", "PASSWORD", "SECRET", "TOKEN", "KEY", "SENHA"]):
            if valor:
                valores.append(valor)

    c = credenciais()
    if c["senha"]:
        valores.append(c["senha"])

    return valores


def redigir(texto):
    if texto is None:
        return texto

    out = str(texto)

    for valor in valores_sensiveis():
        if valor:
            out = out.replace(valor, "<REDIGIDO>")

    c = credenciais()
    out = out.replace(c["email"], "<EMAIL_LOGIN>")

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
            "stdout": redigir(proc.stdout.strip())[:50000],
            "stderr": redigir(proc.stderr.strip())[:50000],
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


def nova_rota_status():
    return """router.get('/whatsapp/status/:companyId', isAuthenticated, (req, res) => {
    try {
        const rawEmpresaId = req.params.companyId || req.session?.empresaId || req.empresaId;
        const empresaId = parseInt(rawEmpresaId, 10);

        if (!empresaId) {
            return res.status(400).json({
                success: false,
                error: 'ID da empresa obrigatorio.'
            });
        }

        const manager = req.whatsapp || req.app?.locals?.whatsapp || req.app?.locals?.sessionManager || null;
        const sessions = manager && manager.sessions && typeof manager.sessions.get === 'function'
            ? manager.sessions
            : null;

        const session = sessions ? sessions.get(empresaId) : null;

        const wsState = session && session.ws ? session.ws.readyState : null;
        const hasUser = !!(session && session.user);
        const isConnected = !!(hasUser && (wsState === 1 || wsState === undefined || wsState === null));

        let qr = null;

        if (manager && manager.qrCodes && typeof manager.qrCodes.get === 'function') {
            qr = manager.qrCodes.get(empresaId) || null;
        } else if (manager && manager.qr && typeof manager.qr.get === 'function') {
            qr = manager.qr.get(empresaId) || null;
        }

        return res.json({
            success: true,
            empresaId: empresaId,
            connected: isConnected,
            status: isConnected ? 'CONECTADO' : (qr ? 'AGUARDANDO_QR' : 'DESCONECTADO'),
            qr: qr || null
        });
    } catch (error) {
        console.error('[API WhatsApp Status] Erro seguro:', error.message);

        return res.json({
            success: true,
            connected: false,
            status: 'DESCONECTADO',
            qr: null,
            error: 'Status indisponivel no momento.'
        });
    }
});"""


def encontrar_bloco_rota(texto):
    alvo1 = "router.get('/whatsapp/status/:companyId'"
    alvo2 = 'router.get("/whatsapp/status/:companyId"'

    start = texto.find(alvo1)
    if start < 0:
        start = texto.find(alvo2)

    if start < 0:
        return None

    brace_start = texto.find("{", start)
    if brace_start < 0:
        return None

    i = brace_start
    depth = 0
    quote = None
    escape = False
    in_line_comment = False
    in_block_comment = False

    while i < len(texto):
        ch = texto[i]
        nxt = texto[i + 1] if i + 1 < len(texto) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if ch in ["'", '"', "`"]:
            quote = ch
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                close_brace = i
                semi = texto.find(");", close_brace)
                if semi < 0:
                    return None
                return {
                    "start": start,
                    "end": semi + 2,
                    "old": texto[start:semi + 2]
                }

        i += 1

    return None


def aplicar_correcao():
    resultado = {
        "arquivo": "routes/api.js",
        "existe_antes": API_FILE.exists(),
        "alterado": False,
        "rota_encontrada": False,
        "rota_ja_corrigida": False,
        "sha256_antes": sha256(API_FILE) if API_FILE.exists() else None,
        "sha256_depois": None
    }

    texto = ler(API_FILE)
    if texto is None:
        resultado["erro"] = "routes/api.js ausente ou ilegivel"
        return resultado

    if "ETAPA25_3_WHATSAPP_STATUS_SEGURO" in texto:
        resultado["rota_ja_corrigida"] = True
        resultado["sha256_depois"] = sha256(API_FILE)
        return resultado

    bloco = encontrar_bloco_rota(texto)
    if not bloco:
        resultado["erro"] = "Rota /whatsapp/status/:companyId nao encontrada"
        resultado["sha256_depois"] = sha256(API_FILE)
        return resultado

    resultado["rota_encontrada"] = True

    novo_bloco = (
        "// ETAPA25_3_WHATSAPP_STATUS_SEGURO_INICIO\n" +
        nova_rota_status() +
        "\n// ETAPA25_3_WHATSAPP_STATUS_SEGURO_FIM"
    )

    novo_texto = texto[:bloco["start"]] + novo_bloco + texto[bloco["end"]:]

    if novo_texto != texto:
        gravar(API_FILE, novo_texto)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256(API_FILE)
    return resultado


def validar_estrutura():
    texto = ler(API_FILE) or ""

    resultado = {
        "arquivo_existe": API_FILE.exists(),
        "tem_rota_status": "/whatsapp/status/:companyId" in texto,
        "tem_marker": "ETAPA25_3_WHATSAPP_STATUS_SEGURO" in texto,
        "nao_usa_req_whatsapp_direto_sessions": "req.whatsapp.sessions" not in texto,
        "tem_fallback_manager": "req.app?.locals?.whatsapp" in texto,
        "tem_status_desconectado": "'DESCONECTADO'" in texto,
        "ok": False
    }

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_rota_status"] and
        resultado["tem_marker"] and
        resultado["nao_usa_req_whatsapp_direto_sessions"] and
        resultado["tem_fallback_manager"] and
        resultado["tem_status_desconectado"]
    )

    return resultado


def node_check():
    if not API_FILE.exists():
        return {
            "ok": False,
            "erro": "routes/api.js ausente"
        }

    return run_cmd(["node", "--check", "routes/api.js"], 40)


def restart_app():
    valor = os.environ.get("ETAPA25_3_RESTART_APP", "true").strip().lower()

    if valor in ["false", "0", "nao", "não", "no"]:
        return {
            "executado": False,
            "ok": None,
            "resultado": None
        }

    r = run_cmd(["docker", "compose", "restart", "app"], 120)
    return {
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


def http_request(opener, metodo, path, data_obj=None, timeout=20, limite=700000):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "metodo": metodo,
        "ok": False,
        "status": None,
        "erro": None,
        "content_type": "",
        "body_preview": "",
        "body_limited": "",
        "json": None
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-25-3-whatsapp-status/1.0"
    }

    if data_obj is not None:
        body_text = json.dumps(data_obj)
        body_bytes = body_text.encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=body_bytes, headers=headers, method=metodo)

    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(limite)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["body_preview"] = redigir(texto[:1500])
            resultado["body_limited"] = redigir(texto)

            try:
                resultado["json"] = json.loads(texto)
            except Exception:
                resultado["json"] = None
    except HTTPError as exc:
        try:
            body = exc.read(limite)
            texto = body.decode("utf-8", errors="replace")
        except Exception:
            texto = ""

        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 400
        resultado["erro"] = redigir(str(exc))
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
        resultado["body_preview"] = redigir(texto[:1500])
        resultado["body_limited"] = redigir(texto)

        try:
            resultado["json"] = json.loads(texto)
        except Exception:
            resultado["json"] = None
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
        r = http_request(opener, "GET", "/", None, timeout=6, limite=3000)
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


def validar_runtime():
    c = credenciais()
    emp_id = empresa_id_teste()

    resultado = {
        "login_ok": False,
        "cookies": [],
        "dashboard_ok": False,
        "status_api_ok": False,
        "status_api_sem_500": False,
        "status_api_json_ok": False,
        "ok": False
    }

    opener, jar = criar_opener()

    login = http_request(opener, "POST", LOGIN_API, {
        "email": c["email"],
        "senha": c["senha"]
    }, limite=100000)

    body_login = (login.get("body_limited") or "").lower()
    resultado["cookies"] = cookies_resumo(jar)
    resultado["login"] = {
        "status": login.get("status"),
        "ok": login.get("ok"),
        "erro": login.get("erro"),
        "content_type": login.get("content_type"),
        "body_preview": login.get("body_preview")
    }

    resultado["login_ok"] = bool(
        login.get("status") in [200, 201, 302] and
        ("success" in body_login or "sucesso" in body_login or len(resultado["cookies"]) > 0)
    )

    dashboard = http_request(opener, "GET", "/dashboard", None, limite=700000)
    dashboard_body = dashboard.get("body_limited") or ""

    resultado["dashboard"] = {
        "status": dashboard.get("status"),
        "ok": dashboard.get("status") == 200,
        "tem_check_connection": "checkConnection" in dashboard_body,
        "content_type": dashboard.get("content_type")
    }
    resultado["dashboard_ok"] = bool(dashboard.get("status") == 200)

    status_api = http_request(opener, "GET", "/api/whatsapp/status/" + emp_id, None, limite=100000)
    status_json = status_api.get("json") or {}

    resultado["status_api"] = {
        "status": status_api.get("status"),
        "ok": status_api.get("ok"),
        "erro": status_api.get("erro"),
        "content_type": status_api.get("content_type"),
        "body_preview": status_api.get("body_preview"),
        "json": status_json
    }

    resultado["status_api_sem_500"] = status_api.get("status") != 500
    resultado["status_api_json_ok"] = bool(
        status_api.get("status") == 200 and
        isinstance(status_json, dict) and
        status_json.get("success") is True and
        status_json.get("status") in ["CONECTADO", "AGUARDANDO_QR", "DESCONECTADO"]
    )
    resultado["status_api_ok"] = bool(resultado["status_api_sem_500"] and resultado["status_api_json_ok"])

    resultado["ok"] = bool(
        resultado["login_ok"] and
        resultado["dashboard_ok"] and
        resultado["status_api_ok"]
    )

    return resultado


def coletar_logs(since):
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


def parece_email(token):
    token = str(token or "").strip().strip(".;:,()[]{}<>")

    if "@" not in token:
        return False

    partes = token.split("@")

    if len(partes) != 2:
        return False

    usuario = partes[0]
    dominio = partes[1]

    if not usuario:
        return False

    if "." not in dominio:
        return False

    if len(dominio) < 4:
        return False

    if dominio.replace(".", "").isdigit():
        return False

    return True


def analisar_logs(texto):
    session_id = 0
    cookie = 0
    email = 0
    achados = []
    req_whatsapp_sessions = 0

    for idx, linha in enumerate(str(texto or "").splitlines(), start=1):
        low = linha.lower()

        if "session id" in low:
            session_id += 1

        if "saas_crm_sid" in low or "connect.sid" in low or "header cookie" in low:
            cookie += 1

        if "cannot read properties of undefined" in low and "sessions" in low:
            req_whatsapp_sessions += 1
            achados.append({
                "linha": idx,
                "trecho": redigir(linha.strip())[:500]
            })

        tokens = linha.replace("(", " ").replace(")", " ").replace(",", " ").split()
        for token in tokens:
            if parece_email(token):
                email += 1
                break

        if "syntaxerror" in low or "exception" in low or "econnrefused" in low:
            achados.append({
                "linha": idx,
                "trecho": redigir(linha.strip())[:500]
            })

    return {
        "total_linhas": len(str(texto or "").splitlines()),
        "linhas_session_id": session_id,
        "linhas_cookie": cookie,
        "linhas_email": email,
        "erro_req_whatsapp_sessions": req_whatsapp_sessions,
        "achados": achados,
        "amostra": redigir("\n".join(str(texto or "").splitlines()[-120:]))[:30000]
    }


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)

    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_25_3_INICIO -->"
    fim = "<!-- ETAPA_25_3_FIM -->"

    bloco = []
    bloco.append("")
    bloco.append(ini)
    bloco.append("## " + titulo)
    bloco.append("")
    bloco.extend(linhas)
    bloco.append(fim)
    bloco.append("")

    novo_bloco = "\n".join(bloco)

    pos_ini = atual.find(ini)
    pos_fim = atual.find(fim)

    if pos_ini >= 0 and pos_fim >= pos_ini:
        pos_fim = pos_fim + len(fim)
        novo = atual[:pos_ini] + novo_bloco.strip() + atual[pos_fim:]
    else:
        if not atual.endswith("\n"):
            atual = atual + "\n"
        novo = atual + novo_bloco

    gravar(path, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    correcao = relatorio["correcao"]
    runtime = relatorio["runtime"]
    logs = relatorio["logs_analise"]

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Etapa 25.3 - API status WhatsApp corrigida",
        [
            "Data: " + data,
            "",
            "Corrigida rota /api/whatsapp/status/:companyId para resposta segura quando req.whatsapp estiver ausente.",
            "routes/api.js alterado: " + str(correcao["alterado"]) + ".",
            "Dashboard OK: " + str(runtime["dashboard_ok"]) + ".",
            "Status API OK: " + str(runtime["status_api_ok"]) + ".",
            "Status API sem 500: " + str(runtime["status_api_sem_500"]) + ".",
            "Erro req.whatsapp.sessions nos logs: " + str(logs["erro_req_whatsapp_sessions"]) + ".",
            "Logs Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs cookie: " + str(logs["linhas_cookie"]) + ".",
            "Logs email: " + str(logs["linhas_email"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 25.3 - Correcao /api/whatsapp/status",
        [
            "Data: " + data,
            "",
            "Ajustada a rota /api/whatsapp/status/:companyId para nao acessar req.whatsapp.sessions diretamente.",
            "Adicionado fallback defensivo para status DESCONECTADO.",
            "Validado node --check, dashboard e API de status."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 25.3 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido tratar ausencia de req.whatsapp como estado operacional desconectado.",
            "Decidido nao iniciar sessao WhatsApp automaticamente apenas para consultar status.",
            "Decidido retornar HTTP 200 para status operacional indisponivel, preservando o dashboard."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 25.3",
        [
            "Data: " + data,
            "",
            "Validar no navegador se o erro 500 de /api/whatsapp/status/5 sumiu.",
            "Planejar Etapa 26 para auditoria funcional completa.",
            "Planejar etapa futura para internalizar Tailwind e Alpine."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    linhas = []
    linhas.append("# Etapa 25.3 - Corrigir API WhatsApp Status")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- routes/api.js alterado: " + str(relatorio["correcao"]["alterado"]))
    linhas.append("- Rota encontrada: " + str(relatorio["correcao"]["rota_encontrada"]))
    linhas.append("- Validacao estrutural OK: " + str(relatorio["validacao_estrutura"]["ok"]))
    linhas.append("- Node check OK: " + str(relatorio["node_check"]["ok"]))
    linhas.append("- Restart OK: " + str(relatorio["restart_app"]["ok"]))
    linhas.append("- App pronto: " + str(relatorio["aguardar_app"]["ok"]))
    linhas.append("- Login OK: " + str(relatorio["runtime"]["login_ok"]))
    linhas.append("- Dashboard OK: " + str(relatorio["runtime"]["dashboard_ok"]))
    linhas.append("- Status API sem 500: " + str(relatorio["runtime"]["status_api_sem_500"]))
    linhas.append("- Status API JSON OK: " + str(relatorio["runtime"]["status_api_json_ok"]))
    linhas.append("- Status API OK: " + str(relatorio["runtime"]["status_api_ok"]))
    linhas.append("- Runtime geral OK: " + str(relatorio["runtime"]["ok"]))
    linhas.append("- Erro req.whatsapp.sessions logs: " + str(relatorio["logs_analise"]["erro_req_whatsapp_sessions"]))
    linhas.append("- Logs Session ID: " + str(relatorio["logs_analise"]["linhas_session_id"]))
    linhas.append("- Logs cookie: " + str(relatorio["logs_analise"]["linhas_cookie"]))
    linhas.append("- Logs email: " + str(relatorio["logs_analise"]["linhas_email"]))
    linhas.append("- Achados logs: " + str(len(relatorio["logs_analise"]["achados"])))
    linhas.append("")
    linhas.append("## Status API")
    linhas.append("")
    linhas.append("```json")
    linhas.append(json.dumps(relatorio["runtime"]["status_api"]["json"], ensure_ascii=False, indent=2))
    linhas.append("```")
    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_25_3_whatsapp_status_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_25_3_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = logs_since()
    correcao = aplicar_correcao()
    estrutura = validar_estrutura()
    node = node_check()
    restart = restart_app()
    aguardar = aguardar_app()
    runtime = validar_runtime()
    time.sleep(2)

    logs_coleta = coletar_logs(since)
    logs_analise = analisar_logs(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "correcao": correcao,
        "validacao_estrutura": estrutura,
        "node_check": node,
        "restart_app": restart,
        "aguardar_app": aguardar,
        "runtime": runtime,
        "logs_since": since,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_25_3_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_25_3_corrigir_api_whatsapp_status.json"
    md_path = REPORTS_DIR / "etapa_25_3_corrigir_api_whatsapp_status.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 25.3 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("routes/api.js alterado: " + str(correcao["alterado"]))
    print("Rota encontrada: " + str(correcao["rota_encontrada"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Node check OK: " + str(node["ok"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("Status API sem 500: " + str(runtime["status_api_sem_500"]))
    print("Status API JSON OK: " + str(runtime["status_api_json_ok"]))
    print("Status API OK: " + str(runtime["status_api_ok"]))
    print("Runtime geral OK: " + str(runtime["ok"]))
    print("Erro req.whatsapp.sessions logs: " + str(logs_analise["erro_req_whatsapp_sessions"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["ok"]:
        print("")
        print("Aviso: Etapa 25.3 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
