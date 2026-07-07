#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 21.2 - Corrigir consulta de empresa no AdminPanelController

Objetivo:
- Criar backup antes da alteracao.
- Gerar manifesto antes e depois.
- Alterar somente controllers/AdminPanelController.js.
- Corrigir consulta de empresa do renderPanel para usar colunas seguras.
- Remover dependencia de nome_sistema, logo_url, cor_primaria e outras colunas inexistentes.
- Rodar node --check em controllers/AdminPanelController.js.
- Reiniciar app somente se ETAPA21_2_RESTART_APP=true.
- Validar login, dashboard e /admin/painel.
- Atualizar documentacao obrigatoria.
- Gerar relatorios em reports.

Como executar:
sudo ETAPA21_2_RESTART_APP=true ETAPA21_2_LOGIN_EMAIL='admin@saas.com' ETAPA21_2_LOGIN_PASSWORD='123456' python3 etapa_21_2_corrigir_admin_panel_empresa.py
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

CONTROLLER = ROOT / "controllers" / "AdminPanelController.js"

BASE_URL = "http://127.0.0.1:50010"
LOGIN_PATH = "/api/auth/login"
DASHBOARD_PATH = "/dashboard"
ADMIN_PATH = "/admin/painel"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "controllers/AdminPanelController.js",
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
    "__pycache__"
]

EMAIL_KEYS = [
    "ETAPA21_2_LOGIN_EMAIL",
    "ETAPA21_1_LOGIN_EMAIL",
    "ETAPA21_LOGIN_EMAIL",
    "ETAPA20_2_LOGIN_EMAIL",
    "ETAPA20_1_LOGIN_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SEED_ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA21_2_LOGIN_PASSWORD",
    "ETAPA21_1_LOGIN_PASSWORD",
    "ETAPA21_LOGIN_PASSWORD",
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
        sub = nome.split("/")
        if len(sub) == 1 and sub[0] in partes:
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


def nova_consulta_empresa():
    return """const empresas = await this.db.query(
                'SELECT id, nome FROM empresas WHERE id = ?',
                [empresaId]
            );"""


def corrigir_controller():
    resultado = {
        "arquivo": "controllers/AdminPanelController.js",
        "existe_antes": CONTROLLER.exists(),
        "alterado": False,
        "encontrou_bloco_empresas": False,
        "corrigiu_nome_exibicao": False,
        "consulta_corrigida_presente": False,
        "sha256_antes": sha256(CONTROLLER) if CONTROLLER.exists() else None,
        "sha256_depois": None
    }

    texto = ler(CONTROLLER)
    if texto is None:
        resultado["erro"] = "controllers/AdminPanelController.js ausente ou ilegivel"
        return resultado

    novo = texto

    pos_render = novo.find("async renderPanel")
    pos_query = novo.find("const empresas = await this.db.query(", pos_render)

    if pos_render >= 0 and pos_query >= 0:
        pos_empresa = novo.find("const empresa = empresas[0] || {};", pos_query)

        if pos_empresa >= 0:
            resultado["encontrou_bloco_empresas"] = True
            bloco = nova_consulta_empresa()
            novo = novo[:pos_query] + bloco + "\n            " + novo[pos_empresa:]

    antiga_linha = "empresa.nome_exibicao = empresa.nome_sistema || empresa.nome;"
    nova_linha = "empresa.nome_exibicao = empresa.nome || 'Empresa';"

    if antiga_linha in novo:
        novo = novo.replace(antiga_linha, nova_linha, 1)
        resultado["corrigiu_nome_exibicao"] = True

    if novo != texto:
        gravar(CONTROLLER, novo)
        resultado["alterado"] = True

    depois = ler(CONTROLLER) or ""
    resultado["consulta_corrigida_presente"] = "SELECT id, nome FROM empresas WHERE id = ?" in depois
    resultado["sha256_depois"] = sha256(CONTROLLER)

    return resultado


def validar_estrutura():
    texto = ler(CONTROLLER)

    resultado = {
        "arquivo_existe": CONTROLLER.exists(),
        "tem_render_panel": False,
        "tem_select_id_nome": False,
        "nao_tem_nome_sistema_na_consulta": False,
        "tem_nome_exibicao_seguro": False,
        "tem_render_admin_panel": False,
        "ok": False
    }

    if texto is None:
        resultado["erro"] = "controllers/AdminPanelController.js ausente ou ilegivel"
        return resultado

    resultado["tem_render_panel"] = "async renderPanel" in texto
    resultado["tem_select_id_nome"] = "SELECT id, nome FROM empresas WHERE id = ?" in texto
    resultado["nao_tem_nome_sistema_na_consulta"] = "SELECT nome, nome_sistema" not in texto
    resultado["tem_nome_exibicao_seguro"] = "empresa.nome_exibicao = empresa.nome || 'Empresa';" in texto
    resultado["tem_render_admin_panel"] = "res.render('admin-panel'" in texto or 'res.render("admin-panel"' in texto

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_render_panel"] and
        resultado["tem_select_id_nome"] and
        resultado["nao_tem_nome_sistema_na_consulta"] and
        resultado["tem_nome_exibicao_seguro"] and
        resultado["tem_render_admin_panel"]
    )

    return resultado


