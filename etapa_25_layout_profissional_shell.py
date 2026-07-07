#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 25 - Layout profissional com menu lateral e tema claro/escuro

Objetivo:
- Criar backup antes da alteracao.
- Gerar manifesto antes e depois.
- Aplicar shell visual comum nas telas principais.
- Garantir menu lateral visivel.
- Garantir tema claro/escuro com localStorage.
- Manter funcoes existentes.
- Nao alterar backend, banco, rotas ou controllers.
- Validar runtime das telas.
- Atualizar documentacao obrigatoria.
- Gerar relatorios JSON e Markdown.

Como executar:
sudo ETAPA25_LOGIN_EMAIL='superadmin.teste@saas.local' ETAPA25_LOGIN_PASSWORD='123456' python3 etapa_25_layout_profissional_shell.py

Ou:
sudo ETAPA25_LOGIN_EMAIL='admin@saas.com' ETAPA25_LOGIN_PASSWORD='123456' python3 etapa_25_layout_profissional_shell.py
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

IGNORE_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "reports",
    "__pycache__",
    "tmp_etapa_24"
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
    "ETAPA25_LOGIN_EMAIL",
    "ETAPA24_SUPER_EMAIL",
    "ETAPA23_LOGIN_EMAIL",
    "ETAPA22_1_LOGIN_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "SUPER_ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA25_LOGIN_PASSWORD",
    "ETAPA24_SUPER_PASSWORD",
    "ETAPA23_LOGIN_PASSWORD",
    "ETAPA22_1_LOGIN_PASSWORD",
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


def deve_ignorar(path):
    partes = set(path.parts)
    rel_path = rel(path)

    for nome in IGNORE_DIRS:
        if nome in partes:
            return True
        if rel_path == nome or rel_path.startswith(nome + "/"):
            return True

    return False


def gerar_manifesto():
    itens = []

    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)
        dirs[:] = [d for d in dirs if not deve_ignorar(base_path / d)]

        for nome in files:
            p = base_path / nome
            if deve_ignorar(p):
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


