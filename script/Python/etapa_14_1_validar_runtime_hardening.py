#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 14.1 - Validar runtime do hardening

Objetivo:
- Criar backup documental.
- Gerar manifesto antes e depois.
- Comparar server.js local com server.js dentro do container app.
- Detectar se o container esta usando codigo antigo.
- Fazer rebuild somente se ETAPA14_1_REBUILD_APP=true.
- Aguardar app responder na porta local.
- Validar login e dashboard.
- Coletar logs novos apos a validacao, evitando contar historico antigo.
- Confirmar reducao de Session ID e cookie nos logs novos.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar sem rebuild:
sudo ETAPA14_1_LOGIN_EMAIL='admin@saas.com' ETAPA14_1_LOGIN_PASSWORD='SUA_SENHA' python3 etapa_14_1_validar_runtime_hardening.py

Como executar com rebuild:
sudo ETAPA14_1_REBUILD_APP=true ETAPA14_1_LOGIN_EMAIL='admin@saas.com' ETAPA14_1_LOGIN_PASSWORD='SUA_SENHA' python3 etapa_14_1_validar_runtime_hardening.py
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


def verificar_docker():
    return {
        "docker_version": run_cmd(["docker", "--version"], 20),
        "docker_compose_version": run_cmd(["docker", "compose", "version"], 20),
        "docker_compose_ps": run_cmd(["docker", "compose", "ps"], 30)
    }


def localizar_server_container():
    script = (
        "set -eu; "
        "for p in /app/server.js /usr/src/app/server.js /home/node/app/server.js ./server.js; do "
        "if [ -f \"$p\" ]; then echo \"$p\"; exit 0; fi; "
        "done; "
        "find /app /usr/src/app /home/node/app -maxdepth 4 -name server.js 2>/dev/null | head -n 1"
    )

    r = run_cmd(["docker", "compose", "exec", "-T", "app", "sh", "-lc", script], 60)

    path = ""
    if r.get("stdout"):
        path = r["stdout"].splitlines()[0].strip()

    return {
        "ok": bool(r.get("ok") and path),
        "path": path,
        "resultado": r
    }


def hash_server_container(path):
    if not path:
        return {
            "ok": False,
            "hash": None,
            "resultado": None
        }

    script = (
        "if command -v sha256sum >/dev/null 2>&1; then "
        "sha256sum " + shell_quote(path) + " | awk '{print $1}'; "
        "else "
        "node -e \"const fs=require('fs');const c=require('crypto');"
        "console.log(c.createHash('sha256').update(fs.readFileSync(process.argv[1])).digest('hex'))\" "
        + shell_quote(path) + "; "
        "fi"
    )

    r = run_cmd(["docker", "compose", "exec", "-T", "app", "sh", "-lc", script], 60)

    h = ""
    if r.get("stdout"):
        h = r["stdout"].splitlines()[0].strip()

    return {
        "ok": bool(r.get("ok") and h),
        "hash": h if h else None,
        "resultado": r
    }


def shell_quote(valor):
    return "'" + str(valor).replace("'", "'\"'\"'") + "'"


def comparar_server_js():
    local_hash = sha256_arquivo(SERVER_JS)
    localizado = localizar_server_container()
    container_hash = hash_server_container(localizado.get("path"))

    iguais = bool(local_hash and container_hash.get("hash") and local_hash == container_hash.get("hash"))

    return {
        "local_existe": SERVER_JS.exists(),
        "local_hash": local_hash,
        "container_server_path": localizado.get("path"),
        "container_localizado_ok": localizado.get("ok"),
        "container_hash_ok": container_hash.get("ok"),
        "container_hash": container_hash.get("hash"),
        "hashes_iguais": iguais,
        "localizar_resultado": localizado.get("resultado"),
        "hash_resultado": container_hash.get("resultado")
    }


def rebuild_se_solicitado():
    valor = os.environ.get("ETAPA14_1_REBUILD_APP", "").strip().lower()

    if valor not in ["true", "1", "sim", "yes"]:
        return {
            "solicitado": False,
            "executado": False,
            "ok": None,
            "resultado": None
        }

    r = run_cmd(["docker", "compose", "up", "-d", "--build", "app"], 600)

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
        "content_type": "",
        "redirect_url": None
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-14-1-runtime/1.0"
    }

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

        if "saas_crm_sid" in low or "header cookie" in low or "conteúdo:" in low or "conteudo:" in low:
            cookie += 1

        if "usuário logado:" in low or "usuario logado:" in low:
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
        "linhas_usuario_email": email,
        "achados": achados,
        "amostra": redigir("\n".join(str(texto or "").splitlines()[-80:]))[:16000]
    }


