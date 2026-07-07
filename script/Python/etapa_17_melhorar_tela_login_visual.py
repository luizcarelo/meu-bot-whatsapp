#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 17 - Melhorar visual da tela de login

Objetivo:
- Criar backup antes da alteracao.
- Gerar manifesto antes e depois.
- Alterar somente views/login.ejs.
- Melhorar visual da tela de login.
- Manter login com email e senha.
- Manter endpoint /api/auth/login.
- Manter textos em PT-BR.
- Nao alterar backend.
- Nao alterar banco.
- Nao reiniciar container.
- Validar estrutura da view.
- Validar GET /login.
- Validar login real e dashboard quando credenciais forem fornecidas.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar:
sudo ETAPA17_LOGIN_EMAIL='admin@saas.com' ETAPA17_LOGIN_PASSWORD='123456' python3 etapa_17_melhorar_tela_login_visual.py
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

LOGIN_VIEW = ROOT / "views" / "login.ejs"

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
    "views/login.ejs",
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
            "stdout": redigir(proc.stdout.strip())[:16000],
            "stderr": redigir(proc.stderr.strip())[:16000],
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


def conteudo_login_ejs():
    return """<!DOCTYPE html>
<html lang="pt-BR" class="h-full bg-slate-950">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Acesso Seguro</title>

    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

    <style>
        html {
            -webkit-text-size-adjust: 100%;
            text-size-adjust: 100%;
        }

        body {
            font-family: Inter, Arial, sans-serif;
        }

        [x-cloak] {
            display: none !important;
        }

        .login-bg {
            background:
                radial-gradient(circle at top left, rgba(239, 68, 68, 0.22), transparent 32rem),
                radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.16), transparent 30rem),
                linear-gradient(135deg, #0f172a 0%, #111827 48%, #1f2937 100%);
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.94);
            backdrop-filter: blur(18px);
            border: 1px solid rgba(255, 255, 255, 0.72);
            box-shadow: 0 24px 70px rgba(15, 23, 42, 0.42);
        }

        .brand-mark {
            background: linear-gradient(135deg, #b91c1c 0%, #ef4444 52%, #f97316 100%);
            box-shadow: 0 16px 32px rgba(239, 68, 68, 0.34);
        }

        .field-focus:focus {
            border-color: #dc2626;
            box-shadow: 0 0 0 4px rgba(220, 38, 38, 0.13);
        }

        .btn-login {
            background: linear-gradient(135deg, #991b1b 0%, #dc2626 50%, #ef4444 100%);
            box-shadow: 0 16px 28px rgba(220, 38, 38, 0.28);
        }

        .btn-login:hover {
            transform: translateY(-1px);
            box-shadow: 0 20px 34px rgba(220, 38, 38, 0.34);
        }

        .soft-grid {
            background-image:
                linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px);
            background-size: 42px 42px;
        }
    </style>
</head>
<body class="h-full login-bg">
    <main class="min-h-screen relative overflow-hidden soft-grid">
        <section class="relative z-10 min-h-screen flex items-center justify-center px-5 py-10">
            <div class="w-full max-w-6xl grid lg:grid-cols-2 gap-8 items-center">

                <div class="hidden lg:block text-white">
                    <div class="inline-flex items-center gap-3 rounded-full bg-white/10 border border-white/15 px-4 py-2 text-sm text-white/85 mb-8">
                        <span class="h-2 w-2 rounded-full bg-emerald-400"></span>
                        Ambiente seguro de atendimento e gestão
                    </div>

                    <h1 class="text-5xl font-black tracking-tight leading-tight mb-6">
                        Centralize sua operação em uma plataforma moderna.
                    </h1>

                    <p class="text-lg text-slate-200 leading-relaxed max-w-xl mb-8">
                        Acesse seus atendimentos, painel administrativo, contatos e indicadores com uma experiência mais limpa e profissional.
                    </p>

                    <div class="grid grid-cols-3 gap-4 max-w-xl">
                        <div class="rounded-2xl bg-white/10 border border-white/15 p-4">
                            <div class="text-2xl mb-2"><i class="fa-solid fa-lock"></i></div>
                            <div class="font-bold">Seguro</div>
                            <div class="text-sm text-slate-300">Sessão protegida</div>
                        </div>
                        <div class="rounded-2xl bg-white/10 border border-white/15 p-4">
                            <div class="text-2xl mb-2"><i class="fa-solid fa-gauge-high"></i></div>
                            <div class="font-bold">Rápido</div>
                            <div class="text-sm text-slate-300">Acesso direto</div>
                        </div>
                        <div class="rounded-2xl bg-white/10 border border-white/15 p-4">
                            <div class="text-2xl mb-2"><i class="fa-solid fa-building"></i></div>
                            <div class="font-bold">Multiempresa</div>
                            <div class="text-sm text-slate-300">Gestão centralizada</div>
                        </div>
                    </div>
                </div>

                <div class="w-full max-w-md mx-auto">
                    <div class="glass-card rounded-3xl p-8 sm:p-10">
                        <div class="flex items-center gap-4 mb-8">
                            <div class="brand-mark h-14 w-14 rounded-2xl flex items-center justify-center text-white text-2xl">
                                <i class="fa-solid fa-comments"></i>
                            </div>
                            <div>
                                <h2 class="text-2xl font-black text-slate-900">Acesso Seguro</h2>
                                <p class="text-sm text-slate-500">Entre para continuar no painel</p>
                            </div>
                        </div>

                        <% if (typeof error !== 'undefined' && error) { %>
                            <div class="mb-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-red-700 text-sm flex gap-3">
                                <i class="fa-solid fa-triangle-exclamation mt-0.5"></i>
                                <span><%= error %></span>
                            </div>
                        <% } %>

                        <div id="login-alert" class="hidden mb-5 rounded-2xl border px-4 py-3 text-sm"></div>

                        <form id="loginForm" class="space-y-5" autocomplete="on">
                            <div>
                                <label for="email" class="block text-sm font-bold text-slate-700 mb-2">
                                    E-mail
                                </label>
                                <div class="relative">
                                    <span class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                                        <i class="fa-solid fa-envelope"></i>
                                    </span>
                                    <input
                                        id="email"
                                        name="email"
                                        type="email"
                                        required
                                        autocomplete="email"
                                        class="field-focus w-full rounded-2xl border border-slate-200 bg-white py-3.5 pl-11 pr-4 text-slate-900 outline-none transition"
                                        placeholder="seuemail@empresa.com">
                                </div>
                            </div>

                            <div>
                                <div class="flex items-center justify-between mb-2">
                                    <label for="senha" class="block text-sm font-bold text-slate-700">
                                        Senha
                                    </label>
                                    <span class="text-xs text-slate-400">Campo obrigatório</span>
                                </div>
                                <div class="relative">
                                    <span class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                                        <i class="fa-solid fa-key"></i>
                                    </span>
                                    <input
                                        id="senha"
                                        name="senha"
                                        type="password"
                                        required
                                        autocomplete="current-password"
                                        class="field-focus w-full rounded-2xl border border-slate-200 bg-white py-3.5 pl-11 pr-12 text-slate-900 outline-none transition"
                                        placeholder="Digite sua senha">
                                    <button
                                        type="button"
                                        id="toggleSenha"
                                        class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                                        aria-label="Mostrar ou ocultar senha">
                                        <i class="fa-solid fa-eye"></i>
                                    </button>
                                </div>
                            </div>

                            <button
                                id="submitBtn"
                                type="submit"
                                class="btn-login w-full rounded-2xl py-3.5 px-4 font-black text-white transition duration-150 flex items-center justify-center gap-2">
                                <span id="submitIcon"><i class="fa-solid fa-right-to-bracket"></i></span>
                                <span id="submitText">Entrar no painel</span>
                            </button>
                        </form>

                        <div class="mt-7 border-t border-slate-200 pt-5">
                            <div class="flex items-center justify-between text-xs text-slate-500">
                                <span>Conexão protegida</span>
                                <span class="inline-flex items-center gap-1">
                                    <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
                                    Sistema online
                                </span>
                            </div>
                        </div>
                    </div>

                    <p class="text-center text-xs text-white/60 mt-6">
                        Use apenas credenciais autorizadas. Todos os acessos podem ser auditados.
                    </p>
                </div>
            </div>
        </section>
    </main>

    <script>
        const form = document.getElementById('loginForm');
        const alertBox = document.getElementById('login-alert');
        const submitBtn = document.getElementById('submitBtn');
        const submitText = document.getElementById('submitText');
        const submitIcon = document.getElementById('submitIcon');
        const senhaInput = document.getElementById('senha');
        const toggleSenha = document.getElementById('toggleSenha');

        function mostrarAlerta(tipo, mensagem) {
            alertBox.className = 'mb-5 rounded-2xl border px-4 py-3 text-sm';

            if (tipo === 'erro') {
                alertBox.className += ' border-red-200 bg-red-50 text-red-700';
            } else {
                alertBox.className += ' border-emerald-200 bg-emerald-50 text-emerald-700';
            }

            alertBox.textContent = mensagem;
            alertBox.classList.remove('hidden');
        }

        function setCarregando(ativo) {
            submitBtn.disabled = ativo;

            if (ativo) {
                submitBtn.classList.add('opacity-80', 'cursor-not-allowed');
                submitIcon.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
                submitText.textContent = 'Validando acesso...';
            } else {
                submitBtn.classList.remove('opacity-80', 'cursor-not-allowed');
                submitIcon.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i>';
                submitText.textContent = 'Entrar no painel';
            }
        }

        toggleSenha.addEventListener('click', function () {
            const tipoAtual = senhaInput.getAttribute('type');
            const novoTipo = tipoAtual === 'password' ? 'text' : 'password';
            senhaInput.setAttribute('type', novoTipo);
            toggleSenha.innerHTML = novoTipo === 'password'
                ? '<i class="fa-solid fa-eye"></i>'
                : '<i class="fa-solid fa-eye-slash"></i>';
        });

        form.addEventListener('submit', async function (event) {
            event.preventDefault();

            alertBox.classList.add('hidden');

            const email = document.getElementById('email').value.trim();
            const senha = document.getElementById('senha').value;

            if (!email || !senha) {
                mostrarAlerta('erro', 'Informe e-mail e senha para continuar.');
                return;
            }

            setCarregando(true);

            try {
                const resposta = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        email: email,
                        senha: senha
                    })
                });

                const dados = await resposta.json().catch(function () {
                    return {};
                });

                if (!resposta.ok || !dados.success) {
                    mostrarAlerta('erro', dados.message || 'Não foi possível realizar o login.');
                    setCarregando(false);
                    return;
                }

                mostrarAlerta('sucesso', 'Login realizado com sucesso. Redirecionando...');
                window.location.href = dados.redirectUrl || '/dashboard';
            } catch (erro) {
                mostrarAlerta('erro', 'Erro de conexão. Verifique o servidor e tente novamente.');
                setCarregando(false);
            }
        });
    </script>
</body>
</html>
"""


