#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 25.4.1 - Corrigir HTML quebrado do dashboard

Objetivo:
- Corrigir /css/style.css como tag <link> valida.
- Corrigir links quebrados /crm, /admin/painel e /super-admin.
- Manter dashboard profissional, responsivo e sem mistura antiga.
- Alterar somente views/dashboard.ejs e documentacao obrigatoria.
- Validar HTML renderizado autenticado.
- Reiniciar app.
- Gerar relatorios JSON e Markdown.

Como executar:
sudo ETAPA25_4_1_LOGIN_EMAIL='admin.cliente.teste@saas.local' ETAPA25_4_1_LOGIN_PASSWORD='123456' python3 etapa_25_4_1_corrigir_dashboard_html.py
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
from html.parser import HTMLParser

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

DASHBOARD_FILE = ROOT / "views" / "dashboard.ejs"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "views/dashboard.ejs",
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
    "ETAPA25_4_1_LOGIN_EMAIL",
    "ETAPA25_4_LOGIN_EMAIL",
    "ETAPA25_3_LOGIN_EMAIL",
    "ETAPA24_CLIENTE_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA25_4_1_LOGIN_PASSWORD",
    "ETAPA25_4_LOGIN_PASSWORD",
    "ETAPA25_3_LOGIN_PASSWORD",
    "ETAPA24_CLIENTE_PASSWORD",
    "LOGIN_PASSWORD",
    "ADMIN_PASSWORD",
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
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")


def gravar(path, texto):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")