def bloco_css_etapa25():
    return r'''
/* ETAPA25_LAYOUT_PROFISSIONAL_INICIO */
:root {
    --er25-bg: #f6f7fb;
    --er25-surface: #ffffff;
    --er25-surface-2: #f9fafb;
    --er25-border: #e5e7eb;
    --er25-text: #0f172a;
    --er25-muted: #64748b;
    --er25-red: #b91c1c;
    --er25-red-2: #ef4444;
    --er25-blue: #2563eb;
    --er25-green: #059669;
    --er25-shadow: 0 18px 45px rgba(15, 23, 42, 0.10);
    --er25-sidebar-w: 282px;
    --er25-header-h: 68px;
}

html.er-theme-dark,
body.er-theme-dark,
.er-theme-dark {
    --er25-bg: #0b1120;
    --er25-surface: #111827;
    --er25-surface-2: #0f172a;
    --er25-border: #243044;
    --er25-text: #f8fafc;
    --er25-muted: #94a3b8;
    --er25-shadow: 0 24px 60px rgba(0, 0, 0, 0.40);
}

body.er25-shell-ready {
    background:
        radial-gradient(circle at top left, rgba(185, 28, 28, 0.08), transparent 28rem),
        radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.08), transparent 28rem),
        var(--er25-bg) !important;
    color: var(--er25-text) !important;
    min-height: 100vh;
}

.er25-shell {
    min-height: 100vh;
    background: var(--er25-bg);
    color: var(--er25-text);
}

.er25-sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    width: var(--er25-sidebar-w);
    background:
        linear-gradient(180deg, rgba(185, 28, 28, 0.14), transparent 28%),
        var(--er25-surface);
    border-right: 1px solid var(--er25-border);
    box-shadow: var(--er25-shadow);
    z-index: 9990;
    display: flex;
    flex-direction: column;
    transform: translateX(0);
    transition: transform 0.22s ease;
}

.er25-brand {
    min-height: var(--er25-header-h);
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 18px;
    border-bottom: 1px solid var(--er25-border);
}

.er25-brand-logo {
    width: 42px;
    height: 42px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    color: #ffffff;
    font-weight: 900;
    background: linear-gradient(135deg, var(--er25-red), var(--er25-red-2));
    box-shadow: 0 14px 30px rgba(239, 68, 68, 0.28);
}

.er25-brand-title {
    font-size: 15px;
    line-height: 1.05;
    font-weight: 900;
    margin: 0;
    color: var(--er25-text);
}

.er25-brand-subtitle {
    font-size: 11px;
    color: var(--er25-muted);
    margin: 4px 0 0;
}

.er25-nav {
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 7px;
    overflow: auto;
}

.er25-nav-section {
    margin: 12px 8px 6px;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--er25-muted);
    font-weight: 800;
}

.er25-nav-link {
    display: flex;
    align-items: center;
    gap: 11px;
    min-height: 42px;
    padding: 10px 12px;
    border-radius: 14px;
    color: var(--er25-text) !important;
    text-decoration: none !important;
    border: 1px solid transparent;
    transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
    font-size: 14px;
    font-weight: 750;
}

.er25-nav-link:hover {
    background: rgba(185, 28, 28, 0.08);
    border-color: rgba(185, 28, 28, 0.14);
    transform: translateX(2px);
}

.er25-nav-link.er25-active {
    background: linear-gradient(135deg, rgba(185, 28, 28, 0.16), rgba(239, 68, 68, 0.09));
    border-color: rgba(185, 28, 28, 0.28);
    color: var(--er25-red) !important;
}

.er25-nav-icon {
    width: 22px;
    display: inline-flex;
    justify-content: center;
    opacity: 0.92;
}

.er25-sidebar-footer {
    margin-top: auto;
    padding: 14px;
    border-top: 1px solid var(--er25-border);
}

.er25-user-card {
    background: var(--er25-surface-2);
    border: 1px solid var(--er25-border);
    border-radius: 16px;
    padding: 12px;
    display: flex;
    gap: 10px;
    align-items: center;
}

.er25-avatar {
    width: 36px;
    height: 36px;
    border-radius: 13px;
    display: grid;
    place-items: center;
    color: #fff;
    background: linear-gradient(135deg, #0f172a, #334155);
    font-weight: 900;
}

.er-theme-dark .er25-avatar {
    background: linear-gradient(135deg, #b91c1c, #ef4444);
}

.er25-main {
    min-height: 100vh;
    margin-left: var(--er25-sidebar-w);
    transition: margin-left 0.22s ease;
}

.er25-topbar {
    position: sticky;
    top: 0;
    min-height: var(--er25-header-h);
    background: color-mix(in srgb, var(--er25-surface) 92%, transparent);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--er25-border);
    z-index: 9980;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 12px 22px;
}

.er25-topbar-title {
    margin: 0;
    font-size: 18px;
    font-weight: 900;
    letter-spacing: -0.02em;
    color: var(--er25-text);
}

.er25-topbar-subtitle {
    margin: 3px 0 0;
    color: var(--er25-muted);
    font-size: 12px;
}

.er25-actions {
    display: flex;
    align-items: center;
    gap: 10px;
}

.er25-btn {
    appearance: none;
    border: 1px solid var(--er25-border);
    background: var(--er25-surface);
    color: var(--er25-text);
    min-height: 40px;
    padding: 9px 12px;
    border-radius: 13px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
}

.er25-btn:hover {
    border-color: rgba(185, 28, 28, 0.35);
    color: var(--er25-red);
}

.er25-menu-toggle {
    display: none;
}

.er25-content {
    padding: 22px;
}

.er25-content > .er-page,
.er25-content > main,
.er25-content > .container,
.er25-content > .max-w-7xl,
.er25-content > .max-w-6xl {
    max-width: none !important;
}

.er25-shell .er-card,
.er25-shell .card,
.er25-shell .panel,
.er25-shell .box {
    border-color: var(--er25-border) !important;
}

.er25-overlay {
    display: none;
}

body.er25-sidebar-collapsed .er25-sidebar {
    transform: translateX(calc(-1 * var(--er25-sidebar-w)));
}

body.er25-sidebar-collapsed .er25-main {
    margin-left: 0;
}

@media (max-width: 1024px) {
    .er25-sidebar {
        transform: translateX(calc(-1 * var(--er25-sidebar-w)));
    }

    .er25-main {
        margin-left: 0;
    }

    body.er25-sidebar-open .er25-sidebar {
        transform: translateX(0);
    }

    .er25-menu-toggle {
        display: inline-flex;
    }

    .er25-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.48);
        z-index: 9985;
    }

    body.er25-sidebar-open .er25-overlay {
        display: block;
    }
}
/* ETAPA25_LAYOUT_PROFISSIONAL_FIM */
'''


