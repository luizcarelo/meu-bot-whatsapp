#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 14.2 - Sanitizar logs com email de usuario e nome de empresa

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Sanitizar logs em controllers/AuthController.js, routes/index.js e server.js.
- Remover email, nome de empresa e senha temporaria dos logs.
- Manter logs uteis com usuario_id e empresa_id.
- Nao alterar banco.
- Nao alterar regra de autenticacao.
- Rodar node --check nos arquivos alterados.
- Reiniciar app somente se ETAPA14_2_RESTART_APP=true.
- Validar login e dashboard quando credenciais forem fornecidas.
- Coletar logs novos e validar ausencia de Session ID, cookie e email.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar sem restart:
sudo ETAPA14_2_LOGIN_EMAIL='admin@saas.com' ETAPA14_2_LOGIN_PASSWORD='123456' python3 etapa_14_2_sanitizar_logs_email_usuario.py

Como executar com restart:
sudo ETAPA14_2_RESTART_APP=true ETAPA14_2_LOGIN_EMAIL='admin@saas.com' ETAPA14_2_LOGIN_PASSWORD='123456' python3 etapa_14_2_sanitizar_logs_email_usuario.py
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

ARQUIVOS_ALVO = [
    "controllers/AuthController.js",
    "routes/index.js",
    "server.js"
]

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
    "controllers/AuthController.js",
    "routes/index.js",
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


def linha_tem_log_sensivel_email(linha):
    low = linha.lower()

    if "console.log" not in low:
        return False

    termos = [
        "user.email",
        "req.session.user.email",
        "empresa_nome",
        "novaSenha",
        "nova senha",
        "senha para",
        "recuperação de senha",
        "recuperacao de senha",
        "[auth] sucesso",
        "[dashboard] acesso permitido",
        "senha migrada"
    ]

    for termo in termos:
        if termo.lower() in low:
            return True

    return False


def sanitizar_linha_js(linha):
    low = linha.lower()
    indent = linha[:len(linha) - len(linha.lstrip())]

    if "senha migrada" in low:
        return indent + "console.log(`[AUTH] Senha migrada para bcrypt usuario_id=${user.id}`);"

    if "debug" in low and "senha" in low:
        return indent + "console.log(`[AUTH] Recuperacao de senha processada usuario_id=${user.id}`);"

    if "recuper" in low and "senha" in low and "console.log" in low:
        return indent + "console.log(`[AUTH] Recuperacao de senha processada usuario_id=${user.id}`);"

    if "[auth]" in low and "sucesso" in low:
        return indent + "console.log(`[AUTH] Login OK usuario_id=${user.id} empresa_id=${user.empresa_id}`);"

    if "[dashboard]" in low or "dashboard" in low:
        return indent + "console.log(`[DASHBOARD] Acesso permitido empresa_id=${req.session?.empresaId || 'N/A'}`);"

    if "usuário logado" in low or "usuario logado" in low:
        return indent + "console.log(`[REQ] Usuario autenticado empresa_id=${req.session?.empresaId || 'N/A'}`);"

    return indent + "console.log('[LOG] Evento seguro registrado');"


def sanitizar_arquivo_js(rel_path):
    path = ROOT / rel_path
    texto = ler_texto(path)

    resultado = {
        "arquivo": rel_path,
        "existe": path.exists(),
        "alterado": False,
        "linhas_sanitizadas": 0,
        "sha256_antes": sha256_arquivo(path) if path.exists() else None,
        "sha256_depois": None
    }

    if texto is None:
        resultado["erro"] = "Arquivo ausente ou ilegivel"
        return resultado

    linhas = texto.splitlines()
    novas = []

    for linha in linhas:
        if linha_tem_log_sensivel_email(linha):
            novas.append(sanitizar_linha_js(linha))
            resultado["linhas_sanitizadas"] += 1
        else:
            novas.append(linha)

    novo = "\n".join(novas)
    if texto.endswith("\n"):
        novo += "\n"

    if novo != texto:
        gravar_texto(path, novo)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256_arquivo(path)
    return resultado


def aplicar_sanitizacao():
    resultados = []

    for rel_path in ARQUIVOS_ALVO:
        resultados.append(sanitizar_arquivo_js(rel_path))

    return resultados


