#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 19 - Criar CSS visual compartilhado

Objetivo:
- Criar backup antes da alteracao.
- Gerar manifesto antes e depois.
- Criar ou atualizar public/css/style.css.
- Nao alterar backend.
- Nao alterar banco.
- Nao alterar views.
- Nao alterar autenticacao.
- Validar GET /css/style.css.
- Validar login e dashboard quando credenciais forem fornecidas.
- Validar logs novos sem Session ID, cookie e email real.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar:
sudo ETAPA19_LOGIN_EMAIL='admin@saas.com' ETAPA19_LOGIN_PASSWORD='123456' python3 etapa_19_criar_css_visual_compartilhado.py
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

CSS_PATH = ROOT / "public" / "css" / "style.css"

BASE_URL = "http://127.0.0.1:50010"
LOGIN_PATH = "/api/auth/login"
DASHBOARD_PATH = "/dashboard"
CSS_ROUTE = "/css/style.css"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "public/css/style.css",
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
    "reports",
    "__pycache__"
]

CHAVES_EMAIL = [
    "ETAPA19_LOGIN_EMAIL",
    "ETAPA18_LOGIN_EMAIL",
    "ETAPA17_1_LOGIN_EMAIL",
    "ETAPA17_LOGIN_EMAIL",
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
    "ETAPA19_LOGIN_PASSWORD",
    "ETAPA18_LOGIN_PASSWORD",
    "ETAPA17_1_LOGIN_PASSWORD",
    "ETAPA17_LOGIN_PASSWORD",
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


def css_compartilhado():
    return """/*
Etapa 19 - CSS visual compartilhado
Arquivo gerado para padronizacao visual inicial das telas antigas.
Nao contem seletor universal para evitar efeitos colaterais amplos.
*/

:root {
    --er-red: #b91c1c;
*   --er-red-dark: #7f1d1d;
    --e*-red-soft: #fef2f2;
    --er-blue:*#1d4ed8;
    --er-green: #047857;
*   --er-yellow: #b45309;
    --er-*g: #f8fafc;
    --er-card: #ffffff*
    --er-text: #0f172a;
    --er-*uted: #64748b;
    --er-border: #e*e8f0;
    --er-shadow: 0 16px 40px*rgba(15, 23, 42, 0.08);
}

html {
*   -webkit-text-size-adjust: 100%;*    text-size-adjust: 100%;
}

bod* {
    background:
        radial-*radient(circle at top left, rgba(1*5, 28, 28, 0.08), transparent 26re*),
        radial-gradient(circle *t bottom right, rgba(29, 78, 216, *.06), transparent 30rem),
        *ar(--er-bg);
    color: var(--er-t*xt);
    font-family: Inter, Arial* sans-serif;
}

a {
    color: var*--er-red);
    text-decoration: no*e;
}

a:hover {
    color: var(--e*-red-dark);
}

.er-page {
    max-*idth: 1500px;
    margin: 0 auto;
*   padding: 24px;
}

.er-page-head*r {
    background: linear-gradien*(135deg, #ffffff 0%, #fef2f2 100%)*
    border: 1px solid var(--er-bo*der);
    border-radius: 24px;
   *padding: 24px;
    box-shadow: var*--er-shadow);
    margin-bottom: 2*px;
}

.er-page-title {
    margin* 0;
    color: var(--er-text);
   *font-size: 28px;
    line-height: *.15;
    font-weight: 900;
    let*er-spacing: -0.03em;
}

.er-page-s*btitle {
    margin: 8px 0 0;
    *olor: var(--er-muted);
    font-si*e: 14px;
}

.er-card,
.card,
.pane*,
.box {
    background: var(--er-*ard);
    border: 1px solid var(--*r-border);
    border-radius: 20px;
    box-shadow: var(--er-shadow);
    padding: 18px;
}

.er-card + .er-card,
.card + .card,
.panel + .panel,
.box + .box {
    margin-top: 16px;
}

.er-card-title,
.card h2,
.panel h2,
.box h2 {
    color: var(--er-text);
    font-weight: 900;
    letter-spacing: -0.02em;
}

.er-grid {
    display: grid;
    gap: 16px;
}

.er-grid-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.er-grid-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.er-grid-4 {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

.er-btn,
button,
input[type="button"],
input[type="submit"] {
    border: 0;
    border-radius: 14px;
    padding: 10px 14px;
    background: var(--er-red);
    color: #ffffff;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 10px 20px rgba(185, 28, 28, 0.18);
    transition: transform 0.14s ease, box-shadow 0.14s ease, opacity 0.14s ease;
}

.er-btn:hover,
button:hover,
input[type="button"]:hover,
input[type="submit"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 14px 26px rgba(185, 28, 28, 0.24);
}

.er-btn:disabled,
button:disabled,
input[type="button"]:disabled,
input[type="submit"]:disabled {
    opacity: 0.65;
    cursor: not-allowed;
    transform: none;
}

.er-btn-secondary,
button.secundario,
button.secondary {
    background: #475569;
    box-shadow: 0 10px 20px rgba(71, 85, 105, 0.14);
}

.er-btn-success,
button.ok,
button.success {
    background: var(--er-green);
    box-shadow: 0 10px 20px rgba(4, 120, 87, 0.16);
}

.er-btn-warning,
button.warn,
button.warning {
    background: var(--er-yellow);
    box-shadow: 0 10px 20px rgba(180, 83, 9, 0.16);
}

.er-btn-danger,
button.danger {
    background: var(--er-red-dark);
}

input,
select,
textarea {
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    padding: 10px 12px;
    background: #ffffff;
    color: var(--er-text);
    outline: none;
}

input:focus,
select:focus,
textarea:focus {
    border-color: var(--er-red);
    box-shadow: 0 0 0 4px rgba(185, 28, 28, 0.10);
}

label {
    color: #334155;
    font-weight: 800;
}

table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    overflow: hidden;
    border-radius: 16px;
    background: #ffffff;
}

th {
    background: #f8fafc;
    color: #334155;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

td,
th {
    border-bottom: 1px solid var(--er-border);
    padding: 12px;
}

tr:last-child td {
    border-bottom: 0;
}

.er-badge,
.badge,
.status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 900;
    background: var(--er-red-soft);
    color: var(--er-red-dark);
    border: 1px solid rgba(185, 28, 28, 0.14);
}

.er-badge-success,
.status.ok,
.status.online {
    background: #ecfdf5;
    color: #065f46;
    border-color: rgba(4, 120, 87, 0.16);
}

.er-badge-warning,
.status.warn,
.status.warning {
    background: #fffbeb;
    color: #92400e;
    border-color: rgba(180, 83, 9, 0.18);
}

.er-badge-muted,
.status.muted {
    background: #f1f5f9;
    color: #475569;
    border-color: #e2e8f0;
}

.er-top-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.er-muted {
    color: var(--er-muted);
}

.er-divider {
    height: 1px;
    background: var(--er-border);
    margin: 16px 0;
}

.er-soft-panel {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid var(--er-border);
    border-radius: 20px;
    padding: 16px;
}

.er-kpi {
    background: #ffffff;
    border: 1px solid var(--er-border);
    border-radius: 20px;
    padding: 16px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}

.er-kpi-label {
    color: var(--er-muted);
    font-size: 13px;
    font-weight: 800;
}

.er-kpi-value {
    color: var(--er-text);
    font-size: 26px;
    font-weight: 900;
    margin-top: 4px;
}

.er-kpi-footnote {
    color: #94a3b8;
    font-size: 12px;
    margin-top: 4px;
}

@media (max-width: 900px) {
    .er-grid-2,
    .er-grid-3,
    .er-grid-4 {
        grid-template-columns: 1fr;
    }

    .er-page {
        padding: 14px;
    }

    .er-page-title {
        font-size: 24px;
    }

    .er-top-actions {
        align-items: stretch;
    }

    .er-top-actions .er-btn,
    .er-top-actions button {
        width: 100%;
    }
}
"""


def aplicar_css():
    resultado = {
        "arquivo": "public/css/style.css",
        "existe_antes": CSS_PATH.exists(),
        "alterado": False,
        "criado": False,
        "sha256_antes": sha256_arquivo(CSS_PATH) if CSS_PATH.exists() else None,
        "sha256_depois": None
    }

    atual = ler_texto(CSS_PATH)
    novo = css_compartilhado()

    validar_sem_asterisco_indevido(novo, "public/css/style.css")

    if atual != novo:
        if not CSS_PATH.exists():
            resultado["criado"] = True
        gravar_texto(CSS_PATH, novo)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256_arquivo(CSS_PATH)
    return resultado


def validar_estrutura_css():
    texto = ler_texto(CSS_PATH)

    resultado = {
        "arquivo_existe": CSS_PATH.exists(),
        "tem_variaveis": False,
        "tem_cards": False,
        "tem_botoes": False,
        "tem_inputs": False,
        "tem_tabelas": False,
        "tem_badges": False,
        "tem_responsivo": False,
        "sem_asterisco": False,
        "ok": False
    }

    if texto is None:
        resultado["erro"] = "public/css/style.css ausente ou ilegivel"
        return resultado

    resultado["tem_variaveis"] = "--er-red" in texto and "--er-bg" in texto
    resultado["tem_cards"] = ".er-card" in texto
    resultado["tem_botoes"] = ".er-btn" in texto
    resultado["tem_inputs"] = "input:focus" in texto
    resultado["tem_tabelas"] = "table" in texto and "th" in texto
    resultado["tem_badges"] = ".er-badge" in texto
    resultado["tem_responsivo"] = "@media" in texto
    resultado["sem_asterisco"] = chr(42) not in texto

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_variaveis"] and
        resultado["tem_cards"] and
        resultado["tem_botoes"] and
        resultado["tem_inputs"] and
        resultado["tem_tabelas"] and
        resultado["tem_badges"] and
        resultado["tem_responsivo"] and
        resultado["sem_asterisco"]
    )

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
        "User-Agent": "etapa-19-css-compartilhado/1.0"
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


