#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Diagnostico do Dashboard Frontend

Objetivo:
- Nao alterar arquivos do projeto.
- Verificar por que /dashboard nao abre corretamente.
- Comparar arquivo local e arquivo dentro do container.
- Buscar mistura de layout antigo e novo.
- Buscar HTML invalido ou links quebrados.
- Testar rotas principais autenticadas.
- Testar API de status WhatsApp.
- Coletar logs recentes.
- Gerar relatorios em reports/.

Como executar:
sudo DIAG_LOGIN_EMAIL='admin.cliente.teste@saas.local' DIAG_LOGIN_PASSWORD='123456' python3 diagnosticar_dashboard_frontend.py

Ou com Super Admin:
sudo DIAG_LOGIN_EMAIL='superadmin.teste@saas.local' DIAG_LOGIN_PASSWORD='123456' python3 diagnosticar_dashboard_frontend.py
"""

import os
import re
import json
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

BASE_URL = "http://127.0.0.1:50010"
LOGIN_API = "/api/auth/login"

ARQUIVOS = [
    "views/dashboard.ejs",
    "views/crm.ejs",
    "views/admin-panel.ejs",
    "views/super-admin.ejs",
    "public/css/style.css",
    "routes/api.js",
    "server.js"
]

PAGES = [
    "/dashboard",
    "/crm",
    "/admin/painel",
    "/super-admin"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)


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


def salvar_json(path, dados):
    gravar(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def sha256_path(path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p

    if not p.exists():
        return None

    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


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
            "stdout": proc.stdout.strip()[:60000],
            "stderr": proc.stderr.strip()[:60000],
            "ok": proc.returncode == 0
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "ok": False
        }


def credenciais():
    email = os.environ.get("DIAG_LOGIN_EMAIL", "").strip()
    senha = os.environ.get("DIAG_LOGIN_PASSWORD", "").strip()

    if not email:
        email = "admin.cliente.teste@saas.local"

    if not senha:
        senha = "123456"

    return {
        "email": email,
        "senha": senha
    }


def redigir(texto):
    if texto is None:
        return texto

    out = str(texto)
    c = credenciais()

    if c["email"]:
        out = out.replace(c["email"], "<EMAIL_LOGIN>")

    if c["senha"]:
        out = out.replace(c["senha"], "<SENHA_LOGIN>")

    return out


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


def http_request(opener, metodo, path, data_obj=None, timeout=20, limite=1200000):
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
        "User-Agent": "diagnostico-dashboard-frontend/1.0"
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
            resultado["body_preview"] = redigir(texto[:3000])

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
        resultado["erro"] = str(exc)
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
        resultado["body"] = texto
        resultado["body_preview"] = redigir(texto[:3000])

        try:
            resultado["json"] = json.loads(texto)
        except Exception:
            resultado["json"] = None
    except URLError as exc:
        resultado["erro"] = str(exc.reason)
    except Exception as exc:
        resultado["erro"] = str(exc)

    return resultado


class SimpleHTMLInspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = {}
        self.links = []
        self.scripts = []
        self.stylesheets = []
        self.body_attrs = {}
        self.title = ""
        self.in_title = False
        self.errors = []

    def handle_starttag(self, tag, attrs):
        self.tags[tag] = self.tags.get(tag, 0) + 1
        attrs_dict = dict(attrs)

        if tag == "body":
            self.body_attrs = attrs_dict

        if tag == "a":
            self.links.append(attrs_dict.get("href", ""))

        if tag == "script":
            self.scripts.append(attrs_dict.get("src", ""))

        if tag == "link":
            href = attrs_dict.get("href", "")
            rel_attr = attrs_dict.get("rel", "")
            if href or rel_attr:
                self.stylesheets.append({
                    "href": href,
                    "rel": rel_attr
                })

        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def html_inspect(html):
    parser = SimpleHTMLInspector()
    try:
        parser.feed(html)
    except Exception as exc:
        parser.errors.append(str(exc))

    links_vazios = []
    links_suspeitos = []

    for href in parser.links:
        if href is None or href == "":
            links_vazios.append(href)
        elif href.startswith("http://127.0.0.1") or href.startswith("http://localhost"):
            links_suspeitos.append(href)
        elif href.startswith("<") or href.startswith("&lt;"):
            links_suspeitos.append(href)
        elif href in ["#", "javascript:void(0)"]:
            pass

    return {
        "title": parser.title.strip(),
        "tags": parser.tags,
        "body_attrs": parser.body_attrs,
        "scripts": parser.scripts,
        "stylesheets": parser.stylesheets,
        "links_total": len(parser.links),
        "links_sample": parser.links[:40],
        "links_vazios": links_vazios,
        "links_suspeitos": links_suspeitos,
        "parse_errors": parser.errors
    }


def procurar_linhas(texto, termos, contexto=2):
    if texto is None:
        return []

    linhas = texto.splitlines()
    achados = []

    for idx, linha in enumerate(linhas, start=1):
        low = linha.lower()
        for termo in termos:
            if termo.lower() in low:
                ini = max(1, idx - contexto)
                fim = min(len(linhas), idx + contexto)
                bloco = []
                for n in range(ini, fim + 1):
                    bloco.append({
                        "linha": n,
                        "texto": linhas[n - 1][:500]
                    })

                achados.append({
                    "termo": termo,
                    "linha": idx,
                    "contexto": bloco
                })
                break

    return achados


def analisar_dashboard_local():
    texto = ler("views/dashboard.ejs")

    termos = [
        "ETAPA25_4",
        "ETAPA25_1",
        "er25dash",
        "er25safe",
        "cdn.tailwindcss.com",
        "alpinejs",
        "x-data",
        "appData",
        "initApp",
        "activeTab",
        "currentChat",
        "qrCodeBase64",
        "CRM WhatsApp Enterprise",
        "/crm",
        "/admin/painel",
        "/super-admin",
        "api/whatsapp/status"
    ]

    return {
        "existe": texto is not None,
        "sha256": sha256_path("views/dashboard.ejs"),
        "tamanho": len(texto or ""),
        "contagens": {t: (texto or "").count(t) for t in termos},
        "linhas_relevantes": procurar_linhas(texto, termos, 2)
    }


def analisar_css_local():
    texto = ler("public/css/style.css")
    termos = [
        "ETAPA25_1_SHELL_SEGURO",
        "ETAPA25_4_DASHBOARD_PROFISSIONAL",
        "er25safe-sidebar",
        "er25safe-topbar",
        "er25dash-page",
        "@media",
        "max-width: 720px",
        "position: fixed",
        "z-index"
    ]

    return {
        "existe": texto is not None,
        "sha256": sha256_path("public/css/style.css"),
        "tamanho": len(texto or ""),
        "contagens": {t: (texto or "").count(t) for t in termos},
        "linhas_relevantes": procurar_linhas(texto, termos, 2)
    }


def comparar_container():
    resultados = {}

    for arq in ARQUIVOS:
        cmd = [
            "docker", "compose", "exec", "-T", "app",
            "sh", "-lc",
            "if [ -f /usr/src/app/" + arq + " ]; then sha256sum /usr/src/app/" + arq + " && wc -c /usr/src/app/" + arq + "; else echo AUSENTE; fi"
        ]
        resultados[arq] = {
            "local_sha256": sha256_path(arq),
            "container": run_cmd(cmd, 40)
        }

    return resultados


def coletar_htmls_autenticados():
    c = credenciais()
    opener, jar = criar_opener()

    login = http_request(opener, "POST", LOGIN_API, {
        "email": c["email"],
        "senha": c["senha"]
    }, limite=100000)

    paginas = {}

    for page in PAGES:
        resp = http_request(opener, "GET", page, None, limite=1200000)
        html = resp.get("body") or ""
        paginas[page] = {
            "status": resp.get("status"),
            "ok": resp.get("ok"),
            "content_type": resp.get("content_type"),
            "tamanho_html": len(html),
            "preview": redigir(html[:3000]),
            "inspecao": html_inspect(html),
            "marcadores": {
                "etapa25_4": "ETAPA25_4" in html or "etapa25-4-dashboard-profissional" in html,
                "etapa25_1": "ETAPA25_1" in html,
                "er25dash": "er25dash" in html,
                "er25safe": "er25safe" in html,
                "tailwind_cdn": "cdn.tailwindcss.com" in html,
                "alpine": "alpinejs" in html or "x-data" in html,
                "dashboard_antigo": "CRM WhatsApp Enterprise" in html or "appData" in html or "activeTab" in html,
                "api_status": "/api/whatsapp/status/" in html,
                "href_crm_literal": 'href="/crm"' in html,
                "href_admin_literal": 'href="/admin/painel"' in html,
                "href_super_literal": 'href="/super-admin"' in html,
                "texto_link_quebrado_crm": "/crmAbrir" in html or "/crm\n" in html,
                "texto_link_quebrado_admin": "/admin/painelPainel" in html or "/admin/painel\n" in html,
                "texto_link_quebrado_super": "/super-adminSuper" in html or "/super-admin\n" in html
            }
        }

    status_api = http_request(opener, "GET", "/api/whatsapp/status/5", None, limite=100000)

    return {
        "login": {
            "status": login.get("status"),
            "ok": login.get("ok"),
            "content_type": login.get("content_type"),
            "body_preview": redigir(login.get("body_preview", "")),
            "cookies": cookies_resumo(jar)
        },
        "paginas": paginas,
        "status_api_5": {
            "status": status_api.get("status"),
            "ok": status_api.get("ok"),
            "content_type": status_api.get("content_type"),
            "body_preview": redigir(status_api.get("body_preview", "")),
            "json": status_api.get("json")
        }
    }


def buscar_padroes_quebrados():
    resultados = {}

    for arq in ARQUIVOS:
        texto = ler(arq)
        if texto is None:
            resultados[arq] = {
                "existe": False
            }
            continue

        padroes = {
            "href_sem_tag_crm": "/crmAbrir" in texto,
            "href_sem_tag_admin": "/admin/painelPainel" in texto,
            "href_sem_tag_super": "/super-adminSuper" in texto,
            "link_literal_css_quebrado": "/css/style.css\n" in texto and 'href="/css/style.css"' not in texto,
            "a_tag_quebrada": bool(re.search(r'(?<!href=")/crm[A-Za-z]', texto)),
            "html_escaped_links": "&lt;a href=" in texto or '<a href="http' in texto,
            "document_body_innerhtml": "document.body.innerHTML" in texto,
            "tailwind_cdn": "cdn.tailwindcss.com" in texto,
            "alpine": "alpinejs" in texto or "x-data" in texto
        }

        resultados[arq] = {
            "existe": True,
            "sha256": sha256_path(arq),
            "padroes": padroes,
            "linhas_suspeitas": procurar_linhas(
                texto,
                [
                    "/crmAbrir",
                    "/admin/painelPainel",
                    "/super-adminSuper",
                    "/css/style.css",
                    "&lt;a href=",
                    "document.body.innerHTML",
                    "cdn.tailwindcss.com",
                    "alpinejs",
                    "x-data"
                ],
                1
            )
        }

    return resultados


def coletar_logs():
    r = run_cmd(["docker", "compose", "logs", "--tail=220", "app"], 80)
    texto = (r.get("stdout") or "") + "\n" + (r.get("stderr") or "")

    linhas = texto.splitlines()
    suspeitas = []

    termos = [
        "error",
        "exception",
        "syntaxerror",
        "cannot read",
        "500",
        "dashboard",
        "whatsapp/status"
    ]

    for idx, linha in enumerate(linhas, start=1):
        low = linha.lower()
        if any(t in low for t in termos):
            suspeitas.append({
                "linha": idx,
                "texto": redigir(linha)[:600]
            })

    return {
        "cmd": r.get("cmd"),
        "ok": r.get("ok"),
        "total_linhas": len(linhas),
        "suspeitas": suspeitas[-80:],
        "amostra": redigir("\n".join(linhas[-160:]))[:60000]
    }


def gerar_diagnostico_resumido(relatorio):
    problemas = []
    recomendacoes = []

    dash_runtime = relatorio["htmls_autenticados"]["paginas"].get("/dashboard", {})
    marc = dash_runtime.get("marcadores", {})
    inspecao = dash_runtime.get("inspecao", {})

    if not relatorio["htmls_autenticados"]["login"].get("ok"):
        problemas.append("Login automatico falhou. A inspecao autenticada pode estar invalida.")

    if dash_runtime.get("status") != 200:
        problemas.append("Dashboard nao retornou HTTP 200.")

    if marc.get("texto_link_quebrado_crm") or marc.get("texto_link_quebrado_admin") or marc.get("texto_link_quebrado_super"):
        problemas.append("Dashboard renderizado contem texto de links quebrados, como /crmAbrir ou /admin/painelPainel.")

    if not marc.get("href_crm_literal"):
        problemas.append("Dashboard nao contem href=\"/crm\" valido.")

    if not marc.get("href_admin_literal"):
        problemas.append("Dashboard nao contem href=\"/admin/painel\" valido.")

    if not marc.get("href_super_literal"):
        problemas.append("Dashboard nao contem href=\"/super-admin\" valido.")

    if marc.get("dashboard_antigo"):
        problemas.append("Dashboard ainda contem marcadores do layout antigo.")

    if marc.get("tailwind_cdn"):
        problemas.append("Dashboard ainda carrega Tailwind CDN.")

    if marc.get("alpine"):
        problemas.append("Dashboard ainda carrega Alpine ou x-data.")

    links_suspeitos = inspecao.get("links_suspeitos", [])
    if links_suspeitos:
        problemas.append("HTML do dashboard possui links suspeitos: " + str(links_suspeitos[:6]))

    if relatorio["status_arquivos_suspeitos"].get("views/dashboard.ejs", {}).get("padroes", {}).get("link_literal_css_quebrado"):
        problemas.append("views/dashboard.ejs pode conter /css/style.css sem tag <link href=...> valida.")

    if not problemas:
        problemas.append("Nenhum problema obvio foi detectado automaticamente. Pode ser conflito visual de CSS ou cache do navegador.")

    recomendacoes.append("Se houver links quebrados no relatorio, corrigir views/dashboard.ejs para usar tags <a href=\"...\"> completas.")
    recomendacoes.append("Se /css/style.css estiver como texto solto, corrigir para <link href=\"/css/style.css\" rel=\"stylesheet\">.")
    recomendacoes.append("Se o HTML local divergir do container, sincronizar arquivos ou reiniciar/recriar container.")
    recomendacoes.append("Se tudo estiver correto no HTML e ainda quebrar visualmente, fazer captura do HTML renderizado e CSS computado no navegador.")

    return {
        "problemas_provaveis": problemas,
        "recomendacoes": recomendacoes
    }


def gerar_md(relatorio):
    diag = relatorio["diagnostico_resumido"]

    linhas = []
    linhas.append("# Diagnostico Dashboard Frontend")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Login OK: " + str(relatorio["htmls_autenticados"]["login"].get("ok")))
    linhas.append("- Dashboard status: " + str(relatorio["htmls_autenticados"]["paginas"].get("/dashboard", {}).get("status")))
    linhas.append("- API status WhatsApp status: " + str(relatorio["htmls_autenticados"]["status_api_5"].get("status")))
    linhas.append("- Dashboard local SHA256: " + str(relatorio["dashboard_local"].get("sha256")))
    linhas.append("- CSS local SHA256: " + str(relatorio["css_local"].get("sha256")))
    linhas.append("")

    linhas.append("## Problemas provaveis")
    linhas.append("")
    for p in diag["problemas_provaveis"]:
        linhas.append("- " + p)

    linhas.append("")
    linhas.append("## Recomendacoes")
    linhas.append("")
    for r in diag["recomendacoes"]:
        linhas.append("- " + r)

    linhas.append("")
    linhas.append("## Marcadores do /dashboard renderizado")
    linhas.append("")
    marc = relatorio["htmls_autenticados"]["paginas"].get("/dashboard", {}).get("marcadores", {})
    for k in sorted(marc.keys()):
        linhas.append("- " + k + ": " + str(marc[k]))

    linhas.append("")
    linhas.append("## Inspecao HTML do /dashboard")
    linhas.append("")
    insp = relatorio["htmls_autenticados"]["paginas"].get("/dashboard", {}).get("inspecao", {})
    linhas.append("- Title: " + str(insp.get("title")))
    linhas.append("- Links total: " + str(insp.get("links_total")))
    linhas.append("- Links sample: " + str(insp.get("links_sample")))
    linhas.append("- Links suspeitos: " + str(insp.get("links_suspeitos")))
    linhas.append("- Scripts: " + str(insp.get("scripts")))
    linhas.append("- Stylesheets: " + str(insp.get("stylesheets")))
    linhas.append("")

    linhas.append("## Padroes suspeitos em arquivos")
    linhas.append("")
    for arq, info in relatorio["status_arquivos_suspeitos"].items():
        if not info.get("existe"):
            linhas.append("- " + arq + ": ausente")
            continue

        suspeitos = []
        for nome, valor in info.get("padroes", {}).items():
            if valor:
                suspeitos.append(nome)

        if suspeitos:
            linhas.append("- " + arq + ": " + ", ".join(suspeitos))
        else:
            linhas.append("- " + arq + ": sem padroes suspeitos principais")

    linhas.append("")
    linhas.append("## Logs suspeitos")
    linhas.append("")
    for item in relatorio["logs"]["suspeitas"][-30:]:
        linhas.append("- linha " + str(item["linha"]) + ": " + item["texto"])

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "credencial_email": redigir(credenciais()["email"]),
        "dashboard_local": analisar_dashboard_local(),
        "css_local": analisar_css_local(),
        "comparacao_container": comparar_container(),
        "htmls_autenticados": coletar_htmls_autenticados(),
        "status_arquivos_suspeitos": buscar_padroes_quebrados(),
        "logs": coletar_logs()
    }

    relatorio["diagnostico_resumido"] = gerar_diagnostico_resumido(relatorio)

    json_path = REPORTS_DIR / ("diagnostico_dashboard_frontend_" + stamp + ".json")
    md_path = REPORTS_DIR / ("diagnostico_dashboard_frontend_" + stamp + ".md")

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Diagnostico concluido.")
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Login OK: " + str(relatorio["htmls_autenticados"]["login"].get("ok")))
    print("Dashboard status: " + str(relatorio["htmls_autenticados"]["paginas"].get("/dashboard", {}).get("status")))
    print("Status API /api/whatsapp/status/5: " + str(relatorio["htmls_autenticados"]["status_api_5"].get("status")))
    print("")
    print("Problemas provaveis:")
    for p in relatorio["diagnostico_resumido"]["problemas_provaveis"]:
        print("- " + p)


if __name__ == "__main__":
    main()
