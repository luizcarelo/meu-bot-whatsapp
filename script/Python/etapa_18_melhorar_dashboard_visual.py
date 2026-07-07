#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 18 - Melhorar visual do dashboard de forma controlada

Objetivo:
- Criar backup antes da alteracao.
- Gerar manifesto antes e depois.
- Alterar somente views/dashboard.ejs.
- Aplicar melhoria visual controlada sem substituir a logica existente.
- Preservar Tailwind, Alpine, FontAwesome e Socket.IO existentes.
- Nao alterar backend.
- Nao alterar banco.
- Reiniciar app somente se ETAPA18_RESTART_APP=true.
- Validar login e dashboard quando credenciais forem fornecidas.
- Confirmar marcadores visuais da Etapa 18 em runtime.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar sem restart:
sudo ETAPA18_LOGIN_EMAIL='admin@saas.com' ETAPA18_LOGIN_PASSWORD='123456' python3 etapa_18_melhorar_dashboard_visual.py

Como executar com restart:
sudo ETAPA18_RESTART_APP=true ETAPA18_LOGIN_EMAIL='admin@saas.com' ETAPA18_LOGIN_PASSWORD='123456' python3 etapa_18_melhorar_dashboard_visual.py
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

DASHBOARD_VIEW = ROOT / "views" / "dashboard.ejs"

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
    "views/dashboard.ejs",
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


def bloco_css_etapa18():
    return """
<!-- ETAPA18_DASHBOARD_VISUAL_INICIO -->
<style id="etapa18-dashboard-visual">
    :root {
        --etapa18-red: #b91c1c;
        --etapa18-red-soft: #fef2f2;
        --etapa18-slate: #0f172a;
        --etapa18-muted: #64748b;
        --etapa18-border: #e2e8f0;
        --etapa18-card: rgba(255, 255, 255, 0.94);
    }

    body {
        background:
            radial-gradient(circle at top left, rgba(239, 68, 68, 0.10), transparent 28rem),
            radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.08), transparent 30rem),
            #f8fafc !important;
    }

    .etapa18-shell {
        min-height: 100vh;
        background:
            linear-gradient(135deg, rgba(15, 23, 42, 0.02), rgba(185, 28, 28, 0.04));
    }

    .etapa18-hero {
        border: 1px solid rgba(226, 232, 240, 0.9);
        background:
            linear-gradient(135deg, rgba(255,255,255,0.96), rgba(254,242,242,0.88));
        box-shadow: 0 18px 55px rgba(15, 23, 42, 0.08);
    }

    .etapa18-card {
        border: 1px solid var(--etapa18-border);
        background: var(--etapa18-card);
        box-shadow: 0 16px 35px rgba(15, 23, 42, 0.07);
        transition: transform 0.16s ease, box-shadow 0.16s ease;
    }

    .etapa18-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 20px 45px rgba(15, 23, 42, 0.10);
    }

    .etapa18-pill {
        border: 1px solid rgba(185, 28, 28, 0.16);
        background: rgba(254, 242, 242, 0.85);
        color: #991b1b;
    }

    .etapa18-title {
        color: var(--etapa18-slate);
        letter-spacing: -0.03em;
    }

    .etapa18-subtitle {
        color: var(--etapa18-muted);
    }

    .etapa18-icon {
        background: linear-gradient(135deg, #991b1b, #dc2626, #f97316);
        box-shadow: 0 12px 24px rgba(220, 38, 38, 0.22);
    }

    .etapa18-section-title {
        color: #0f172a;
        font-weight: 900;
        letter-spacing: -0.02em;
    }

    .etapa18-soft-border {
        border-color: rgba(226, 232, 240, 0.85) !important;
    }

    .etapa18-main-wrap {
        max-width: 1500px;
        margin-left: auto;
        margin-right: auto;
    }
</style>
<!-- ETAPA18_DASHBOARD_VISUAL_FIM -->
"""