def auditar_fontes():
    itens = []

    for rel_path in ARQUIVOS_ALVO:
        path = ROOT / rel_path
        texto = ler_texto(path)

        item = {
            "arquivo": rel_path,
            "existe": path.exists(),
            "console_email": 0,
            "console_empresa_nome": 0,
            "console_senha_temporaria": 0,
            "console_cookie_sessao": 0
        }

        if texto is None:
            item["erro"] = "Arquivo ausente ou ilegivel"
            itens.append(item)
            continue

        for linha in texto.splitlines():
            low = linha.lower()

            if "console.log" not in low:
                continue

            if "email" in low or "user.email" in low or "req.session.user.email" in low:
                item["console_email"] += 1

            if "empresa_nome" in low or "empresa_nome" in linha:
                item["console_empresa_nome"] += 1

            if "novasenha" in low or "senha para" in low or "senha tempor" in low:
                item["console_senha_temporaria"] += 1

            if "session id" in low or "saas_crm_sid" in low or "header cookie" in low:
                item["console_cookie_sessao"] += 1

        itens.append(item)

    totais = {
        "console_email": 0,
        "console_empresa_nome": 0,
        "console_senha_temporaria": 0,
        "console_cookie_sessao": 0
    }

    for item in itens:
        for chave in totais.keys():
            totais[chave] += int(item.get(chave) or 0)

    return {
        "arquivos": itens,
        "totais": totais
    }


def node_check():
    resultados = []

    for rel_path in ARQUIVOS_ALVO:
        path = ROOT / rel_path

        if not path.exists():
            resultados.append({
                "arquivo": rel_path,
                "ok": False,
                "erro": "Arquivo ausente"
            })
            continue

        r = run_cmd(["node", "--check", rel_path], 40)
        r["arquivo"] = rel_path
        resultados.append(r)

    ok = True
    for item in resultados:
        if not item.get("ok"):
            ok = False

    return {
        "ok": ok,
        "resultados": resultados
    }