def bloco_js_etapa25():
    return r'''
<!-- ETAPA25_LAYOUT_PROFISSIONAL_INICIO -->
<script id="etapa25-layout-profissional">
(function () {
    if (window.__ETAPA25_LAYOUT_APLICADO__) {
        return;
    }
    window.__ETAPA25_LAYOUT_APLICADO__ = true;

    function pathAtual() {
        return window.location.pathname || '/';
    }

    function labelPagina() {
        var p = pathAtual();
        if (p.indexOf('/crm') === 0) return ['CRM Atendimento', 'Conversas, contatos, filas e produtividade'];
        if (p.indexOf('/admin/painel') === 0) return ['Painel Administrativo', 'Gestao da empresa, usuarios e configuracoes'];
        if (p.indexOf('/super-admin') === 0) return ['Super Admin', 'Gestao geral da plataforma e tenants'];
        return ['Dashboard', 'Indicadores, operacao e atalhos principais'];
    }

    function temaInicial() {
        var salvo = localStorage.getItem('er25-theme');
        if (salvo === 'dark' || salvo === 'light') return salvo;
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
        return 'light';
    }

    function aplicarTema(tema) {
        var escuro = tema === 'dark';
        document.documentElement.classList.toggle('er-theme-dark', escuro);
        document.body.classList.toggle('er-theme-dark', escuro);
        document.documentElement.classList.toggle('dark', escuro);
        document.documentElement.classList.toggle('light', !escuro);
        localStorage.setItem('er25-theme', tema);
        var btn = document.getElementById('er25-theme-toggle');
        if (btn) {
            btn.innerHTML = escuro ? '☀️ <span>Claro</span>' : '🌙 <span>Escuro</span>';
            btn.setAttribute('aria-label', escuro ? 'Ativar tema claro' : 'Ativar tema escuro');
        }
    }

    function criarLink(href, icon, text, section) {
        if (section) {
            var s = document.createElement('div');
            s.className = 'er25-nav-section';
            s.textContent = text;
            return s;
        }

        var a = document.createElement('a');
        a.className = 'er25-nav-link';
        a.href = href;
        a.innerHTML = '<span class="er25-nav-icon">' + icon + '</span><span>' + text + '</span>';

        var p = pathAtual();
        if (href === '/dashboard' && p === '/dashboard') a.classList.add('er25-active');
        if (href !== '/dashboard' && p.indexOf(href) === 0) a.classList.add('er25-active');

        return a;
    }

    function criarShell() {
        if (document.getElementById('er25-shell')) {
            return;
        }

        document.body.classList.add('er25-shell-ready');

        var shell = document.createElement('div');
        shell.id = 'er25-shell';
        shell.className = 'er25-shell';

        var sidebar = document.createElement('aside');
        sidebar.id = 'er25-sidebar';
        sidebar.className = 'er25-sidebar';
        sidebar.innerHTML = ''
            + '<div class="er25-brand">'
            + '  <div class="er25-brand-logo">ER</div>'
            + '  <div>'
            + '    <p class="er25-brand-title">Engeradios CRM</p>'
            + '    <p class="er25-brand-subtitle">Atendimento profissional</p>'
            + '  </div>'
            + '</div>';

        var nav = document.createElement('nav');
        nav.className = 'er25-nav';
        nav.appendChild(criarLink('', '', 'Principal', true));
        nav.appendChild(criarLink('/dashboard', '📊', 'Dashboard'));
        nav.appendChild(criarLink('/crm', '💬', 'CRM Atendimento'));
        nav.appendChild(criarLink('', '', 'Gestao', true));
        nav.appendChild(criarLink('/admin/painel', '⚙️', 'Painel Administrativo'));
        nav.appendChild(criarLink('/super-admin', '🛡️', 'Super Admin'));
        nav.appendChild(criarLink('', '', 'Atalhos', true));
        nav.appendChild(criarLink('/logout', '🚪', 'Sair'));
        sidebar.appendChild(nav);

        var footer = document.createElement('div');
        footer.className = 'er25-sidebar-footer';
        footer.innerHTML = ''
            + '<div class="er25-user-card">'
            + '  <div class="er25-avatar">U</div>'
            + '  <div style="min-width:0">'
            + '    <div style="font-weight:900;font-size:13px;color:var(--er25-text)">Usuario logado</div>'
            + '    <div style="font-size:11px;color:var(--er25-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">Sistema SaaS</div>'
            + '  </div>'
            + '</div>';
        sidebar.appendChild(footer);

        var overlay = document.createElement('div');
        overlay.className = 'er25-overlay';
        overlay.id = 'er25-overlay';
        overlay.addEventListener('click', function () {
            document.body.classList.remove('er25-sidebar-open');
        });

        var main = document.createElement('div');
        main.className = 'er25-main';

        var nomes = labelPagina();

        var topbar = document.createElement('header');
        topbar.className = 'er25-topbar';
        topbar.innerHTML = ''
            + '<div style="display:flex;align-items:center;gap:12px">'
            + '  <button type="button" class="er25-btn er25-menu-toggle" id="er25-menu-toggle">☰</button>'
            + '  <div>'
            + '    <h1 class="er25-topbar-title">' + nomes[0] + '</h1>'
            + '    <p class="er25-topbar-subtitle">' + nomes[1] + '</p>'
            + '  </div>'
            + '</div>'
            + '<div class="er25-actions">'
            + '  <button type="button" class="er25-btn" id="er25-theme-toggle">🌙 <span>Escuro</span></button>'
            + '  <button type="button" class="er25-btn" id="er25-collapse-toggle">⇤ <span>Menu</span></button>'
            + '</div>';

        var content = document.createElement('main');
        content.className = 'er25-content';
        content.id = 'er25-content';

        var nodes = [];
        for (var i = 0; i < document.body.childNodes.length; i++) {
            var n = document.body.childNodes[i];
            if (n.nodeType === 1 && (
                n.id === 'er25-shell' ||
                n.id === 'etapa25-layout-profissional' ||
                n.className === 'er25-overlay'
            )) {
                continue;
            }
            nodes.push(n);
        }

        document.body.innerHTML = '';

        for (var j = 0; j < nodes.length; j++) {
            content.appendChild(nodes[j]);
        }

        main.appendChild(topbar);
        main.appendChild(content);

        shell.appendChild(sidebar);
        shell.appendChild(overlay);
        shell.appendChild(main);

        document.body.appendChild(shell);

        var menuBtn = document.getElementById('er25-menu-toggle');
        if (menuBtn) {
            menuBtn.addEventListener('click', function () {
                document.body.classList.toggle('er25-sidebar-open');
            });
        }

        var collapseBtn = document.getElementById('er25-collapse-toggle');
        if (collapseBtn) {
            collapseBtn.addEventListener('click', function () {
                document.body.classList.toggle('er25-sidebar-collapsed');
            });
        }

        var themeBtn = document.getElementById('er25-theme-toggle');
        if (themeBtn) {
            themeBtn.addEventListener('click', function () {
                var atual = localStorage.getItem('er25-theme') || temaInicial();
                aplicarTema(atual === 'dark' ? 'light' : 'dark');
            });
        }

        aplicarTema(temaInicial());
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', criarShell);
    } else {
        criarShell();
    }
})();
</script>
<!-- ETAPA25_LAYOUT_PROFISSIONAL_FIM -->
'''