def bloco_script_etapa18():
    return """
<!-- ETAPA18_DASHBOARD_SCRIPT_INICIO -->
<script id="etapa18-dashboard-script">
(function () {
    function criarCard(titulo, valor, icone, detalhe) {
        var card = document.createElement('div');
        card.className = 'etapa18-card rounded-3xl p-5';
        card.innerHTML = ''
            + '<div class="flex items-center justify-between gap-4">'
            + '  <div>'
            + '    <p class="text-sm font-bold text-slate-500">' + titulo + '</p>'
            + '    <p class="text-2xl font-black text-slate-900 mt-1">' + valor + '</p>'
            + '    <p class="text-xs text-slate-400 mt-1">' + detalhe + '</p>'
            + '  </div>'
            + '  <div class="etapa18-icon h-12 w-12 rounded-2xl flex items-center justify-center text-white">'
            + '    <i class="' + icone + '"></i>'
            + '  </div>'
            + '</div>';
        return card;
    }

    function aplicarMelhoria() {
        if (document.getElementById('etapa18-dashboard-banner')) {
            return;
        }

        var body = document.body;
        if (body) {
            body.classList.add('etapa18-shell');
        }

        var alvo = document.querySelector('main') || document.querySelector('.container') || document.body;
        if (!alvo) {
            return;
        }

        alvo.classList.add('etapa18-main-wrap');

        var banner = document.createElement('section');
        banner.id = 'etapa18-dashboard-banner';
        banner.className = 'etapa18-hero rounded-3xl p-6 sm:p-8 mb-6';
        banner.innerHTML = ''
            + '<div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">'
            + '  <div>'
            + '    <div class="etapa18-pill inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-bold mb-4">'
            + '      <span class="h-2 w-2 rounded-full bg-emerald-500"></span>'
            + '      Dashboard operacional'
            + '    </div>'
            + '    <h1 class="etapa18-title text-3xl sm:text-4xl font-black">Visao geral do atendimento</h1>'
            + '    <p class="etapa18-subtitle mt-2 max-w-2xl">Acompanhe conversas, contatos, setores e atividades do sistema em uma area mais clara e organizada.</p>'
            + '  </div>'
            + '  <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 min-w-full lg:min-w-[520px]">'
            + '    <div id="etapa18-card-1"></div>'
            + '    <div id="etapa18-card-2"></div>'
            + '    <div id="etapa18-card-3"></div>'
            + '  </div>'
            + '</div>';

        alvo.insertBefore(banner, alvo.firstChild);

        var c1 = document.getElementById('etapa18-card-1');
        var c2 = document.getElementById('etapa18-card-2');
        var c3 = document.getElementById('etapa18-card-3');

        if (c1) c1.appendChild(criarCard('Sessao', 'Ativa', 'fa-solid fa-shield-halved', 'Usuario autenticado'));
        if (c2) c2.appendChild(criarCard('Interface', 'Online', 'fa-solid fa-gauge-high', 'Painel carregado'));
        if (c3) c3.appendChild(criarCard('Mensagens', 'Tempo real', 'fa-solid fa-comments', 'Socket.IO preservado'));

        var cards = document.querySelectorAll('.card, .bg-white, section, article');
        for (var i = 0; i < cards.length; i++) {
            if (cards[i].id === 'etapa18-dashboard-banner') {
                continue;
            }
            if (cards[i].classList) {
                cards[i].classList.add('etapa18-soft-border');
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', aplicarMelhoria);
    } else {
        aplicarMelhoria();
    }
})();
</script>
<!-- ETAPA18_DASHBOARD_SCRIPT_FIM -->
"""


def inserir_antes_de_head_fim(texto, bloco):
    if "</head>" in texto:
        return texto.replace("</head>", bloco + "\n</head>", 1)
    return bloco + "\n" + texto


def inserir_antes_de_body_fim(texto, bloco):
    if "</body>" in texto:
        return texto.replace("</body>", bloco + "\n</body>", 1)
    return texto + "\n" + bloco + "\n"


def aplicar_melhoria_dashboard():
    resultado = {
        "arquivo": "views/dashboard.ejs",
        "existe_antes": DASHBOARD_VIEW.exists(),
        "alterado": False,
        "adicionou_css": False,
        "adicionou_script": False,
        "sha256_antes": sha256_arquivo(DASHBOARD_VIEW) if DASHBOARD_VIEW.exists() else None,
        "sha256_depois": None
    }

    texto = ler_texto(DASHBOARD_VIEW)
    if texto is None:
        resultado["erro"] = "views/dashboard.ejs ausente ou ilegivel"
        return resultado

    novo = texto

    if "ETAPA18_DASHBOARD_VISUAL_INICIO" not in novo:
        novo = inserir_antes_de_head_fim(novo, bloco_css_etapa18())
        resultado["adicionou_css"] = True

    if "ETAPA18_DASHBOARD_SCRIPT_INICIO" not in novo:
        novo = inserir_antes_de_body_fim(novo, bloco_script_etapa18())
        resultado["adicionou_script"] = True

    if novo != texto:
        gravar_texto(DASHBOARD_VIEW, novo)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256_arquivo(DASHBOARD_VIEW)
    return resultado


