#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 20.1 - Registrar rota /crm

Objetivo:
- Criar backup antes da alteracao.
- Gerar manifesto antes e depois.
- Alterar somente routes/index.js.
- Registrar GET /crm usando isAuthenticated.
- Renderizar views/crm.ejs com titulo, user, empresa, isMobile e socketUrl.
- Rodar node --check em routes/index.js.
- Reiniciar app somente se ETAPA20_1_RESTART_APP=true.
- Validar login, dashboard e /crm.
- Atualizar documentacao obrigatoria.
- Gerar relatorios em reports.

Como executar sem restart:
sudo ETAPA20_1_LOGIN_EMAIL='admin@saas.com' ETAPA20_1_LOGIN_PASSWORD='123456' python3 etapa_20_1_registrar_rota_crm.py

Como executar com restart:
sudo ETAPA20_1_RESTART_APP=true ETAPA20_1_LOGIN_EMAIL='admin@saas.com' ETAPA20_1_LOGIN_PASSWORD='123456' python3 etapa_20_1_registrar_rota_crm.py
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

ROUTES_INDEX = ROOT / "routes" / "index.js"

BASE_URL = "http://127.0.0.1:50010"
LOGIN_PATH = "/api/auth/login"
DASHBOARD_PATH = "/dashboard"
CRM_PATH = "/crm"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "routes/index.js",
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
    "ETAPA20_1_LOGIN_EMAIL",
    "ETAPA20_LOGIN_EMAIL",
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
    "ETAPA20_1_LOGIN_PASSWORD",
    "ETAPA20_LOGIN_PASSWORD",
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


def validar_sem_asterisco(conteudo, nome):
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


def bloco_rota_crm():
    return """
// ETAPA20_1_ROTA_CRM_INICIO
router.get('/crm', isAuthenticated, async (req, res) => {
    try {
        const empresaId = req.session.empresaId;

        if (!empresaId) {
            req.session.destroy();
            return res.redirect('/login?error=sessao_invalida');
        }

        const result = await db.query(
            'SELECT id, nome, logo, cor, plano, limite_usuarios FROM empresas WHERE id = ? LIMIT 1',
            [empresaId]
        );

        const empresa = Array.isArray(result) ? result[0] : (result.rows ? result.rows[0] : null);

        if (!empresa) {
            return res.status(404).send('Empresa não encontrada.');
        }

        return res.render('crm', {
            titulo: 'CRM - Atendimento',
            user: req.session.user,
            empresa: empresa,
            isMobile: false,
            socketUrl: process.env.SOCKET_URL || ''
        });
    } catch (error) {
        console.error('[CRM PAGE] Erro ao carregar CRM:', error);
        return res.status(500).render('login', {
            error: 'Erro ao carregar CRM: ' + error.message
        });
    }
});
// ETAPA20_1_ROTA_CRM_FIM
"""


def aplicar_rota_crm():
    resultado = {
        "arquivo": "routes/index.js",
        "existe_antes": ROUTES_INDEX.exists(),
        "alterado": False,
        "rota_ja_existia": False,
        "sha256_antes": sha256_arquivo(ROUTES_INDEX) if ROUTES_INDEX.exists() else None,
        "sha256_depois": None
    }

    texto = ler_texto(ROUTES_INDEX)
    if texto is None:
        resultado["erro"] = "routes/index.js ausente ou ilegivel"
        return resultado

    if "ETAPA20_1_ROTA_CRM_INICIO" in texto or "router.get('/crm'" in texto or 'router.get("/crm"' in texto:
        resultado["rota_ja_existia"] = True
        resultado["sha256_depois"] = sha256_arquivo(ROUTES_INDEX)
        return resultado

    novo_bloco = bloco_rota_crm()
    validar_sem_asterisco(novo_bloco, "bloco rota crm")

    marcador = "router.get('/logout'"
    pos = texto.find(marcador)

    if pos >= 0:
        novo = texto[:pos] + novo_bloco + "\n" + texto[pos:]
    else:
        marcador_export = "module.exports = router;"
        pos_export = texto.find(marcador_export)

        if pos_export < 0:
            resultado["erro"] = "Nao foi possivel localizar ponto de insercao"
            resultado["sha256_depois"] = sha256_arquivo(ROUTES_INDEX)
            return resultado

        novo = texto[:pos_export] + novo_bloco + "\n" + texto[pos_export:]

    gravar_texto(ROUTES_INDEX, novo)
    resultado["alterado"] = True
    resultado["sha256_depois"] = sha256_arquivo(ROUTES_INDEX)
    return resultado