def garantir_css_link(texto):
    if "/css/style.css" in texto:
        return texto, False

    link = '    /css/style.css\n'

    if "</head>" in texto:
        return texto.replace("</head>", link + "</head>", 1), True

    return link + texto, True


def inserir_antes_body_fim(texto, bloco):
    if "</body>" in texto:
        return texto.replace("</body>", bloco + "\n</body>", 1)
    return texto + "\n" + bloco + "\n"


def aplicar_layout():
    resultado = {
        "css": {
            "arquivo": "public/css/style.css",
            "existe_antes": CSS_FILE.exists(),
            "alterado": False,
            "sha256_antes": sha256(CSS_FILE) if CSS_FILE.exists() else None,
            "sha256_depois": None
        },
        "views": []
    }

    css = ler(CSS_FILE)
    if css is None:
        css = ""

    if "ETAPA25_LAYOUT_PROFISSIONAL_INICIO" not in css:
        if not css.endswith("\n"):
            css += "\n"
        css += bloco_css_etapa25() + "\n"
        gravar(CSS_FILE, css)
        resultado["css"]["alterado"] = True

    resultado["css"]["sha256_depois"] = sha256(CSS_FILE)

    for view in VIEW_FILES:
        item = {
            "arquivo": rel(view),
            "existe_antes": view.exists(),
            "alterado": False,
            "adicionou_css": False,
            "adicionou_script": False,
            "sha256_antes": sha256(view) if view.exists() else None,
            "sha256_depois": None
        }

        texto = ler(view)
        if texto is None:
            item["erro"] = "arquivo ausente ou ilegivel"
            resultado["views"].append(item)
            continue

        novo = texto

        novo, css_adicionado = garantir_css_link(novo)
        item["adicionou_css"] = css_adicionado

        if "ETAPA25_LAYOUT_PROFISSIONAL_INICIO" not in novo:
            novo = inserir_antes_body_fim(novo, bloco_js_etapa25())
            item["adicionou_script"] = True

        if novo != texto:
            gravar(view, novo)
            item["alterado"] = True

        item["sha256_depois"] = sha256(view)
        resultado["views"].append(item)

    return resultado


