#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 25.1 - Corrigir frontend com shell seguro

Objetivo:
- Remover o shell invasivo da Etapa 25 das views.
- Aplicar menu lateral e tema claro/escuro sem reconstruir o body.
- Nao mover scripts existentes.
- Nao usar document.body.innerHTML = ''.
- Preservar funcoes originais das paginas.
- Validar dashboard, crm, admin panel e super admin.
- Atualizar documentacao obrigatoria.

Como executar:
sudo ETAPA25_1_LOGIN_EMAIL='superadmin.teste@saas.local' ETAPA25_1_LOGIN_PASSWORD='123456' python3 etapa_25_1_corrigir_frontend_shell_seguro.py
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

CSS_FILE = ROOT / "public" / "css" / "style.css"

VIEW_FILES = [
    ROOT / "views" / "dashboard.ejs",
    ROOT / "views" / "crm.ejs",
    ROOT / "views" / "admin-panel.ejs",
    ROOT / "views" / "super-admin.ejs"
]

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "public/css/style.css",
    "views/dashboard.ejs",
    "views/crm.ejs",
    "views/admin-panel.ejs",
    "views/super-admin.ejs",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BASE_URL = "http://127.0.0.1:50010"
LOGIN_API = "/api/auth/login"

PAGES = [
    "/dashboard",
    "/crm",
    "/admin/painel",
    "/super-admin"
]

