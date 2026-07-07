#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 12.1 - Diagnosticar login e autenticacao

Objetivo:
- Criar backup documental.
- Gerar manifesto antes e depois.
- Nao alterar banco.
- Nao alterar codigo.
- Verificar usuario admin no banco em modo somente leitura.
- Verificar se usuario esta ativo e empresa vinculada.
- Identificar tipo de hash da senha sem imprimir o hash completo.
- Inspecionar arquivos locais de autenticacao.
- Detectar campos esperados pelo login.
- Testar payloads de login com senha fornecida por ambiente.
- Nao imprimir senha.
- Manter cookies apenas em memoria.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar com credenciais:
sudo ETAPA12_LOGIN_EMAIL='admin@saas.com' ETAPA12_LOGIN_PASSWORD='SUA_SENHA' python3 etapa_12_1_diagnosticar_login_auth.py
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
from urllib.parse import urlencode
from http.cookiejar import CookieJar

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

MAX_LEITURA = 3145728
BASE_URL = "http://127.0.0.1:50010"
LOGIN_PATH = "/api/auth/login"

ARQUIVOS_AUTH = [
    "controllers/AuthController.js",
    "routes/api.js",
    "routes/index.js",
    "server.js"
]

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
    "ETAPA12_LOGIN_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SEED_ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

CHAVES_SENHA = [
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
        if path.stat().st_size > MAX_LEITURA:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def gravar_texto(path, conteudo):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8")


def limpar_saida(texto):
    if texto is None:
        return texto

    out = str(texto)

    for valor in valores_sensiveis_env():
        if valor:
            out = out.replace(valor, "<REDIGIDO>")

    out = out.replace(chr(42), "[asterisco]")
    return out


def validar_sem_asterisco_indevido(conteudo, nome):
    if chr(42) in conteudo:
        raise ValueError(
            "Validacao bloqueou a geracao de "
            + nome
            + " por conter caractere asterisco."
        )


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
                "erro": limpar_saida(str(exc))
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
    if origem.is_dir():
        shutil.copytree(origem, destino, dirs_exist_ok=True)
    else:
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
                "erro": limpar_saida(str(exc))
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
            "stdout": limpar_saida(proc.stdout.strip())[:12000],
            "stderr": limpar_saida(proc.stderr.strip())[:12000],
            "ok": proc.returncode == 0
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "returncode": None,
            "stdout": "",
            "stderr": limpar_saida(str(exc)),
            "ok": False
        }


def verificar_docker():
    return {
        "docker_version": run_cmd(["docker", "--version"], 20),
        "docker_compose_version": run_cmd(["docker", "compose", "version"], 20),
        "docker_compose_ps": run_cmd(["docker", "compose", "ps"], 30)
    }


def executar_psql(sql, db_user, db_name):
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-At",
        "-F",
        "|",
        "-c",
        sql
    ]

    return run_cmd(cmd, 60)


def sql_quote(valor):
    return "'" + str(valor).replace("'", "''") + "'"


