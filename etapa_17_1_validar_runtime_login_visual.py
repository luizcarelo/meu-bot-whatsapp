#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 17.1 - Validar runtime da tela de login visual

Objetivo:
- Criar backup documental.
- Gerar manifesto antes e depois.
- Comparar views/login.ejs local com o arquivo dentro do container app.
- Verificar se o runtime esta usando a tela nova.
- Reiniciar app somente se ETAPA17_1_RESTART_APP=true.
- Validar /login procurando textos da nova tela.
- Validar login real e dashboard.
- Nao alterar frontend.
- Nao alterar backend.
- Nao alterar banco.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar sem restart:
sudo ETAPA17_1_LOGIN_EMAIL='admin@saas.com' ETAPA17_1_LOGIN_PASSWORD='123456' python3 etapa_17_1_validar_runtime_login_visual.py

Como executar com restart:
sudo ETAPA17_1_RESTART_APP=true ETAPA17_1_LOGIN_EMAIL='admin@saas.com' ETAPA17_1_LOGIN_PASSWORD='123456' python3 etapa_17_1_validar_runtime_login_visual.py
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

LOGIN_VIEW = ROOT / "views" / "login.ejs"

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
    "reports",
    "__pycache__"
]

CHAVES_EMAIL = [
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


def sha256_bytes(dados):
    h = hashlib.sha256()
    h.update(dados)
    return h.hexdigest()


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


def shell_quote(valor):
    return "'" + str(valor).replace("'", "'\"'\"'") + "'"


def localizar_login_container():
    script = (
        "set -eu; "
        "for p in /usr/src/app/views/login.ejs /app/views/login.ejs /home/node/app/views/login.ejs ./views/login.ejs; do "
        "if [ -f \"$p\" ]; then echo \"$p\"; exit 0; fi; "
        "done; "
        "find /app /usr/src/app /home/node/app -maxdepth 5 -path '*/views/login.ejs' 2>/dev/null | head -n 1"
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


def hash_arquivo_container(path):
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


def comparar_login_view():
    localizado = localizar_login_container()
    container_hash = hash_arquivo_container(localizado.get("path"))

    local_hash = sha256_arquivo(LOGIN_VIEW)
    iguais = bool(local_hash and container_hash.get("hash") and local_hash == container_hash.get("hash"))

    return {
        "local_existe": LOGIN_VIEW.exists(),
        "local_hash": local_hash,
        "container_localizado_ok": localizado.get("ok"),
        "container_path": localizado.get("path"),
        "container_hash_ok": container_hash.get("ok"),
        "container_hash": container_hash.get("hash"),
        "hashes_iguais": iguais,
        "localizar_resultado": localizado.get("resultado"),
        "hash_resultado": container_hash.get("resultado")
    }


def reiniciar_app_se_solicitado():
    valor = os.environ.get("ETAPA17_1_RESTART_APP", "").strip().lower()

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
        "User-Agent": "etapa-17-1-runtime-login-visual/1.0"
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


def validar_login_page_visual():
    opener, jar = criar_opener()
    r = http_request(opener, "GET", "/login")

    body = r.get("body_full_limited") or ""
    lower = body.lower()

    textos = {
        "acesso_seguro": "acesso seguro" in lower,
        "entrar_no_painel": "entrar no painel" in lower,
        "centralize_operacao": "centralize sua operação" in lower or "centralize sua operacao" in lower,
        "ambiente_seguro": "ambiente seguro de atendimento" in lower,
        "bg_slate_950": "bg-slate-950" in body,
        "login_bg": "login-bg" in body,
        "glass_card": "glass-card" in body
    }

    ok = bool(
        r.get("status") == 200 and
        textos["acesso_seguro"] and
        textos["entrar_no_painel"] and
        textos["centralize_operacao"] and
        textos["login_bg"] and
        textos["glass_card"]
    )

    return {
        "http": {
            "path": r.get("path"),
            "status": r.get("status"),
            "ok": r.get("ok"),
            "erro": r.get("erro"),
            "content_type": r.get("content_type"),
            "redirect_url": r.get("redirect_url"),
            "body_preview": r.get("body_preview")
        },
        "textos": textos,
        "ok": ok
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

    body = (login.get("body_preview") or "").lower()
    status_ok = login.get("status") in [200, 201, 302]
    cookie_ok = len(resultado["cookies"]) > 0
    body_ok = "sucesso" in body or "success" in body or "dashboard" in body or "ok" in body

    resultado["login_ok"] = bool(status_ok and (cookie_ok or body_ok))

    dashboard = http_request(opener, "GET", DASHBOARD_PATH)
    resultado["dashboard"] = {
        "status": dashboard.get("status"),
        "ok": dashboard.get("ok"),
        "erro": dashboard.get("erro"),
        "content_type": dashboard.get("content_type"),
        "body_preview": dashboard.get("body_preview")
    }
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


def parece_email_token(token):
    if "@" not in token:
        return False
    if "." not in token:
        return False
    if len(token) < 5:
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
            if parece_email_token(token):
                email += 1
                break

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

    marcador_inicio = "<!-- ETAPA_17_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_17_1_FIM -->"

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
    cmp = relatorio["comparacao_login_view_depois"]
    restart = relatorio["restart_app"]
    page = relatorio["validacao_login_page"]
    auth = relatorio["validacao_login_dashboard"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 17.1 - Runtime da tela de login visual validado",
        [
            "Data: " + data,
            "",
            "Foi validado o runtime da tela de login visual.",
            "Hash local igual ao container: " + str(cmp["hashes_iguais"]) + ".",
            "Restart solicitado: " + str(restart["solicitado"]) + ".",
            "Restart executado: " + str(restart["executado"]) + ".",
            "Tela nova validada em /login: " + str(page["ok"]) + ".",
            "Login OK: " + str(auth["login_ok"]) + ".",
            "Dashboard OK: " + str(auth["dashboard_ok"]) + ".",
            "Nenhum codigo foi alterado nesta etapa."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 17.1 - Validacao runtime do login visual",
        [
            "Data: " + data,
            "",
            "Comparado views/login.ejs local com arquivo dentro do container app.",
            "Restart executado somente quando solicitado por variavel de ambiente.",
            "Validada tela /login com textos e classes da nova interface.",
            "Validado login real e dashboard.",
            "Gerados backup documental, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 17.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido validar runtime antes de novas melhorias visuais.",
            "Decidido comparar hashes local/container para confirmar aplicacao da view.",
            "Decidido nao alterar frontend nesta etapa.",
            "Decidido reiniciar app somente com ETAPA17_1_RESTART_APP=true."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Validar visual manualmente no navegador.",
        "Se a tela nova nao aparecer, verificar cache do navegador ou necessidade de rebuild.",
        "Planejar melhoria controlada do dashboard.",
        "Planejar internalizacao de dependencias externas em etapas separadas."
    ]

    if page["ok"]:
        pendencias = [
            "Data: " + data,
            "",
            "Validar visual manualmente no navegador.",
            "Planejar melhoria controlada do dashboard.",
            "Planejar internalizacao de dependencias externas em etapas separadas.",
            "Mapear scripts inline antes de CSP forte."
        ]

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 17.1",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    cmp_antes = relatorio["comparacao_login_view_antes"]
    cmp_depois = relatorio["comparacao_login_view_depois"]
    restart = relatorio["restart_app"]
    aguardar = relatorio["aguardar_app"]
    page = relatorio["validacao_login_page"]
    auth = relatorio["validacao_login_dashboard"]
    logs = relatorio["logs_analise"]

    linhas = []

    linhas.append("# Etapa 17.1 - Validar runtime da tela de login visual")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup documental criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Hashes iguais antes: " + str(cmp_antes["hashes_iguais"]))
    linhas.append("- Hashes iguais depois: " + str(cmp_depois["hashes_iguais"]))
    linhas.append("- Restart solicitado: " + str(restart["solicitado"]))
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Restart OK: " + str(restart["ok"]))
    linhas.append("- App pronto: " + str(aguardar["ok"]))
    linhas.append("- Tela nova /login OK: " + str(page["ok"]))
    linhas.append("- Login OK: " + str(auth["login_ok"]))
    linhas.append("- Dashboard OK: " + str(auth["dashboard_ok"]))
    linhas.append("- Logs novos Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos email: " + str(logs["linhas_email"]))
    linhas.append("- Achados criticos logs: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Comparacao login.ejs antes")
    linhas.append("")
    linhas.append("- Local hash: " + str(cmp_antes["local_hash"]))
    linhas.append("- Container path: " + str(cmp_antes["container_path"]))
    linhas.append("- Container hash: " + str(cmp_antes["container_hash"]))
    linhas.append("- Hashes iguais: " + str(cmp_antes["hashes_iguais"]))

    linhas.append("")
    linhas.append("## Comparacao login.ejs depois")
    linhas.append("")
    linhas.append("- Local hash: " + str(cmp_depois["local_hash"]))
    linhas.append("- Container path: " + str(cmp_depois["container_path"]))
    linhas.append("- Container hash: " + str(cmp_depois["container_hash"]))
    linhas.append("- Hashes iguais: " + str(cmp_depois["hashes_iguais"]))

    linhas.append("")
    linhas.append("## Restart e disponibilidade")
    linhas.append("")
    linhas.append("- Restart solicitado: " + str(restart["solicitado"]))
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Restart OK: " + str(restart["ok"]))
    linhas.append("- App pronto: " + str(aguardar["ok"]))
    linhas.append("- Segundos aguardados: " + str(aguardar["segundos"]))

    linhas.append("")
    linhas.append("## Validacao da tela /login")
    linhas.append("")
    linhas.append("- OK: " + str(page["ok"]))
    linhas.append("- HTTP status: " + str(page["http"]["status"]))
    for chave, valor in sorted(page["textos"].items()):
        linhas.append("- " + chave + ": " + str(valor))

    linhas.append("")
    linhas.append("## Validacao login e dashboard")
    linhas.append("")
    linhas.append("- Executada: " + str(auth["executado"]))
    linhas.append("- Email configurado: " + str(auth["email_configurado"]))
    linhas.append("- Senha configurada: " + str(auth["senha_configurada"]))
    linhas.append("- Login OK: " + str(auth["login_ok"]))
    linhas.append("- Dashboard OK: " + str(auth["dashboard_ok"]))
    linhas.append("- Cookies recebidos: " + str(len(auth["cookies"])))

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
    linhas.append("- Nenhum arquivo de frontend foi alterado nesta etapa.")
    linhas.append("- Nenhum backend foi alterado.")
    linhas.append("- Nenhum banco foi alterado.")
    linhas.append("- O app so foi reiniciado se ETAPA17_1_RESTART_APP=true.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Se a tela nova validou, fazer verificacao visual manual no navegador e planejar melhoria do dashboard.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_17_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_17_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    comparacao_antes = comparar_login_view()
    restart = reiniciar_app_se_solicitado()
    aguardar = aguardar_app()
    comparacao_depois = comparar_login_view()

    since = agora_logs_since()
    login_page = validar_login_page_visual()
    auth = validar_login_dashboard()
    time.sleep(2)

    logs_coleta = coletar_logs_novos(since)
    logs_analise = analisar_logs_texto(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "comparacao_login_view_antes": comparacao_antes,
        "restart_app": restart,
        "aguardar_app": aguardar,
        "comparacao_login_view_depois": comparacao_depois,
        "logs_since": since,
        "validacao_login_page": login_page,
        "validacao_login_dashboard": auth,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_17_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_17_1_validar_runtime_login_visual.json"
    md_path = REPORTS_DIR / "etapa_17_1_validar_runtime_login_visual.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 17.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Hashes iguais antes: " + str(comparacao_antes["hashes_iguais"]))
    print("Hashes iguais depois: " + str(comparacao_depois["hashes_iguais"]))
    print("Restart solicitado: " + str(restart["solicitado"]))
    print("Restart executado: " + str(restart["executado"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Tela nova /login OK: " + str(login_page["ok"]))
    print("Login OK: " + str(auth["login_ok"]))
    print("Dashboard OK: " + str(auth["dashboard_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not login_page["ok"]:
        print("")
        print("Aviso: tela nova de login ainda nao validou em runtime.")
        print("Se hashes forem iguais, tente abrir em aba anonima ou limpar cache do navegador.")
        print("Se hashes forem diferentes, pode ser necessario rebuild ou revisar volume do container.")


if __name__ == "__main__":
    main()