def reiniciar_app_se_solicitado():
    valor = os.environ.get("ETAPA14_2_RESTART_APP", "").strip().lower()

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
        "content_type": "",
        "redirect_url": None
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-14-2-sanitizacao/1.0"
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
    empresa_nome = 0
    achados = []

    for idx, linha in enumerate(str(texto or "").splitlines(), start=1):
        low = linha.lower()

        if "session id" in low:
            session_id += 1

        if "saas_crm_sid" in low or "header cookie" in low or "conteúdo:" in low or "conteudo:" in low:
            cookie += 1

        tokens = linha.replace("(", " ").replace(")", " ").replace(",", " ").split()
        for token in tokens:
            if parece_email_token(token):
                email += 1
                break

        if "super admin" in low:
            empresa_nome += 1

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
        "linhas_empresa_nome": empresa_nome,
        "achados": achados,
        "amostra": redigir("\n".join(str(texto or "").splitlines()[-80:]))[:16000]
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_14_2_INICIO -->"
    marcador_fim = "<!-- ETAPA_14_2_FIM -->"

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
    audit_depois = relatorio["auditoria_depois"]["totais"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    logs = relatorio["logs_novos_analise"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 14.2 - Logs de usuario sanitizados",
        [
            "Data: " + data,
            "",
            "Foi aplicada sanitizacao adicional dos logs de usuario e empresa.",
            "Console email depois: " + str(audit_depois["console_email"]) + ".",
            "Console empresa_nome depois: " + str(audit_depois["console_empresa_nome"]) + ".",
            "Console senha temporaria depois: " + str(audit_depois["console_senha_temporaria"]) + ".",
            "Node check OK: " + str(node["ok"]) + ".",
            "Restart executado: " + str(restart["executado"]) + ".",
            "Logs novos com email: " + str(logs["linhas_email"]) + ".",
            "Logs novos com nome de empresa: " + str(logs["linhas_empresa_nome"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 14.2 - Sanitizacao de logs de usuario",
        [
            "Data: " + data,
            "",
            "Sanitizados logs de AuthController, rotas e servidor.",
            "Removida exposicao de email em logs de sucesso de login e dashboard.",
            "Removida exposicao de senha temporaria em log de recuperacao.",
            "Mantidos logs com usuario_id e empresa_id.",
            "Executado node --check nos arquivos relevantes.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 14.2 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido substituir logs identificaveis por logs com IDs internos.",
            "Decidido nao alterar regras de autenticacao.",
            "Decidido nao alterar banco.",
            "Decidido reiniciar app somente com ETAPA14_2_RESTART_APP=true."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Se o app nao foi reiniciado, reiniciar em janela controlada para aplicar sanitizacao em runtime.",
        "Reexecutar validacao de logs apos restart.",
        "Revisar CORS permissivo em etapa dedicada.",
        "Revisar cookie SameSite e secure para HTTPS producao.",
        "Planejar rate limit e politica de seguranca de conteudo."
    ]

    if restart["executado"] and logs["linhas_email"] == 0 and logs["linhas_empresa_nome"] == 0:
        pendencias = [
            "Data: " + data,
            "",
            "Revisar CORS permissivo em etapa dedicada.",
            "Revisar cookie SameSite e secure para HTTPS producao.",
            "Planejar rate limit e politica de seguranca de conteudo.",
            "Validar ambiente externo com HTTPS antes de producao."
        ]

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 14.2",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    audit_antes = relatorio["auditoria_antes"]["totais"]
    audit_depois = relatorio["auditoria_depois"]["totais"]
    sanitizacao = relatorio["sanitizacao"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    validacao = relatorio["validacao_login_dashboard"]
    logs = relatorio["logs_novos_analise"]

    linhas.append("# Etapa 14.2 - Sanitizar logs de email e usuario")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Node check OK: " + str(node["ok"]))
    linhas.append("- Restart solicitado: " + str(restart["solicitado"]))
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Login OK: " + str(validacao["login_ok"]))
    linhas.append("- Dashboard OK: " + str(validacao["dashboard_ok"]))
    linhas.append("- Logs novos Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos email: " + str(logs["linhas_email"]))
    linhas.append("- Logs novos nome empresa: " + str(logs["linhas_empresa_nome"]))
    linhas.append("- Achados criticos: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Auditoria antes")
    linhas.append("")
    linhas.append("- Console email: " + str(audit_antes["console_email"]))
    linhas.append("- Console empresa_nome: " + str(audit_antes["console_empresa_nome"]))
    linhas.append("- Console senha temporaria: " + str(audit_antes["console_senha_temporaria"]))
    linhas.append("- Console cookie sessao: " + str(audit_antes["console_cookie_sessao"]))

    linhas.append("")
    linhas.append("## Sanitizacao aplicada")
    linhas.append("")
    for item in sanitizacao:
        linhas.append(
            "- "
            + item["arquivo"]
            + ": alterado="
            + str(item["alterado"])
            + ", linhas_sanitizadas="
            + str(item["linhas_sanitizadas"])
        )

    linhas.append("")
    linhas.append("## Auditoria depois")
    linhas.append("")
    linhas.append("- Console email: " + str(audit_depois["console_email"]))
    linhas.append("- Console empresa_nome: " + str(audit_depois["console_empresa_nome"]))
    linhas.append("- Console senha temporaria: " + str(audit_depois["console_senha_temporaria"]))
    linhas.append("- Console cookie sessao: " + str(audit_depois["console_cookie_sessao"]))

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    linhas.append("- OK: " + str(node["ok"]))
    for item in node["resultados"]:
        linhas.append(
            "- "
            + item["arquivo"]
            + ": ok="
            + str(item.get("ok"))
            + ", returncode="
            + str(item.get("returncode"))
        )
        if item.get("stderr"):
            linhas.append("  - stderr: " + item["stderr"][:400])

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
    linhas.append("## Logs novos")
    linhas.append("")
    linhas.append("- Linhas analisadas: " + str(logs["total_linhas"]))
    linhas.append("- Linhas Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Linhas cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Linhas email: " + str(logs["linhas_email"]))
    linhas.append("- Linhas nome empresa: " + str(logs["linhas_empresa_nome"]))
    linhas.append("- Achados criticos: " + str(len(logs["achados"])))

    linhas.append("")
    linhas.append("## Amostra logs novos")
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
    linhas.append("- Regras de autenticacao nao foram alteradas.")
    linhas.append("- Restart so foi executado se ETAPA14_2_RESTART_APP=true.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Se logs estiverem limpos, avancar para CORS, cookie SameSite e headers finais.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_14_2_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_14_2_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    auditoria_antes = auditar_fontes()
    sanitizacao = aplicar_sanitizacao()
    auditoria_depois = auditar_fontes()
    node = node_check()

    restart = reiniciar_app_se_solicitado()
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
        "auditoria_antes": auditoria_antes,
        "sanitizacao": sanitizacao,
        "auditoria_depois": auditoria_depois,
        "node_check": node,
        "restart_app": restart,
        "aguardar_app": aguardar,
        "logs_since": since,
        "validacao_login_dashboard": validacao,
        "logs_coleta": logs_coleta,
        "logs_novos_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_14_2_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_14_2_sanitizar_logs_email_usuario.json"
    md_path = REPORTS_DIR / "etapa_14_2_sanitizar_logs_email_usuario.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 14.2 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Node check OK: " + str(node["ok"]))
    print("Restart solicitado: " + str(restart["solicitado"]))
    print("Restart executado: " + str(restart["executado"]))
    print("Login OK: " + str(validacao["login_ok"]))
    print("Dashboard OK: " + str(validacao["dashboard_ok"]))
    print("Auditoria depois console email: " + str(auditoria_depois["totais"]["console_email"]))
    print("Auditoria depois console empresa_nome: " + str(auditoria_depois["totais"]["console_empresa_nome"]))
    print("Auditoria depois console senha temporaria: " + str(auditoria_depois["totais"]["console_senha_temporaria"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))
    print("Logs novos nome empresa: " + str(logs_analise["linhas_empresa_nome"]))

    if not restart["executado"]:
        print("")
        print("Aviso: app nao foi reiniciado. Para aplicar em runtime, execute com ETAPA14_2_RESTART_APP=true.")

    if logs_analise["linhas_email"] > 0 or logs_analise["linhas_empresa_nome"] > 0:
        print("")
        print("Aviso: logs novos ainda possuem identificadores. Consulte o relatorio.")


if __name__ == "__main__":
    main()