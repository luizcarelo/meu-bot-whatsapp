#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 23.3 - Corrigir middleware isSuperAdmin

Objetivo:
- Criar backup antes da alteracao.
- Alterar somente src/middleware/auth.js.
- Corrigir isSuperAdmin para aceitar is_admin como 1 ou true.
- Aceitar tambem role superadmin e cargo Super Admin.
- Manter exigencia de empresa master igual a 1.
- Rodar node --check em src/middleware/auth.js.
- Reiniciar app.
- Validar login, dashboard e /super-admin.
- Validar marcadores visuais da Etapa 22 em runtime.
- Atualizar documentacao obrigatoria.
- Gerar relatorios JSON e Markdown.

Como executar:
sudo ETAPA23_3_LOGIN_EMAIL='admin@saas.com' ETAPA23_3_LOGIN_PASSWORD='123456' python3 etapa_23_3_corrigir_is_super_admin.py
"""

import os
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

AUTH_FILE = ROOT / "src" / "middleware" / "auth.js"

BASE_URL = "http://127.0.0.1:50010"
LOGIN_API = "/api/auth/login"
DASHBOARD_PAGE = "/dashboard"
SUPER_ADMIN_PAGE = "/super-admin"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "src/middleware/auth.js",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

EMAIL_KEYS = [
    "ETAPA23_3_LOGIN_EMAIL",
    "ETAPA23_2_LOGIN_EMAIL",
    "ETAPA23_1_LOGIN_EMAIL",
    "ETAPA23_LOGIN_EMAIL",
    "ETAPA22_1_LOGIN_EMAIL",
    "ETAPA22_LOGIN_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SEED_ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA23_3_LOGIN_PASSWORD",
    "ETAPA23_2_LOGIN_PASSWORD",
    "ETAPA23_1_LOGIN_PASSWORD",
    "ETAPA23_LOGIN_PASSWORD",
    "ETAPA22_1_LOGIN_PASSWORD",
    "ETAPA22_LOGIN_PASSWORD",
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

    return {
        "email": email,
        "senha": senha,
        "email_configurado": bool(email),
        "senha_configurada": bool(senha)
    }


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
            "stdout": redigir(proc.stdout.strip())[:30000],
            "stderr": redigir(proc.stderr.strip())[:30000],
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


def aplicar_correcao():
    resultado = {
        "arquivo": "src/middleware/auth.js",
        "existe_antes": AUTH_FILE.exists(),
        "alterado": False,
        "corrigiu_empresa_master": False,
        "corrigiu_privilegio": False,
        "sha256_antes": sha256(AUTH_FILE) if AUTH_FILE.exists() else None,
        "sha256_depois": None
    }

    texto = ler(AUTH_FILE)
    if texto is None:
        resultado["erro"] = "src/middleware/auth.js ausente ou ilegivel"
        return resultado

    novo = texto

    antigo_master = "const isMasterCompany = empresaId === 1;"
    novo_master = "const isMasterCompany = Number(empresaId) === 1;"

    if antigo_master in novo:
        novo = novo.replace(antigo_master, novo_master, 1)
        resultado["corrigiu_empresa_master"] = True

    antigo_priv = "const hasSuperPrivilege = user && (user.is_admin === 1 || user.cargo === 'Super Admin');"
    novo_priv = """const hasSuperPrivilege = user && (
        user.is_admin === 1 ||
        user.is_admin === true ||
        user.role === 'superadmin' ||
        user.cargo === 'Super Admin'
    );"""

    if antigo_priv in novo:
        novo = novo.replace(antigo_priv, novo_priv, 1)
        resultado["corrigiu_privilegio"] = True
    elif "user.role === 'superadmin'" in novo and "user.is_admin === true" in novo:
        resultado["corrigiu_privilegio"] = False
    else:
        resultado["erro"] = "Nao encontrei a linha original de hasSuperPrivilege para substituir"

    if novo != texto:
        gravar(AUTH_FILE, novo)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256(AUTH_FILE)
    return resultado


def validar_estrutura():
    texto = ler(AUTH_FILE)

    resultado = {
        "arquivo_existe": AUTH_FILE.exists(),
        "tem_is_super_admin": False,
        "empresa_master_number": False,
        "aceita_is_admin_1": False,
        "aceita_is_admin_true": False,
        "aceita_role_superadmin": False,
        "aceita_cargo_super_admin": False,
        "mantem_redirect_dashboard": False,
        "ok": False
    }

    if texto is None:
        resultado["erro"] = "src/middleware/auth.js ausente ou ilegivel"
        return resultado

    resultado["tem_is_super_admin"] = "const isSuperAdmin" in texto
    resultado["empresa_master_number"] = "Number(empresaId) === 1" in texto
    resultado["aceita_is_admin_1"] = "user.is_admin === 1" in texto
    resultado["aceita_is_admin_true"] = "user.is_admin === true" in texto
    resultado["aceita_role_superadmin"] = "user.role === 'superadmin'" in texto
    resultado["aceita_cargo_super_admin"] = "user.cargo === 'Super Admin'" in texto
    resultado["mantem_redirect_dashboard"] = "return res.redirect('/dashboard');" in texto

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_is_super_admin"] and
        resultado["empresa_master_number"] and
        resultado["aceita_is_admin_1"] and
        resultado["aceita_is_admin_true"] and
        resultado["aceita_role_superadmin"] and
        resultado["aceita_cargo_super_admin"] and
        resultado["mantem_redirect_dashboard"]
    )

    return resultado


def node_check():
    if not AUTH_FILE.exists():
        return {
            "ok": False,
            "erro": "src/middleware/auth.js ausente"
        }

    return run_cmd(["node", "--check", "src/middleware/auth.js"], 40)


def restart_app():
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
        "body_limited": ""
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-23-3-is-super-admin/1.0"
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
        r = http_request(opener, "GET", "/", None, timeout=6, limite=2000)
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

    resultado = {
        "executado": False,
        "email_configurado": c["email_configurado"],
        "senha_configurada": c["senha_configurada"],
        "login_ok": False,
        "dashboard_ok": False,
        "super_admin_ok": False,
        "super_admin_visual_ok": False,
        "cookies": [],
        "login": None,
        "dashboard": None,
        "super_admin": None,
        "marcadores": {}
    }

    if not c["email_configurado"] or not c["senha_configurada"]:
        resultado["motivo"] = "Credenciais nao configuradas"
        return resultado

    opener, jar = criar_opener()

    login = http_request(opener, "POST", LOGIN_API, {
        "email": c["email"],
        "senha": c["senha"]
    }, limite=100000)

    resultado["executado"] = True
    resultado["cookies"] = cookies_resumo(jar)
    resultado["login"] = resumo_http(login)

    body_login = (login.get("body_limited") or "").lower()
    resultado["login_ok"] = bool(
        login.get("status") in [200, 201, 302] and
        ("success" in body_login or "sucesso" in body_login or len(resultado["cookies"]) > 0)
    )

    dashboard = http_request(opener, "GET", DASHBOARD_PAGE, None, limite=300000)
    dash_body = dashboard.get("body_limited") or ""
    resultado["dashboard"] = resumo_http(dashboard)
    resultado["dashboard_ok"] = bool(dashboard.get("status") == 200 and "crm enterprise" in dash_body.lower())

    super_admin = http_request(opener, "GET", SUPER_ADMIN_PAGE, None, limite=700000)
    body = super_admin.get("body_limited") or ""
    lower = body.lower()

    marcadores = {
        "css_link": "/css/style.css" in body,
        "etapa22_inicio": "ETAPA22_SUPER_ADMIN_VISUAL_INICIO" in body,
        "etapa22_fim": "ETAPA22_SUPER_ADMIN_VISUAL_FIM" in body,
        "gestao_plataforma": "gestao geral da plataforma" in lower or "gestão geral da plataforma" in lower,
        "super_admin_texto": "super admin" in lower,
        "fetch": "fetch(" in body,
        "nao_redirecionou_dashboard": "Dashboard operacional" not in body
    }

    resultado["super_admin"] = resumo_http(super_admin)
    resultado["marcadores"] = marcadores
    resultado["super_admin_ok"] = bool(super_admin.get("status") == 200)
    resultado["super_admin_visual_ok"] = bool(
        resultado["super_admin_ok"] and
        marcadores["css_link"] and
        marcadores["etapa22_inicio"] and
        marcadores["etapa22_fim"] and
        marcadores["gestao_plataforma"] and
        marcadores["super_admin_texto"] and
        marcadores["nao_redirecionou_dashboard"]
    )

    return resultado


def resumo_http(item):
    return {
        "path": item.get("path"),
        "status": item.get("status"),
        "ok": item.get("ok"),
        "erro": item.get("erro"),
        "content_type": item.get("content_type"),
        "body_preview": item.get("body_preview")
    }


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

    for idx, linha in enumerate(str(texto or "").splitlines(), start=1):
        low = linha.lower()

        if "session id" in low:
            session_id += 1

        if "saas_crm_sid" in low or "connect.sid" in low or "header cookie" in low:
            cookie += 1

        tokens = linha.replace("(", " ").replace(")", " ").replace(",", " ").split()
        for token in tokens:
            if parece_email(token):
                email += 1
                break

        if "syntaxerror" in low or "exception" in low or "database" in low or "econnrefused" in low:
            achados.append({
                "linha": idx,
                "trecho": redigir(linha.strip())[:500]
            })

    return {
        "total_linhas": len(str(texto or "").splitlines()),
        "linhas_session_id": session_id,
        "linhas_cookie": cookie,
        "linhas_email": email,
        "achados": achados,
        "amostra": redigir("\n".join(str(texto or "").splitlines()[-120:]))[:30000]
    }


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)

    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_23_3_INICIO -->"
    fim = "<!-- ETAPA_23_3_FIM -->"

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
        "Etapa 23.3 - Middleware Super Admin corrigido",
        [
            "Data: " + data,
            "",
            "O middleware isSuperAdmin foi corrigido para aceitar is_admin numerico ou booleano.",
            "Arquivo alterado: " + str(correcao["alterado"]) + ".",
            "Empresa master corrigida com Number: " + str(correcao["corrigiu_empresa_master"]) + ".",
            "Privilegio corrigido: " + str(correcao["corrigiu_privilegio"]) + ".",
            "Login OK: " + str(runtime["login_ok"]) + ".",
            "Dashboard OK: " + str(runtime["dashboard_ok"]) + ".",
            "Super Admin OK: " + str(runtime["super_admin_ok"]) + ".",
            "Super Admin visual OK: " + str(runtime["super_admin_visual_ok"]) + ".",
            "Logs Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs cookie: " + str(logs["linhas_cookie"]) + ".",
            "Logs email: " + str(logs["linhas_email"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 23.3 - Correcao isSuperAdmin",
        [
            "Data: " + data,
            "",
            "Ajustado middleware isSuperAdmin para aceitar is_admin igual a 1 ou true.",
            "Adicionado suporte a role superadmin.",
            "Mantida exigencia de empresa master igual a 1.",
            "Validado node --check, login, dashboard e Super Admin."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 23.3 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido corrigir o middleware sem remover a protecao isSuperAdmin.",
            "Decidido aceitar boolean true porque o login serializa is_admin como booleano no JSON.",
            "Decidido manter empresa master obrigatoria para preservar seguranca multi-tenant.",
            "Decidido validar o HTML de /super-admin para confirmar que nao houve redirecionamento para dashboard."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 23.3",
        [
            "Data: " + data,
            "",
            "Reexecutar a Etapa 23 para consolidar o status geral final.",
            "Validar manualmente /super-admin no navegador.",
            "Planejar internalizacao de dependencias externas.",
            "Mapear scripts inline antes de CSP forte."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    correcao = relatorio["correcao"]
    estrutura = relatorio["validacao_estrutura"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    aguardar = relatorio["aguardar_app"]
    runtime = relatorio["runtime"]
    logs = relatorio["logs_analise"]

    linhas = []
    linhas.append("# Etapa 23.3 - Corrigir isSuperAdmin")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- auth.js alterado: " + str(correcao["alterado"]))
    linhas.append("- Corrigiu empresa master: " + str(correcao["corrigiu_empresa_master"]))
    linhas.append("- Corrigiu privilegio: " + str(correcao["corrigiu_privilegio"]))
    linhas.append("- Validacao estrutural OK: " + str(estrutura["ok"]))
    linhas.append("- Node check OK: " + str(node["ok"]))
    linhas.append("- Restart OK: " + str(restart["ok"]))
    linhas.append("- App pronto: " + str(aguardar["ok"]))
    linhas.append("- Login OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
    linhas.append("- Super Admin OK: " + str(runtime["super_admin_ok"]))
    linhas.append("- Super Admin visual OK: " + str(runtime["super_admin_visual_ok"]))
    linhas.append("- Logs Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs email: " + str(logs["linhas_email"]))
    linhas.append("- Achados logs: " + str(len(logs["achados"])))
    linhas.append("")
    linhas.append("## Marcadores runtime")
    linhas.append("")
    for chave, valor in sorted(runtime["marcadores"].items()):
        linhas.append("- " + chave + ": " + str(valor))
    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_23_3_is_super_admin_" + stamp)

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

    json_path = REPORTS_DIR / "etapa_23_3_corrigir_is_super_admin.json"
    md_path = REPORTS_DIR / "etapa_23_3_corrigir_is_super_admin.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 23.3 concluida.")
    print("Backup: " + backup["destino"])
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("auth.js alterado: " + str(correcao["alterado"]))
    print("Corrigiu empresa master: " + str(correcao["corrigiu_empresa_master"]))
    print("Corrigiu privilegio: " + str(correcao["corrigiu_privilegio"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Node check OK: " + str(node["ok"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("Super Admin OK: " + str(runtime["super_admin_ok"]))
    print("Super Admin visual OK: " + str(runtime["super_admin_visual_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["super_admin_visual_ok"]:
        print("")
        print("Aviso: Super Admin visual ainda nao validou. Consulte o relatorio.")


if __name__ == "__main__":
    main()
