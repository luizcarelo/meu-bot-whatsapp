#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 14 - Hardening de logs, sessao, cookies e headers HTTP

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Reduzir logs sensiveis em server.js.
- Remover impressao de Session ID.
- Remover impressao de cookie ou saas_crm_sid.
- Remover impressao de email do usuario logado em middleware geral.
- Adicionar app.disable('x-powered-by') quando possivel.
- Adicionar headers HTTP basicos quando possivel.
- Auditar configuracao de cookie de sessao.
- Rodar node --check em server.js.
- Opcionalmente reiniciar app se ETAPA14_RESTART_APP=true.
- Validar login e dashboard quando credenciais forem fornecidas.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar:
python3 etapa_14_hardening_logs_sessao_cookies.py

Com validacao de login:
sudo ETAPA14_LOGIN_EMAIL='admin@saas.com' ETAPA14_LOGIN_PASSWORD='SUA_SENHA' python3 etapa_14_hardening_logs_sessao_cookies.py

Com reinicio do app:
sudo ETAPA14_RESTART_APP=true ETAPA14_LOGIN_EMAIL='admin@saas.com' ETAPA14_LOGIN_PASSWORD='SUA_SENHA' python3 etapa_14_hardening_logs_sessao_cookies.py
"""

import os
import json
import shutil
import hashlib
import subprocess
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


def linha_sensivel_log(linha):
    lower = linha.lower()

    termos = [
        "session id",
        "header cookie",
        "saas_crm_sid",
        "conteúdo:",
        "conteudo:",
        "req.sessionid",
        "req.headers.cookie"
    ]

    for termo in termos:
        if termo in lower:
            return True

    return False


def linha_usuario_logado(linha):
    lower = linha.lower()

    if "usuário logado" in lower:
        return True

    if "usuario logado" in lower:
        return True

    if "req.session.user.email" in lower:
        return True

    return False


def adicionar_disable_x_powered(texto, alteracoes):
    if "app.disable('x-powered-by')" in texto:
        return texto

    if 'app.disable("x-powered-by")' in texto:
        return texto

    candidatos = [
        "const app = express();",
        "const app = require('express')();",
        'const app = require("express")();'
    ]

    for candidato in candidatos:
        pos = texto.find(candidato)
        if pos >= 0:
            fim = pos + len(candidato)
            novo = texto[:fim] + "\napp.disable('x-powered-by');" + texto[fim:]
            alteracoes.append("Adicionado app.disable x-powered-by")
            return novo

    alteracoes.append("Nao foi possivel localizar criacao do app para x-powered-by")
    return texto


def adicionar_headers_basicos(texto, alteracoes):
    marcador = "ETAPA14_SECURITY_HEADERS"

    if marcador in texto:
        return texto

    bloco = []
    bloco.append("")
    bloco.append("// ETAPA14_SECURITY_HEADERS_INICIO")
    bloco.append("app.use((req, res, next) => {")
    bloco.append("    res.setHeader('X-Content-Type-Options', 'nosniff');")
    bloco.append("    res.setHeader('X-Frame-Options', 'SAMEORIGIN');")
    bloco.append("    res.setHeader('Referrer-Policy', 'no-referrer');")
    bloco.append("    res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');")
    bloco.append("    next();")
    bloco.append("});")
    bloco.append("// ETAPA14_SECURITY_HEADERS_FIM")
    bloco.append("")

    bloco_texto = "\n".join(bloco)

    alvo = "app.disable('x-powered-by');"
    pos = texto.find(alvo)

    if pos >= 0:
        fim = pos + len(alvo)
        novo = texto[:fim] + bloco_texto + texto[fim:]
        alteracoes.append("Adicionados headers HTTP basicos")
        return novo

    candidato = "const app = express();"
    pos = texto.find(candidato)

    if pos >= 0:
        fim = pos + len(candidato)
        novo = texto[:fim] + bloco_texto + texto[fim:]
        alteracoes.append("Adicionados headers HTTP basicos")
        return novo

    alteracoes.append("Nao foi possivel inserir headers HTTP basicos automaticamente")
    return texto


def sanitizar_logs_server(texto):
    linhas = texto.splitlines()
    novas = []
    alteracoes = []
    removidas = 0
    substituidas = 0

    for linha in linhas:
        if linha_sensivel_log(linha):
            removidas += 1
            continue

        if linha_usuario_logado(linha):
            indent = linha[:len(linha) - len(linha.lstrip())]
            novas.append(indent + "console.log(`[REQ] Usuario autenticado empresa_id=${req.session?.empresaId || 'N/A'}`);")
            substituidas += 1
            continue

        novas.append(linha)

    novo = "\n".join(novas)
    if texto.endswith("\n"):
        novo += "\n"

    if removidas > 0:
        alteracoes.append("Removidas linhas de log com sessao ou cookie: " + str(removidas))

    if substituidas > 0:
        alteracoes.append("Substituidas linhas de usuario logado: " + str(substituidas))

    novo = adicionar_disable_x_powered(novo, alteracoes)
    novo = adicionar_headers_basicos(novo, alteracoes)

    return novo, alteracoes


def auditar_server_js():
    texto = ler_texto(SERVER_JS)

    resultado = {
        "existe": SERVER_JS.exists(),
        "linhas_session_id": 0,
        "linhas_cookie": 0,
        "linhas_usuario_email": 0,
        "x_powered_disable": False,
        "headers_etapa14": False,
        "cookie_http_only": False,
        "cookie_same_site": False,
        "cookie_secure": False
    }

    if texto is None:
        resultado["erro"] = "server.js ausente ou ilegivel"
        return resultado

    lower = texto.lower()

    for linha in texto.splitlines():
        low = linha.lower()

        if "session id" in low or "req.sessionid" in low:
            resultado["linhas_session_id"] += 1

        if "header cookie" in low or "saas_crm_sid" in low or "req.headers.cookie" in low or "conteúdo:" in low or "conteudo:" in low:
            resultado["linhas_cookie"] += 1

        if "req.session.user.email" in low or "usuário logado" in low or "usuario logado" in low:
            resultado["linhas_usuario_email"] += 1

    resultado["x_powered_disable"] = "app.disable('x-powered-by')" in texto or 'app.disable("x-powered-by")' in texto
    resultado["headers_etapa14"] = "ETAPA14_SECURITY_HEADERS" in texto
    resultado["cookie_http_only"] = "httponly" in lower
    resultado["cookie_same_site"] = "samesite" in lower
    resultado["cookie_secure"] = "secure" in lower

    return resultado


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

    novo, alteracoes = sanitizar_logs_server(texto)

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
    valor = os.environ.get("ETAPA14_RESTART_APP", "").strip().lower()

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


def http_request(opener, metodo, path, data_obj=None):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "metodo": metodo,
        "ok": False,
        "status": None,
        "erro": None,
        "body_preview": "",
        "content_type": "",
        "redirect_url": None
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-14-hardening/1.0"
    }

    if data_obj is not None:
        body_text = json.dumps(data_obj)
        body_bytes = body_text.encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=body_bytes, headers=headers, method=metodo)

    try:
        with opener.open(req, timeout=15) as resp:
            body = resp.read(8192)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["body_preview"] = redigir(texto[:1200])
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["redirect_url"] = resp.geturl()
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
    except URLError as exc:
        resultado["erro"] = redigir(str(exc.reason))
    except Exception as exc:
        resultado["erro"] = redigir(str(exc))

    return resultado


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
    resultado["dashboard_ok"] = bool(dashboard.get("status") == 200 and "crm enterprise" in (dashboard.get("body_preview") or "").lower())

    return resultado


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


def analisar_logs_runtime(resultados_logs):
    texto = ""

    for item in resultados_logs:
        texto += "\n" + (item.get("stdout") or "")
        texto += "\n" + (item.get("stderr") or "")

    session_id = 0
    cookies = 0
    achados = []

    for idx, linha in enumerate(texto.splitlines(), start=1):
        low = linha.lower()

        if "session id" in low:
            session_id += 1

        if "saas_crm_sid" in low or "header cookie" in low or "conteúdo:" in low or "conteudo:" in low:
            cookies += 1

        if "error" in low or "exception" in low or "syntaxerror" in low or "database" in low:
            achados.append({
                "linha": idx,
                "trecho": redigir(linha.strip())[:300]
            })

    return {
        "total_linhas": len(texto.splitlines()),
        "linhas_session_id": session_id,
        "linhas_cookie": cookies,
        "achados": achados,
        "amostra": redigir("\n".join(texto.splitlines()[-60:]))[:12000]
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_14_INICIO -->"
    marcador_fim = "<!-- ETAPA_14_FIM -->"

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
    audit_antes = relatorio["auditoria_antes"]
    audit_depois = relatorio["auditoria_depois"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 14 - Hardening de logs e headers",
        [
            "Data: " + data,
            "",
            "Foi aplicado hardening inicial em server.js.",
            "Linhas sensiveis antes session id: " + str(audit_antes["linhas_session_id"]) + ".",
            "Linhas sensiveis antes cookie: " + str(audit_antes["linhas_cookie"]) + ".",
            "Linhas sensiveis depois session id: " + str(audit_depois["linhas_session_id"]) + ".",
            "Linhas sensiveis depois cookie: " + str(audit_depois["linhas_cookie"]) + ".",
            "Node check OK: " + str(node["ok"]) + ".",
            "Restart app executado: " + str(restart["executado"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 14 - Hardening de seguranca operacional",
        [
            "Data: " + data,
            "",
            "Removida impressao de Session ID e cookie em logs do middleware geral quando localizada.",
            "Reduzido log de usuario autenticado para empresa_id sem email.",
            "Adicionado app.disable para x-powered-by quando possivel.",
            "Adicionados headers HTTP basicos quando possivel.",
            "Executado node --check em server.js.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 14 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido remover dados de sessao e cookie dos logs.",
            "Decidido manter logs uteis sem identificadores sensiveis.",
            "Decidido nao reiniciar app por padrao.",
            "Decidido permitir restart somente com ETAPA14_RESTART_APP=true.",
            "Decidido adicionar headers basicos sem alterar regras de negocio."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Se o app nao foi reiniciado, reiniciar em janela controlada para aplicar server.js.",
        "Reexecutar Etapa 13 apos restart para confirmar reducao dos logs em runtime.",
        "Revisar CORS permissivo em etapa dedicada.",
        "Revisar configuracao completa de cookie de sessao para HTTPS producao.",
        "Planejar rate limit e politica de seguranca de conteudo."
    ]

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 14",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    audit_antes = relatorio["auditoria_antes"]
    audit_depois = relatorio["auditoria_depois"]
    correcao = relatorio["correcao_server"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    validacao = relatorio["validacao_login_dashboard"]
    logs = relatorio["logs_runtime"]

    linhas.append("# Etapa 14 - Hardening de logs, sessao, cookies e headers HTTP")
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
    linhas.append("- Validacao login executada: " + str(validacao["executado"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("")

    linhas.append("## Auditoria estatica antes")
    linhas.append("")
    linhas.append("- Linhas Session ID: " + str(audit_antes["linhas_session_id"]))
    linhas.append("- Linhas cookie: " + str(audit_antes["linhas_cookie"]))
    linhas.append("- Linhas usuario email: " + str(audit_antes["linhas_usuario_email"]))
    linhas.append("- x-powered-by disable: " + str(audit_antes["x_powered_disable"]))
    linhas.append("- headers etapa14: " + str(audit_antes["headers_etapa14"]))
    linhas.append("- cookie httpOnly citado: " + str(audit_antes["cookie_http_only"]))
    linhas.append("- cookie sameSite citado: " + str(audit_antes["cookie_same_site"]))
    linhas.append("- cookie secure citado: " + str(audit_antes["cookie_secure"]))

    linhas.append("")
    linhas.append("## Alteracoes aplicadas")
    linhas.append("")
    if correcao["alteracoes"]:
        for item in correcao["alteracoes"]:
            linhas.append("- " + item)
    else:
        linhas.append("- Nenhuma alteracao aplicada.")

    linhas.append("")
    linhas.append("## Auditoria estatica depois")
    linhas.append("")
    linhas.append("- Linhas Session ID: " + str(audit_depois["linhas_session_id"]))
    linhas.append("- Linhas cookie: " + str(audit_depois["linhas_cookie"]))
    linhas.append("- Linhas usuario email: " + str(audit_depois["linhas_usuario_email"]))
    linhas.append("- x-powered-by disable: " + str(audit_depois["x_powered_disable"]))
    linhas.append("- headers etapa14: " + str(audit_depois["headers_etapa14"]))
    linhas.append("- cookie httpOnly citado: " + str(audit_depois["cookie_http_only"]))
    linhas.append("- cookie sameSite citado: " + str(audit_depois["cookie_same_site"]))
    linhas.append("- cookie secure citado: " + str(audit_depois["cookie_secure"]))

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    linhas.append("- OK: " + str(node["ok"]))
    if node.get("stderr"):
        linhas.append("- stderr: " + node["stderr"][:500])

    linhas.append("")
    linhas.append("## Restart")
    linhas.append("")
    linhas.append("- Solicitado: " + str(restart["solicitado"]))
    linhas.append("- Executado: " + str(restart["executado"]))
    linhas.append("- OK: " + str(restart["ok"]))

    linhas.append("")
    linhas.append("## Validacao login e dashboard")
    linhas.append("")
    linhas.append("- Executada: " + str(validacao["executado"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("- Cookies recebidos: " + str(len(validacao["cookies"])))

    linhas.append("")
    linhas.append("## Logs runtime")
    linhas.append("")
    linhas.append("- Linhas analisadas: " + str(logs["total_linhas"]))
    linhas.append("- Linhas Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Linhas cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Achados criticos: " + str(len(logs["achados"])))

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhuma alteracao foi aplicada ao banco.")
    linhas.append("- O app so foi reiniciado se ETAPA14_RESTART_APP=true.")
    linhas.append("- Se o app nao foi reiniciado, os logs runtime ainda podem refletir a versao antiga em execucao.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Reexecutar Etapa 13 apos restart controlado para confirmar que Session ID e cookies nao aparecem mais nos logs.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_14_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_14_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    docker = verificar_docker()

    auditoria_antes = auditar_server_js()
    correcao_server = aplicar_hardening_server()
    auditoria_depois = auditar_server_js()
    node_check = node_check_server()

    restart_app = reiniciar_app_se_solicitado()
    validacao_login_dashboard = validar_login_dashboard()

    logs_resultados = coletar_logs_app()
    logs_runtime = analisar_logs_runtime(logs_resultados)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "auditoria_antes": auditoria_antes,
        "correcao_server": correcao_server,
        "auditoria_depois": auditoria_depois,
        "node_check": node_check,
        "restart_app": restart_app,
        "validacao_login_dashboard": validacao_login_dashboard,
        "logs_resultados": logs_resultados,
        "logs_runtime": logs_runtime
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_14_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_14_hardening_logs_sessao_cookies.json"
    md_path = REPORTS_DIR / "etapa_14_hardening_logs_sessao_cookies.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 14 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("server.js alterado: " + str(correcao_server["alterado"]))
    print("Node check OK: " + str(node_check["ok"]))
    print("Restart solicitado: " + str(restart_app["solicitado"]))
    print("Restart executado: " + str(restart_app["executado"]))
    print("Login validacao executada: " + str(validacao_login_dashboard["executado"]))
    print("Login OK: " + str(validacao_login_dashboard["login_ok"]))
    print("Dashboard OK: " + str(validacao_login_dashboard["dashboard_ok"]))
    print("Auditoria depois Session ID: " + str(auditoria_depois["linhas_session_id"]))
    print("Auditoria depois cookie: " + str(auditoria_depois["linhas_cookie"]))
    print("Logs runtime Session ID: " + str(logs_runtime["linhas_session_id"]))
    print("Logs runtime cookie: " + str(logs_runtime["linhas_cookie"]))

    if not node_check["ok"]:
        print("")
        print("Falha em node --check. Consulte o relatorio.")

    if not restart_app["executado"]:
        print("")
        print("Aviso: app nao foi reiniciado. Para aplicar em runtime, execute com ETAPA14_RESTART_APP=true.")


if __name__ == "__main__":
    main()