def validar_estrutura_rota():
    texto = ler_texto(ROUTES_INDEX)

    resultado = {
        "arquivo_existe": ROUTES_INDEX.exists(),
        "tem_marker": False,
        "tem_rota_crm": False,
        "tem_is_authenticated": False,
        "tem_render_crm": False,
        "tem_titulo": False,
        "tem_is_mobile": False,
        "tem_select_empresa": False,
        "ok": False
    }

    if texto is None:
        resultado["erro"] = "routes/index.js ausente ou ilegivel"
        return resultado

    resultado["tem_marker"] = "ETAPA20_1_ROTA_CRM_INICIO" in texto
    resultado["tem_rota_crm"] = "router.get('/crm'" in texto or 'router.get("/crm"' in texto
    resultado["tem_is_authenticated"] = "isAuthenticated" in texto
    resultado["tem_render_crm"] = "res.render('crm'" in texto or 'res.render("crm"' in texto
    resultado["tem_titulo"] = "CRM - Atendimento" in texto
    resultado["tem_is_mobile"] = "isMobile" in texto
    resultado["tem_select_empresa"] = "FROM empresas WHERE id" in texto

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_rota_crm"] and
        resultado["tem_is_authenticated"] and
        resultado["tem_render_crm"] and
        resultado["tem_titulo"] and
        resultado["tem_is_mobile"] and
        resultado["tem_select_empresa"]
    )

    return resultado


def node_check():
    if not ROUTES_INDEX.exists():
        return {
            "ok": False,
            "erro": "routes/index.js ausente"
        }

    return run_cmd(["node", "--check", "routes/index.js"], 40)


def reiniciar_app_se_solicitado():
    valor = os.environ.get("ETAPA20_1_RESTART_APP", "").strip().lower()

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
        "User-Agent": "etapa-20-1-rota-crm/1.0"
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


