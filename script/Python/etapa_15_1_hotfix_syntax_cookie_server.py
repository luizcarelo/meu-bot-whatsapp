#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 15.1 - Hotfix de sintaxe no cookie do server.js

Objetivo:
- Criar backup do server.js atual.
- Corrigir virgulas ausentes no bloco cookie.
- Validar sintaxe com node --check.
- Reiniciar app somente se node --check passar.
- Aguardar app responder.
- Validar rota inicial, login e dashboard.
- Nao alterar banco.
- Nao alterar regra de autenticacao.
- Atualizar documentacao obrigatoria.
- Gerar relatorios JSON e Markdown em reports.

Como executar:
sudo ETAPA15_1_LOGIN_EMAIL='admin@saas.com' ETAPA15_1_LOGIN_PASSWORD='123456' python3 etapa_15_1_hotfix_syntax_cookie_server.py
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


def node_check_server():
    if not SERVER_JS.exists():
        return {
            "ok": False,
            "stderr": "server.js ausente",
            "stdout": "",
            "returncode": None
        }

    return run_cmd(["node", "--check", "server.js"], 40)


def linha_eh_propriedade_objeto(linha):
    stripped = linha.strip()

    if not stripped:
        return False

    if stripped.startswith("//"):
        return False

    if stripped.startswith("/*"):
        return False

    if ":" not in stripped:
        return False

    antes = stripped.split(":", 1)[0].strip()

    if not antes:
        return False

    caracteres_ok = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$"
    for ch in antes:
        if ch not in caracteres_ok:
            return False

    return True


def linha_fecha_bloco(linha):
    stripped = linha.strip()
    return stripped.startswith("}") or stripped.startswith("});") or stripped.startswith("})")


def linha_precisa_virgula(linha_atual, proxima_linha):
    atual = linha_atual.rstrip()
    atual_limpa = atual.strip()
    proxima_limpa = proxima_linha.strip()

    if not atual_limpa:
        return False

    if atual_limpa.endswith(","):
        return False

    if atual_limpa.endswith("{"):
        return False

    if atual_limpa.endswith("["):
        return False

    if atual_limpa.startswith("//"):
        return False

    if linha_fecha_bloco(atual_limpa):
        return False

    if not linha_eh_propriedade_objeto(atual_limpa):
        return False

    if linha_eh_propriedade_objeto(proxima_limpa):
        return True

    if linha_fecha_bloco(proxima_limpa):
        return False

    return False


def encontrar_intervalo_cookie(linhas):
    inicio = None

    for idx, linha in enumerate(linhas):
        if "cookie:" in linha:
            pos = linha.find("cookie:")
            resto = linha[pos:]
            if "{" in resto:
                inicio = idx
                break

    if inicio is None:
        return None

    nivel = 0
    abriu = False

    for idx in range(inicio, len(linhas)):
        linha = linhas[idx]

        for ch in linha:
            if ch == "{":
                nivel += 1
                abriu = True
            elif ch == "}":
                nivel -= 1
                if abriu and nivel == 0:
                    return (inicio, idx)

    return None


def corrigir_cookie_server():
    resultado = {
        "arquivo": "server.js",
        "existe": SERVER_JS.exists(),
        "alterado": False,
        "linhas_corrigidas": [],
        "intervalo_cookie": None,
        "sha256_antes": sha256_arquivo(SERVER_JS) if SERVER_JS.exists() else None,
        "sha256_depois": None
    }

    texto = ler_texto(SERVER_JS)

    if texto is None:
        resultado["erro"] = "server.js ausente ou ilegivel"
        return resultado

    linhas = texto.splitlines()
    intervalo = encontrar_intervalo_cookie(linhas)
    resultado["intervalo_cookie"] = intervalo

    if intervalo is None:
        resultado["erro"] = "Bloco cookie nao localizado"
        resultado["sha256_depois"] = sha256_arquivo(SERVER_JS)
        return resultado

    inicio, fim = intervalo
    novas = list(linhas)

    for idx in range(inicio, fim):
        atual = novas[idx]
        proxima = novas[idx + 1] if idx + 1 < len(novas) else ""

        if linha_precisa_virgula(atual, proxima):
            novas[idx] = atual.rstrip() + ","
            resultado["linhas_corrigidas"].append(idx + 1)

    novo_texto = "\n".join(novas)
    if texto.endswith("\n"):
        novo_texto += "\n"

    if novo_texto != texto:
        gravar_texto(SERVER_JS, novo_texto)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256_arquivo(SERVER_JS)

    return resultado


