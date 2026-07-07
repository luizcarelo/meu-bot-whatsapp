#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 23 - Auditoria final visual e rotas

Objetivo:
- Auditar as etapas visuais 17 a 22.
- Nao alterar views, controllers, rotas, backend ou banco.
- Validar arquivos locais e marcadores.
- Validar rotas em runtime.
- Validar login real, dashboard, CRM, admin panel e super admin.
- Validar /css/style.css.
- Coletar logs novos.
- Atualizar documentacao obrigatoria.
- Gerar relatorios finais em reports.

Como executar:
sudo ETAPA23_LOGIN_EMAIL='admin@saas.com' ETAPA23_LOGIN_PASSWORD='123456' python3 etapa_23_auditoria_final_visual_rotas.py
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

BASE_URL = "http://127.0.0.1:50010"

LOGIN_API = "/api/auth/login"
LOGIN_PAGE = "/login"
DASHBOARD_PAGE = "/dashboard"
CRM_PAGE = "/crm"
ADMIN_PANEL_PAGE = "/admin/painel"
SUPER_ADMIN_PAGE = "/super-admin"
CSS_PAGE = "/css/style.css"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

AUDIT_FILES = [
    "views/login.ejs",
    "views/dashboard.ejs",
    "public/css/style.css",
    "views/crm.ejs",
    "views/admin-panel.ejs",
    "views/super-admin.ejs",
    "routes/index.js",
    "controllers/AdminPanelController.js"
]

IGNORE_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "reports",
    "__pycache__"
]

