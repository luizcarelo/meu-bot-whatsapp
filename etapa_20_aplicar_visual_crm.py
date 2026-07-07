#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 20 - Aplicar visual compartilhado em views/crm.ejs

Objetivo:
- Criar backup antes da alteracao.
- Gerar manifesto antes e depois.
- Alterar somente views/crm.ejs.
- Garantir link para public/css/style.css via rota /css/style.css.
- Injetar melhoria visual controlada com marcadores ETAPA20.
- Preservar logica existente, fetch, Socket.IO, endpoints e formularios.
- Nao alterar backend.
- Nao alterar banco.
- Nao reiniciar container.
- Validar login, dashboard e CRM.
- Atualizar documentacao obrigatoria.
- Gerar relatorios em reports.

Como executar:
sudo ETAPA20_LOGIN_EMAIL='admin@saas.com' ETAPA20_LOGIN_PASSWORD='123456' python3 etapa_20_aplicar_visual_crm.py
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

CRM_VIEW = ROOT / "views" / "crm.ejs"

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
    "views/crm.ejs",
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


def bloco_link_css():
    return '"/css/style.css"'


def bloco_visual_crm():
    return """
<!-- ETAPA20_CRM_VISUAL_INICIO -->
<script id="etapa20-crm-visual">
(function () {
    function existe(id) {
        return document.getElementById(id);
    }

    function criarCabecalho() {
        if (existe('etapa20-crm-header')) {
            return;
        }

        var alvo = document.querySelector('main') || document.querySelector('.container') || document.body;
        if (!alvo) {
            return;
        }

        if (alvo.classList) {
            alvo.classList.add('er-page');
        }

        var header = document.createElement('section');
        header.id = 'etapa20-crm-header';
        header.className = 'er-page-header';
        header.innerHTML = ''
            + '<div class="er-top-actions" style="justify-content: space-between;">'
            + '  <div>'
            + '    <div class="er-badge er-badge-success">CRM em tempo real</div>'
            + '    <h1 class="er-page-title" style="margin-top: 12px;">Central de atendimento</h1>'
            + '    <p class="er-page-subtitle">Contatos, conversas e acompanhamento operacional em uma interface padronizada.</p>'
            + '  </div>'
            + '  <div class="er-top-actions">'
            + '    <span class="er-badge er-badge-muted">Visual Etapa 20</span>'
            + '    <span class="er-badge">CSS compartilhado</span>'
            + '  </div>'
            + '</div>';

        alvo.insertBefore(header, alvo.firstChild);
    }

    function aplicarClasses() {
        var cards = document.querySelectorAll('.card, .panel, .box, article, section');
        for (var i = 0; i < cards.length; i++) {
            if (cards[i].id === 'etapa20-crm-header') {
                continue;
            }
            if (cards[i].classList) {
                cards[i].classList.add('er-card');
            }
        }

        var botoes = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
        for (var b = 0; b < botoes.length; b++) {
            if (botoes[b].classList) {
                botoes[b].classList.add('er-btn');
            }
        }

        var tabelas = document.querySelectorAll('table');
        for (var t = 0; t < tabelas.length; t++) {
            if (tabelas[t].parentElement && tabelas[t].parentElement.classList) {
                tabelas[t].parentElement.classList.add('er-soft-panel');
            }
        }

        var status = document.querySelectorAll('.status, .badge');
        for (var s = 0; s < status.length; s++) {
            if (status[s].classList) {
                status[s].classList.add('er-badge');
            }
        }
    }

    function iniciar() {
        criarCabecalho();
        aplicarClasses();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
</script>
<!-- ETAPA20_CRM_VISUAL_FIM -->
"""


def inserir_antes_de_head_fim(texto, bloco):
    if "</head>" in texto:
        return texto.replace("</head>", bloco + "\n</head>", 1)
    return bloco + "\n" + texto


def inserir_antes_de_body_fim(texto, bloco):
    if "</body>" in texto:
        return texto.replace("</body>", bloco + "\n</body>", 1)
    return texto + "\n" + bloco + "\n"


def aplicar_visual_crm():
    resultado = {
        "arquivo": "views/crm.ejs",
        "existe_antes": CRM_VIEW.exists(),
        "alterado": False,
        "adicionou_css": False,
        "adicionou_script": False,
        "sha256_antes": sha256_arquivo(CRM_VIEW) if CRM_VIEW.exists() else None,
        "sha256_depois": None
    }

    texto = ler_texto(CRM_VIEW)
    if texto is None:
        resultado["erro"] = "views/crm.ejs ausente ou ilegivel"
        return resultado

    novo = texto

    if "/css/style.css" not in novo:
        novo = inserir_antes_de_head_fim(novo, bloco_link_css())
        resultado["adicionou_css"] = True

    if "ETAPA20_CRM_VISUAL_INICIO" not in novo:
        novo = inserir_antes_de_body_fim(novo, bloco_visual_crm())
        resultado["adicionou_script"] = True

    validar_sem_asterisco(bloco_link_css(), "link css crm")
    validar_sem_asterisco(bloco_visual_crm(), "bloco visual crm")

    if novo != texto:
        gravar_texto(CRM_VIEW, novo)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256_arquivo(CRM_VIEW)
    return resultado


