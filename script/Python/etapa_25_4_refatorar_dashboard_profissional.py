#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 25.4 - Refatorar dashboard principal profissional e responsivo

Objetivo:
- Corrigir a pagina principal que estava misturando layout antigo e novo.
- Recriar views/dashboard.ejs como dashboard limpo e responsivo.
- Remover Alpine/Tailwind CDN do dashboard.
- Remover x-data/appData/initApp/activeTab/currentChat/qrCodeBase64 do dashboard.
- Manter shell seguro, menu lateral e tema claro/escuro.
- Nao alterar CRM, rotas, controllers ou banco.
- Validar /dashboard, /crm, /admin/painel e /super-admin.
- Atualizar documentacao obrigatoria.

Como executar:
sudo ETAPA25_4_LOGIN_EMAIL='admin.cliente.teste@saas.local' ETAPA25_4_LOGIN_PASSWORD='123456' python3 etapa_25_4_refatorar_dashboard_profissional.py

Ou com super admin:
sudo ETAPA25_4_LOGIN_EMAIL='superadmin.teste@saas.local' ETAPA25_4_LOGIN_PASSWORD='123456' python3 etapa_25_4_refatorar_dashboard_profissional.py
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

DASHBOARD_FILE = ROOT / "views" / "dashboard.ejs"
CSS_FILE = ROOT / "public" / "css" / "style.css"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "views/dashboard.ejs",
    "public/css/style.css",
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
    "ETAPA25_4_LOGIN_EMAIL",
    "ETAPA25_3_LOGIN_EMAIL",
    "ETAPA25_2_LOGIN_EMAIL",
    "ETAPA25_1_LOGIN_EMAIL",
    "ETAPA24_CLIENTE_EMAIL",
    "LOGIN_EMAIL",
    "ADMIN_EMAIL",
    "DEFAULT_ADMIN_EMAIL"
]