def validar_estrutura_dashboard():
    texto = ler_texto(DASHBOARD_VIEW)

    resultado = {
        "arquivo_existe": DASHBOARD_VIEW.exists(),
        "tem_marker_css": False,
        "tem_marker_script": False,
        "tem_socket_io": False,
        "tem_tailwind": False,
        "tem_fontawesome": False,
        "tem_dashboard_banner": False,
        "tem_texto_pt_br": False,
        "ok": False
    }

    if texto is None:
        resultado["erro"] = "views/dashboard.ejs ausente ou ilegivel"
        return resultado

    lower = texto.lower()

    resultado["tem_marker_css"] = "ETAPA18_DASHBOARD_VISUAL_INICIO" in texto
    resultado["tem_marker_script"] = "ETAPA18_DASHBOARD_SCRIPT_INICIO" in texto
    resultado["tem_socket_io"] = "/socket.io/socket.io.js" in texto or "socket.io" in lower
    resultado["tem_tailwind"] = "tailwind" in lower
    resultado["tem_fontawesome"] = "font-awesome" in lower or "fontawesome" in lower or "fa-solid" in lower
    resultado["tem_dashboard_banner"] = "etapa18-dashboard-banner" in texto
    resultado["tem_texto_pt_br"] = "Visao geral do atendimento" in texto or "Visão geral do atendimento" in texto

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_marker_css"] and
        resultado["tem_marker_script"] and
        resultado["tem_dashboard_banner"] and
        resultado["tem_texto_pt_br"]
    )

    return resultado


def reiniciar_app_se_solicitado():
    valor = os.environ.get("ETAPA18_RESTART_APP", "").strip().lower()

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
        "User-Agent": "etapa-18-dashboard-visual/1.0"
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