def diagnosticar_usuario_banco():
    env = parse_env()
    db_user = env.get("DB_USER") or "postgres"
    db_name = env.get("DB_NAME") or "postgres"
    cred = obter_credenciais()

    resultado = {
        "executado": False,
        "email_configurado": cred["email_configurado"],
        "usuario_encontrado": False,
        "email": cred["email"] if cred["email"] else "",
        "dados": None,
        "erro": None
    }

    if not cred["email"]:
        resultado["erro"] = "Email nao configurado"
        return resultado

    email_sql = sql_quote(cred["email"])

    sql = (
        "SELECT "
        "u.id, "
        "u.email, "
        "COALESCE(u.ativo::text, ''), "
        "COALESCE(u.is_admin::text, ''), "
        "COALESCE(u.empresa_id::text, ''), "
        "COALESCE(e.nome, ''), "
        "COALESCE(e.ativo::text, ''), "
        "COALESCE(length(u.senha)::text, '0'), "
        "COALESCE(substring(u.senha from 1 for 7), '') "
        "FROM usuarios_painel u "
        "LEFT JOIN empresas e ON e.id = u.empresa_id "
        "WHERE u.email = "
        + email_sql
        + " LIMIT 1"
    )

    r = executar_psql(sql, db_user, db_name)
    resultado["executado"] = True

    if not r.get("ok"):
        resultado["erro"] = r.get("stderr") or r.get("stdout")
        return resultado

    linha = str(r.get("stdout") or "").strip()

    if not linha:
        return resultado

    partes = linha.split("|")
    while len(partes) < 9:
        partes.append("")

    senha_prefixo = partes[8]
    hash_tipo = "desconhecido"

    if senha_prefixo.startswith("$2a$") or senha_prefixo.startswith("$2b$") or senha_prefixo.startswith("$2y$"):
        hash_tipo = "bcrypt"
    elif senha_prefixo.startswith("$argon"):
        hash_tipo = "argon"
    elif len(senha_prefixo) >= 7:
        hash_tipo = "texto_ou_hash_outro"

    resultado["usuario_encontrado"] = True
    resultado["dados"] = {
        "id": partes[0],
        "email": partes[1],
        "usuario_ativo": partes[2],
        "is_admin": partes[3],
        "empresa_id": partes[4],
        "empresa_nome": partes[5],
        "empresa_ativa": partes[6],
        "senha_tamanho": partes[7],
        "senha_tipo_provavel": hash_tipo,
        "senha_prefixo_redigido": senha_prefixo[:4] + "..."
    }

    return resultado


def linha_contem_interesse(linha):
    termos = [
        "/api/auth/login",
        "auth/login",
        "login",
        "password",
        "senha",
        "req.body",
        "email",
        "bcrypt",
        "compare"
    ]

    lower = linha.lower()

    for termo in termos:
        if termo in lower:
            return True

    return False


def inspecionar_arquivos_auth():
    resultados = []

    for nome in ARQUIVOS_AUTH:
        path = ROOT / nome
        texto = ler_texto(path)

        item = {
            "arquivo": nome,
            "existe": path.exists(),
            "achados": [],
            "campos_detectados": []
        }

        if texto is None:
            item["erro"] = "Arquivo ausente ou ilegivel"
            resultados.append(item)
            continue

        linhas = texto.splitlines()

        for numero, linha in enumerate(linhas, start=1):
            if linha_contem_interesse(linha):
                item["achados"].append({
                    "linha": numero,
                    "trecho": limpar_saida(linha.strip())[:260]
                })

        lower = texto.lower()

        campos = []
        if "password" in lower:
            campos.append("password")
        if "senha" in lower:
            campos.append("senha")
        if "email" in lower:
            campos.append("email")
        if "req.body" in lower:
            campos.append("req.body")
        if "bcrypt" in lower:
            campos.append("bcrypt")

        item["campos_detectados"] = campos
        resultados.append(item)

    resumo = {
        "usa_password": False,
        "usa_senha": False,
        "usa_bcrypt": False,
        "rota_login_detectada": False
    }

    for item in resultados:
        campos = item.get("campos_detectados", [])
        if "password" in campos:
            resumo["usa_password"] = True
        if "senha" in campos:
            resumo["usa_senha"] = True
        if "bcrypt" in campos:
            resumo["usa_bcrypt"] = True

        for achado in item.get("achados", []):
            trecho = achado.get("trecho", "").lower()
            if "auth/login" in trecho or "/api/auth/login" in trecho:
                resumo["rota_login_detectada"] = True

    return {
        "arquivos": resultados,
        "resumo": resumo
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


def http_request(opener, metodo, path, data_obj=None, form=False):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "url": url,
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
        "User-Agent": "etapa-12-1-diagnostico-local/1.0"
    }

    if data_obj is not None:
        if form:
            body_text = urlencode(data_obj)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body_text = json.dumps(data_obj)
            headers["Content-Type"] = "application/json"

        body_bytes = body_text.encode("utf-8")

    req = Request(
        url,
        data=body_bytes,
        headers=headers,
        method=metodo
    )

    try:
        with opener.open(req, timeout=15) as resp:
            body = resp.read(8192)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["body_preview"] = limpar_saida(texto[:1200])
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
        resultado["erro"] = limpar_saida(str(exc))
        resultado["body_preview"] = limpar_saida(texto[:1200])
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
    except URLError as exc:
        resultado["erro"] = limpar_saida(str(exc.reason))
    except Exception as exc:
        resultado["erro"] = limpar_saida(str(exc))

    return resultado