PASSWORD_KEYS = [
    "ETAPA25_4_LOGIN_PASSWORD",
    "ETAPA25_3_LOGIN_PASSWORD",
    "ETAPA25_2_LOGIN_PASSWORD",
    "ETAPA25_1_LOGIN_PASSWORD",
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
        email = "admin.cliente.teste@saas.local"

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


def css_etapa_25_4():
    return r'''
/* ETAPA25_4_DASHBOARD_PROFISSIONAL_INICIO */
.er25dash-page {
    width: 100%;
    max-width: 1440px;
    margin: 0 auto;
    padding: 24px;
    color: var(--er25safe-text, #0f172a);
}

.er25dash-hero {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--er25safe-border, #e5e7eb);
    background:
        radial-gradient(circle at top left, rgba(185, 28, 28, 0.12), transparent 28rem),
        linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(254, 242, 242, 0.88));
    border-radius: 28px;
    padding: 28px;
    box-shadow: var(--er25safe-shadow, 0 18px 45px rgba(15, 23, 42, 0.10));
}

body.er25safe-dark .er25dash-hero,
html.er25safe-dark .er25dash-hero {
    background:
        radial-gradient(circle at top left, rgba(239, 68, 68, 0.14), transparent 28rem),
        linear-gradient(135deg, rgba(17, 24, 39, 0.98), rgba(15, 23, 42, 0.92));
}

.er25dash-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: 1px solid rgba(185, 28, 28, 0.24);
    color: #b91c1c;
    background: rgba(254, 242, 242, 0.92);
    border-radius: 999px;
    padding: 7px 11px;
    font-size: 12px;
    font-weight: 900;
}

body.er25safe-dark .er25dash-badge,
html.er25safe-dark .er25dash-badge {
    background: rgba(127, 29, 29, 0.22);
    color: #fecaca;
    border-color: rgba(248, 113, 113, 0.28);
}

.er25dash-title {
    margin: 18px 0 8px;
    font-size: clamp(28px, 4vw, 48px);
    line-height: 1.03;
    letter-spacing: -0.05em;
    font-weight: 950;
    color: var(--er25safe-text, #0f172a);
}

.er25dash-subtitle {
    max-width: 760px;
    margin: 0;
    color: var(--er25safe-muted, #64748b);
    font-size: 15px;
    line-height: 1.65;
}

.er25dash-hero-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 22px;
}

.er25dash-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    min-height: 44px;
    padding: 11px 15px;
    border-radius: 14px;
    border: 1px solid var(--er25safe-border, #e5e7eb);
    background: var(--er25safe-card, #ffffff);
    color: var(--er25safe-text, #0f172a);
    text-decoration: none;
    font-weight: 900;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.07);
}

.er25dash-button:hover {
    border-color: rgba(185, 28, 28, 0.35);
    color: #b91c1c;
}

.er25dash-button-primary {
    color: #ffffff;
    border-color: transparent;
    background: linear-gradient(135deg, #b91c1c, #ef4444);
}

.er25dash-button-primary:hover {
    color: #ffffff;
    filter: brightness(1.02);
}

.er25dash-grid {
    display: grid;
    gap: 16px;
    margin-top: 18px;
}

.er25dash-grid-metrics {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

.er25dash-grid-main {
    grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.8fr);
    align-items: start;
}

.er25dash-card {
    border: 1px solid var(--er25safe-border, #e5e7eb);
    background: var(--er25safe-card, #ffffff);
    border-radius: 22px;
    padding: 20px;
    box-shadow: var(--er25safe-shadow, 0 18px 45px rgba(15, 23, 42, 0.10));
    min-width: 0;
}

.er25dash-card-soft {
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.07);
}

.er25dash-metric {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 14px;
}

.er25dash-icon {
    width: 46px;
    height: 46px;
    border-radius: 16px;
    display: grid;
    place-items: center;
    color: #ffffff;
    background: linear-gradient(135deg, #b91c1c, #ef4444);
    box-shadow: 0 14px 28px rgba(239, 68, 68, 0.24);
    flex: 0 0 auto;
}

.er25dash-label {
    color: var(--er25safe-muted, #64748b);
    font-size: 12px;
    font-weight: 850;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.er25dash-value {
    margin: 7px 0 0;
    color: var(--er25safe-text, #0f172a);
    font-size: 26px;
    line-height: 1;
    font-weight: 950;
}

.er25dash-helper {
    margin: 8px 0 0;
    color: var(--er25safe-muted, #64748b);
    font-size: 12px;
    line-height: 1.45;
}

.er25dash-section-title {
    margin: 0;
    color: var(--er25safe-text, #0f172a);
    font-size: 19px;
    font-weight: 950;
    letter-spacing: -0.03em;
}

.er25dash-section-subtitle {
    margin: 5px 0 0;
    color: var(--er25safe-muted, #64748b);
    font-size: 13px;
    line-height: 1.55;
}

.er25dash-actions-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-top: 16px;
}

.er25dash-action-card {
    border: 1px solid var(--er25safe-border, #e5e7eb);
    border-radius: 18px;
    background: rgba(148, 163, 184, 0.08);
    padding: 16px;
    text-decoration: none;
    color: var(--er25safe-text, #0f172a);
    min-height: 112px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.er25dash-action-card:hover {
    border-color: rgba(185, 28, 28, 0.32);
    background: rgba(185, 28, 28, 0.07);
}

.er25dash-action-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}

.er25dash-action-title {
    margin: 0;
    font-weight: 950;
    font-size: 15px;
}

.er25dash-action-desc {
    margin: 10px 0 0;
    color: var(--er25safe-muted, #64748b);
    font-size: 12px;
    line-height: 1.45;
}

.er25dash-status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid var(--er25safe-border, #e5e7eb);
}

.er25dash-status-row:last-child {
    border-bottom: 0;
}

.er25dash-status-name {
    margin: 0;
    font-weight: 900;
    font-size: 13px;
}

.er25dash-status-desc {
    margin: 3px 0 0;
    color: var(--er25safe-muted, #64748b);
    font-size: 12px;
}

.er25dash-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    border-radius: 999px;
    padding: 7px 10px;
    font-size: 11px;
    font-weight: 950;
    border: 1px solid var(--er25safe-border, #e5e7eb);
    background: rgba(148, 163, 184, 0.10);
    color: var(--er25safe-text, #0f172a);
    white-space: nowrap;
}

.er25dash-pill-ok {
    background: rgba(16, 185, 129, 0.12);
    color: #047857;
    border-color: rgba(16, 185, 129, 0.22);
}

.er25dash-pill-warn {
    background: rgba(245, 158, 11, 0.12);
    color: #b45309;
    border-color: rgba(245, 158, 11, 0.22);
}

.er25dash-pill-off {
    background: rgba(239, 68, 68, 0.10);
    color: #b91c1c;
    border-color: rgba(239, 68, 68, 0.22);
}

.er25dash-footer-note {
    margin-top: 18px;
    padding: 14px 16px;
    border: 1px dashed rgba(185, 28, 28, 0.28);
    border-radius: 18px;
    background: rgba(254, 242, 242, 0.62);
    color: var(--er25safe-muted, #64748b);
    font-size: 12px;
    line-height: 1.55;
}

body.er25safe-dark .er25dash-footer-note,
html.er25safe-dark .er25dash-footer-note {
    background: rgba(127, 29, 29, 0.12);
}

@media (max-width: 1180px) {
    .er25dash-grid-metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .er25dash-grid-main {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 720px) {
    .er25dash-page {
        padding: 14px;
    }

    .er25dash-hero {
        border-radius: 22px;
        padding: 20px;
    }

    .er25dash-grid-metrics {
        grid-template-columns: 1fr;
    }

    .er25dash-actions-list {
        grid-template-columns: 1fr;
    }

    .er25dash-status-row {
        align-items: flex-start;
        flex-direction: column;
    }

    .er25dash-button {
        width: 100%;
    }
}
/* ETAPA25_4_DASHBOARD_PROFISSIONAL_FIM */
'''


def dashboard_ejs_limpo():
    return r'''<!DOCTYPE html>
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
'''


def aplicar_correcao():
    resultado = {
        "dashboard": {
            "arquivo": "views/dashboard.ejs",
            "existe_antes": DASHBOARD_FILE.exists(),
            "alterado": False,
            "sha256_antes": sha256(DASHBOARD_FILE) if DASHBOARD_FILE.exists() else None,
            "sha256_depois": None
        },
        "css": {
            "arquivo": "public/css/style.css",
            "existe_antes": CSS_FILE.exists(),
            "alterado": False,
            "sha256_antes": sha256(CSS_FILE) if CSS_FILE.exists() else None,
            "sha256_depois": None
        }
    }

    atual_dashboard = ler(DASHBOARD_FILE) or ""
    novo_dashboard = dashboard_ejs_limpo()

    if atual_dashboard != novo_dashboard:
        gravar(DASHBOARD_FILE, novo_dashboard)
        resultado["dashboard"]["alterado"] = True

    resultado["dashboard"]["sha256_depois"] = sha256(DASHBOARD_FILE)

    css = ler(CSS_FILE) or ""

    if "ETAPA25_4_DASHBOARD_PROFISSIONAL_INICIO" not in css:
        if not css.endswith("\n"):
            css += "\n"
        css += css_etapa_25_4() + "\n"
        gravar(CSS_FILE, css)
        resultado["css"]["alterado"] = True

    resultado["css"]["sha256_depois"] = sha256(CSS_FILE)

    return resultado


def validar_estrutura():
    dash = ler(DASHBOARD_FILE) or ""
    css = ler(CSS_FILE) or ""

    proibidos = [
        "cdn.tailwindcss.com",
        "alpinejs",
        "x-data",
        "appData",
        "initApp",
        "activeTab",
        "currentChat",
        "qrCodeBase64",
        "CRM WhatsApp Enterprise"
    ]

    encontrados = []
    for termo in proibidos:
        if termo in dash:
            encontrados.append(termo)

    resultado = {
        "dashboard_existe": DASHBOARD_FILE.exists(),
        "css_existe": CSS_FILE.exists(),
        "dashboard_tem_marker": "etapa25-4-dashboard-profissional" in dash,
        "dashboard_tem_shell_seguro": "ETAPA25_1_SHELL_SEGURO_INICIO" in dash,
        "dashboard_tem_cards": "er25dash-grid-metrics" in dash,
        "dashboard_tem_status_fetch": "/api/whatsapp/status/" in dash,
        "css_tem_marker": "ETAPA25_4_DASHBOARD_PROFISSIONAL_INICIO" in css,
        "css_tem_responsivo": "@media (max-width: 720px)" in css,
        "proibidos_encontrados": encontrados,
        "sem_mistura_antiga": len(encontrados) == 0,
        "ok": False
    }

    resultado["ok"] = bool(
        resultado["dashboard_existe"] and
        resultado["css_existe"] and
        resultado["dashboard_tem_marker"] and
        resultado["dashboard_tem_shell_seguro"] and
        resultado["dashboard_tem_cards"] and
        resultado["dashboard_tem_status_fetch"] and
        resultado["css_tem_marker"] and
        resultado["css_tem_responsivo"] and
        resultado["sem_mistura_antiga"]
    )

    return resultado


def node_check():
    checks = []
    for file_name in ["routes/api.js", "server.js"]:
        if (ROOT / file_name).exists():
            checks.append(run_cmd(["node", "--check", file_name], 40))

    return {
        "checks": checks,
        "ok": all(c.get("ok") for c in checks) if checks else True
    }


def restart_app():
    valor = os.environ.get("ETAPA25_4_RESTART_APP", "true").strip().lower()

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


def http_request(opener, metodo, path, data_obj=None, timeout=20, limite=800000):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "metodo": metodo,
        "ok": False,
        "status": None,
        "erro": None,
        "content_type": "",
        "body_preview": "",
        "body_limited": "",
        "json": None
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-25-4-dashboard-profissional/1.0"
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
            resultado["body_preview"] = redigir(texto[:1600])
            resultado["body_limited"] = redigir(texto)

            try:
                resultado["json"] = json.loads(texto)
            except Exception:
                resultado["json"] = None
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
        resultado["body_preview"] = redigir(texto[:1600])
        resultado["body_limited"] = redigir(texto)

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

    resultado = {
        "login_ok": False,
        "cookies": [],
        "paginas": [],
        "dashboard_ok": False,
        "dashboard_limpo": False,
        "status_api_ok": False,
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
        r = http_request(opener, "GET", page, None, limite=800000)
        body = r.get("body_limited") or ""

        item = {
            "path": page,
            "status": r.get("status"),
            "ok": r.get("status") == 200,
            "content_type": r.get("content_type")
        }

        if page == "/dashboard":
            item["tem_dashboard_novo"] = "etapa25-4-dashboard-profissional" in body
            item["tem_shell_seguro"] = "ETAPA25_1_SHELL_SEGURO_INICIO" in body
            item["tem_css"] = "/css/style.css" in body
            item["sem_tailwind_cdn"] = "cdn.tailwindcss.com" not in body
            item["sem_alpine"] = "alpinejs" not in body and "x-data" not in body
            item["sem_crm_antigo"] = "CRM WhatsApp Enterprise" not in body and "appData" not in body
            item["dashboard_limpo"] = bool(
                item["ok"] and
                item["tem_dashboard_novo"] and
                item["tem_shell_seguro"] and
                item["tem_css"] and
                item["sem_tailwind_cdn"] and
                item["sem_alpine"] and
                item["sem_crm_antigo"]
            )

        resultado["paginas"].append(item)

    dash = [p for p in resultado["paginas"] if p["path"] == "/dashboard"]
    resultado["dashboard_ok"] = bool(dash and dash[0]["ok"])
    resultado["dashboard_limpo"] = bool(dash and dash[0].get("dashboard_limpo"))

    status_api = http_request(opener, "GET", "/api/whatsapp/status/5", None, limite=100000)
    status_json = status_api.get("json") or {}

    resultado["status_api"] = {
        "status": status_api.get("status"),
        "ok": status_api.get("ok"),
        "json": status_json,
        "body_preview": status_api.get("body_preview")
    }

    resultado["status_api_ok"] = bool(
        status_api.get("status") == 200 and
        isinstance(status_json, dict) and
        status_json.get("success") is True
    )

    resultado["paginas_ok"] = all(p["ok"] for p in resultado["paginas"])

    resultado["ok"] = bool(
        resultado["login_ok"] and
        resultado["paginas_ok"] and
        resultado["dashboard_ok"] and
        resultado["dashboard_limpo"] and
        resultado["status_api_ok"]
    )

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
    erro_status = 0

    for idx, linha in enumerate(str(texto or "").splitlines(), start=1):
        low = linha.lower()

        if "session id" in low:
            session_id += 1

        if "saas_crm_sid" in low or "connect.sid" in low or "header cookie" in low:
            cookie += 1

        if "cannot read properties of undefined" in low and "sessions" in low:
            erro_status += 1
            achados.append({
                "linha": idx,
                "trecho": redigir(linha.strip())[:500]
            })

        tokens = linha.replace("(", " ").replace(")", " ").replace(",", " ").split()
        for token in tokens:
            if parece_email(token):
                email += 1
                break

        if "syntaxerror" in low or "exception" in low or "econnrefused" in low:
            achados.append({
                "linha": idx,
                "trecho": redigir(linha.strip())[:500]
            })

    return {
        "total_linhas": len(str(texto or "").splitlines()),
        "linhas_session_id": session_id,
        "linhas_cookie": cookie,
        "linhas_email": email,
        "erro_status_whatsapp_sessions": erro_status,
        "achados": achados,
        "amostra": redigir("\n".join(str(texto or "").splitlines()[-120:]))[:30000]
    }


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)

    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_25_4_INICIO -->"
    fim = "<!-- ETAPA_25_4_FIM -->"

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
        "Etapa 25.4 - Dashboard profissional e responsivo",
        [
            "Data: " + data,
            "",
            "O dashboard principal foi refatorado para remover mistura entre layout antigo e novo.",
            "Dashboard limpo em runtime: " + str(runtime["dashboard_limpo"]) + ".",
            "Paginas OK: " + str(runtime["paginas_ok"]) + ".",
            "Status API OK: " + str(runtime["status_api_ok"]) + ".",
            "Validacao estrutural OK: " + str(estrutura["ok"]) + ".",
            "Termos antigos encontrados: " + str(estrutura["proibidos_encontrados"]) + ".",
            "Logs Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs cookie: " + str(logs["linhas_cookie"]) + ".",
            "Logs email: " + str(logs["linhas_email"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 25.4 - Dashboard principal refatorado",
        [
            "Data: " + data,
            "",
            "Recriado views/dashboard.ejs como painel principal limpo e responsivo.",
            "Removido dashboard antigo baseado em Alpine/Tailwind CDN.",
            "Separado dashboard da tela de atendimento CRM.",
            "Adicionados cards, atalhos e status WhatsApp seguro."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 25.4 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido separar a pagina principal do CRM para evitar mistura visual e quebra de scripts.",
            "Decidido manter o CRM completo apenas na rota /crm.",
            "Decidido nao usar Alpine nem Tailwind CDN no novo dashboard.",
            "Decidido manter a internalizacao completa de Tailwind/Alpine como pendencia futura para as demais telas."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 25.4",
        [
            "Data: " + data,
            "",
            "Validar manualmente /dashboard em desktop, notebook, tablet e celular.",
            "Executar auditoria funcional completa na Etapa 26.",
            "Planejar etapa futura para remover CDN de Tailwind/Alpine das demais telas.",
            "Planejar refinamento visual do /crm sem misturar com dashboard."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    linhas = []
    linhas.append("# Etapa 25.4 - Dashboard profissional e responsivo")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Dashboard alterado: " + str(relatorio["aplicacao"]["dashboard"]["alterado"]))
    linhas.append("- CSS alterado: " + str(relatorio["aplicacao"]["css"]["alterado"]))
    linhas.append("- Validacao estrutural OK: " + str(relatorio["validacao_estrutura"]["ok"]))
    linhas.append("- Termos antigos encontrados: " + str(relatorio["validacao_estrutura"]["proibidos_encontrados"]))
    linhas.append("- Node checks OK: " + str(relatorio["node_check"]["ok"]))
    linhas.append("- Restart OK: " + str(relatorio["restart_app"]["ok"]))
    linhas.append("- App pronto: " + str(relatorio["aguardar_app"]["ok"]))
    linhas.append("- Login OK: " + str(relatorio["runtime"]["login_ok"]))
    linhas.append("- Paginas OK: " + str(relatorio["runtime"]["paginas_ok"]))
    linhas.append("- Dashboard limpo: " + str(relatorio["runtime"]["dashboard_limpo"]))
    linhas.append("- Status API OK: " + str(relatorio["runtime"]["status_api_ok"]))
    linhas.append("- Runtime geral OK: " + str(relatorio["runtime"]["ok"]))
    linhas.append("- Erro status WhatsApp logs: " + str(relatorio["logs_analise"]["erro_status_whatsapp_sessions"]))
    linhas.append("- Logs Session ID: " + str(relatorio["logs_analise"]["linhas_session_id"]))
    linhas.append("- Logs cookie: " + str(relatorio["logs_analise"]["linhas_cookie"]))
    linhas.append("- Logs email: " + str(relatorio["logs_analise"]["linhas_email"]))
    linhas.append("- Achados logs: " + str(len(relatorio["logs_analise"]["achados"])))
    linhas.append("")
    linhas.append("## Runtime por pagina")
    linhas.append("")

    for item in relatorio["runtime"]["paginas"]:
        if item["path"] == "/dashboard":
            linhas.append(
                "- /dashboard: status " + str(item["status"]) +
                ", novo " + str(item.get("tem_dashboard_novo")) +
                ", sem_tailwind_cdn " + str(item.get("sem_tailwind_cdn")) +
                ", sem_alpine " + str(item.get("sem_alpine")) +
                ", sem_crm_antigo " + str(item.get("sem_crm_antigo"))
            )
        else:
            linhas.append("- " + item["path"] + ": status " + str(item["status"]) + ", ok " + str(item["ok"]))

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_25_4_dashboard_profissional_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_25_4_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = logs_since()
    aplicacao = aplicar_correcao()
    estrutura = validar_estrutura()
    node = node_check()
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
        "node_check": node,
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
    manifesto_depois_path = REPORTS_DIR / "etapa_25_4_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_25_4_refatorar_dashboard_profissional.json"
    md_path = REPORTS_DIR / "etapa_25_4_refatorar_dashboard_profissional.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 25.4 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Dashboard alterado: " + str(aplicacao["dashboard"]["alterado"]))
    print("CSS alterado: " + str(aplicacao["css"]["alterado"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Termos antigos encontrados: " + str(estrutura["proibidos_encontrados"]))
    print("Node checks OK: " + str(node["ok"]))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Paginas OK: " + str(runtime["paginas_ok"]))
    print("Dashboard limpo: " + str(runtime["dashboard_limpo"]))
    print("Status API OK: " + str(runtime["status_api_ok"]))
    print("Runtime geral OK: " + str(runtime["ok"]))
    print("Erro status WhatsApp logs: " + str(logs_analise["erro_status_whatsapp_sessions"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not runtime["ok"]:
        print("")
        print("Aviso: Etapa 25.4 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