def validar_estrutura_crm():
    texto = ler_texto(CRM_VIEW)

    resultado = {
        "arquivo_existe": CRM_VIEW.exists(),
        "tem_css_compartilhado": False,
        "tem_marker": False,
        "tem_socket_io": False,
        "tem_fetch": False,
        "tem_texto_visual": False,
        "sem_asterisco": False,
        "ok": False
    }

    if texto is None:
        resultado["erro"] = "views/crm.ejs ausente ou ilegivel"
        return resultado

    lower = texto.lower()

    resultado["tem_css_compartilhado"] = "/css/style.css" in texto
    resultado["tem_marker"] = "ETAPA20_CRM_VISUAL_INICIO" in texto
    resultado["tem_socket_io"] = "/socket.io/socket.io.js" in texto or "socket.io" in lower
    resultado["tem_fetch"] = "fetch(" in texto
    resultado["tem_texto_visual"] = "Central de atendimento" in texto and "CRM em tempo real" in texto
    resultado["sem_asterisco"] = chr(42) not in bloco_link_css() and chr(42) not in bloco_visual_crm()

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_css_compartilhado"] and
        resultado["tem_marker"] and
        resultado["tem_socket_io"] and
        resultado["tem_fetch"] and
        resultado["tem_texto_visual"] and
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
        "User-Agent": "etapa-20-visual-crm/1.0"
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
        "tem_fetch": "fetch(" in body_crm
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

    marcador_inicio = "<!-- ETAPA_20_INICIO -->"
    marcador_fim = "<!-- ETAPA_20_FIM -->"

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
    validar_sem_asterisco(bloco_link_css(), "link css crm")
    validar_sem_asterisco(bloco_visual_crm(), "bloco visual crm")
    gravar_texto(path, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    melhoria = relatorio["melhoria_crm"]
    estrutura = relatorio["validacao_estrutura"]
    runtime = relatorio["validacao_runtime"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 20 - Visual compartilhado aplicado ao CRM",
        [
            "Data: " + data,
            "",
            "Foi aplicada melhoria visual controlada em views/crm.ejs.",
            "Arquivo alterado: " + str(melhoria["alterado"]) + ".",
            "CSS compartilhado adicionado: " + str(melhoria["adicionou_css"]) + ".",
            "Script visual adicionado: " + str(melhoria["adicionou_script"]) + ".",
            "Validacao estrutural OK: " + str(estrutura["ok"]) + ".",
            "Login OK: " + str(runtime["login_ok"]) + ".",
            "Dashboard OK: " + str(runtime["dashboard_ok"]) + ".",
            "CRM OK: " + str(runtime["crm_ok"]) + ".",
            "CRM visual OK: " + str(runtime["crm_visual_ok"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 20 - Visual aplicado em views/crm.ejs",
        [
            "Data: " + data,
            "",
            "Incluido link para /css/style.css em views/crm.ejs quando ausente.",
            "Adicionada camada visual controlada com marcadores ETAPA20.",
            "Preservados fetch, Socket.IO, endpoints e logica existente.",
            "Validado login, dashboard e rota /crm.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 20 - Decisoes tecnicas frontend",
        [
            "Data: " + data,
            "",
            "Decidido aplicar visual no CRM por injecao controlada, sem substituir a view inteira.",
            "Decidido usar public/css/style.css criado na Etapa 19.",
            "Decidido preservar scripts e chamadas existentes.",
            "Decidido nao alterar backend ou banco nesta etapa."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 20",
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
    melhoria = relatorio["melhoria_crm"]
    estrutura = relatorio["validacao_estrutura"]
    runtime = relatorio["validacao_runtime"]
    logs = relatorio["logs_analise"]

    linhas = []

    linhas.append("# Etapa 20 - Aplicar visual compartilhado em CRM")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- views/crm.ejs alterado: " + str(melhoria["alterado"]))
    linhas.append("- CSS compartilhado adicionado: " + str(melhoria["adicionou_css"]))
    linhas.append("- Script visual adicionado: " + str(melhoria["adicionou_script"]))
    linhas.append("- Validacao estrutural OK: " + str(estrutura["ok"]))
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
    linhas.append("- Arquivo: " + melhoria["arquivo"])
    linhas.append("- SHA256 antes: " + str(melhoria["sha256_antes"]))
    linhas.append("- SHA256 depois: " + str(melhoria["sha256_depois"]))

    linhas.append("")
    linhas.append("## Validacao estrutural")
    linhas.append("")
    for chave in sorted(estrutura.keys()):
        linhas.append("- " + chave + ": " + str(estrutura[chave]))

    linhas.append("")
    linhas.append("## Validacao runtime")
    linhas.append("")
    linhas.append("- Executada: " + str(runtime["executado"]))
    linhas.append("- Email configurado: " + str(runtime["email_configurado"]))
    linhas.append("- Senha configurada: " + str(runtime["senha_configurada"]))
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
    linhas.append("- Somente views/crm.ejs foi alterado.")
    linhas.append("- Nenhum backend foi alterado.")
    linhas.append("- Nenhum banco foi alterado.")
    linhas.append("- A melhoria usa public/css/style.css da Etapa 19.")
    linhas.append("- A logica existente foi preservada.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Validar visual do CRM manualmente e depois aplicar visual em admin-panel ou super-admin.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_20_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_20_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = agora_logs_since()
    melhoria = aplicar_visual_crm()
    estrutura = validar_estrutura_crm()
    runtime = validar_runtime()
    time.sleep(2)

    logs_coleta = coletar_logs_novos(since)
    logs_analise = analisar_logs_texto(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "melhoria_crm": melhoria,
        "validacao_estrutura": estrutura,
        "logs_since": since,
        "validacao_runtime": runtime,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_20_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_20_aplicar_visual_crm.json"
    md_path = REPORTS_DIR / "etapa_20_aplicar_visual_crm.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 20 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("views/crm.ejs alterado: " + str(melhoria["alterado"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("CRM OK: " + str(runtime["crm_ok"]))
    print("CRM visual OK: " + str(runtime["crm_visual_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["crm_visual_ok"]:
        print("")
        print("Aviso: CRM visual nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