def aplicar_melhoria_login():
    resultado = {
        "arquivo": "views/login.ejs",
        "existe_antes": LOGIN_VIEW.exists(),
        "alterado": False,
        "sha256_antes": sha256_arquivo(LOGIN_VIEW) if LOGIN_VIEW.exists() else None,
        "sha256_depois": None
    }

    atual = ler_texto(LOGIN_VIEW)
    novo = conteudo_login_ejs()

    if atual != novo:
        gravar_texto(LOGIN_VIEW, novo)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256_arquivo(LOGIN_VIEW)
    return resultado


def validar_estrutura_login():
    texto = ler_texto(LOGIN_VIEW)

    resultado = {
        "arquivo_existe": LOGIN_VIEW.exists(),
        "tem_input_email": False,
        "tem_input_senha": False,
        "tem_api_auth_login": False,
        "usa_payload_senha": False,
        "usa_payload_password": False,
        "tem_pt_br": False,
        "tem_estado_carregando": False,
        "tem_toggle_senha": False,
        "ok": False
    }

    if texto is None:
        resultado["erro"] = "views/login.ejs ausente ou ilegivel"
        return resultado

    lower = texto.lower()

    resultado["tem_input_email"] = 'name="email"' in lower or "name='email'" in lower
    resultado["tem_input_senha"] = 'name="senha"' in lower or "name='senha'" in lower
    resultado["tem_api_auth_login"] = "/api/auth/login" in texto
    resultado["usa_payload_senha"] = "senha:" in texto or '"senha"' in texto
    resultado["usa_payload_password"] = "password:" in texto or '"password"' in texto
    resultado["tem_pt_br"] = "Entrar no painel" in texto and "Senha" in texto
    resultado["tem_estado_carregando"] = "Validando acesso" in texto
    resultado["tem_toggle_senha"] = "toggleSenha" in texto

    resultado["ok"] = bool(
        resultado["arquivo_existe"] and
        resultado["tem_input_email"] and
        resultado["tem_input_senha"] and
        resultado["tem_api_auth_login"] and
        resultado["usa_payload_senha"] and
        resultado["tem_pt_br"] and
        resultado["tem_estado_carregando"] and
        resultado["tem_toggle_senha"]
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
        "content_type": "",
        "redirect_url": None
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-17-login-visual/1.0"
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


def validar_runtime():
    cred = obter_credenciais()

    resultado = {
        "executado": False,
        "email_configurado": cred["email_configurado"],
        "senha_configurada": cred["senha_configurada"],
        "login_page_ok": False,
        "login_ok": False,
        "dashboard_ok": False,
        "cookies": [],
        "login_page": None,
        "login": None,
        "dashboard": None
    }

    opener, jar = criar_opener()

    login_page = http_request(opener, "GET", "/login")
    resultado["login_page"] = login_page
    body_login_page = (login_page.get("body_preview") or "").lower()

    resultado["login_page_ok"] = bool(
        login_page.get("status") == 200 and
        "acesso seguro" in body_login_page and
        "entrar no painel" in body_login_page
    )

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

        if "@" in linha and "." in linha:
            email += 1

        if "error" in low or "exception" in low or "syntaxerror" in low or "database" in low:
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

    marcador_inicio = "<!-- ETAPA_17_INICIO -->"
    marcador_fim = "<!-- ETAPA_17_FIM -->"

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
    melhoria = relatorio["melhoria_login"]
    estrutura = relatorio["validacao_estrutura"]
    runtime = relatorio["validacao_runtime"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 17 - Melhoria visual da tela de login",
        [
            "Data: " + data,
            "",
            "Foi aplicada melhoria visual controlada em views/login.ejs.",
            "Arquivo alterado: " + str(melhoria["alterado"]) + ".",
            "Validacao estrutural OK: " + str(estrutura["ok"]) + ".",
            "Pagina de login OK: " + str(runtime["login_page_ok"]) + ".",
            "Login OK: " + str(runtime["login_ok"]) + ".",
            "Dashboard OK: " + str(runtime["dashboard_ok"]) + ".",
            "Nenhuma regra de backend ou banco foi alterada."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 17 - Login visual melhorado",
        [
            "Data: " + data,
            "",
            "Melhorado layout da tela de login.",
            "Mantido payload email e senha para /api/auth/login.",
            "Adicionado estado visual de carregamento.",
            "Adicionado botao para mostrar ou ocultar senha.",
            "Validado login real e dashboard quando credenciais foram fornecidas.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 17 - Decisoes tecnicas frontend",
        [
            "Data: " + data,
            "",
            "Decidido melhorar apenas views/login.ejs nesta etapa.",
            "Decidido nao remover CDNs ainda para reduzir risco.",
            "Decidido manter endpoint /api/auth/login.",
            "Decidido manter campo senha no payload.",
            "Decidido tratar dashboard em etapa posterior."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 17",
        [
            "Data: " + data,
            "",
            "Validar visual da tela de login manualmente no navegador.",
            "Planejar melhoria controlada do dashboard.",
            "Planejar internalizacao de Alpine, FontAwesome e Tailwind em etapas separadas.",
            "Mapear scripts inline antes de CSP forte.",
            "Revisar assets locais ausentes apontados na Etapa 16."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    melhoria = relatorio["melhoria_login"]
    estrutura = relatorio["validacao_estrutura"]
    runtime = relatorio["validacao_runtime"]
    logs = relatorio["logs_analise"]

    linhas = []

    linhas.append("# Etapa 17 - Melhorar visual da tela de login")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- views/login.ejs alterado: " + str(melhoria["alterado"]))
    linhas.append("- Validacao estrutural OK: " + str(estrutura["ok"]))
    linhas.append("- Pagina de login OK: " + str(runtime["login_page_ok"]))
    linhas.append("- Login OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
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
    linhas.append("- Pagina login OK: " + str(runtime["login_page_ok"]))
    linhas.append("- Login OK: " + str(runtime["login_ok"]))
    linhas.append("- Dashboard OK: " + str(runtime["dashboard_ok"]))
    linhas.append("- Cookies recebidos: " + str(len(runtime["cookies"])))

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
    linhas.append("- Somente views/login.ejs foi alterado.")
    linhas.append("- Nenhum backend foi alterado.")
    linhas.append("- Nenhum banco foi alterado.")
    linhas.append("- Nenhum container foi reiniciado.")
    linhas.append("- CDNs foram mantidas nesta etapa para reduzir risco.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Validar visual manualmente no navegador e depois planejar melhoria do dashboard.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_17_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_17_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = agora_logs_since()
    melhoria = aplicar_melhoria_login()
    estrutura = validar_estrutura_login()
    runtime = validar_runtime()
    time.sleep(2)

    logs_coleta = coletar_logs_novos(since)
    logs_analise = analisar_logs_texto(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "melhoria_login": melhoria,
        "validacao_estrutura": estrutura,
        "logs_since": since,
        "validacao_runtime": runtime,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_17_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_17_melhorar_tela_login_visual.json"
    md_path = REPORTS_DIR / "etapa_17_melhorar_tela_login_visual.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 17 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("views/login.ejs alterado: " + str(melhoria["alterado"]))
    print("Validacao estrutural OK: " + str(estrutura["ok"]))
    print("Pagina login OK: " + str(runtime["login_page_ok"]))
    print("Login OK: " + str(runtime["login_ok"]))
    print("Dashboard OK: " + str(runtime["dashboard_ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not estrutura["ok"]:
        print("")
        print("Aviso: validacao estrutural falhou. Consulte o relatorio.")

    if not runtime["login_page_ok"]:
        print("")
        print("Aviso: pagina de login nao validou em runtime.")

    if runtime["email_configurado"] and runtime["senha_configurada"]:
        if not runtime["login_ok"] or not runtime["dashboard_ok"]:
            print("")
            print("Aviso: login ou dashboard nao validaram. Consulte o relatorio.")


if __name__ == "__main__":
    main()