def validar_css_runtime():
    opener, jar = criar_opener()
    r = http_request(opener, "GET", CSS_ROUTE)

    body = r.get("body_full_limited") or ""

    return {
        "status": r.get("status"),
        "ok_http": bool(r.get("status") == 200),
        "content_type": r.get("content_type"),
        "erro": r.get("erro"),
        "tem_er_card": ".er-card" in body,
        "tem_er_btn": ".er-btn" in body,
        "tem_variaveis": "--er-red" in body,
        "sem_asterisco": chr(42) not in body,
        "ok": bool(
            r.get("status") == 200 and
            ".er-card" in body and
            ".er-btn" in body and
            "--er-red" in body and
            chr(42) not in body
        )
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
        "content_type": dashboard.get("content_type"),
        "body_preview": dashboard.get("body_preview")
    }

    resultado["dashboard_ok"] = bool(
        dashboard.get("status") == 200 and
        "crm enterprise" in body_dash.lower()
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
    if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$", token):
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
            token_limpo = token.strip().strip(".;:")
            if parece_email_token(token_limpo):
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


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_19_INICIO -->"
    marcador_fim = "<!-- ETAPA_19_FIM -->"

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
    css = relatorio["css_compartilhado"]
    estrutura = relatorio["validacao_estrutura_css"]
    runtime_css = relatorio["validacao_css_runtime"]
    runtime = relatorio["validacao_login_dashboard"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 19 - CSS visual compartilhado",
        [
            "Data: " + data,
            "",
            "Foi criado ou atualizado public/css/style.css como base visual compartilhada.",
            "Arquivo criado: " + str(css["criado"]) + ".",
            "Arquivo alterado: " + str(css["alterado"]) + ".",
            "Validacao estrutural CSS OK: " + str(estrutura["ok"]) + ".",
            "GET /css/style.css OK: " + str(runtime_css["ok"]) + ".",
            "Login OK: " + str(runtime["login_ok"]) + ".",
            "Dashboard OK: " + str(runtime["dashboard_ok"]) + ".",
            "Nenhuma view, backend ou banco foi alterado."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 19 - CSS compartilhado criado",
        [
            "Data: " + data,
            "",
            "Criado public/css/style.css com estilos compartilhados.",
            "Incluidos estilos para cards, botoes, inputs, tabelas, badges e responsividade.",
            "Preservadas views existentes.",
            "Validado acesso runtime a /css/style.css.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 19 - Decisoes tecnicas frontend",
        [
            "Data: " + data,
            "",
            "Decidido criar CSS compartilhado antes de alterar telas antigas.",
            "Decidido evitar seletor universal no CSS para reduzir efeitos colaterais.",
            "Decidido manter escopo visual inicial por classes er.",
            "Decidido nao alterar views nesta etapa."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 19",
        [
            "Data: " + data,
            "",
            "Validar visual de admin-panel, crm e super-admin no navegador.",
            "Planejar etapa para aplicar classes er de forma controlada nas views antigas.",
            "Planejar internalizacao de FontAwesome, Alpine, Tailwind e imagens externas.",
            "Revisar /socket.io/socket.io.js marcado como ausente pela auditoria anterior, pois e servido dinamicamente.",
            "Mapear scripts inline antes de CSP forte."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    css = relatorio["css_compartilhado"]
    estrutura = relatorio["validacao_estrutura_css"]
    css_runtime = relatorio["validacao_css_runtime"]
    runtime = relatorio["validacao_login_dashboard"]
    logs = relatorio["logs_analise"]

    linhas = []

    linhas.append("# Etapa 19 - Criar CSS visual compartilhado")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- CSS criado: " + str(css["criado"]))
    linhas.append("- CSS alterado: " + str(css["alterado"]))
    linhas.append("- Validacao estrutural CSS OK: " + str(estrutura["ok"]))
    linhas.append("- GET /css/style.css OK: " + str(css_runtime["ok"]))
    linhas.append("- Login OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
    linhas.append("- Logs novos Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos email: " + str(logs["linhas_email"]))
    linhas.append("- Achados criticos logs: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Arquivo CSS")
    linhas.append("")
    linhas.append("- Arquivo: " + css["arquivo"])
    linhas.append("- Existia antes: " + str(css["existe_antes"]))
    linhas.append("- Criado: " + str(css["criado"]))
    linhas.append("- Alterado: " + str(css["alterado"]))
    linhas.append("- SHA256 antes: " + str(css["sha256_antes"]))
    linhas.append("- SHA256 depois: " + str(css["sha256_depois"]))

    linhas.append("")
    linhas.append("## Validacao estrutural CSS")
    linhas.append("")
    for chave in sorted(estrutura.keys()):
        linhas.append("- " + chave + ": " + str(estrutura[chave]))

    linhas.append("")
    linhas.append("## Validacao runtime CSS")
    linhas.append("")
    for chave in sorted(css_runtime.keys()):
        linhas.append("- " + chave + ": " + str(css_runtime[chave]))

    linhas.append("")
    linhas.append("## Validacao login e dashboard")
    linhas.append("")
    linhas.append("- Executada: " + str(runtime["executado"]))
    linhas.append("- Email configurado: " + str(runtime["email_configurado"]))
    linhas.append("- Senha configurada: " + str(runtime["senha_configurada"]))
    linhas.append("- Login OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
    linhas.append("- Cookies recebidos: " + str(len(runtime["cookies"])))

    linhas.append("")
    linhas.append("## Logs novos")
    linhas.append("")
    linhas.append("- Linhas analisadas: " + str(logs["total_linhas"]))
    linhas.append("- Linhas Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Linhas cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Linhas email: " + str(logs["linhas_email"]))
    linhas.append("- Achados: " + str(len(logs["achados"])))

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Somente public/css/style.css foi criado ou alterado.")
    linhas.append("- Nenhuma view foi alterada.")
    linhas.append("- Nenhum backend foi alterado.")
    linhas.append("- Nenhum banco foi alterado.")
    linhas.append("- O CSS nao usa seletor universal para reduzir risco de efeito colateral.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Aplicar classes e estrutura visual de forma controlada em views/crm.ejs ou views/admin-panel.ejs.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_19_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_19_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = agora_logs_since()
    css = aplicar_css()
    estrutura = validar_estrutura_css()
    css_runtime = validar_css_runtime()
    runtime = validar_login_dashboard()
    time.sleep(2)

    logs_coleta = coletar_logs_novos(since)
    logs_analise = analisar_logs_texto(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "css_compartilhado": css,
        "validacao_estrutura_css": estrutura,
        "validacao_css_runtime": css_runtime,
        "logs_since": since,
        "validacao_login_dashboard": runtime,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_19_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_19_criar_css_visual_compartilhado.json"
    md_path = REPORTS_DIR / "etapa_19_criar_css_visual_compartilhado.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 19 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("CSS criado: " + str(css["criado"]))
    print("CSS alterado: " + str(css["alterado"]))
    print("Validacao estrutural CSS OK: " + str(estrutura["ok"]))
    print("GET /css/style.css OK: " + str(css_runtime["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not css_runtime["ok"]:
        print("")
        print("Aviso: /css/style.css nao validou em runtime. Verifique se public esta servido estaticamente.")

    if not runtime["login_ok"] or not runtime["dashboard_ok"]:
        print("")
        print("Aviso: login ou dashboard nao validaram. Consulte o relatorio.")


if __name__ == "__main__":
    main()