def validar_estrutura():
    resultado = {
        "css_ok": False,
        "views_ok": False,
        "views": [],
        "ok": False
    }

    css = ler(CSS_FILE) or ""
    resultado["css_ok"] = bool(
        "ETAPA25_LAYOUT_PROFISSIONAL_INICIO" in css and
        ".er25-sidebar" in css and
        ".er25-topbar" in css and
        ".er-theme-dark" in css
    )

    for view in VIEW_FILES:
        texto = ler(view) or ""
        item = {
            "arquivo": rel(view),
            "existe": view.exists(),
            "tem_css": "/css/style.css" in texto,
            "tem_marker": "ETAPA25_LAYOUT_PROFISSIONAL_INICIO" in texto,
            "tem_shell": "er25-shell" in texto,
            "ok": False
        }

        item["ok"] = bool(
            item["existe"] and
            item["tem_css"] and
            item["tem_marker"] and
            item["tem_shell"]
        )
        resultado["views"].append(item)

    resultado["views_ok"] = all(v["ok"] for v in resultado["views"])
    resultado["ok"] = bool(resultado["css_ok"] and resultado["views_ok"])
    return resultado


def restart_app():
    valor = os.environ.get("ETAPA25_RESTART_APP", "true").strip().lower()

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
        "User-Agent": "etapa-25-layout-profissional/1.0"
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
        "todas_paginas_ok": False,
        "layout_runtime_ok": False,
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
            "tem_css": "/css/style.css" in body,
            "tem_marker": "ETAPA25_LAYOUT_PROFISSIONAL_INICIO" in body,
            "tem_sidebar": "er25-sidebar" in body,
            "tem_theme": "er25-theme-toggle" in body,
            "content_type": r.get("content_type")
        }

        item["layout_ok"] = bool(
            item["ok"] and
            item["tem_css"] and
            item["tem_marker"] and
            item["tem_sidebar"] and
            item["tem_theme"]
        )

        resultado["paginas"].append(item)

    resultado["todas_paginas_ok"] = all(p["ok"] for p in resultado["paginas"])
    resultado["layout_runtime_ok"] = all(p["layout_ok"] for p in resultado["paginas"])
    resultado["ok"] = bool(resultado["login_ok"] and resultado["todas_paginas_ok"] and resultado["layout_runtime_ok"])

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

    ini = "<!-- ETAPA_25_INICIO -->"
    fim = "<!-- ETAPA_25_FIM -->"

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
        "Etapa 25 - Layout profissional com menu lateral",
        [
            "Data: " + data,
            "",
            "Aplicado layout profissional comum com menu lateral, topbar e tema claro/escuro.",
            "CSS estrutural OK: " + str(estrutura["css_ok"]) + ".",
            "Views OK: " + str(estrutura["views_ok"]) + ".",
            "Runtime OK: " + str(runtime["ok"]) + ".",
            "Login OK: " + str(runtime["login_ok"]) + ".",
            "Paginas OK: " + str(runtime["todas_paginas_ok"]) + ".",
            "Layout runtime OK: " + str(runtime["layout_runtime_ok"]) + ".",
            "Logs Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs cookie: " + str(logs["linhas_cookie"]) + ".",
            "Logs email: " + str(logs["linhas_email"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 25 - Layout profissional aplicado",
        [
            "Data: " + data,
            "",
            "Adicionado shell visual profissional nas telas principais.",
            "Adicionado menu lateral comum.",
            "Adicionado botao de tema claro/escuro com localStorage.",
            "Padronizada estrutura visual via public/css/style.css.",
            "Preservadas as funcoes existentes das telas."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 25 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido aplicar o layout por camada visual injetada para evitar reescrever views grandes.",
            "Decidido manter backend, banco, rotas e controllers sem alteracao nesta etapa.",
            "Decidido usar localStorage para persistencia do tema claro/escuro.",
            "Decidido validar o menu lateral em runtime nas quatro telas principais."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 25",
        [
            "Data: " + data,
            "",
            "Validar manualmente o layout no navegador em desktop e mobile.",
            "Executar Etapa 26 para auditoria funcional completa.",
            "Planejar Etapa 27 para Baileys e camada WhatsApp.",
            "Planejar refinamento visual fino apos avaliacao manual."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    linhas = []
    linhas.append("# Etapa 25 - Layout profissional com menu lateral")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- CSS alterado: " + str(relatorio["aplicacao"]["css"]["alterado"]))
    linhas.append("- Validacao estrutural OK: " + str(relatorio["validacao_estrutura"]["ok"]))
    linhas.append("- Restart executado: " + str(relatorio["restart_app"]["executado"]))
    linhas.append("- Restart OK: " + str(relatorio["restart_app"]["ok"]))
    linhas.append("- App pronto: " + str(relatorio["aguardar_app"]["ok"]))
    linhas.append("- Login OK: " + str(relatorio["runtime"]["login_ok"]))
    linhas.append("- Todas paginas OK: " + str(relatorio["runtime"]["todas_paginas_ok"]))
    linhas.append("- Layout runtime OK: " + str(relatorio["runtime"]["layout_runtime_ok"]))
    linhas.append("- Runtime geral OK: " + str(relatorio["runtime"]["ok"]))
    linhas.append("- Logs Session ID: " + str(relatorio["logs_analise"]["linhas_session_id"]))
    linhas.append("- Logs cookie: " + str(relatorio["logs_analise"]["linhas_cookie"]))
    linhas.append("- Logs email: " + str(relatorio["logs_analise"]["linhas_email"]))
    linhas.append("- Achados logs: " + str(len(relatorio["logs_analise"]["achados"])))
    linhas.append("")

    linhas.append("## Views alteradas")
    linhas.append("")
    for item in relatorio["aplicacao"]["views"]:
        linhas.append("- " + item["arquivo"] + ": alterado " + str(item["alterado"]) + ", script " + str(item["adicionou_script"]))

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
    backup_dir = BACKUPS_DIR / ("etapa_25_layout_profissional_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_25_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = logs_since()
    aplicacao = aplicar_layout()
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
    manifesto_depois_path = REPORTS_DIR / "etapa_25_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_25_layout_profissional_shell.json"
    md_path = REPORTS_DIR / "etapa_25_layout_profissional_shell.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 25 concluida.")
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
    print("Todas paginas OK: " + str(runtime["todas_paginas_ok"]))
    print("Layout runtime OK: " + str(runtime["layout_runtime_ok"]))
    print("Runtime geral OK: " + str(runtime["ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["ok"]:
        print("")
        print("Aviso: layout nao validou completamente em runtime. Consulte o relatorio.")


if __name__ == "__main__":
    main()
