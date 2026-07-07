#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 23.1 - Validar e sincronizar runtime do Super Admin

Objetivo:
- Comparar views/super-admin.ejs local com o arquivo dentro do container.
- Copiar a view local para o container se os hashes forem diferentes.
- Reiniciar app por padrao, exceto se ETAPA23_1_RESTART_APP=false.
- Validar login, dashboard e /super-admin.
- Validar marcadores visuais da Etapa 22 em runtime.
- Atualizar documentacao obrigatoria.
- Gerar relatorios JSON e Markdown.

Como executar:
sudo ETAPA23_1_LOGIN_EMAIL='admin@saas.com' ETAPA23_1_LOGIN_PASSWORD='123456' python3 etapa_23_1_validar_runtime_super_admin.py

Para nao reiniciar:
sudo ETAPA23_1_RESTART_APP=false ETAPA23_1_LOGIN_EMAIL='admin@saas.com' ETAPA23_1_LOGIN_PASSWORD='123456' python3 etapa_23_1_validar_runtime_super_admin.py
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

LOCAL_VIEW = ROOT / "views" / "super-admin.ejs"
CONTAINER_VIEW = "/usr/src/app/views/super-admin.ejs"
CONTAINER_SERVICE = "app"

BASE_URL = "http://127.0.0.1:50010"
LOGIN_API = "/api/auth/login"
DASHBOARD_PAGE = "/dashboard"
SUPER_ADMIN_PAGE = "/super-admin"
CSS_PAGE = "/css/style.css"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "views/super-admin.ejs",
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
    "ETAPA23_1_LOGIN_EMAIL",
    "ETAPA23_LOGIN_EMAIL",
    "ETAPA22_1_LOGIN_EMAIL",
    "ETAPA22_LOGIN_EMAIL",
    "ETAPA21_3_LOGIN_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SEED_ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA23_1_LOGIN_PASSWORD",
    "ETAPA23_LOGIN_PASSWORD",
    "ETAPA22_1_LOGIN_PASSWORD",
    "ETAPA22_LOGIN_PASSWORD",
    "ETAPA21_3_LOGIN_PASSWORD",
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


def sha256_file(path):
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
                    "sha256": sha256_file(p)
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


def obter_container_id():
    r = run_cmd(["docker", "compose", "ps", "-q", CONTAINER_SERVICE], 30)
    cid = (r.get("stdout") or "").strip().splitlines()

    if r.get("ok") and cid:
        return {
            "ok": True,
            "container_id": cid[0],
            "metodo": "docker compose ps",
            "resultado": r
        }

    r2 = run_cmd(["docker", "ps", "--filter", "name=whatsapp_bot_app", "--format", "{{.ID}}"], 30)
    cid2 = (r2.get("stdout") or "").strip().splitlines()

    if r2.get("ok") and cid2:
        return {
            "ok": True,
            "container_id": cid2[0],
            "metodo": "docker ps filter",
            "resultado": r2
        }

    return {
        "ok": False,
        "container_id": "",
        "metodo": "nenhum",
        "resultado": {
            "compose": r,
            "docker_ps": r2
        }
    }


def hash_container(container_id):
    if not container_id:
        return {
            "ok": False,
            "sha256": None,
            "resultado": None
        }

    r = run_cmd(["docker", "exec", container_id, "sha256sum", CONTAINER_VIEW], 30)

    sha = None
    if r.get("ok") and r.get("stdout"):
        sha = r["stdout"].strip().split()[0]

    return {
        "ok": bool(r.get("ok") and sha),
        "sha256": sha,
        "resultado": r
    }