def reiniciar_app_se_ok(node_check):
    if not node_check.get("ok"):
        return {
            "executado": False,
            "ok": None,
            "motivo": "node --check falhou",
            "resultado": None
        }

    r = run_cmd(["docker", "compose", "restart", "app"], 120)

    return {
        "executado": True,
        "ok": r.get("ok"),
        "motivo": None,
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
        "User-Agent": "etapa-15-1-hotfix/1.0"
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
        "home_ok": False,
        "login_ok": False,
        "dashboard_ok": False,
        "cookies": [],
        "home": None,
        "login": None,
        "dashboard": None
    }

    opener, jar = criar_opener()

    home = http_request(opener, "GET", "/")
    resultado["home"] = home
    resultado["home_ok"] = home.get("status") in [200, 302, 404]

    if not cred["email_configurado"] or not cred["senha_configurada"]:
        resultado["motivo"] = "Credenciais nao configuradas"
        return resultado

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
    achados = []
    session_id = 0
    cookie = 0
    email = 0

    for idx, linha in enumerate(str(texto or "").splitlines(), start=1):
        low = linha.lower()

        if "session id" in low:
            session_id += 1

        if "saas_crm_sid" in low or "connect.sid" in low or "header cookie" in low or "conteúdo:" in low or "conteudo:" in low:
            cookie += 1

        if "@" in linha and "." in linha:
            email += 1

        if "syntaxerror" in low or "error" in low or "exception" in low or "econnrefused" in low:
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

    marcador_inicio = "<!-- ETAPA_15_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_15_1_FIM -->"

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
    hotfix = relatorio["hotfix_cookie"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    validacao = relatorio["validacao"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 15.1 - Hotfix de sintaxe do cookie",
        [
            "Data: " + data,
            "",
            "Foi executado hotfix para corrigir sintaxe do bloco cookie em server.js.",
            "Linhas corrigidas: " + str(hotfix["linhas_corrigidas"]) + ".",
            "Node check OK: " + str(node["ok"]) + ".",
            "Restart executado: " + str(restart["executado"]) + ".",
            "App home OK: " + str(validacao["home_ok"]) + ".",
            "Login OK: " + str(validacao["login_ok"]) + ".",
            "Dashboard OK: " + str(validacao["dashboard_ok"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 15.1 - Correcao emergencial de sintaxe",
        [
            "Data: " + data,
            "",
            "Corrigidas virgulas ausentes no bloco cookie do server.js.",
            "Executado node --check em server.js.",
            "Reiniciado app somente apos validacao de sintaxe.",
            "Validado app, login e dashboard apos restart.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 15.1 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido corrigir apenas sintaxe do bloco cookie.",
            "Decidido nao alterar banco nem regra de autenticacao.",
            "Decidido reiniciar app somente apos node --check OK.",
            "Decidido manter a Etapa 15 para revisao posterior de CORS e headers."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Reexecutar ou revisar Etapa 15 apos hotfix se necessario.",
        "Confirmar headers e CORS em runtime com app estavel.",
        "Definir CORS_ORIGINS no ambiente final com dominio real HTTPS.",
        "Definir COOKIE_SECURE=true apenas com HTTPS valido.",
        "Planejar rate limit e politica CSP dedicada."
    ]

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 15.1",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    hotfix = relatorio["hotfix_cookie"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    aguardar = relatorio["aguardar_app"]
    validacao = relatorio["validacao"]
    logs = relatorio["logs_analise"]

    linhas.append("# Etapa 15.1 - Hotfix de sintaxe do cookie em server.js")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- server.js alterado: " + str(hotfix["alterado"]))
    linhas.append("- Linhas corrigidas: " + str(hotfix["linhas_corrigidas"]))
    linhas.append("- Node check OK: " + str(node["ok"]))
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Restart OK: " + str(restart["ok"]))
    linhas.append("- App pronto: " + str(aguardar["ok"]))
    linhas.append("- Home OK: " + str(validacao["home_ok"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("- Logs novos Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos email: " + str(logs["linhas_email"]))
    linhas.append("- Achados logs: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Hotfix aplicado")
    linhas.append("")
    linhas.append("- Intervalo cookie: " + str(hotfix["intervalo_cookie"]))
    linhas.append("- Linhas corrigidas: " + str(hotfix["linhas_corrigidas"]))
    linhas.append("- SHA256 antes: " + str(hotfix["sha256_antes"]))
    linhas.append("- SHA256 depois: " + str(hotfix["sha256_depois"]))
    if hotfix.get("erro"):
        linhas.append("- Erro: " + str(hotfix["erro"]))

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    linhas.append("- OK: " + str(node["ok"]))
    if node.get("stderr"):
        linhas.append("- stderr: " + node["stderr"][:1000])

    linhas.append("")
    linhas.append("## Restart e app")
    linhas.append("")
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Restart OK: " + str(restart["ok"]))
    linhas.append("- App pronto: " + str(aguardar["ok"]))
    linhas.append("- Segundos aguardados: " + str(aguardar["segundos"]))

    linhas.append("")
    linhas.append("## Validacao")
    linhas.append("")
    linhas.append("- Home OK: " + str(validacao["home_ok"]))
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
    linhas.append("- Linhas email: " + str(logs["linhas_email"]))
    linhas.append("- Achados: " + str(len(logs["achados"])))

    linhas.append("")
    linhas.append("## Amostra logs")
    linhas.append("")
    amostra = logs.get("amostra") or ""
    if amostra:
        for linha in amostra.splitlines()[-60:]:
            linhas.append("- " + linha[:240])
    else:
        linhas.append("- Sem logs novos.")

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhuma alteracao foi aplicada ao banco.")
    linhas.append("- A correcao foi limitada ao bloco cookie e validacao operacional.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Revalidar CORS e headers com app estavel antes de nova alteracao.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_15_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_15_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    hotfix = corrigir_cookie_server()
    node = node_check_server()
    restart = reiniciar_app_se_ok(node)
    aguardar = aguardar_app()

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
        "hotfix_cookie": hotfix,
        "node_check": node,
        "restart_app": restart,
        "aguardar_app": aguardar,
        "logs_since": since,
        "validacao": validacao,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_15_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_15_1_hotfix_syntax_cookie_server.json"
    md_path = REPORTS_DIR / "etapa_15_1_hotfix_syntax_cookie_server.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 15.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("server.js alterado: " + str(hotfix["alterado"]))
    print("Linhas corrigidas: " + str(hotfix["linhas_corrigidas"]))
    print("Node check OK: " + str(node["ok"]))
    print("Restart executado: " + str(restart["executado"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Home OK: " + str(validacao["home_ok"]))
    print("Login OK: " + str(validacao["login_ok"]))
    print("Dashboard OK: " + str(validacao["dashboard_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not node["ok"]:
        print("")
        print("Falha em node --check. O app nao foi reiniciado.")

    if not aguardar["ok"]:
        print("")
        print("App nao ficou pronto dentro do tempo limite. Consulte o relatorio.")


if __name__ == "__main__":
    main()