EMAIL_KEYS = [
    "ETAPA25_1_LOGIN_EMAIL",
    "ETAPA25_LOGIN_EMAIL",
    "ETAPA24_SUPER_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA25_1_LOGIN_PASSWORD",
    "ETAPA25_LOGIN_PASSWORD",
    "ETAPA24_SUPER_PASSWORD",
    "LOGIN_PASSWORD",
    "ADMIN_PASSWORD",
    "SUPER_ADMIN_PASSWORD",
    "DEFAULT_ADMIN_PASSWORD"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def logs_since():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


def rel(path):
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def ler(path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def gravar(path, texto):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def sha256(path):
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


def salvar_json(path, dados):
    gravar(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def deve_ignorar_manifesto(path):
    partes = set(path.parts)
    rel_path = rel(path)

    ignorar = [
        "node_modules",
        ".git",
        "backups",
        "auth_sessions",
        "reports",
        "__pycache__",
        "tmp_etapa_24"
    ]

    for nome in ignorar:
        if nome in partes:
            return True
        if rel_path == nome or rel_path.startswith(nome + "/"):
            return True

    return False


def gerar_manifesto():
    itens = []

    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)
        dirs[:] = [d for d in dirs if not deve_ignorar_manifesto(base_path / d)]

        for nome in files:
            p = base_path / nome

            if deve_ignorar_manifesto(p):
                continue

            try:
                st = p.stat()
                itens.append({
                    "arquivo": rel(p),
                    "tamanho_bytes": st.st_size,
                    "sha256": sha256(p)
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
        "arquivos": sorted(itens, key=lambda x: x.get("arquivo", ""))
    }



def criar_backup(destino):
    destino.mkdir(parents=True, exist_ok=True)

    copiados = []
    ausentes = []
    erros = []

    for nome in BACKUP_FILES:
        origem = ROOT / nome
        destino_item = destino / nome

        if not origem.exists():
            ausentes.append(nome)
            continue

        try:
            destino_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino_item)
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
    texto = ler(env_path)

    if texto:
        for linha in texto.splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
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


def primeiro(dados, chaves):
    for chave in chaves:
        valor = dados.get(chave)
        if valor:
            return valor
    return ""


def credenciais():
    dados = parse_env()
    email = primeiro(dados, EMAIL_KEYS)
    senha = primeiro(dados, PASSWORD_KEYS)

    if not email:
        email = "superadmin.teste@saas.local"

    if not senha:
        senha = "123456"

    return {
        "email": email,
        "senha": senha,
        "email_configurado": bool(email),
        "senha_configurada": bool(senha)
    }


def valores_sensiveis():
    dados = parse_env()
    valores = []

    for chave, valor in dados.items():
        upper = chave.upper()
        if any(t in upper for t in ["PASS", "PASSWORD", "SECRET", "TOKEN", "KEY", "SENHA"]):
            if valor:
                valores.append(valor)

    c = credenciais()
    if c["senha"]:
        valores.append(c["senha"])

    return valores


def redigir(texto):
    if texto is None:
        return texto

    out = str(texto)

    for valor in valores_sensiveis():
        if valor:
            out = out.replace(valor, "<REDIGIDO>")

    c = credenciais()
    out = out.replace(c["email"], "<EMAIL_LOGIN>")

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
            "stdout": redigir(proc.stdout.strip())[:40000],
            "stderr": redigir(proc.stderr.strip())[:40000],
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


def bloco_css_25_1():
    return r'''
/* ETAPA25_1_SHELL_SEGURO_INICIO */
:root {
    --er25safe-sidebar-w: 280px;
    --er25safe-topbar-h: 64px;
    --er25safe-bg: #f6f7fb;
    --er25safe-card: #ffffff;
    --er25safe-border: #e5e7eb;
    --er25safe-text: #0f172a;
    --er25safe-muted: #64748b;
    --er25safe-red: #b91c1c;
    --er25safe-red-2: #ef4444;
    --er25safe-shadow: 0 18px 45px rgba(15, 23, 42, 0.10);
}

html.er25safe-dark,
body.er25safe-dark {
    --er25safe-bg: #0b1120;
    --er25safe-card: #111827;
    --er25safe-border: #243044;
    --er25safe-text: #f8fafc;
    --er25safe-muted: #94a3b8;
    --er25safe-shadow: 0 24px 60px rgba(0, 0, 0, 0.40);
}

body.er25safe-ready {
    background:
        radial-gradient(circle at top left, rgba(185, 28, 28, 0.08), transparent 28rem),
        radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.08), transparent 28rem),
        var(--er25safe-bg) !important;
    color: var(--er25safe-text) !important;
}

@media (min-width: 1025px) {
    body.er25safe-ready {
        padding-left: var(--er25safe-sidebar-w);
        padding-top: var(--er25safe-topbar-h);
    }

    body.er25safe-ready.er25safe-collapsed {
        padding-left: 0;
    }
}

.er25safe-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: var(--er25safe-sidebar-w);
    background:
        linear-gradient(180deg, rgba(185, 28, 28, 0.14), transparent 28%),
        var(--er25safe-card);
    border-right: 1px solid var(--er25safe-border);
    box-shadow: var(--er25safe-shadow);
    z-index: 2147483000;
    display: flex;
    flex-direction: column;
    transition: transform 0.22s ease;
}

.er25safe-brand {
    min-height: var(--er25safe-topbar-h);
    padding: 13px 16px;
    border-bottom: 1px solid var(--er25safe-border);
    display: flex;
    align-items: center;
    gap: 12px;
}

.er25safe-brand-mark {
    width: 40px;
    height: 40px;
    border-radius: 14px;
    background: linear-gradient(135deg, var(--er25safe-red), var(--er25safe-red-2));
    color: #fff;
    display: grid;
    place-items: center;
    font-weight: 900;
}

.er25safe-brand-title {
    margin: 0;
    color: var(--er25safe-text);
    font-size: 15px;
    font-weight: 900;
    line-height: 1.05;
}

.er25safe-brand-subtitle {
    margin: 4px 0 0;
    color: var(--er25safe-muted);
    font-size: 11px;
}

.er25safe-nav {
    padding: 14px;
    overflow: auto;
}

.er25safe-section {
    margin: 12px 8px 6px;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--er25safe-muted);
    font-weight: 800;
}

.er25safe-link {
    display: flex;
    align-items: center;
    gap: 11px;
    min-height: 42px;
    padding: 10px 12px;
    border-radius: 14px;
    color: var(--er25safe-text) !important;
    text-decoration: none !important;
    border: 1px solid transparent;
    font-size: 14px;
    font-weight: 750;
}

.er25safe-link:hover {
    background: rgba(185, 28, 28, 0.08);
    border-color: rgba(185, 28, 28, 0.14);
}

.er25safe-link.er25safe-active {
    background: linear-gradient(135deg, rgba(185, 28, 28, 0.16), rgba(239, 68, 68, 0.09));
    border-color: rgba(185, 28, 28, 0.28);
    color: var(--er25safe-red) !important;
}

.er25safe-footer {
    margin-top: auto;
    padding: 14px;
    border-top: 1px solid var(--er25safe-border);
}

.er25safe-user {
    background: rgba(148, 163, 184, 0.10);
    border: 1px solid var(--er25safe-border);
    border-radius: 16px;
    padding: 12px;
    color: var(--er25safe-text);
    font-size: 12px;
}

.er25safe-topbar {
    position: fixed;
    top: 0;
    right: 0;
    left: var(--er25safe-sidebar-w);
    min-height: var(--er25safe-topbar-h);
    background: color-mix(in srgb, var(--er25safe-card) 92%, transparent);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--er25safe-border);
    z-index: 2147482990;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 10px 18px;
    transition: left 0.22s ease;
}

body.er25safe-collapsed .er25safe-topbar {
    left: 0;
}

body.er25safe-collapsed .er25safe-sidebar {
    transform: translateX(calc(-1 * var(--er25safe-sidebar-w)));
}

.er25safe-title {
    margin: 0;
    color: var(--er25safe-text);
    font-size: 18px;
    font-weight: 900;
    letter-spacing: -0.02em;
}

.er25safe-subtitle {
    margin: 2px 0 0;
    color: var(--er25safe-muted);
    font-size: 12px;
}

.er25safe-actions {
    display: flex;
    align-items: center;
    gap: 8px;
}

.er25safe-btn {
    border: 1px solid var(--er25safe-border);
    background: var(--er25safe-card);
    color: var(--er25safe-text);
    min-height: 38px;
    padding: 8px 11px;
    border-radius: 12px;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-weight: 800;
    cursor: pointer;
}

.er25safe-overlay {
    display: none;
}

@media (max-width: 1024px) {
    body.er25safe-ready {
        padding-top: var(--er25safe-topbar-h);
    }

    .er25safe-sidebar {
        transform: translateX(calc(-1 * var(--er25safe-sidebar-w)));
    }

    .er25safe-topbar {
        left: 0;
    }

    body.er25safe-open .er25safe-sidebar {
        transform: translateX(0);
    }

    .er25safe-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.48);
        z-index: 2147482980;
    }

    body.er25safe-open .er25safe-overlay {
        display: block;
    }
}
/* ETAPA25_1_SHELL_SEGURO_FIM */
'''


def bloco_js_25_1():
    return r'''
<!-- ETAPA25_1_SHELL_SEGURO_INICIO -->
<script id="etapa25-1-shell-seguro">
(function () {
    if (window.__ETAPA25_1_SHELL_SEGURO__) {
        return;
    }
    window.__ETAPA25_1_SHELL_SEGURO__ = true;

    function pagina() {
        return window.location.pathname || '/';
    }

    function tituloPagina() {
        var p = pagina();

        if (p.indexOf('/crm') === 0) {
            return ['CRM Atendimento', 'Conversas, filas e contatos'];
        }

        if (p.indexOf('/admin/painel') === 0) {
            return ['Painel Administrativo', 'Usuarios, empresa e configuracoes'];
        }

        if (p.indexOf('/super-admin') === 0) {
            return ['Super Admin', 'Tenants e gestao geral'];
        }

        return ['Dashboard', 'Indicadores e atalhos principais'];
    }

    function temaAtual() {
        var salvo = localStorage.getItem('er25safe-theme');
        if (salvo === 'dark' || salvo === 'light') {
            return salvo;
        }

        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }

        return 'light';
    }

    function aplicarTema(tema) {
        var dark = tema === 'dark';

        document.documentElement.classList.toggle('er25safe-dark', dark);
        document.body.classList.toggle('er25safe-dark', dark);
        document.documentElement.classList.toggle('dark', dark);
        document.documentElement.classList.toggle('light', !dark);

        localStorage.setItem('er25safe-theme', tema);

        var btn = document.getElementById('er25safe-theme');
        if (btn) {
            btn.innerHTML = dark ? '☀️ <span>Claro</span>' : '🌙 <span>Escuro</span>';
        }
    }

    function link(href, icon, text) {
        var a = document.createElement('a');
        a.href = href;
        a.className = 'er25safe-link';
        a.innerHTML = '<span>' + icon + '</span><span>' + text + '</span>';

        var p = pagina();

        if (href === '/dashboard' && p === '/dashboard') {
            a.classList.add('er25safe-active');
        } else if (href !== '/dashboard' && p.indexOf(href) === 0) {
            a.classList.add('er25safe-active');
        }

        return a;
    }

    function section(text) {
        var div = document.createElement('div');
        div.className = 'er25safe-section';
        div.textContent = text;
        return div;
    }

    function criar() {
        if (document.getElementById('er25safe-sidebar')) {
            return;
        }

        document.body.classList.add('er25safe-ready');

        var sidebar = document.createElement('aside');
        sidebar.id = 'er25safe-sidebar';
        sidebar.className = 'er25safe-sidebar';

        sidebar.innerHTML = ''
            + '<div class="er25safe-brand">'
            + '  <div class="er25safe-brand-mark">ER</div>'
            + '  <div>'
            + '    <p class="er25safe-brand-title">Engeradios CRM</p>'
            + '    <p class="er25safe-brand-subtitle">Atendimento profissional</p>'
            + '  </div>'
            + '</div>';

        var nav = document.createElement('nav');
        nav.className = 'er25safe-nav';
        nav.appendChild(section('Principal'));
        nav.appendChild(link('/dashboard', '📊', 'Dashboard'));
        nav.appendChild(link('/crm', '💬', 'CRM Atendimento'));
        nav.appendChild(section('Gestao'));
        nav.appendChild(link('/admin/painel', '⚙️', 'Painel Administrativo'));
        nav.appendChild(link('/super-admin', '🛡️', 'Super Admin'));
        nav.appendChild(section('Sessao'));
        nav.appendChild(link('/logout', '🚪', 'Sair'));

        sidebar.appendChild(nav);

        var footer = document.createElement('div');
        footer.className = 'er25safe-footer';
        footer.innerHTML = '<div class="er25safe-user"><strong>Usuario logado</strong><br><span>Sistema SaaS</span></div>';
        sidebar.appendChild(footer);

        var nomes = tituloPagina();

        var topbar = document.createElement('header');
        topbar.id = 'er25safe-topbar';
        topbar.className = 'er25safe-topbar';
        topbar.innerHTML = ''
            + '<div style="display:flex;align-items:center;gap:10px">'
            + '  <button type="button" class="er25safe-btn" id="er25safe-mobile">☰</button>'
            + '  <div>'
            + '    <h1 class="er25safe-title">' + nomes[0] + '</h1>'
            + '    <p class="er25safe-subtitle">' + nomes[1] + '</p>'
            + '  </div>'
            + '</div>'
            + '<div class="er25safe-actions">'
            + '  <button type="button" class="er25safe-btn" id="er25safe-theme">🌙 <span>Escuro</span></button>'
            + '  <button type="button" class="er25safe-btn" id="er25safe-collapse">⇤ <span>Menu</span></button>'
            + '</div>';

        var overlay = document.createElement('div');
        overlay.id = 'er25safe-overlay';
        overlay.className = 'er25safe-overlay';

        document.body.insertBefore(overlay, document.body.firstChild);
        document.body.insertBefore(topbar, document.body.firstChild);
        document.body.insertBefore(sidebar, document.body.firstChild);

        var mobile = document.getElementById('er25safe-mobile');
        if (mobile) {
            mobile.addEventListener('click', function () {
                document.body.classList.toggle('er25safe-open');
            });
        }

        overlay.addEventListener('click', function () {
            document.body.classList.remove('er25safe-open');
        });

        var collapse = document.getElementById('er25safe-collapse');
        if (collapse) {
            collapse.addEventListener('click', function () {
                document.body.classList.toggle('er25safe-collapsed');
            });
        }

        var theme = document.getElementById('er25safe-theme');
        if (theme) {
            theme.addEventListener('click', function () {
                var atual = localStorage.getItem('er25safe-theme') || temaAtual();
                aplicarTema(atual === 'dark' ? 'light' : 'dark');
            });
        }

        aplicarTema(temaAtual());
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', criar);
    } else {
        criar();
    }
})();
</script>
<!-- ETAPA25_1_SHELL_SEGURO_FIM -->
'''


def remover_bloco_etapa25_antigo(texto):
    padrao = re.compile(
        r'\s*<!-- ETAPA25_LAYOUT_PROFISSIONAL_INICIO -->\s*'
        r'<script id="etapa25-layout-profissional">.*?</script>\s*'
        r'<!-- ETAPA25_LAYOUT_PROFISSIONAL_FIM -->\s*',
        re.DOTALL
    )

    novo, qtd = padrao.subn("\n", texto)
    return novo, qtd


def inserir_antes_body_fim(texto, bloco):
    if "</body>" in texto:
        return texto.replace("</body>", bloco + "\n</body>", 1)
    return texto + "\n" + bloco + "\n"


def garantir_css_link(texto):
    if "/css/style.css" in texto:
        return texto, False

    link = '    /css/style.css\n'

    if "</head>" in texto:
        return texto.replace("</head>", link + "</head>", 1), True

    return link + texto, True


def aplicar():
    resultado = {
        "css": {
            "alterado": False,
            "sha256_antes": sha256(CSS_FILE) if CSS_FILE.exists() else None,
            "sha256_depois": None
        },
        "views": []
    }

    css = ler(CSS_FILE)
    if css is None:
        css = ""

    if "ETAPA25_1_SHELL_SEGURO_INICIO" not in css:
        if not css.endswith("\n"):
            css += "\n"
        css += bloco_css_25_1() + "\n"
        gravar(CSS_FILE, css)
        resultado["css"]["alterado"] = True

    resultado["css"]["sha256_depois"] = sha256(CSS_FILE)

    for view in VIEW_FILES:
        item = {
            "arquivo": rel(view),
            "existe": view.exists(),
            "alterado": False,
            "removeu_blocos_antigos": 0,
            "adicionou_css": False,
            "adicionou_shell_seguro": False,
            "sha256_antes": sha256(view) if view.exists() else None,
            "sha256_depois": None
        }

        texto = ler(view)
        if texto is None:
            item["erro"] = "arquivo ausente ou ilegivel"
            resultado["views"].append(item)
            continue

        novo = texto

        novo, qtd = remover_bloco_etapa25_antigo(novo)
        item["removeu_blocos_antigos"] = qtd

        novo, adicionou_css = garantir_css_link(novo)
        item["adicionou_css"] = adicionou_css

        if "ETAPA25_1_SHELL_SEGURO_INICIO" not in novo:
            novo = inserir_antes_body_fim(novo, bloco_js_25_1())
            item["adicionou_shell_seguro"] = True

        if novo != texto:
            gravar(view, novo)
            item["alterado"] = True

        item["sha256_depois"] = sha256(view)
        resultado["views"].append(item)

    return resultado


def validar_estrutura():
    resultado = {
        "css_ok": False,
        "views": [],
        "views_ok": False,
        "ok": False
    }

    css = ler(CSS_FILE) or ""
    resultado["css_ok"] = bool(
        "ETAPA25_1_SHELL_SEGURO_INICIO" in css and
        ".er25safe-sidebar" in css and
        ".er25safe-topbar" in css
    )

    for view in VIEW_FILES:
        texto = ler(view) or ""

        item = {
            "arquivo": rel(view),
            "existe": view.exists(),
            "sem_shell_antigo": "document.body.innerHTML = ''" not in texto and "er25-shell" not in texto,
            "tem_shell_seguro": "ETAPA25_1_SHELL_SEGURO_INICIO" in texto,
            "tem_css": "/css/style.css" in texto,
            "ok": False
        }

        item["ok"] = bool(
            item["existe"] and
            item["sem_shell_antigo"] and
            item["tem_shell_seguro"] and
            item["tem_css"]
        )

        resultado["views"].append(item)

    resultado["views_ok"] = all(v["ok"] for v in resultado["views"])
    resultado["ok"] = bool(resultado["css_ok"] and resultado["views_ok"])
    return resultado


def restart_app():
    valor = os.environ.get("ETAPA25_1_RESTART_APP", "true").strip().lower()

    if valor in ["false", "0", "nao", "não", "no"]:
        return {
            "executado": False,
            "ok": None,
            "resultado": None
        }

    r = run_cmd(["docker", "compose", "restart", "app"], 120)
    return {
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


def http_request(opener, metodo, path, data_obj=None, timeout=20, limite=700000):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "metodo": metodo,
        "ok": False,
        "status": None,
        "erro": None,
        "content_type": "",
        "body_preview": "",
        "body_limited": ""
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-25-1-shell-seguro/1.0"
    }

    if data_obj is not None:
        body_text = json.dumps(data_obj)
        body_bytes = body_text.encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=body_bytes, headers=headers, method=metodo)

    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(limite)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["body_preview"] = redigir(texto[:1500])
            resultado["body_limited"] = redigir(texto)
    except HTTPError as exc:
        try:
            body = exc.read(limite)
            texto = body.decode("utf-8", errors="replace")
        except Exception:
            texto = ""

        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 400
        resultado["erro"] = redigir(str(exc))
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
        resultado["body_preview"] = redigir(texto[:1500])
        resultado["body_limited"] = redigir(texto)
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
        r = http_request(opener, "GET", "/", None, timeout=6, limite=3000)
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


def validar_runtime():
    c = credenciais()

    resultado = {
        "login_ok": False,
        "cookies": [],
        "paginas": [],
        "paginas_ok": False,
        "layout_ok": False,
        "ok": False
    }

    opener, jar = criar_opener()

    login = http_request(opener, "POST", LOGIN_API, {
        "email": c["email"],
        "senha": c["senha"]
    }, limite=100000)

    body_login = (login.get("body_limited") or "").lower()
    resultado["cookies"] = cookies_resumo(jar)
    resultado["login"] = {
        "status": login.get("status"),
        "ok": login.get("ok"),
        "erro": login.get("erro"),
        "content_type": login.get("content_type"),
        "body_preview": login.get("body_preview")
    }

    resultado["login_ok"] = bool(
        login.get("status") in [200, 201, 302] and
        ("success" in body_login or "sucesso" in body_login or len(resultado["cookies"]) > 0)
    )

    for page in PAGES:
        r = http_request(opener, "GET", page, None, limite=700000)
        body = r.get("body_limited") or ""

        item = {
            "path": page,
            "status": r.get("status"),
            "ok": r.get("status") == 200,
            "tem_shell_seguro": "ETAPA25_1_SHELL_SEGURO_INICIO" in body,
            "tem_sidebar": "er25safe-sidebar" in body,
            "tem_theme": "er25safe-theme" in body,
            "sem_shell_antigo": "document.body.innerHTML = ''" not in body and "er25-shell" not in body,
            "content_type": r.get("content_type")
        }

        item["layout_ok"] = bool(
            item["ok"] and
            item["tem_shell_seguro"] and
            item["tem_sidebar"] and
            item["tem_theme"] and
            item["sem_shell_antigo"]
        )

        resultado["paginas"].append(item)

    resultado["paginas_ok"] = all(p["ok"] for p in resultado["paginas"])
    resultado["layout_ok"] = all(p["layout_ok"] for p in resultado["paginas"])
    resultado["ok"] = bool(resultado["login_ok"] and resultado["paginas_ok"] and resultado["layout_ok"])
    return resultado


def coletar_logs(since):
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


def parece_email(token):
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


def analisar_logs(texto):
    session_id = 0
    cookie = 0
    email = 0
    achados = []

    for idx, linha in enumerate(str(texto or "").splitlines(), start=1):
        low = linha.lower()

        if "session id" in low:
            session_id += 1

        if "saas_crm_sid" in low or "connect.sid" in low or "header cookie" in low:
            cookie += 1

        tokens = linha.replace("(", " ").replace(")", " ").replace(",", " ").split()
        for token in tokens:
            if parece_email(token):
                email += 1
                break

        if "syntaxerror" in low or "exception" in low or "database" in low or "econnrefused" in low:
            achados.append({
                "linha": idx,
                "trecho": redigir(linha.strip())[:500]
            })

    return {
        "total_linhas": len(str(texto or "").splitlines()),
        "linhas_session_id": session_id,
        "linhas_cookie": cookie,
        "linhas_email": email,
        "achados": achados,
        "amostra": redigir("\n".join(str(texto or "").splitlines()[-120:]))[:30000]
    }


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)

    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_25_1_INICIO -->"
    fim = "<!-- ETAPA_25_1_FIM -->"

    bloco = []
    bloco.append("")
    bloco.append(ini)
    bloco.append("## " + titulo)
    bloco.append("")
    bloco.extend(linhas)
    bloco.append(fim)
    bloco.append("")

    novo_bloco = "\n".join(bloco)

    pos_ini = atual.find(ini)
    pos_fim = atual.find(fim)

    if pos_ini >= 0 and pos_fim >= pos_ini:
        pos_fim = pos_fim + len(fim)
        novo = atual[:pos_ini] + novo_bloco.strip() + atual[pos_fim:]
    else:
        if not atual.endswith("\n"):
            atual = atual + "\n"
        novo = atual + novo_bloco

    gravar(path, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    estrutura = relatorio["validacao_estrutura"]
    runtime = relatorio["runtime"]
    logs = relatorio["logs_analise"]

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Etapa 25.1 - Frontend corrigido com shell seguro",
        [
            "Data: " + data,
            "",
            "Substituido shell invasivo por shell seguro sem reconstruir o body.",
            "Validacao estrutural OK: " + str(estrutura["ok"]) + ".",
            "Login OK: " + str(runtime["login_ok"]) + ".",
            "Paginas OK: " + str(runtime["paginas_ok"]) + ".",
            "Layout OK: " + str(runtime["layout_ok"]) + ".",
            "Runtime OK: " + str(runtime["ok"]) + ".",
            "Logs Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs cookie: " + str(logs["linhas_cookie"]) + ".",
            "Logs email: " + str(logs["linhas_email"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 25.1 - Correcao do frontend",
        [
            "Data: " + data,
            "",
            "Removido script antigo que reconstruia o body.",
            "Adicionado shell seguro com menu lateral e tema claro/escuro.",
            "Preservados scripts originais das paginas.",
            "Validadas rotas principais em runtime."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 25.1 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido nao mover os nos originais do body para evitar quebra de scripts das views.",
            "Decidido inserir sidebar e topbar como elementos fixos independentes.",
            "Decidido manter a navegacao por links normais para preservar comportamento do navegador.",
            "Decidido corrigir o layout antes de continuar com Baileys e auditoria funcional."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 25.1",
        [
            "Data: " + data,
            "",
            "Validar manualmente a navegacao entre dashboard, CRM, admin panel e super admin.",
            "Se aprovado visualmente, seguir para Etapa 26 de auditoria funcional.",
            "Refinar responsividade mobile se necessario."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    linhas = []
    linhas.append("# Etapa 25.1 - Corrigir frontend com shell seguro")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- CSS alterado: " + str(relatorio["aplicacao"]["css"]["alterado"]))
    linhas.append("- Validacao estrutural OK: " + str(relatorio["validacao_estrutura"]["ok"]))
    linhas.append("- Restart executado: " + str(relatorio["restart_app"]["executado"]))
    linhas.append("- Restart OK: " + str(relatorio["restart_app"]["ok"]))
    linhas.append("- App pronto: " + str(relatorio["aguardar_app"]["ok"]))
    linhas.append("- Login OK: " + str(relatorio["runtime"]["login_ok"]))
    linhas.append("- Paginas OK: " + str(relatorio["runtime"]["paginas_ok"]))
    linhas.append("- Layout OK: " + str(relatorio["runtime"]["layout_ok"]))
    linhas.append("- Runtime geral OK: " + str(relatorio["runtime"]["ok"]))
    linhas.append("- Logs Session ID: " + str(relatorio["logs_analise"]["linhas_session_id"]))
    linhas.append("- Logs cookie: " + str(relatorio["logs_analise"]["linhas_cookie"]))
    linhas.append("- Logs email: " + str(relatorio["logs_analise"]["linhas_email"]))
    linhas.append("- Achados logs: " + str(len(relatorio["logs_analise"]["achados"])))
    linhas.append("")

    linhas.append("## Views")
    linhas.append("")
    for item in relatorio["aplicacao"]["views"]:
        linhas.append(
            "- " + item["arquivo"] +
            ": alterado " + str(item["alterado"]) +
            ", blocos antigos removidos " + str(item["removeu_blocos_antigos"]) +
            ", shell seguro " + str(item["adicionou_shell_seguro"])
        )

    linhas.append("")
    linhas.append("## Runtime por pagina")
    linhas.append("")
    for item in relatorio["runtime"]["paginas"]:
        linhas.append("- " + item["path"] + ": status " + str(item["status"]) + ", layout_ok " + str(item["layout_ok"]))

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_25_1_shell_seguro_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_25_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = logs_since()
    aplicacao = aplicar()
    estrutura = validar_estrutura()
    restart = restart_app()
    aguardar = aguardar_app()
    runtime = validar_runtime()
    time.sleep(2)

    logs_coleta = coletar_logs(since)
    logs_analise = analisar_logs(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "aplicacao": aplicacao,
        "validacao_estrutura": estrutura,
        "restart_app": restart,
        "aguardar_app": aguardar,
        "runtime": runtime,
        "logs_since": since,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_25_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_25_1_corrigir_frontend_shell_seguro.json"
    md_path = REPORTS_DIR / "etapa_25_1_corrigir_frontend_shell_seguro.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 25.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("CSS alterado: " + str(aplicacao["css"]["alterado"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Restart executado: " + str(restart["executado"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Paginas OK: " + str(runtime["paginas_ok"]))
    print("Layout OK: " + str(runtime["layout_ok"]))
    print("Runtime geral OK: " + str(runtime["ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["ok"]:
        print("")
        print("Aviso: shell seguro nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