def headers_basicos_validar():
    opener, jar = criar_opener()
    r = http_request(opener, "GET", "/")
    return r


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_14_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_14_1_FIM -->"

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
    cmp = relatorio["comparacao_server"]
    rebuild = relatorio["rebuild"]
    validacao = relatorio["validacao_login_dashboard"]
    logs = relatorio["logs_novos_analise"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 14.1 - Runtime do hardening validado",
        [
            "Data: " + data,
            "",
            "Foi validado o runtime do hardening aplicado na Etapa 14.",
            "Server local e container com mesmo hash: " + str(cmp["hashes_iguais"]) + ".",
            "Rebuild solicitado: " + str(rebuild["solicitado"]) + ".",
            "Rebuild executado: " + str(rebuild["executado"]) + ".",
            "Login OK: " + str(validacao["login_ok"]) + ".",
            "Dashboard OK: " + str(validacao["dashboard_ok"]) + ".",
            "Logs novos com Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs novos com cookie: " + str(logs["linhas_cookie"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 14.1 - Validacao runtime do hardening",
        [
            "Data: " + data,
            "",
            "Comparado server.js local com server.js dentro do container app.",
            "Executado rebuild do app somente quando solicitado por variavel de ambiente.",
            "Validado login e dashboard apos disponibilidade do app.",
            "Analisados logs novos para confirmar ausencia de Session ID e cookies.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 14.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido comparar hashes para confirmar se o container usa o codigo atualizado.",
            "Decidido nao fazer rebuild automaticamente sem ETAPA14_1_REBUILD_APP=true.",
            "Decidido analisar logs novos usando marco temporal da propria etapa.",
            "Decidido manter a validacao sem alterar banco."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Se os hashes forem diferentes, executar rebuild controlado com ETAPA14_1_REBUILD_APP=true.",
        "Se logs novos ainda exibirem sessao ou cookie, revisar outras fontes de log alem do server.js.",
        "Revisar CORS permissivo em etapa dedicada.",
        "Revisar configuracao completa de cookie de sessao para HTTPS producao.",
        "Planejar rate limit e politica de seguranca de conteudo."
    ]

    if cmp["hashes_iguais"] and logs["linhas_session_id"] == 0 and logs["linhas_cookie"] == 0:
        pendencias = [
            "Data: " + data,
            "",
            "Revisar CORS permissivo em etapa dedicada.",
            "Revisar configuracao completa de cookie de sessao para HTTPS producao.",
            "Planejar rate limit e politica de seguranca de conteudo.",
            "Validar ambiente externo com HTTPS antes de producao."
        ]

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 14.1",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    cmp = relatorio["comparacao_server"]
    rebuild = relatorio["rebuild"]
    espera = relatorio["aguardar_app"]
    validacao = relatorio["validacao_login_dashboard"]
    logs = relatorio["logs_novos_analise"]

    linhas.append("# Etapa 14.1 - Validar runtime do hardening")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Docker OK: " + str(relatorio["docker"]["docker_version"]["ok"]))
    linhas.append("- Docker Compose OK: " + str(relatorio["docker"]["docker_compose_version"]["ok"]))
    linhas.append("- Server local existe: " + str(cmp["local_existe"]))
    linhas.append("- Server container localizado: " + str(cmp["container_localizado_ok"]))
    linhas.append("- Hashes iguais: " + str(cmp["hashes_iguais"]))
    linhas.append("- Rebuild solicitado: " + str(rebuild["solicitado"]))
    linhas.append("- Rebuild executado: " + str(rebuild["executado"]))
    linhas.append("- Rebuild OK: " + str(rebuild["ok"]))
    linhas.append("- App respondeu apos espera: " + str(espera["ok"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("- Logs novos linhas Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos linhas cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos linhas usuario email: " + str(logs["linhas_usuario_email"]))
    linhas.append("- Achados criticos logs novos: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Comparacao server.js")
    linhas.append("")
    linhas.append("- Hash local: " + str(cmp["local_hash"]))
    linhas.append("- Caminho no container: " + str(cmp["container_server_path"]))
    linhas.append("- Hash container: " + str(cmp["container_hash"]))
    linhas.append("- Hashes iguais: " + str(cmp["hashes_iguais"]))

    linhas.append("")
    linhas.append("## Rebuild")
    linhas.append("")
    linhas.append("- Solicitado: " + str(rebuild["solicitado"]))
    linhas.append("- Executado: " + str(rebuild["executado"]))
    linhas.append("- OK: " + str(rebuild["ok"]))
    if rebuild.get("resultado"):
        stdout = rebuild["resultado"].get("stdout") or ""
        stderr = rebuild["resultado"].get("stderr") or ""
        if stdout:
            linhas.append("- stdout: " + stdout[:700])
        if stderr:
            linhas.append("- stderr: " + stderr[:700])

    linhas.append("")
    linhas.append("## Validacao app")
    linhas.append("")
    linhas.append("- App pronto: " + str(espera["ok"]))
    linhas.append("- Segundos aguardados: " + str(espera["segundos"]))
    linhas.append("- Login executado: " + str(validacao["executado"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("- Cookies recebidos: " + str(len(validacao["cookies"])))

    linhas.append("")
    linhas.append("## Logs novos")
    linhas.append("")
    linhas.append("- Linhas analisadas: " + str(logs["total_linhas"]))
    linhas.append("- Linhas Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Linhas cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Linhas usuario email: " + str(logs["linhas_usuario_email"]))
    linhas.append("- Achados criticos: " + str(len(logs["achados"])))
    if logs["achados"]:
        for item in logs["achados"]:
            linhas.append("- Linha " + str(item["linha"]) + ": " + item["trecho"])

    linhas.append("")
    linhas.append("## Amostra dos logs novos")
    linhas.append("")
    amostra = logs.get("amostra") or ""
    if amostra:
        for linha in amostra.splitlines()[-60:]:
            linhas.append("- " + linha[:240])
    else:
        linhas.append("- Sem logs novos na janela analisada.")

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhuma alteracao foi aplicada ao banco.")
    linhas.append("- Rebuild so foi executado se ETAPA14_1_REBUILD_APP=true.")
    linhas.append("- Logs antigos nao sao usados na contagem principal desta etapa.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Se logs novos estiverem limpos, avancar para CORS, cookie SameSite e headers finais.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_14_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_14_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    docker = verificar_docker()

    comparacao_antes = comparar_server_js()
    rebuild = rebuild_se_solicitado()
    aguardar = aguardar_app()
    comparacao_depois = comparar_server_js()

    since = agora_logs_since()
    validacao = validar_login_dashboard()
    time.sleep(2)

    logs_coleta = coletar_logs_novos(since)
    logs_analise = analisar_logs_texto(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "comparacao_server_antes": comparacao_antes,
        "rebuild": rebuild,
        "aguardar_app": aguardar,
        "comparacao_server": comparacao_depois,
        "logs_since": since,
        "validacao_login_dashboard": validacao,
        "logs_coleta": logs_coleta,
        "logs_novos_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_14_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_14_1_validar_runtime_hardening.json"
    md_path = REPORTS_DIR / "etapa_14_1_validar_runtime_hardening.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 14.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Docker OK: " + str(docker["docker_version"]["ok"]))
    print("Docker Compose OK: " + str(docker["docker_compose_version"]["ok"]))
    print("Container server.js localizado: " + str(comparacao_depois["container_localizado_ok"]))
    print("Hashes iguais: " + str(comparacao_depois["hashes_iguais"]))
    print("Rebuild solicitado: " + str(rebuild["solicitado"]))
    print("Rebuild executado: " + str(rebuild["executado"]))
    print("Rebuild OK: " + str(rebuild["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(validacao["login_ok"]))
    print("Dashboard OK: " + str(validacao["dashboard_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos usuario email: " + str(logs_analise["linhas_usuario_email"]))
    print("Achados criticos logs novos: " + str(len(logs_analise["achados"])))

    if not comparacao_depois["hashes_iguais"]:
        print("")
        print("Aviso: container ainda parece usar server.js diferente do local.")
        print("Se desejar aplicar o codigo local na imagem, rode com ETAPA14_1_REBUILD_APP=true.")

    if logs_analise["linhas_session_id"] > 0 or logs_analise["linhas_cookie"] > 0:
        print("")
        print("Aviso: logs novos ainda exibem dados sensiveis. Consulte o relatorio.")


if __name__ == "__main__":
    main()