def sha256(path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return None

    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            bloco = f.read(1024 * 1024)
            if not bloco:
                break
            h.update(bloco)
    return h.hexdigest()


def salvar_json(path, dados):
    gravar(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


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
        email = "admin.cliente.teste@saas.local"

    if not senha:
        senha = "123456"

    return {
        "email": email,
        "senha": senha
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
            "stdout": redigir(proc.stdout.strip())[:50000],
            "stderr": redigir(proc.stderr.strip())[:50000],
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


def dashboard_html_corrigido():
    # Importante: manter HTML literal completo, com tags validas.
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard | Engeradios CRM</title>
    /css/style.css
</head>
<body>
    <main class="er25dash-page" id="dashboard-principal">
        <section class="er25dash-hero">
            <span class="er25dash-badge">● Dashboard operacional</span>
            <h1 class="er25dash-title">Visao geral do atendimento</h1>
            <p class="er25dash-subtitle">
                Acompanhe conexao WhatsApp, atalhos de operacao, acesso ao CRM e indicadores principais em uma pagina limpa, responsiva e separada da tela de atendimento.
            </p>

            <div class="er25dash-hero-actions">
                /crmAbrir CRM Atendimento</a>
                /admin/painelPainel Administrativo</a>
                /super-adminSuper Admin</a>
            </div>
        </section>

        <section class="er25dash-grid er25dash-grid-metrics" aria-label="Indicadores principais">
            <article class="er25dash-card er25dash-card-soft er25dash-metric">
                <div>
                    <div class="er25dash-label">Sessao</div>
                    <div class="er25dash-value" id="dash-session-value">Ativa</div>
                    <p class="er25dash-helper">Usuario autenticado no painel.</p>
                </div>
                <div class="er25dash-icon">S</div>
            </article>

            <article class="er25dash-card er25dash-card-soft er25dash-metric">
                <div>
                    <div class="er25dash-label">WhatsApp</div>
                    <div class="er25dash-value" id="dash-whatsapp-value">...</div>
                    <p class="er25dash-helper" id="dash-whatsapp-helper">Verificando status da conexao.</p>
                </div>
                <div class="er25dash-icon">W</div>
            </article>

            <article class="er25dash-card er25dash-card-soft er25dash-metric">
                <div>
                    <div class="er25dash-label">Atendimento</div>
                    <div class="er25dash-value">CRM</div>
                    <p class="er25dash-helper">Conversas e contatos em area dedicada.</p>
                </div>
                <div class="er25dash-icon">C</div>
            </article>

            <article class="er25dash-card er25dash-card-soft er25dash-metric">
                <div>
                    <div class="er25dash-label">Interface</div>
                    <div class="er25dash-value">Online</div>
                    <p class="er25dash-helper">Layout claro/escuro e responsivo.</p>
                </div>
                <div class="er25dash-icon">UI</div>
            </article>
        </section>

        <section class="er25dash-grid er25dash-grid-main">
            <article class="er25dash-card">
                <h2 class="er25dash-section-title">Atalhos de operacao</h2>
                <p class="er25dash-section-subtitle">
                    Acesse rapidamente as areas principais sem misturar dashboard com tela de atendimento.
                </p>

                <div class="er25dash-actions-list">
                    /crm
                        <div class="er25dash-action-top">
                            <h3 class="er25dash-action-title">CRM Atendimento</h3>
                            <span class="er25dash-pill">Abrir</span>
                        </div>
                        <p class="er25dash-action-desc">Conversas, contatos, atendimento humano, mensagens e fila operacional.</p>
                    </a>

                    /admin/painel
                        <div class="er25dash-action-top">
                            <h3 class="er25dash-action-title">Painel Administrativo</h3>
                            <span class="er25dash-pill">Gerir</span>
                        </div>
                        <p class="er25dash-action-desc">Usuarios, configuracoes da empresa, setores, mensagens rapidas e recursos do tenant.</p>
                    </a>

                    /super-admin
                        <div class="er25dash-action-top">
                            <h3 class="er25dash-action-title">Super Admin</h3>
                            <span class="er25dash-pill">Master</span>
                        </div>
                        <p class="er25dash-action-desc">Gestao de tenants, empresas, limites e administracao geral da plataforma.</p>
                    </a>

                    /crm
                        <div class="er25dash-action-top">
                            <h3 class="er25dash-action-title">Conexao WhatsApp</h3>
                            <span class="er25dash-pill" id="dash-whatsapp-pill">Status</span>
                        </div>
                        <p class="er25dash-action-desc">Status operacional exibido no dashboard. Gestao completa sera organizada em etapa propria.</p>
                    </a>
                </div>
            </article>

            <aside class="er25dash-card">
                <h2 class="er25dash-section-title">Estado do sistema</h2>
                <p class="er25dash-section-subtitle">
                    Leitura rapida das areas principais.
                </p>

                <div class="er25dash-status-row">
                    <div>
                        <p class="er25dash-status-name">Dashboard</p>
                        <p class="er25dash-status-desc">Pagina principal refatorada.</p>
                    </div>
                    <span class="er25dash-pill er25dash-pill-ok">OK</span>
                </div>

                <div class="er25dash-status-row">
                    <div>
                        <p class="er25dash-status-name">WhatsApp</p>
                        <p class="er25dash-status-desc" id="dash-whatsapp-status-desc">Aguardando leitura.</p>
                    </div>
                    <span class="er25dash-pill er25dash-pill-warn" id="dash-whatsapp-status-pill">Verificando</span>
                </div>

                <div class="er25dash-status-row">
                    <div>
                        <p class="er25dash-status-name">Menu lateral</p>
                        <p class="er25dash-status-desc">Shell seguro sem reconstruir o body.</p>
                    </div>
                    <span class="er25dash-pill er25dash-pill-ok">Ativo</span>
                </div>

                <div class="er25dash-status-row">
                    <div>
                        <p class="er25dash-status-name">Tema</p>
                        <p class="er25dash-status-desc">Claro e escuro via localStorage.</p>
                    </div>
                    <span class="er25dash-pill er25dash-pill-ok">Ativo</span>
                </div>

                <div class="er25dash-footer-note">
                    Esta pagina foi separada da tela de atendimento. Use o menu lateral ou o botao "Abrir CRM Atendimento" para acessar o fluxo completo de conversas.
                </div>
            </aside>
        </section>
    </main>

<script id="etapa25-4-dashboard-profissional">
(function () {
    function getEmpresaId() {
        var candidates = [];

        try {
            var metaEmpresa = document.querySelector('meta[name="empresa-id"]');
            if (metaEmpresa && metaEmpresa.content) {
                candidates.push(metaEmpresa.content);
            }
        } catch (e) {}

        candidates.push(window.EMPRESA_ID);
        candidates.push(window.empresaId);
        candidates.push(localStorage.getItem('empresaId'));
        candidates.push('5');

        for (var i = 0; i < candidates.length; i++) {
            var n = parseInt(candidates[i], 10);
            if (n && n > 0) {
                return n;
            }
        }

        return 5;
    }

    function setText(id, value) {
        var el = document.getElementById(id);
        if (el) {
            el.textContent = value;
        }
    }

    function setClass(id, value) {
        var el = document.getElementById(id);
        if (el) {
            el.className = value;
        }
    }

    async function carregarStatusWhatsApp() {
        var empresaId = getEmpresaId();
        var status = 'DESCONECTADO';

        try {
            var resp = await fetch('/api/whatsapp/status/' + empresaId, {
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (resp.ok) {
                var data = await resp.json();
                status = data.status || (data.connected ? 'CONECTADO' : 'DESCONECTADO');
            }
        } catch (e) {
            status = 'DESCONECTADO';
        }

        setText('dash-whatsapp-value', status);

        if (status === 'CONECTADO') {
            setText('dash-whatsapp-helper', 'Numero conectado e pronto para atendimento.');
            setText('dash-whatsapp-pill', 'Conectado');
            setText('dash-whatsapp-status-pill', 'Conectado');
            setText('dash-whatsapp-status-desc', 'Sessao WhatsApp operacional.');
            setClass('dash-whatsapp-status-pill', 'er25dash-pill er25dash-pill-ok');
            return;
        }

        if (status === 'AGUARDANDO_QR') {
            setText('dash-whatsapp-helper', 'Aguardando leitura do QR Code.');
            setText('dash-whatsapp-pill', 'QR Code');
            setText('dash-whatsapp-status-pill', 'QR Code');
            setText('dash-whatsapp-status-desc', 'Conexao aguardando pareamento.');
            setClass('dash-whatsapp-status-pill', 'er25dash-pill er25dash-pill-warn');
            return;
        }

        setText('dash-whatsapp-helper', 'WhatsApp desconectado. Conecte pela area de atendimento.');
        setText('dash-whatsapp-pill', 'Desconectado');
        setText('dash-whatsapp-status-pill', 'Desconectado');
        setText('dash-whatsapp-status-desc', 'Nenhuma sessao ativa no momento.');
        setClass('dash-whatsapp-status-pill', 'er25dash-pill er25dash-pill-off');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', carregarStatusWhatsApp);
    } else {
        carregarStatusWhatsApp();
    }
})();
</script>

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
</body>
</html>
"""


class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.stylesheets = []
        self.scripts = []
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a":
            self.links.append(d.get("href", ""))
        if tag == "link":
            self.stylesheets.append(d.get("href", ""))
        if tag == "script":
            self.scripts.append(d.get("src", ""))
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def inspecionar_html(html):
    p = Inspector()
    try:
        p.feed(html or "")
    except Exception:
        pass

    return {
        "title": p.title.strip(),
        "links": p.links,
        "links_total": len(p.links),
        "stylesheets": p.stylesheets,
        "scripts": p.scripts
    }


def aplicar_correcao():
    resultado = {
        "arquivo": "views/dashboard.ejs",
        "existe_antes": DASHBOARD_FILE.exists(),
        "alterado": False,
        "sha256_antes": sha256(DASHBOARD_FILE),
        "sha256_depois": None
    }

    atual = ler(DASHBOARD_FILE) or ""
    novo = dashboard_html_corrigido()

    if atual != novo:
        gravar(DASHBOARD_FILE, novo)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256(DASHBOARD_FILE)
    return resultado


def validar_estrutura_local():
    html = ler(DASHBOARD_FILE) or ""
    insp = inspecionar_html(html)

    quebrados = {
        "css_texto_solto": "/css/style.css\n" in html and '/css/style.css' not in html,
        "crm_texto_quebrado": "/crmAbrir" in html,
        "admin_texto_quebrado": "/admin/painelPainel" in html,
        "super_texto_quebrado": "/super-adminSuper" in html,
        "tailwind_cdn": "cdn.tailwindcss.com" in html,
        "alpine": "alpinejs" in html or "x-data" in html,
        "dashboard_antigo": "CRM WhatsApp Enterprise" in html or "appData" in html or "activeTab" in html
    }

    resultado = {
        "arquivo_existe": DASHBOARD_FILE.exists(),
        "links_total": insp["links_total"],
        "links": insp["links"],
        "stylesheets": insp["stylesheets"],
        "tem_css_link": "/css/style.css" in insp["stylesheets"],
        "tem_href_crm": "/crm" in insp["links"],
        "tem_href_admin": "/admin/painel" in insp["links"],
        "tem_href_super": "/super-admin" in insp["links"],
        "tem_dashboard_novo": "etapa25-4-dashboard-profissional" in html,
        "tem_shell_seguro": "ETAPA25_1_SHELL_SEGURO_INICIO" in html,
        "quebrados": quebrados,
        "ok": False
    }

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_css_link"] and
        resultado["tem_href_crm"] and
        resultado["tem_href_admin"] and
        resultado["tem_href_super"] and
        resultado["tem_dashboard_novo"] and
        resultado["tem_shell_seguro"] and
        not any(quebrados.values())
    )

    return resultado


def restart_app():
    valor = os.environ.get("ETAPA25_4_1_RESTART_APP", "true").strip().lower()

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
    out = []
    for c in jar:
        out.append({
            "name": c.name,
            "domain": c.domain,
            "path": c.path,
            "secure": c.secure
        })
    return out


def http_request(opener, metodo, path, data_obj=None, timeout=20, limite=900000):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "metodo": metodo,
        "status": None,
        "ok": False,
        "erro": None,
        "content_type": "",
        "body": "",
        "body_preview": "",
        "json": None
    }

    headers = {
        "User-Agent": "etapa-25-4-1-dashboard-html/1.0"
    }

    body_bytes = None

    if data_obj is not None:
        body_bytes = json.dumps(data_obj).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=body_bytes, headers=headers, method=metodo)

    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(limite)
            texto = raw.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["body"] = texto
            resultado["body_preview"] = redigir(texto[:1800])
            try:
                resultado["json"] = json.loads(texto)
            except Exception:
                resultado["json"] = None
    except HTTPError as exc:
        try:
            raw = exc.read(limite)
            texto = raw.decode("utf-8", errors="replace")
        except Exception:
            texto = ""
        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 400
        resultado["erro"] = redigir(str(exc))
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
        resultado["body"] = texto
        resultado["body_preview"] = redigir(texto[:1800])
        try:
            resultado["json"] = json.loads(texto)
        except Exception:
            resultado["json"] = None
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
    opener, jar = criar_opener()

    resultado = {
        "login_ok": False,
        "cookies": [],
        "dashboard_ok": False,
        "dashboard_html_ok": False,
        "status_api_ok": False,
        "paginas_ok": False,
        "ok": False
    }

    login = http_request(opener, "POST", LOGIN_API, {
        "email": c["email"],
        "senha": c["senha"]
    }, limite=100000)

    body_login = (login.get("body") or "").lower()
    resultado["cookies"] = cookies_resumo(jar)
    resultado["login"] = {
        "status": login.get("status"),
        "ok": login.get("ok"),
        "body_preview": login.get("body_preview")
    }

    resultado["login_ok"] = bool(
        login.get("status") in [200, 201, 302] and
        ("success" in body_login or "sucesso" in body_login or len(resultado["cookies"]) > 0)
    )

    paginas = []
    for page in PAGES:
        r = http_request(opener, "GET", page, None, limite=900000)
        item = {
            "path": page,
            "status": r.get("status"),
            "ok": r.get("status") == 200,
            "content_type": r.get("content_type")
        }

        if page == "/dashboard":
            html = r.get("body") or ""
            insp = inspecionar_html(html)

            item["links_total"] = insp["links_total"]
            item["links"] = insp["links"]
            item["stylesheets"] = insp["stylesheets"]
            item["tem_css_link"] = "/css/style.css" in insp["stylesheets"]
            item["tem_href_crm"] = "/crm" in insp["links"]
            item["tem_href_admin"] = "/admin/painel" in insp["links"]
            item["tem_href_super"] = "/super-admin" in insp["links"]
            item["texto_link_quebrado"] = any(x in html for x in ["/crmAbrir", "/admin/painelPainel", "/super-adminSuper"])
            item["css_texto_solto"] = "/css/style.css\n" in html and '/css/style.css' not in html
            item["sem_tailwind"] = "cdn.tailwindcss.com" not in html
            item["sem_alpine"] = "alpinejs" not in html and "x-data" not in html
            item["dashboard_html_ok"] = bool(
                item["ok"] and
                item["tem_css_link"] and
                item["tem_href_crm"] and
                item["tem_href_admin"] and
                item["tem_href_super"] and
                not item["texto_link_quebrado"] and
                not item["css_texto_solto"] and
                item["sem_tailwind"] and
                item["sem_alpine"]
            )

        paginas.append(item)

    resultado["paginas"] = paginas
    resultado["paginas_ok"] = all(p["ok"] for p in paginas)

    dash = [p for p in paginas if p["path"] == "/dashboard"]
    resultado["dashboard_ok"] = bool(dash and dash[0]["ok"])
    resultado["dashboard_html_ok"] = bool(dash and dash[0].get("dashboard_html_ok"))

    status_api = http_request(opener, "GET", "/api/whatsapp/status/5", None, limite=100000)
    resultado["status_api"] = {
        "status": status_api.get("status"),
        "ok": status_api.get("ok"),
        "json": status_api.get("json"),
        "body_preview": status_api.get("body_preview")
    }
    resultado["status_api_ok"] = bool(status_api.get("status") == 200 and isinstance(status_api.get("json"), dict))

    resultado["ok"] = bool(
        resultado["login_ok"] and
        resultado["paginas_ok"] and
        resultado["dashboard_ok"] and
        resultado["dashboard_html_ok"] and
        resultado["status_api_ok"]
    )

    return resultado


def coletar_logs(since):
    r = run_cmd(["docker", "compose", "logs", "--since", since, "app"], 80)

    texto = (r.get("stdout") or "") + "\n" + (r.get("stderr") or "")

    linhas = texto.splitlines()
    achados = []
    for idx, linha in enumerate(linhas, start=1):
        low = linha.lower()
        if "error" in low or "exception" in low or "cannot read" in low or "syntaxerror" in low:
            achados.append({
                "linha": idx,
                "texto": redigir(linha)[:500]
            })

    return {
        "principal": r,
        "total_linhas": len(linhas),
        "achados": achados,
        "amostra": redigir("\n".join(linhas[-120:]))[:30000]
    }


def analisar_logs(logs):
    texto = logs.get("amostra", "")

    return {
        "linhas_session_id": texto.lower().count("session id"),
        "linhas_cookie": texto.lower().count("connect.sid") + texto.lower().count("saas_crm_sid"),
        "linhas_email": texto.count("@"),
        "achados": logs.get("achados", [])
    }


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)

    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_25_4_1_INICIO -->"
    fim = "<!-- ETAPA_25_4_1_FIM -->"

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
    runtime = relatorio["runtime"]
    estrutura = relatorio["validacao_estrutura"]
    logs = relatorio["logs_analise"]

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Etapa 25.4.1 - HTML do dashboard corrigido",
        [
            "Data: " + data,
            "",
            "Corrigidos link CSS e links de navegacao do dashboard.",
            "Validacao estrutural OK: " + str(estrutura["ok"]) + ".",
            "Dashboard HTML OK: " + str(runtime["dashboard_html_ok"]) + ".",
            "Links renderizados: " + str(runtime["paginas"][0].get("links")) + ".",
            "Stylesheets renderizados: " + str(runtime["paginas"][0].get("stylesheets")) + ".",
            "Runtime OK: " + str(runtime["ok"]) + ".",
            "Logs Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs cookie: " + str(logs["linhas_cookie"]) + ".",
            "Logs email: " + str(logs["linhas_email"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 25.4.1 - Correcao HTML dashboard",
        [
            "Data: " + data,
            "",
            "Corrigida tag link para /css/style.css.",
            "Corrigidos hrefs para /crm, /admin/painel e /super-admin.",
            "Removidos textos soltos gerados por HTML quebrado."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 25.4.1 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido corrigir apenas views/dashboard.ejs.",
            "Decidido manter dashboard sem Alpine e sem Tailwind CDN.",
            "Decidido validar HTML renderizado com parser para confirmar links e stylesheets."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 25.4.1",
        [
            "Data: " + data,
            "",
            "Validar manualmente o dashboard com Ctrl+F5.",
            "Se aprovado, seguir para auditoria funcional completa.",
            "Refinar futuramente o shell em todas as telas se necessario."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    linhas = []
    linhas.append("# Etapa 25.4.1 - Corrigir HTML do Dashboard")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Dashboard alterado: " + str(relatorio["correcao"]["alterado"]))
    linhas.append("- Validacao estrutural OK: " + str(relatorio["validacao_estrutura"]["ok"]))
    linhas.append("- Restart OK: " + str(relatorio["restart_app"]["ok"]))
    linhas.append("- App pronto: " + str(relatorio["aguardar_app"]["ok"]))
    linhas.append("- Login OK: " + str(relatorio["runtime"]["login_ok"]))
    linhas.append("- Paginas OK: " + str(relatorio["runtime"]["paginas_ok"]))
    linhas.append("- Dashboard HTML OK: " + str(relatorio["runtime"]["dashboard_html_ok"]))
    linhas.append("- Status API OK: " + str(relatorio["runtime"]["status_api_ok"]))
    linhas.append("- Runtime geral OK: " + str(relatorio["runtime"]["ok"]))
    linhas.append("- Logs Session ID: " + str(relatorio["logs_analise"]["linhas_session_id"]))
    linhas.append("- Logs cookie: " + str(relatorio["logs_analise"]["linhas_cookie"]))
    linhas.append("- Logs email: " + str(relatorio["logs_analise"]["linhas_email"]))
    linhas.append("- Achados logs: " + str(len(relatorio["logs_analise"]["achados"])))
    linhas.append("")
    linhas.append("## HTML renderizado do dashboard")
    linhas.append("")
    dash = relatorio["runtime"]["paginas"][0]
    linhas.append("- Links total: " + str(dash.get("links_total")))
    linhas.append("- Links: " + str(dash.get("links")))
    linhas.append("- Stylesheets: " + str(dash.get("stylesheets")))
    linhas.append("- tem_css_link: " + str(dash.get("tem_css_link")))
    linhas.append("- tem_href_crm: " + str(dash.get("tem_href_crm")))
    linhas.append("- tem_href_admin: " + str(dash.get("tem_href_admin")))
    linhas.append("- tem_href_super: " + str(dash.get("tem_href_super")))
    linhas.append("- texto_link_quebrado: " + str(dash.get("texto_link_quebrado")))
    linhas.append("- css_texto_solto: " + str(dash.get("css_texto_solto")))
    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_25_4_1_dashboard_html_" + stamp)

    backup = criar_backup(backup_dir)
    since = logs_since()

    correcao = aplicar_correcao()
    estrutura = validar_estrutura_local()
    restart = restart_app()
    aguardar = aguardar_app()
    runtime = validar_runtime()
    time.sleep(2)

    logs = coletar_logs(since)
    logs_analise = analisar_logs(logs)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "correcao": correcao,
        "validacao_estrutura": estrutura,
        "restart_app": restart,
        "aguardar_app": aguardar,
        "runtime": runtime,
        "logs": logs,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    json_path = REPORTS_DIR / "etapa_25_4_1_corrigir_dashboard_html.json"
    md_path = REPORTS_DIR / "etapa_25_4_1_corrigir_dashboard_html.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 25.4.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Dashboard alterado: " + str(correcao["alterado"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Paginas OK: " + str(runtime["paginas_ok"]))
    print("Dashboard HTML OK: " + str(runtime["dashboard_html_ok"]))
    print("Status API OK: " + str(runtime["status_api_ok"]))
    print("Runtime geral OK: " + str(runtime["ok"]))
    print("Links dashboard: " + str(runtime["paginas"][0].get("links")))
    print("Stylesheets dashboard: " + str(runtime["paginas"][0].get("stylesheets")))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["ok"]:
        print("")
        print("Aviso: Etapa 25.4.1 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