def testar_payloads_login():
    cred = obter_credenciais()

    resultado = {
        "executado": False,
        "email_configurado": cred["email_configurado"],
        "senha_configurada": cred["senha_configurada"],
        "email_usado": cred["email"] if cred["email"] else "",
        "tentativas": [],
        "melhor_tentativa": None,
        "login_ok": False
    }

    if not cred["email_configurado"] or not cred["senha_configurada"]:
        resultado["motivo"] = "Credenciais nao configuradas"
        return resultado

    payloads = [
        {
            "nome": "json_email_password",
            "payload": {
                "email": cred["email"],
                "password": cred["senha"]
            },
            "form": False
        },
        {
            "nome": "json_email_senha",
            "payload": {
                "email": cred["email"],
                "senha": cred["senha"]
            },
            "form": False
        },
        {
            "nome": "form_email_password",
            "payload": {
                "email": cred["email"],
                "password": cred["senha"]
            },
            "form": True
        },
        {
            "nome": "form_email_senha",
            "payload": {
                "email": cred["email"],
                "senha": cred["senha"]
            },
            "form": True
        }
    ]

    resultado["executado"] = True

    for plano in payloads:
        opener, jar = criar_opener()
        http = http_request(opener, "POST", LOGIN_PATH, plano["payload"], plano["form"])
        cookies = cookies_resumo(jar)

        body = (http.get("body_preview") or "").lower()
        status = http.get("status")
        sucesso_por_body = "sucesso" in body or "success" in body or "dashboard" in body or "ok" in body
        sucesso_por_cookie = len(cookies) > 0
        status_possivel = status in [200, 201, 302]

        tentativa_ok = bool(status_possivel and (sucesso_por_body or sucesso_por_cookie))

        dash = None
        if tentativa_ok:
            dash = http_request(opener, "GET", "/dashboard")
            dash_body = (dash.get("body_preview") or "").lower()
            if "login - acesso seguro" in dash_body and dash.get("redirect_url", "").endswith("/login"):
                tentativa_ok = False

        tentativa = {
            "nome": plano["nome"],
            "content_type": "form" if plano["form"] else "json",
            "status": status,
            "ok_http": http.get("ok"),
            "tentativa_ok": tentativa_ok,
            "cookies_total": len(cookies),
            "cookies": cookies,
            "erro": http.get("erro"),
            "body_preview": http.get("body_preview"),
            "dashboard_pos_login": dash
        }

        resultado["tentativas"].append(tentativa)

        if tentativa_ok and resultado["melhor_tentativa"] is None:
            resultado["melhor_tentativa"] = plano["nome"]
            resultado["login_ok"] = True

    return resultado


def coletar_logs_app():
    comandos = [
        ["docker", "compose", "logs", "--tail=180", "app"],
        ["docker", "logs", "--tail=180", "whatsapp_bot_app"]
    ]

    resultados = []

    for cmd in comandos:
        r = run_cmd(cmd, 50)
        resultados.append(r)
        if r.get("ok") and (r.get("stdout") or r.get("stderr")):
            break

    return resultados