def sincronizar_view():
    resultado = {
        "local_existe": LOCAL_VIEW.exists(),
        "local_sha256": sha256_file(LOCAL_VIEW) if LOCAL_VIEW.exists() else None,
        "container": obter_container_id(),
        "container_sha256_antes": None,
        "container_sha256_depois": None,
        "hashes_iguais_antes": False,
        "hashes_iguais_depois": False,
        "copiou_para_container": False,
        "docker_cp": None,
        "ok": False
    }

    if not resultado["local_existe"]:
        resultado["erro"] = "views/super-admin.ejs local ausente"
        return resultado

    if not resultado["container"]["ok"]:
        resultado["erro"] = "container app nao encontrado"
        return resultado

    cid = resultado["container"]["container_id"]

    hc_antes = hash_container(cid)
    resultado["container_sha256_antes"] = hc_antes.get("sha256")
    resultado["hashes_iguais_antes"] = bool(resultado["local_sha256"] and resultado["local_sha256"] == resultado["container_sha256_antes"])

    if not resultado["hashes_iguais_antes"]:
        rcp = run_cmd(["docker", "cp", str(LOCAL_VIEW), cid + ":" + CONTAINER_VIEW], 60)
        resultado["docker_cp"] = rcp
        resultado["copiou_para_container"] = bool(rcp.get("ok"))

    hc_depois = hash_container(cid)
    resultado["container_sha256_depois"] = hc_depois.get("sha256")
    resultado["hashes_iguais_depois"] = bool(resultado["local_sha256"] and resultado["local_sha256"] == resultado["container_sha256_depois"])
    resultado["ok"] = resultado["hashes_iguais_depois"]

    return resultado


def restart_app():
    valor = os.environ.get("ETAPA23_1_RESTART_APP", "true").strip().lower()

    if valor in ["false", "0", "nao", "não", "no"]:
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