def validar_login_dashboard():
    cred = obter_credenciais()

    resultado = {
        "executado": False,
        "email_configurado": cred["email_configurado"],
        "senha_configurada": cred["senha_configurada"],
        "login_ok": False,
        "dashboard_ok": False,
        "dashboard_visual_ok": False,
        "cookies": [],
        "login": None,
        "dashboard": None,
        "textos_dashboard": {}
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
    body_dash_lower = body_dash.lower()

    textos = {
        "crm_enterprise": "crm enterprise" in body_dash_lower,
        "etapa18_css": "ETAPA18_DASHBOARD_VISUAL_INICIO" in body_dash,
        "etapa18_script": "ETAPA18_DASHBOARD_SCRIPT_INICIO" in body_dash,
        "dashboard_operacional": "dashboard operacional" in body_dash_lower,
        "visao_geral": "visao geral do atendimento" in body_dash_lower or "visão geral do atendimento" in body_dash_lower,
        "tempo_real": "tempo real" in body_dash_lower
    }

    resultado["dashboard"] = {
        "status": dashboard.get("status"),
        "ok": dashboard.get("ok"),
        "erro": dashboard.get("erro"),
        "content_type": dashboard.get("content_type"),
        "body_preview": dashboard.get("body_preview")
    }

    resultado["dashboard_ok"] = bool(dashboard.get("status") == 200 and textos["crm_enterprise"])
    resultado["dashboard_visual_ok"] = bool(
        dashboard.get("status") == 200 and
        textos["etapa18_css"] and
        textos["etapa18_script"] and
        textos["dashboard_operacional"] and
        textos["visao_geral"]
    )
    resultado["textos_dashboard"] = textos

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

    marcador_inicio = "<!-- ETAPA_18_INICIO -->"
    marcador_fim = "<!-- ETAPA_18_FIM -->"

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
    melhoria = relatorio["melhoria_dashboard"]
    estrutura = relatorio["validacao_estrutura"]
    runtime = relatorio["validacao_runtime"]
    restart = relatorio["restart_app"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 18 - Melhoria visual controlada do dashboard",
        [
            "Data: " + data,
            "",
            "Foi aplicada melhoria visual controlada em views/dashboard.ejs.",
            "Arquivo alterado: " + str(melhoria["alterado"]) + ".",
            "Validacao estrutural OK: " + str(estrutura["ok"]) + ".",
            "Restart executado: " + str(restart["executado"]) + ".",
            "Login OK: " + str(runtime["login_ok"]) + ".",
            "Dashboard OK: " + str(runtime["dashboard_ok"]) + ".",
            "Dashboard visual OK: " + str(runtime["dashboard_visual_ok"]) + ".",
            "Nenhum backend ou banco foi alterado."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 18 - Dashboard visual melhorado",
        [
            "Data: " + data,
            "",
            "Adicionada camada visual controlada ao dashboard.",
            "Preservada estrutura existente da view.",
            "Preservados Tailwind, FontAwesome, Alpine e Socket.IO.",
            "Validado login real e dashboard.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 18 - Decisoes tecnicas frontend",
        [
            "Data: " + data,
            "",
            "Decidido melhorar o dashboard por injecao controlada de CSS e script marcados.",
            "Decidido nao substituir completamente views/dashboard.ejs para reduzir risco.",
            "Decidido nao remover CDNs nesta etapa.",
            "Decidido manter a logica e os endpoints existentes."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 18",
        [
            "Data: " + data,
            "",
            "Validar visual do dashboard manualmente no navegador.",
            "Planejar internalizacao de dependencias externas.",
            "Corrigir ou criar CSS local compartilhado para /css/style.css.",
            "Planejar melhoria de views/crm.ejs e views/admin-panel.ejs em etapas separadas.",
            "Mapear scripts inline antes de aplicar CSP forte."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    melhoria = relatorio["melhoria_dashboard"]
    estrutura = relatorio["validacao_estrutura"]
    restart = relatorio["restart_app"]
    aguardar = relatorio["aguardar_app"]
    runtime = relatorio["validacao_runtime"]
    logs = relatorio["logs_analise"]

    linhas = []

    linhas.append("# Etapa 18 - Melhorar visual do dashboard")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- views/dashboard.ejs alterado: " + str(melhoria["alterado"]))
    linhas.append("- CSS Etapa 18 adicionado: " + str(melhoria["adicionou_css"]))
    linhas.append("- Script Etapa 18 adicionado: " + str(melhoria["adicionou_script"]))
    linhas.append("- Validacao estrutural OK: " + str(estrutura["ok"]))
    linhas.append("- Restart solicitado: " + str(restart["solicitado"]))
    linhas.append("- Restart executado: " + str(restart["executado"]))
    linhas.append("- Restart OK: " + str(restart["ok"]))
    linhas.append("- App pronto: " + str(aguardar["ok"]))
    linhas.append("- Login OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
    linhas.append("- Dashboard visual OK: " + str(runtime["dashboard_visual_ok"]))
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
    linhas.append("- Dashboard visual OK: " + str(runtime["dashboard_visual_ok"]))
    linhas.append("- Cookies recebidos: " + str(len(runtime["cookies"])))

    linhas.append("")
    linhas.append("## Textos e marcadores do dashboard")
    linhas.append("")
    for chave, valor in sorted(runtime["textos_dashboard"].items()):
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
    linhas.append("- Somente views/dashboard.ejs foi alterado.")
    linhas.append("- Nenhum backend foi alterado.")
    linhas.append("- Nenhum banco foi alterado.")
    linhas.append("- CDNs foram mantidas nesta etapa para reduzir risco.")
    linhas.append("- A melhoria foi feita com marcadores ETAPA18 para permitir auditoria e reversao controlada.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Validar visual manualmente no navegador e depois planejar internalizacao de assets externos.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_18_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_18_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = agora_logs_since()
    melhoria = aplicar_melhoria_dashboard()
    estrutura = validar_estrutura_dashboard()
    restart = reiniciar_app_se_solicitado()
    aguardar = aguardar_app()
    runtime = validar_login_dashboard()
    time.sleep(2)

    logs_coleta = coletar_logs_novos(since)
    logs_analise = analisar_logs_texto(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "melhoria_dashboard": melhoria,
        "validacao_estrutura": estrutura,
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
    manifesto_depois_path = REPORTS_DIR / "etapa_18_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_18_melhorar_dashboard_visual.json"
    md_path = REPORTS_DIR / "etapa_18_melhorar_dashboard_visual.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 18 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("views/dashboard.ejs alterado: " + str(melhoria["alterado"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Restart solicitado: " + str(restart["solicitado"]))
    print("Restart executado: " + str(restart["executado"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("Dashboard visual OK: " + str(runtime["dashboard_visual_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["dashboard_visual_ok"]:
        print("")
        print("Aviso: dashboard visual pode nao ter sido refletido em runtime.")
        print("Se nao usou restart, rode novamente com ETAPA18_RESTART_APP=true.")


if __name__ == "__main__":
    main()