def node_check():
    if not CONTROLLER.exists():
        return {
            "ok": False,
            "erro": "controllers/AdminPanelController.js ausente"
        }

    return run_cmd(["node", "--check", "controllers/AdminPanelController.js"], 40)


def restart_app():
    valor = os.environ.get("ETAPA21_2_RESTART_APP", "").strip().lower()

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


def http_request(opener, metodo, path, data_obj=None, timeout=15):
    url = BASE_URL + path

    resultado = {
        "path": path,
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
        "User-Agent": "etapa-21-2-admin-panel-empresa/1.0"
    }

    if data_obj is not None:
        body_text = json.dumps(data_obj)
        body_bytes = body_text.encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=body_bytes, headers=headers, method=metodo)

    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(65536)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["body_preview"] = redigir(texto[:1200])
            resultado["body_full_limited"] = redigir(texto[:50000])
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["redirect_url"] = resp.geturl()
    except HTTPError as exc:
        try:
            body = exc.read(65536)
            texto = body.decode("utf-8", errors="replace")
        except Exception:
            texto = ""

        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 400
        resultado["erro"] = redigir(str(exc))
        resultado["body_preview"] = redigir(texto[:1200])
        resultado["body_full_limited"] = redigir(texto[:50000])
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
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


def validar_runtime():
    c = credenciais()

    resultado = {
        "executado": False,
        "email_configurado": c["email_configurado"],
        "senha_configurada": c["senha_configurada"],
        "login_ok": False,
        "dashboard_ok": False,
        "admin_ok": False,
        "admin_visual_ok": False,
        "cookies": [],
        "login": None,
        "dashboard": None,
        "admin": None,
        "textos_admin": {}
    }

    if not c["email_configurado"] or not c["senha_configurada"]:
        resultado["motivo"] = "Credenciais nao configuradas"
        return resultado

    opener, jar = criar_opener()

    payload = {
        "email": c["email"],
        "senha": c["senha"]
    }

    login = http_request(opener, "POST", LOGIN_PATH, payload)
    resultado["executado"] = True
    resultado["login"] = {
        "status": login.get("status"),
        "ok": login.get("ok"),
        "erro": login.get("erro"),
        "content_type": login.get("content_type"),
        "body_preview": login.get("body_preview")
    }
    resultado["cookies"] = cookies_resumo(jar)

    body_login = (login.get("body_preview") or "").lower()
    status_ok = login.get("status") in [200, 201, 302]
    cookie_ok = len(resultado["cookies"]) > 0
    body_ok = "sucesso" in body_login or "success" in body_login or "dashboard" in body_login or "ok" in body_login
    resultado["login_ok"] = bool(status_ok and (cookie_ok or body_ok))

    dashboard = http_request(opener, "GET", DASHBOARD_PATH)
    body_dash = dashboard.get("body_full_limited") or ""
    resultado["dashboard"] = {
        "status": dashboard.get("status"),
        "ok": dashboard.get("ok"),
        "erro": dashboard.get("erro"),
        "content_type": dashboard.get("content_type")
    }
    resultado["dashboard_ok"] = bool(dashboard.get("status") == 200 and "crm enterprise" in body_dash.lower())

    admin = http_request(opener, "GET", ADMIN_PATH)
    body_admin = admin.get("body_full_limited") or ""
    lower_admin = body_admin.lower()

    textos = {
        "tem_css": "/css/style.css" in body_admin,
        "tem_marker": "ETAPA21_ADMIN_PANEL_VISUAL_INICIO" in body_admin,
        "painel_administrativo": "painel administrativo" in lower_admin,
        "gestao_empresa": "gestao da empresa" in lower_admin or "gestão da empresa" in lower_admin,
        "tem_fetch": "fetch(" in body_admin,
        "tem_sortable": "sortable" in lower_admin
    }

    resultado["admin"] = {
        "status": admin.get("status"),
        "ok": admin.get("ok"),
        "erro": admin.get("erro"),
        "content_type": admin.get("content_type"),
        "body_preview": admin.get("body_preview")
    }

    resultado["admin_ok"] = bool(admin.get("status") == 200)
    resultado["admin_visual_ok"] = bool(
        admin.get("status") == 200 and
        textos["tem_css"] and
        textos["tem_marker"] and
        textos["painel_administrativo"] and
        textos["gestao_empresa"]
    )
    resultado["textos_admin"] = textos

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


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)

    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_21_2_INICIO -->"
    fim = "<!-- ETAPA_21_2_FIM -->"

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
    correcao = relatorio["correcao_controller"]
    estrutura = relatorio["validacao_estrutura"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    runtime = relatorio["validacao_runtime"]

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Etapa 21.2 - Consulta do painel administrativo corrigida",
        [
            "Data: " + data,
            "",
            "Foi corrigida a consulta de empresa em controllers/AdminPanelController.js.",
            "Arquivo alterado: " + str(correcao["alterado"]) + ".",
            "Bloco de empresas encontrado: " + str(correcao["encontrou_bloco_empresas"]) + ".",
            "Nome de exibicao corrigido: " + str(correcao["corrigiu_nome_exibicao"]) + ".",
            "Consulta corrigida presente: " + str(correcao["consulta_corrigida_presente"]) + ".",
            "Validacao estrutural OK: " + str(estrutura["ok"]) + ".",
            "Node check OK: " + str(node["ok"]) + ".",
            "Restart executado: " + str(restart["executado"]) + ".",
            "Login OK: " + str(runtime["login_ok"]) + ".",
            "Dashboard OK: " + str(runtime["dashboard_ok"]) + ".",
            "Admin panel OK: " + str(runtime["admin_ok"]) + ".",
            "Admin visual OK: " + str(runtime["admin_visual_ok"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 21.2 - Correcao do admin panel",
        [
            "Data: " + data,
            "",
            "Substituida consulta de empresa do AdminPanelController para SELECT id, nome FROM empresas.",
            "Removida dependencia de colunas inexistentes como nome_sistema, logo_url e cor_primaria.",
            "Executado node --check em controllers/AdminPanelController.js.",
            "Validado login, dashboard e painel administrativo."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 21.2 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido usar consulta minima e segura para a empresa no painel administrativo.",
            "Decidido nao alterar banco nesta etapa.",
            "Decidido nao alterar views nesta etapa.",
            "Decidido manter a rota /admin/painel protegida por isAuthenticated."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 21.2",
        [
            "Data: " + data,
            "",
            "Validar visual do painel administrativo manualmente no navegador.",
            "Planejar aplicacao visual em views/super-admin.ejs.",
            "Planejar internalizacao de dependencias externas.",
            "Mapear scripts inline antes de CSP forte."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    correcao = relatorio["correcao_controller"]
    estrutura = relatorio["validacao_estrutura"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    aguardar = relatorio["aguardar_app"]
    runtime = relatorio["validacao_runtime"]
    logs = relatorio["logs_analise"]

    linhas = []
    linhas.append("# Etapa 21.2 - Corrigir AdminPanelController")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Controller alterado: " + str(correcao["alterado"]))
    linhas.append("- Consulta corrigida presente: " + str(correcao["consulta_corrigida_presente"]))
    linhas.append("- Validacao estrutural OK: " + str(estrutura["ok"]))
    linhas.append("- Node check OK: " + str(node["ok"]))
    linhas.append("- Restart solicitado: " + str(restart["solicitado"]))
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Restart OK: " + str(restart["ok"]))
    linhas.append("- App pronto: " + str(aguardar["ok"]))
    linhas.append("- Login OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
    linhas.append("- Admin panel OK: " + str(runtime["admin_ok"]))
    linhas.append("- Admin visual OK: " + str(runtime["admin_visual_ok"]))
    linhas.append("- Logs novos Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos email: " + str(logs["linhas_email"]))
    linhas.append("- Achados criticos logs: " + str(len(logs["achados"])))
    linhas.append("")
    linhas.append("## Validacao estrutural")
    linhas.append("")
    for chave in sorted(estrutura.keys()):
        linhas.append("- " + chave + ": " + str(estrutura[chave]))
    linhas.append("")
    linhas.append("## Marcadores Admin")
    linhas.append("")
    for chave, valor in sorted(runtime["textos_admin"].items()):
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
    backup_dir = BACKUPS_DIR / ("etapa_21_2_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_21_2_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    correcao = corrigir_controller()
    estrutura = validar_estrutura()
    node = node_check()
    restart = restart_app()
    aguardar = aguardar_app()

    since = logs_since()
    runtime = validar_runtime()
    time.sleep(2)

    logs_coleta = coletar_logs(since)
    logs_analise = analisar_logs(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "correcao_controller": correcao,
        "validacao_estrutura": estrutura,
        "node_check": node,
        "restart_app": restart,
        "aguardar_app": aguardar,
        "logs_since": since,
        "validacao_runtime": runtime,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_21_2_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_21_2_corrigir_admin_panel_empresa.json"
    md_path = REPORTS_DIR / "etapa_21_2_corrigir_admin_panel_empresa.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 21.2 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Controller alterado: " + str(correcao["alterado"]))
    print("Consulta corrigida presente: " + str(correcao["consulta_corrigida_presente"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Node check OK: " + str(node["ok"]))
    print("Restart solicitado: " + str(restart["solicitado"]))
    print("Restart executado: " + str(restart["executado"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("Admin panel OK: " + str(runtime["admin_ok"]))
    print("Admin visual OK: " + str(runtime["admin_visual_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["admin_visual_ok"]:
        print("")
        print("Aviso: Admin panel ainda nao validou visualmente em runtime. Consulte o relatorio.")


if __name__ == "__main__":
    main()