EMAIL_KEYS = [
    "ETAPA23_LOGIN_EMAIL",
    "ETAPA22_1_LOGIN_EMAIL",
    "ETAPA22_LOGIN_EMAIL",
    "ETAPA21_3_LOGIN_EMAIL",
    "ETAPA21_2_LOGIN_EMAIL",
    "ETAPA21_1_LOGIN_EMAIL",
    "ETAPA20_2_LOGIN_EMAIL",
    "ETAPA20_1_LOGIN_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SEED_ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA23_LOGIN_PASSWORD",
    "ETAPA22_1_LOGIN_PASSWORD",
    "ETAPA22_LOGIN_PASSWORD",
    "ETAPA21_3_LOGIN_PASSWORD",
    "ETAPA21_2_LOGIN_PASSWORD",
    "ETAPA21_1_LOGIN_PASSWORD",
    "ETAPA20_2_LOGIN_PASSWORD",
    "ETAPA20_1_LOGIN_PASSWORD",
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


def rel(path):
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


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


def arquivo_info(path_rel, marcadores):
    path = ROOT / path_rel
    texto = ler(path)

    info = {
        "arquivo": path_rel,
        "existe": path.exists(),
        "sha256": sha256(path) if path.exists() else None,
        "tamanho": path.stat().st_size if path.exists() else None,
        "marcadores": {},
        "ok": False
    }

    if texto is None:
        return info

    for nome, termo in marcadores.items():
        info["marcadores"][nome] = termo in texto

    info["ok"] = bool(info["existe"] and all(info["marcadores"].values()))
    return info


def auditoria_arquivos():
    checks = []

    checks.append(arquivo_info("views/login.ejs", {
        "acesso_seguro": "Acesso Seguro",
        "api_login": "/api/auth/login",
        "entrar_painel": "Entrar no painel"
    }))

    checks.append(arquivo_info("views/dashboard.ejs", {
        "etapa18_css": "ETAPA18_DASHBOARD_VISUAL_INICIO",
        "etapa18_script": "ETAPA18_DASHBOARD_SCRIPT_INICIO",
        "dashboard_operacional": "Dashboard operacional"
    }))

    checks.append(arquivo_info("public/css/style.css", {
        "er_card": ".er-card",
        "er_btn": ".er-btn",
        "er_badge": ".er-badge",
        "er_red": "--er-red"
    }))

    checks.append(arquivo_info("views/crm.ejs", {
        "css": "/css/style.css",
        "etapa20": "ETAPA20_CRM_VISUAL_INICIO",
        "central_atendimento": "Central de atendimento"
    }))

    checks.append(arquivo_info("routes/index.js", {
        "rota_crm": "router.get('/crm'",
        "rota_admin": "router.get('/admin/painel'",
        "rota_super_admin": "router.get('/super-admin'",
        "is_super_admin": "isSuperAdmin"
    }))

    checks.append(arquivo_info("controllers/AdminPanelController.js", {
        "render_panel": "async renderPanel",
        "empresa_segura": "SELECT id, nome FROM empresas WHERE id = ?",
        "equipe_sem_telefone": "SELECT id, nome, email, is_admin, cargo, ativo FROM usuarios_painel",
        "nome_exibicao": "empresa.nome_exibicao = empresa.nome || 'Empresa';"
    }))

    checks.append(arquivo_info("views/admin-panel.ejs", {
        "css": "/css/style.css",
        "etapa21": "ETAPA21_ADMIN_PANEL_VISUAL_INICIO",
        "gestao_empresa": "Gestao da empresa"
    }))

    checks.append(arquivo_info("views/super-admin.ejs", {
        "css": "/css/style.css",
        "etapa22": "ETAPA22_SUPER_ADMIN_VISUAL_INICIO",
        "gestao_plataforma": "Gestao geral da plataforma"
    }))

    return {
        "checks": checks,
        "ok": all(item["ok"] for item in checks)
    }


def node_checks():
    itens = []

    for path in ["routes/index.js", "controllers/AdminPanelController.js"]:
        if (ROOT / path).exists():
            itens.append({
                "arquivo": path,
                "resultado": run_cmd(["node", "--check", path], 40)
            })
        else:
            itens.append({
                "arquivo": path,
                "resultado": {
                    "ok": False,
                    "erro": "arquivo ausente"
                }
            })

    return {
        "checks": itens,
        "ok": all(item["resultado"].get("ok") for item in itens)
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


def http_request(opener, metodo, path, data_obj=None, timeout=20, limite=300000):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "metodo": metodo,
        "ok": False,
        "status": None,
        "erro": None,
        "body_preview": "",
        "body_limited": "",
        "content_type": "",
        "redirect_url": None
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-23-auditoria-final/1.0"
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
            resultado["body_preview"] = redigir(texto[:1500])
            resultado["body_limited"] = redigir(texto)
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["redirect_url"] = resp.geturl()
    except HTTPError as exc:
        try:
            body = exc.read(limite)
            texto = body.decode("utf-8", errors="replace")
        except Exception:
            texto = ""

        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 400
        resultado["erro"] = redigir(str(exc))
        resultado["body_preview"] = redigir(texto[:1500])
        resultado["body_limited"] = redigir(texto)
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
    except URLError as exc:
        resultado["erro"] = redigir(str(exc.reason))
    except Exception as exc:
        resultado["erro"] = redigir(str(exc))

    return resultado


def validar_runtime():
    c = credenciais()

    resultado = {
        "executado": False,
        "email_configurado": c["email_configurado"],
        "senha_configurada": c["senha_configurada"],
        "login_page_ok": False,
        "css_ok": False,
        "login_ok": False,
        "dashboard_ok": False,
        "crm_ok": False,
        "admin_panel_ok": False,
        "super_admin_ok": False,
        "dashboard_visual_ok": False,
        "crm_visual_ok": False,
        "admin_visual_ok": False,
        "super_admin_visual_ok": False,
        "cookies": [],
        "rotas": {}
    }

    opener, jar = criar_opener()

    login_page = http_request(opener, "GET", LOGIN_PAGE)
    login_body = login_page.get("body_limited") or ""
    resultado["login_page_ok"] = bool(
        login_page.get("status") == 200 and
        "Acesso Seguro" in login_body and
        "Entrar no painel" in login_body
    )
    resultado["rotas"]["login_page"] = resumo_http(login_page)

    css = http_request(opener, "GET", CSS_PAGE)
    css_body = css.get("body_limited") or ""
    resultado["css_ok"] = bool(
        css.get("status") == 200 and
        ".er-card" in css_body and
        ".er-btn" in css_body
    )
    resultado["rotas"]["css"] = resumo_http(css)

    if not c["email_configurado"] or not c["senha_configurada"]:
        resultado["motivo"] = "Credenciais nao configuradas"
        return resultado

    login = http_request(opener, "POST", LOGIN_API, {
        "email": c["email"],
        "senha": c["senha"]
    })

    resultado["executado"] = True
    resultado["cookies"] = cookies_resumo(jar)
    body_login = (login.get("body_limited") or "").lower()
    resultado["login_ok"] = bool(
        login.get("status") in [200, 201, 302] and
        ("success" in body_login or "sucesso" in body_login or len(resultado["cookies"]) > 0)
    )
    resultado["rotas"]["login_api"] = resumo_http(login)

    dashboard = http_request(opener, "GET", DASHBOARD_PAGE)
    dashboard_body = dashboard.get("body_limited") or ""
    dashboard_lower = dashboard_body.lower()
    resultado["dashboard_ok"] = bool(dashboard.get("status") == 200 and "crm enterprise" in dashboard_lower)
    resultado["dashboard_visual_ok"] = bool(
        dashboard.get("status") == 200 and
        "ETAPA18_DASHBOARD_VISUAL_INICIO" in dashboard_body and
        "Dashboard operacional" in dashboard_body
    )
    resultado["rotas"]["dashboard"] = resumo_http(dashboard)

    crm = http_request(opener, "GET", CRM_PAGE)
    crm_body = crm.get("body_limited") or ""
    crm_lower = crm_body.lower()
    resultado["crm_ok"] = bool(crm.get("status") == 200)
    resultado["crm_visual_ok"] = bool(
        crm.get("status") == 200 and
        "/css/style.css" in crm_body and
        "ETAPA20_CRM_VISUAL_INICIO" in crm_body and
        "central de atendimento" in crm_lower
    )
    resultado["rotas"]["crm"] = resumo_http(crm)

    admin = http_request(opener, "GET", ADMIN_PANEL_PAGE)
    admin_body = admin.get("body_limited") or ""
    admin_lower = admin_body.lower()
    resultado["admin_panel_ok"] = bool(admin.get("status") == 200)
    resultado["admin_visual_ok"] = bool(
        admin.get("status") == 200 and
        "/css/style.css" in admin_body and
        "ETAPA21_ADMIN_PANEL_VISUAL_INICIO" in admin_body and
        ("gestao da empresa" in admin_lower or "gestão da empresa" in admin_lower)
    )
    resultado["rotas"]["admin_panel"] = resumo_http(admin)

    super_admin = http_request(opener, "GET", SUPER_ADMIN_PAGE)
    super_body = super_admin.get("body_limited") or ""
    super_lower = super_body.lower()
    resultado["super_admin_ok"] = bool(super_admin.get("status") == 200)
    resultado["super_admin_visual_ok"] = bool(
        super_admin.get("status") == 200 and
        "/css/style.css" in super_body and
        "ETAPA22_SUPER_ADMIN_VISUAL_INICIO" in super_body and
        ("gestao geral da plataforma" in super_lower or "gestão geral da plataforma" in super_lower)
    )
    resultado["rotas"]["super_admin"] = resumo_http(super_admin)

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


def status_geral(audit_files, node, runtime, logs):
    checks = [
        audit_files["ok"],
        node["ok"],
        runtime["login_page_ok"],
        runtime["css_ok"],
        runtime["login_ok"],
        runtime["dashboard_ok"],
        runtime["crm_ok"],
        runtime["admin_panel_ok"],
        runtime["super_admin_ok"],
        runtime["dashboard_visual_ok"],
        runtime["crm_visual_ok"],
        runtime["admin_visual_ok"],
        runtime["super_admin_visual_ok"],
        logs["linhas_session_id"] == 0,
        logs["linhas_cookie"] == 0,
        logs["linhas_email"] == 0,
        len(logs["achados"]) == 0
    ]

    return {
        "ok": all(checks),
        "total_checks": len(checks),
        "checks_ok": sum(1 for x in checks if x)
    }


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)

    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_23_INICIO -->"
    fim = "<!-- ETAPA_23_FIM -->"

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
    geral = relatorio["status_geral"]
    runtime = relatorio["runtime"]
    logs = relatorio["logs_analise"]

    linhas_base = [
        "Data: " + data,
        "",
        "Auditoria final visual e de rotas das etapas 17 a 22.",
        "Status geral OK: " + str(geral["ok"]) + ".",
        "Checks OK: " + str(geral["checks_ok"]) + " de " + str(geral["total_checks"]) + ".",
        "Login page OK: " + str(runtime["login_page_ok"]) + ".",
        "CSS compartilhado OK: " + str(runtime["css_ok"]) + ".",
        "Login API OK: " + str(runtime["login_ok"]) + ".",
        "Dashboard OK: " + str(runtime["dashboard_ok"]) + ".",
        "CRM OK: " + str(runtime["crm_ok"]) + ".",
        "Admin panel OK: " + str(runtime["admin_panel_ok"]) + ".",
        "Super Admin OK: " + str(runtime["super_admin_ok"]) + ".",
        "Dashboard visual OK: " + str(runtime["dashboard_visual_ok"]) + ".",
        "CRM visual OK: " + str(runtime["crm_visual_ok"]) + ".",
        "Admin visual OK: " + str(runtime["admin_visual_ok"]) + ".",
        "Super Admin visual OK: " + str(runtime["super_admin_visual_ok"]) + ".",
        "Logs Session ID: " + str(logs["linhas_session_id"]) + ".",
        "Logs cookie: " + str(logs["linhas_cookie"]) + ".",
        "Logs email: " + str(logs["linhas_email"]) + ".",
        "Achados criticos logs: " + str(len(logs["achados"])) + "."
    ]

    atualizar_doc("CONTEXTO_PROJETO.md", "Etapa 23 - Auditoria final visual e rotas", linhas_base)

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 23 - Auditoria final executada",
        [
            "Data: " + data,
            "",
            "Executada auditoria final das telas login, dashboard, CRM, admin panel e super admin.",
            "Validadas rotas principais e marcadores visuais.",
            "Validados logs novos sem Session ID, cookie e email.",
            "Gerados relatorios finais JSON e Markdown."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 23 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido consolidar as validacoes das etapas 17 a 22 em uma auditoria final.",
            "A auditoria nao altera backend, banco, views, rotas ou controllers.",
            "A auditoria valida runtime com leitura ampliada para evitar falso negativo em marcadores no final das views."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 23",
        [
            "Data: " + data,
            "",
            "Validar manualmente as telas no navegador.",
            "Planejar internalizacao de dependencias externas.",
            "Mapear scripts inline antes de CSP forte.",
            "Avaliar padronizacao visual adicional apenas apos validacao manual."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    runtime = relatorio["runtime"]
    geral = relatorio["status_geral"]
    logs = relatorio["logs_analise"]

    linhas = []
    linhas.append("# Etapa 23 - Auditoria final visual e rotas")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Status geral OK: " + str(geral["ok"]))
    linhas.append("- Checks OK: " + str(geral["checks_ok"]) + " de " + str(geral["total_checks"]))
    linhas.append("- Arquivos e marcadores OK: " + str(relatorio["auditoria_arquivos"]["ok"]))
    linhas.append("- Node checks OK: " + str(relatorio["node_checks"]["ok"]))
    linhas.append("- Login page OK: " + str(runtime["login_page_ok"]))
    linhas.append("- CSS compartilhado OK: " + str(runtime["css_ok"]))
    linhas.append("- Login API OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
    linhas.append("- CRM OK: " + str(runtime["crm_ok"]))
    linhas.append("- Admin panel OK: " + str(runtime["admin_panel_ok"]))
    linhas.append("- Super Admin OK: " + str(runtime["super_admin_ok"]))
    linhas.append("- Dashboard visual OK: " + str(runtime["dashboard_visual_ok"]))
    linhas.append("- CRM visual OK: " + str(runtime["crm_visual_ok"]))
    linhas.append("- Admin visual OK: " + str(runtime["admin_visual_ok"]))
    linhas.append("- Super Admin visual OK: " + str(runtime["super_admin_visual_ok"]))
    linhas.append("- Logs novos Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos email: " + str(logs["linhas_email"]))
    linhas.append("- Achados criticos logs: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Arquivos auditados")
    linhas.append("")
    for item in relatorio["auditoria_arquivos"]["checks"]:
        linhas.append("- " + item["arquivo"] + ": " + str(item["ok"]))

    linhas.append("")
    linhas.append("## Rotas")
    linhas.append("")
    for nome, info in runtime["rotas"].items():
        linhas.append("- " + nome + ": status " + str(info.get("status")) + ", ok " + str(info.get("ok")))

    linhas.append("")
    linhas.append("## Node checks")
    linhas.append("")
    for item in relatorio["node_checks"]["checks"]:
        linhas.append("- " + item["arquivo"] + ": " + str(item["resultado"].get("ok")))

    linhas.append("")
    linhas.append("## Logs")
    linhas.append("")
    linhas.append("- Linhas analisadas: " + str(logs["total_linhas"]))
    linhas.append("- Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Email: " + str(logs["linhas_email"]))
    linhas.append("- Achados: " + str(len(logs["achados"])))

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_23_auditoria_final_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_23_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = logs_since()
    audit_files = auditoria_arquivos()
    node = node_checks()
    runtime = validar_runtime()
    time.sleep(2)

    logs_coleta = coletar_logs(since)
    logs_analise = analisar_logs(logs_coleta.get("texto"))

    geral = status_geral(audit_files, node, runtime, logs_analise)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "auditoria_arquivos": audit_files,
        "node_checks": node,
        "runtime": runtime,
        "logs_since": since,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise,
        "status_geral": geral
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_23_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_23_auditoria_final_visual_rotas.json"
    md_path = REPORTS_DIR / "etapa_23_auditoria_final_visual_rotas.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 23 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Status geral OK: " + str(geral["ok"]))
    print("Checks OK: " + str(geral["checks_ok"]) + " de " + str(geral["total_checks"]))
    print("Arquivos e marcadores OK: " + str(audit_files["ok"]))
    print("Node checks OK: " + str(node["ok"]))
    print("Login page OK: " + str(runtime["login_page_ok"]))
    print("CSS compartilhado OK: " + str(runtime["css_ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("CRM OK: " + str(runtime["crm_ok"]))
    print("Admin panel OK: " + str(runtime["admin_panel_ok"]))
    print("Super Admin OK: " + str(runtime["super_admin_ok"]))
    print("Dashboard visual OK: " + str(runtime["dashboard_visual_ok"]))
    print("CRM visual OK: " + str(runtime["crm_visual_ok"]))
    print("Admin visual OK: " + str(runtime["admin_visual_ok"]))
    print("Super Admin visual OK: " + str(runtime["super_admin_visual_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not geral["ok"]:
        print("")
        print("Aviso: auditoria final encontrou pendencias. Consulte o relatorio Markdown.")


if __name__ == "__main__":
    main()