def http_request(opener, metodo, path, data_obj=None, timeout=20, limite=500000):
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
        "User-Agent": "etapa-23-1-super-admin-runtime/1.0"
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
        "css_ok": False,
        "cookies": [],
        "login": None,
        "dashboard": None,
        "super_admin": None,
        "css": None,
        "marcadores": {}
    }

    opener, jar = criar_opener()

    css = http_request(opener, "GET", CSS_PAGE, None, limite=200000)
    css_body = css.get("body_limited") or ""
    resultado["css"] = resumo_http(css)
    resultado["css_ok"] = bool(css.get("status") == 200 and ".er-card" in css_body and ".er-btn" in css_body)

    if not c["email_configurado"] or not c["senha_configurada"]:
        resultado["motivo"] = "Credenciais nao configuradas"
        return resultado

    login = http_request(opener, "POST", LOGIN_API, {
        "email": c["email"],
        "senha": c["senha"]
    }, limite=100000)

    resultado["executado"] = True
    resultado["login"] = resumo_http(login)
    resultado["cookies"] = cookies_resumo(jar)

    body_login = (login.get("body_limited") or "").lower()
    resultado["login_ok"] = bool(
        login.get("status") in [200, 201, 302] and
        ("success" in body_login or "sucesso" in body_login or len(resultado["cookies"]) > 0)
    )

    dashboard = http_request(opener, "GET", DASHBOARD_PAGE, None, limite=300000)
    dash_body = dashboard.get("body_limited") or ""
    resultado["dashboard"] = resumo_http(dashboard)
    resultado["dashboard_ok"] = bool(dashboard.get("status") == 200 and "crm enterprise" in dash_body.lower())

    super_admin = http_request(opener, "GET", SUPER_ADMIN_PAGE, None, limite=500000)
    body = super_admin.get("body_limited") or ""
    lower = body.lower()

    marcadores = {
        "css_link": "/css/style.css" in body,
        "etapa22_inicio": "ETAPA22_SUPER_ADMIN_VISUAL_INICIO" in body,
        "etapa22_fim": "ETAPA22_SUPER_ADMIN_VISUAL_FIM" in body,
        "gestao_plataforma": "gestao geral da plataforma" in lower or "gestão geral da plataforma" in lower,
        "super_admin_texto": "super admin" in lower,
        "fetch": "fetch(" in body
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
        marcadores["super_admin_texto"]
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

    ini = "<!-- ETAPA_23_1_INICIO -->"
    fim = "<!-- ETAPA_23_1_FIM -->"

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
    sync = relatorio["sincronizacao"]
    runtime = relatorio["runtime"]
    logs = relatorio["logs_analise"]

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Etapa 23.1 - Runtime Super Admin sincronizado",
        [
            "Data: " + data,
            "",
            "Foi validado e sincronizado views/super-admin.ejs no container.",
            "Hashes iguais antes: " + str(sync["hashes_iguais_antes"]) + ".",
            "Copiou para container: " + str(sync["copiou_para_container"]) + ".",
            "Hashes iguais depois: " + str(sync["hashes_iguais_depois"]) + ".",
            "CSS runtime OK: " + str(runtime["css_ok"]) + ".",
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
        "Etapa 23.1 - Super Admin sincronizado no runtime",
        [
            "Data: " + data,
            "",
            "Comparado hash local e hash do container para views/super-admin.ejs.",
            "Copiada a view para o container quando necessario.",
            "Validado /super-admin com marcadores visuais da Etapa 22.",
            "Gerados relatorios JSON e Markdown."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 23.1 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido sincronizar a view super-admin no container para eliminar divergencia entre arquivo local e runtime.",
            "Decidido nao alterar rotas, controllers, banco ou outras views nesta etapa.",
            "Decidido validar o HTML de /super-admin com limite ampliado de leitura."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 23.1",
        [
            "Data: " + data,
            "",
            "Executar novamente a Etapa 23 se desejar consolidar status geral final.",
            "Validar manualmente as telas no navegador.",
            "Planejar internalizacao de dependencias externas.",
            "Mapear scripts inline antes de CSP forte."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    sync = relatorio["sincronizacao"]
    restart = relatorio["restart_app"]
    aguardar = relatorio["aguardar_app"]
    runtime = relatorio["runtime"]
    logs = relatorio["logs_analise"]

    linhas = []
    linhas.append("# Etapa 23.1 - Validar runtime Super Admin")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Local existe: " + str(sync["local_existe"]))
    linhas.append("- Container encontrado: " + str(sync["container"]["ok"]))
    linhas.append("- Hash local: " + str(sync["local_sha256"]))
    linhas.append("- Hash container antes: " + str(sync["container_sha256_antes"]))
    linhas.append("- Hashes iguais antes: " + str(sync["hashes_iguais_antes"]))
    linhas.append("- Copiou para container: " + str(sync["copiou_para_container"]))
    linhas.append("- Hash container depois: " + str(sync["container_sha256_depois"]))
    linhas.append("- Hashes iguais depois: " + str(sync["hashes_iguais_depois"]))
    linhas.append("- Sincronizacao OK: " + str(sync["ok"]))
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Restart OK: " + str(restart["ok"]))
    linhas.append("- App pronto: " + str(aguardar["ok"]))
    linhas.append("- CSS OK: " + str(runtime["css_ok"]))
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
    backup_dir = BACKUPS_DIR / ("etapa_23_1_super_admin_runtime_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_23_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = logs_since()
    sync = sincronizar_view()
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
        "sincronizacao": sync,
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
    manifesto_depois_path = REPORTS_DIR / "etapa_23_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_23_1_validar_runtime_super_admin.json"
    md_path = REPORTS_DIR / "etapa_23_1_validar_runtime_super_admin.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 23.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Hashes iguais antes: " + str(sync["hashes_iguais_antes"]))
    print("Copiou para container: " + str(sync["copiou_para_container"]))
    print("Hashes iguais depois: " + str(sync["hashes_iguais_depois"]))
    print("Sincronizacao OK: " + str(sync["ok"]))
    print("Restart executado: " + str(restart["executado"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("CSS OK: " + str(runtime["css_ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("Super Admin OK: " + str(runtime["super_admin_ok"]))
    print("Super Admin visual OK: " + str(runtime["super_admin_visual_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["super_admin_visual_ok"]:
        print("")
        print("Aviso: Super Admin visual ainda nao validou em runtime. Consulte o relatorio.")


if __name__ == "__main__":
    main()
