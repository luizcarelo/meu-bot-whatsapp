#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 25.2 - Corrigir Alpine no Dashboard

Objetivo:
- Corrigir inicializacao do Alpine em views/dashboard.ejs.
- Garantir script Alpine com defer.
- Garantir appData disponivel em window antes da inicializacao.
- Manter shell seguro da Etapa 25.1.
- Nao alterar CRM, rotas, controllers ou banco.
- Validar dashboard e demais paginas principais.
- Atualizar documentacao obrigatoria.
- Gerar relatorios JSON e Markdown.

Como executar:
sudo ETAPA25_2_LOGIN_EMAIL='superadmin.teste@saas.local' ETAPA25_2_LOGIN_PASSWORD='123456' python3 etapa_25_2_corrigir_dashboard_alpine.py
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

DASHBOARD_FILE = ROOT / "views" / "dashboard.ejs"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "views/dashboard.ejs",
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

PAGES = [
    "/dashboard",
    "/crm",
    "/admin/painel",
    "/super-admin"
]

EMAIL_KEYS = [
    "ETAPA25_2_LOGIN_EMAIL",
    "ETAPA25_1_LOGIN_EMAIL",
    "ETAPA25_LOGIN_EMAIL",
    "ETAPA24_SUPER_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA25_2_LOGIN_PASSWORD",
    "ETAPA25_1_LOGIN_PASSWORD",
    "ETAPA25_LOGIN_PASSWORD",
    "ETAPA24_SUPER_PASSWORD",
    "LOGIN_PASSWORD",
    "ADMIN_PASSWORD",
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
        email = "superadmin.teste@saas.local"

    if not senha:
        senha = "123456"

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
            "stdout": redigir(proc.stdout.strip())[:40000],
            "stderr": redigir(proc.stderr.strip())[:40000],
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


def corrigir_alpine_defer(texto):
    novo = texto
    alterou = False

    # Caso exato conhecido.
    antigo = '<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>'
    novo_script = '<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>'

    if antigo in novo:
        novo = novo.replace(antigo, novo_script, 1)
        alterou = True

    # Caso tenha espacos/atributos diferentes, mas sem defer.
    padrao = re.compile(
        r'<script(?![^>]*\bdefer\b)([^>]*src=["\']https://cdn\.jsdelivr\.net/npm/alpinejs@3\.x\.x/dist/cdn\.min\.js["\'][^>]*)></script>',
        re.IGNORECASE
    )

    def repl(match):
        return '<script defer' + match.group(1) + '></script>'

    novo2, qtd = padrao.subn(repl, novo)
    if qtd > 0:
        novo = novo2
        alterou = True

    return novo, alterou


def garantir_window_appdata(texto):
    if "window.appData = appData" in texto:
        return texto, False

    if "function appData()" not in texto:
        return texto, False

    marcador_shell = "<!-- ETAPA25_1_SHELL_SEGURO_INICIO -->"
    pos_marker = texto.find(marcador_shell)

    bloco = """
<script id="etapa25-2-dashboard-appdata-global">
(function () {
    if (typeof appData === 'function') {
        window.appData = appData;
    }
})();
</script>
"""

    if pos_marker >= 0:
        novo = texto[:pos_marker] + bloco + "\n" + texto[pos_marker:]
        return novo, True

    pos_body = texto.rfind("</body>")
    if pos_body >= 0:
        novo = texto[:pos_body] + bloco + "\n" + texto[pos_body:]
        return novo, True

    return texto + "\n" + bloco + "\n", True


def aplicar_correcao():
    resultado = {
        "arquivo": "views/dashboard.ejs",
        "existe_antes": DASHBOARD_FILE.exists(),
        "alterado": False,
        "corrigiu_defer": False,
        "adicionou_window_appdata": False,
        "sha256_antes": sha256(DASHBOARD_FILE) if DASHBOARD_FILE.exists() else None,
        "sha256_depois": None
    }

    texto = ler(DASHBOARD_FILE)
    if texto is None:
        resultado["erro"] = "views/dashboard.ejs ausente ou ilegivel"
        return resultado

    novo = texto

    novo, defer_ok = corrigir_alpine_defer(novo)
    resultado["corrigiu_defer"] = defer_ok

    novo, appdata_ok = garantir_window_appdata(novo)
    resultado["adicionou_window_appdata"] = appdata_ok

    if novo != texto:
        gravar(DASHBOARD_FILE, novo)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256(DASHBOARD_FILE)
    return resultado


def validar_estrutura():
    texto = ler(DASHBOARD_FILE) or ""

    tem_alpine = "alpinejs@3.x.x/dist/cdn.min.js" in texto or "cdn.min.js" in texto
    alpine_defer = bool(
        re.search(
            r'<script[^>]*\bdefer\b[^>]*src=["\']https://cdn\.jsdelivr\.net/npm/alpinejs@3\.x\.x/dist/cdn\.min\.js["\'][^>]*></script>',
            texto,
            re.IGNORECASE
        )
    )

    script_sem_defer = bool(
        re.search(
            r'<script(?![^>]*\bdefer\b)[^>]*src=["\']https://cdn\.jsdelivr\.net/npm/alpinejs@3\.x\.x/dist/cdn\.min\.js["\'][^>]*></script>',
            texto,
            re.IGNORECASE
        )
    )

    resultado = {
        "arquivo_existe": DASHBOARD_FILE.exists(),
        "tem_alpine": tem_alpine,
        "alpine_defer": alpine_defer,
        "sem_alpine_sem_defer": not script_sem_defer,
        "tem_x_data_appdata": 'x-data="appData()"' in texto or "x-data='appData()'" in texto,
        "tem_function_appdata": "function appData()" in texto,
        "tem_window_appdata": "window.appData = appData" in texto,
        "tem_shell_seguro": "ETAPA25_1_SHELL_SEGURO_INICIO" in texto,
        "ok": False
    }

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_alpine"] and
        resultado["alpine_defer"] and
        resultado["sem_alpine_sem_defer"] and
        resultado["tem_x_data_appdata"] and
        resultado["tem_function_appdata"] and
        resultado["tem_window_appdata"] and
        resultado["tem_shell_seguro"]
    )

    return resultado