def analisar_logs(resultados_logs):
    texto = ""

    for item in resultados_logs:
        texto += "\n" + (item.get("stdout") or "")
        texto += "\n" + (item.get("stderr") or "")

    achados = []
    termos = [
        "error",
        "exception",
        "stack",
        "syntaxerror",
        "database",
        "senha incorreta",
        "usuario nao encontrado",
        "credenciais",
        "unauthorized"
    ]

    lower = texto.lower()
    for termo in termos:
        if termo in lower:
            for idx, linha in enumerate(texto.splitlines(), start=1):
                if termo in linha.lower():
                    achados.append({
                        "termo": termo,
                        "linha": idx,
                        "trecho": limpar_saida(linha.strip())[:300]
                    })
                    break

    return {
        "total_linhas": len(texto.splitlines()),
        "achados": achados,
        "tem_achados": len(achados) > 0,
        "amostra": limpar_saida("\n".join(texto.splitlines()[-60:]))[:12000]
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_12_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_12_1_FIM -->"

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
    usuario = relatorio["usuario_banco"]
    auth = relatorio["auth_inspecao"]["resumo"]
    testes = relatorio["testes_login"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 12.1 - Diagnostico de login",
        [
            "Data: " + data,
            "",
            "Foi executado diagnostico seguro do login e autenticacao.",
            "Usuario encontrado no banco: " + str(usuario["usuario_encontrado"]) + ".",
            "Rota de login detectada nos arquivos: " + str(auth["rota_login_detectada"]) + ".",
            "Uso de password detectado: " + str(auth["usa_password"]) + ".",
            "Uso de senha detectado: " + str(auth["usa_senha"]) + ".",
            "Login validado em payload testado: " + str(testes["login_ok"]) + ".",
            "Nenhuma alteracao foi aplicada ao banco ou ao codigo."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 12.1 - Diagnostico de autenticacao",
        [
            "Data: " + data,
            "",
            "Verificado usuario admin no banco em modo somente leitura.",
            "Inspecionados arquivos locais de autenticacao.",
            "Testados payloads de login sem imprimir senha.",
            "Coletados logs recentes para apoio ao diagnostico.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 12.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido diagnosticar antes de resetar senha.",
            "Decidido nao persistir cookies nem credenciais.",
            "Decidido testar payloads JSON e form com campos password e senha.",
            "Decidido nao alterar banco nem codigo nesta etapa."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Revisar resultado do diagnostico de login.",
        "Se a senha informada nao autenticar, aprovar etapa separada para reset controlado de senha.",
        "Validar rotas reais do sistema apos login confirmado.",
        "Reduzir verbosidade de logs de sessao e cookies em producao.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes."
    ]

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 12.1",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    usuario = relatorio["usuario_banco"]
    auth = relatorio["auth_inspecao"]
    testes = relatorio["testes_login"]
    logs = relatorio["logs_analise"]

    linhas.append("# Etapa 12.1 - Diagnosticar login e autenticacao")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup documental criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Docker OK: " + str(relatorio["docker"]["docker_version"]["ok"]))
    linhas.append("- Docker Compose OK: " + str(relatorio["docker"]["docker_compose_version"]["ok"]))
    linhas.append("- Email configurado: " + str(testes["email_configurado"]))
    linhas.append("- Senha configurada: " + str(testes["senha_configurada"]))
    linhas.append("- Usuario encontrado no banco: " + str(usuario["usuario_encontrado"]))
    linhas.append("- Login OK em algum payload: " + str(testes["login_ok"]))
    linhas.append("- Melhor tentativa: " + str(testes["melhor_tentativa"]))
    linhas.append("- Achados em logs: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Usuario no banco")
    linhas.append("")
    linhas.append("- Executado: " + str(usuario["executado"]))
    linhas.append("- Encontrado: " + str(usuario["usuario_encontrado"]))
    linhas.append("- Email: " + str(usuario["email"]))
    if usuario.get("dados"):
        dados = usuario["dados"]
        linhas.append("- ID: " + str(dados["id"]))
        linhas.append("- Ativo: " + str(dados["usuario_ativo"]))
        linhas.append("- Admin: " + str(dados["is_admin"]))
        linhas.append("- Empresa ID: " + str(dados["empresa_id"]))
        linhas.append("- Empresa nome: " + str(dados["empresa_nome"]))
        linhas.append("- Empresa ativa: " + str(dados["empresa_ativa"]))
        linhas.append("- Tamanho senha/hash: " + str(dados["senha_tamanho"]))
        linhas.append("- Tipo provavel da senha/hash: " + str(dados["senha_tipo_provavel"]))
        linhas.append("- Prefixo redigido: " + str(dados["senha_prefixo_redigido"]))
    if usuario.get("erro"):
        linhas.append("- Erro: " + str(usuario["erro"]))

    linhas.append("")
    linhas.append("## Inspecao dos arquivos de autenticacao")
    linhas.append("")
    resumo = auth["resumo"]
    linhas.append("- Rota login detectada: " + str(resumo["rota_login_detectada"]))
    linhas.append("- Usa campo password: " + str(resumo["usa_password"]))
    linhas.append("- Usa campo senha: " + str(resumo["usa_senha"]))
    linhas.append("- Usa bcrypt: " + str(resumo["usa_bcrypt"]))
    linhas.append("")
    for item in auth["arquivos"]:
        linhas.append("- " + item["arquivo"] + ": existe=" + str(item["existe"]))
        if item.get("campos_detectados"):
            linhas.append("  - campos detectados: " + ", ".join(item["campos_detectados"]))
        for achado in item.get("achados", [])[:10]:
            trecho = achado["trecho"].replace(chr(42), "[asterisco]")
            linhas.append("  - linha " + str(achado["linha"]) + ": " + trecho)

    linhas.append("")
    linhas.append("## Tentativas de login")
    linhas.append("")
    if not testes["executado"]:
        linhas.append("- Login nao executado: " + str(testes.get("motivo")))
    else:
        for item in testes["tentativas"]:
            linhas.append(
                "- "
                + item["nome"]
                + ": status="
                + str(item["status"])
                + ", tentativa_ok="
                + str(item["tentativa_ok"])
                + ", cookies="
                + str(item["cookies_total"])
                + ", erro="
                + str(item["erro"])
            )
            preview = (item.get("body_preview") or "").replace("\n", " ")[:240]
            if preview:
                linhas.append("  - preview: " + preview.replace(chr(42), "[asterisco]"))
            dash = item.get("dashboard_pos_login")
            if dash:
                linhas.append("  - dashboard status: " + str(dash.get("status")))
                linhas.append("  - dashboard redirect: " + str(dash.get("redirect_url")))

    linhas.append("")
    linhas.append("## Achados em logs")
    linhas.append("")
    if logs["achados"]:
        for item in logs["achados"]:
            trecho = item["trecho"].replace(chr(42), "[asterisco]")
            linhas.append(
                "- termo="
                + item["termo"]
                + " linha="
                + str(item["linha"])
                + " trecho="
                + trecho
            )
    else:
        linhas.append("- Nenhum padrao critico encontrado nos logs analisados.")

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhum hash completo foi impresso.")
    linhas.append("- Nenhuma alteracao foi aplicada ao banco.")
    linhas.append("- Nenhuma alteracao foi aplicada ao codigo.")
    linhas.append("- Cookies foram mantidos apenas em memoria durante os testes.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Se a senha testada nao autenticar, criar etapa controlada para reset de senha admin.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_12_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_12_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    docker = verificar_docker()
    usuario_banco = diagnosticar_usuario_banco()
    auth_inspecao = inspecionar_arquivos_auth()
    testes_login = testar_payloads_login()
    logs_resultados = coletar_logs_app()
    logs_analise = analisar_logs(logs_resultados)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "usuario_banco": usuario_banco,
        "auth_inspecao": auth_inspecao,
        "testes_login": testes_login,
        "logs_resultados": logs_resultados,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_12_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_12_1_diagnosticar_login_auth.json"
    md_path = REPORTS_DIR / "etapa_12_1_diagnosticar_login_auth.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 12.1 concluida.")
    print("Backup documental: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Docker OK: " + str(docker["docker_version"]["ok"]))
    print("Usuario encontrado: " + str(usuario_banco["usuario_encontrado"]))
    print("Rota login detectada: " + str(auth_inspecao["resumo"]["rota_login_detectada"]))
    print("Usa password: " + str(auth_inspecao["resumo"]["usa_password"]))
    print("Usa senha: " + str(auth_inspecao["resumo"]["usa_senha"]))
    print("Usa bcrypt: " + str(auth_inspecao["resumo"]["usa_bcrypt"]))
    print("Login testado: " + str(testes_login["executado"]))
    print("Login OK: " + str(testes_login["login_ok"]))
    print("Melhor tentativa: " + str(testes_login["melhor_tentativa"]))
    print("Achados em logs: " + str(len(logs_analise["achados"])))

    if not testes_login["login_ok"]:
        print("")
        print("Login ainda nao validado. Consulte o relatorio Markdown.")


if __name__ == "__main__":
    main()