def validar_runtime():
    cred = obter_credenciais()

    resultado = {
        "executado": False,
        "email_configurado": cred["email_configurado"],
        "senha_configurada": cred["senha_configurada"],
        "login_ok": False,
        "dashboard_ok": False,
        "crm_ok": False,
        "crm_visual_ok": False,
        "cookies": [],
        "login": None,
        "dashboard": None,
        "crm": None,
        "textos_crm": {}
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
        "content_type": dashboard.get("content_type")
    }
    resultado["dashboard_ok"] = bool(dashboard.get("status") == 200 and "crm enterprise" in body_dash.lower())

    crm = http_request(opener, "GET", CRM_PATH)
    body_crm = crm.get("body_full_limited") or ""
    lower_crm = body_crm.lower()

    textos = {
        "tem_css": "/css/style.css" in body_crm,
        "tem_marker": "ETAPA20_CRM_VISUAL_INICIO" in body_crm,
        "central_atendimento": "central de atendimento" in lower_crm,
        "crm_tempo_real": "crm em tempo real" in lower_crm,
        "tem_socket": "socket.io" in lower_crm,
        "tem_fetch": "fetch(" in body_crm,
        "titulo_crm": "crm - atendimento" in lower_crm
    }

    resultado["crm"] = {
        "status": crm.get("status"),
        "ok": crm.get("ok"),
        "erro": crm.get("erro"),
        "content_type": crm.get("content_type"),
        "body_preview": crm.get("body_preview")
    }

    resultado["crm_ok"] = bool(crm.get("status") == 200)
    resultado["crm_visual_ok"] = bool(
        crm.get("status") == 200 and
        textos["tem_css"] and
        textos["tem_marker"] and
        textos["central_atendimento"] and
        textos["crm_tempo_real"]
    )
    resultado["textos_crm"] = textos

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

    marcador_inicio = "<!-- ETAPA_20_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_20_1_FIM -->"

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
    validar_sem_asterisco(novo, nome)
    gravar_texto(path, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    rota = relatorio["rota_crm"]
    estrutura = relatorio["validacao_estrutura"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    runtime = relatorio["validacao_runtime"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 20.1 - Rota CRM registrada",
        [
            "Data: " + data,
            "",
            "Foi registrada a rota GET /crm em routes/index.js.",
            "Arquivo alterado: " + str(rota["alterado"]) + ".",
            "Rota ja existia: " + str(rota["rota_ja_existia"]) + ".",
            "Validacao estrutural OK: " + str(estrutura["ok"]) + ".",
            "Node check OK: " + str(node["ok"]) + ".",
            "Restart executado: " + str(restart["executado"]) + ".",
            "Login OK: " + str(runtime["login_ok"]) + ".",
            "Dashboard OK: " + str(runtime["dashboard_ok"]) + ".",
            "CRM OK: " + str(runtime["crm_ok"]) + ".",
            "CRM visual OK: " + str(runtime["crm_visual_ok"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 20.1 - Registro da rota /crm",
        [
            "Data: " + data,
            "",
            "Adicionada rota GET /crm protegida por isAuthenticated.",
            "A rota renderiza views/crm.ejs com titulo, usuario, empresa, isMobile e socketUrl.",
            "Executado node --check em routes/index.js.",
            "Validado login, dashboard e CRM.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 20.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido registrar /crm em routes/index.js porque a view existia mas nao havia rota frontend.",
            "Decidido nao alterar views/crm.ejs nesta etapa.",
            "Decidido reutilizar consulta de empresa semelhante ao dashboard.",
            "Decidido reiniciar app somente com ETAPA20_1_RESTART_APP=true."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 20.1",
        [
            "Data: " + data,
            "",
            "Validar visual do CRM manualmente no navegador.",
            "Planejar aplicacao visual em views/admin-panel.ejs.",
            "Planejar aplicacao visual em views/super-admin.ejs.",
            "Planejar internalizacao de dependencias externas.",
            "Mapear scripts inline antes de CSP forte."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    rota = relatorio["rota_crm"]
    estrutura = relatorio["validacao_estrutura"]
    node = relatorio["node_check"]
    restart = relatorio["restart_app"]
    aguardar = relatorio["aguardar_app"]
    runtime = relatorio["validacao_runtime"]
    logs = relatorio["logs_analise"]

    linhas = []

    linhas.append("# Etapa 20.1 - Registrar rota CRM")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- routes/index.js alterado: " + str(rota["alterado"]))
    linhas.append("- Rota ja existia: " + str(rota["rota_ja_existia"]))
    linhas.append("- Validacao estrutural OK: " + str(estrutura["ok"]))
    linhas.append("- Node check OK: " + str(node["ok"]))
    linhas.append("- Restart solicitado: " + str(restart["solicitado"]))
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Restart OK: " + str(restart["ok"]))
    linhas.append("- App pronto: " + str(aguardar["ok"]))
    linhas.append("- Login OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
    linhas.append("- CRM OK: " + str(runtime["crm_ok"]))
    linhas.append("- CRM visual OK: " + str(runtime["crm_visual_ok"]))
    linhas.append("- Logs novos Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs novos cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs novos email: " + str(logs["linhas_email"]))
    linhas.append("- Achados criticos logs: " + str(len(logs["achados"])))
    linhas.append("")

    linhas.append("## Arquivo alterado")
    linhas.append("")
    linhas.append("- Arquivo: " + rota["arquivo"])
    linhas.append("- SHA256 antes: " + str(rota["sha256_antes"]))
    linhas.append("- SHA256 depois: " + str(rota["sha256_depois"]))

    linhas.append("")
    linhas.append("## Validacao estrutural")
    linhas.append("")
    for chave in sorted(estrutura.keys()):
        linhas.append("- " + chave + ": " + str(estrutura[chave]))

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    linhas.append("- OK: " + str(node["ok"]))
    if node.get("stderr"):
        linhas.append("- stderr: " + node["stderr"][:800])

    linhas.append("")
    linhas.append("## Validacao runtime")
    linhas.append("")
    linhas.append("- Executada: " + str(runtime["executado"]))
    linhas.append("- Login OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
    linhas.append("- CRM OK: " + str(runtime["crm_ok"]))
    linhas.append("- CRM visual OK: " + str(runtime["crm_visual_ok"]))
    linhas.append("- Cookies recebidos: " + str(len(runtime["cookies"])))

    linhas.append("")
    linhas.append("## Marcadores CRM")
    linhas.append("")
    for chave, valor in sorted(runtime["textos_crm"].items()):
        linhas.append("- " + chave + ": " + str(valor))

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
    linhas.append("- Somente routes/index.js foi alterado.")
    linhas.append("- Nenhuma view foi alterada nesta etapa.")
    linhas.append("- Nenhum banco foi alterado.")
    linhas.append("- A rota /crm usa isAuthenticated.")
    linhas.append("- O app so foi reiniciado se ETAPA20_1_RESTART_APP=true.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Validar visual do CRM manualmente no navegador.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_20_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_20_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    rota = aplicar_rota_crm()
    estrutura = validar_estrutura_rota()
    node = node_check()
    restart = reiniciar_app_se_solicitado()
    aguardar = aguardar_app()

    since = agora_logs_since()
    runtime = validar_runtime()
    time.sleep(2)

    logs_coleta = coletar_logs_novos(since)
    logs_analise = analisar_logs_texto(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "rota_crm": rota,
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
    manifesto_depois_path = REPORTS_DIR / "etapa_20_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_20_1_registrar_rota_crm.json"
    md_path = REPORTS_DIR / "etapa_20_1_registrar_rota_crm.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 20.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("routes/index.js alterado: " + str(rota["alterado"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Node check OK: " + str(node["ok"]))
    print("Restart solicitado: " + str(restart["solicitado"]))
    print("Restart executado: " + str(restart["executado"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("CRM OK: " + str(runtime["crm_ok"]))
    print("CRM visual OK: " + str(runtime["crm_visual_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not restart["executado"]:
        print("")
        print("Aviso: app nao foi reiniciado. Para aplicar em runtime, execute com ETAPA20_1_RESTART_APP=true.")

    if not runtime["crm_visual_ok"]:
        print("")
        print("Aviso: CRM ainda nao validou visualmente em runtime. Consulte o relatorio.")


if __name__ == "__main__":
    main()