def restart_app():
    valor = os.environ.get("ETAPA25_2_RESTART_APP", "true").strip().lower()

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
        "body_limited": ""
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-25-2-dashboard-alpine/1.0"
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

    resultado = {
        "login_ok": False,
        "cookies": [],
        "paginas": [],
        "paginas_ok": False,
        "dashboard_alpine_ok": False,
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

    for page in PAGES:
        r = http_request(opener, "GET", page, None, limite=700000)
        body = r.get("body_limited") or ""

        item = {
            "path": page,
            "status": r.get("status"),
            "ok": r.get("status") == 200,
            "tem_shell_seguro": "ETAPA25_1_SHELL_SEGURO_INICIO" in body,
            "content_type": r.get("content_type")
        }

        if page == "/dashboard":
            item["tem_alpine"] = "alpinejs@3.x.x/dist/cdn.min.js" in body
            item["tem_defer_alpine"] = bool(
                re.search(
                    r'<script[^>]*\bdefer\b[^>]*src=["\']https://cdn\.jsdelivr\.net/npm/alpinejs@3\.x\.x/dist/cdn\.min\.js["\'][^>]*></script>',
                    body,
                    re.IGNORECASE
                )
            )
            item["tem_window_appdata"] = "window.appData = appData" in body
            item["tem_function_appdata"] = "function appData()" in body
            item["sem_alpine_sem_defer"] = not bool(
                re.search(
                    r'<script(?![^>]*\bdefer\b)[^>]*src=["\']https://cdn\.jsdelivr\.net/npm/alpinejs@3\.x\.x/dist/cdn\.min\.js["\'][^>]*></script>',
                    body,
                    re.IGNORECASE
                )
            )
            item["dashboard_alpine_ok"] = bool(
                item["ok"] and
                item["tem_alpine"] and
                item["tem_defer_alpine"] and
                item["tem_window_appdata"] and
                item["tem_function_appdata"] and
                item["sem_alpine_sem_defer"]
            )

        resultado["paginas"].append(item)

    resultado["paginas_ok"] = all(p["ok"] for p in resultado["paginas"])
    dash = [p for p in resultado["paginas"] if p["path"] == "/dashboard"]
    resultado["dashboard_alpine_ok"] = bool(dash and dash[0].get("dashboard_alpine_ok"))
    resultado["ok"] = bool(resultado["login_ok"] and resultado["paginas_ok"] and resultado["dashboard_alpine_ok"])

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

    ini = "<!-- ETAPA_25_2_INICIO -->"
    fim = "<!-- ETAPA_25_2_FIM -->"

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
    estrutura = relatorio["validacao_estrutura"]
    runtime = relatorio["runtime"]
    logs = relatorio["logs_analise"]

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Etapa 25.2 - Dashboard Alpine corrigido",
        [
            "Data: " + data,
            "",
            "Corrigida inicializacao do Alpine no dashboard.",
            "Dashboard alterado: " + str(correcao["alterado"]) + ".",
            "Alpine defer corrigido: " + str(correcao["corrigiu_defer"]) + ".",
            "window.appData garantido: " + str(correcao["adicionou_window_appdata"]) + ".",
            "Validacao estrutural OK: " + str(estrutura["ok"]) + ".",
            "Dashboard Alpine runtime OK: " + str(runtime["dashboard_alpine_ok"]) + ".",
            "Runtime OK: " + str(runtime["ok"]) + ".",
            "Logs Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs cookie: " + str(logs["linhas_cookie"]) + ".",
            "Logs email: " + str(logs["linhas_email"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 25.2 - Correcao Alpine no Dashboard",
        [
            "Data: " + data,
            "",
            "Adicionado defer ao carregamento do Alpine no dashboard.",
            "Garantida exposicao de appData em window para inicializacao do Alpine.",
            "Mantido shell seguro da Etapa 25.1.",
            "Validadas rotas principais em runtime."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 25.2 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido corrigir apenas views/dashboard.ejs para evitar impacto no CRM.",
            "Decidido manter Alpine via CDN por enquanto e deixar internalizacao para etapa futura.",
            "Decidido usar window.appData como compatibilidade segura com x-data=appData()."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 25.2",
        [
            "Data: " + data,
            "",
            "Validar manualmente o dashboard no navegador e confirmar ausencia de erros appData/initApp.",
            "Planejar etapa futura para remover Tailwind CDN e Alpine CDN em producao.",
            "Seguir para Etapa 26 de auditoria funcional apos validacao manual."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    linhas = []
    linhas.append("# Etapa 25.2 - Corrigir Alpine no Dashboard")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Dashboard alterado: " + str(relatorio["correcao"]["alterado"]))
    linhas.append("- Corrigiu defer Alpine: " + str(relatorio["correcao"]["corrigiu_defer"]))
    linhas.append("- Adicionou window.appData: " + str(relatorio["correcao"]["adicionou_window_appdata"]))
    linhas.append("- Validacao estrutural OK: " + str(relatorio["validacao_estrutura"]["ok"]))
    linhas.append("- Restart executado: " + str(relatorio["restart_app"]["executado"]))
    linhas.append("- Restart OK: " + str(relatorio["restart_app"]["ok"]))
    linhas.append("- App pronto: " + str(relatorio["aguardar_app"]["ok"]))
    linhas.append("- Login OK: " + str(relatorio["runtime"]["login_ok"]))
    linhas.append("- Paginas OK: " + str(relatorio["runtime"]["paginas_ok"]))
    linhas.append("- Dashboard Alpine OK: " + str(relatorio["runtime"]["dashboard_alpine_ok"]))
    linhas.append("- Runtime geral OK: " + str(relatorio["runtime"]["ok"]))
    linhas.append("- Logs Session ID: " + str(relatorio["logs_analise"]["linhas_session_id"]))
    linhas.append("- Logs cookie: " + str(relatorio["logs_analise"]["linhas_cookie"]))
    linhas.append("- Logs email: " + str(relatorio["logs_analise"]["linhas_email"]))
    linhas.append("- Achados logs: " + str(len(relatorio["logs_analise"]["achados"])))
    linhas.append("")

    linhas.append("## Runtime por pagina")
    linhas.append("")
    for item in relatorio["runtime"]["paginas"]:
        if item["path"] == "/dashboard":
            linhas.append(
                "- /dashboard: status " + str(item["status"]) +
                ", alpine_defer " + str(item.get("tem_defer_alpine")) +
                ", window_appData " + str(item.get("tem_window_appdata")) +
                ", dashboard_alpine_ok " + str(item.get("dashboard_alpine_ok"))
            )
        else:
            linhas.append("- " + item["path"] + ": status " + str(item["status"]) + ", ok " + str(item["ok"]))

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_25_2_dashboard_alpine_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_25_2_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = logs_since()
    correcao = aplicar_correcao()
    estrutura = validar_estrutura()
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
    manifesto_depois_path = REPORTS_DIR / "etapa_25_2_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_25_2_corrigir_dashboard_alpine.json"
    md_path = REPORTS_DIR / "etapa_25_2_corrigir_dashboard_alpine.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 25.2 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Dashboard alterado: " + str(correcao["alterado"]))
    print("Corrigiu defer Alpine: " + str(correcao["corrigiu_defer"]))
    print("Adicionou window.appData: " + str(correcao["adicionou_window_appdata"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Restart executado: " + str(restart["executado"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Paginas OK: " + str(runtime["paginas_ok"]))
    print("Dashboard Alpine OK: " + str(runtime["dashboard_alpine_ok"]))
    print("Runtime geral OK: " + str(runtime["ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["ok"]:
        print("")
        print("Aviso: Etapa 25.2 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
