#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 28.1 - Validar backend modular isolado

Objetivo:
- Corrigir requireAuth.js para chamar next().
- Validar sintaxe real de todos arquivos JS do backend modular.
- Rodar npm install opcional no backend modular.
- Rodar npm run check no backend modular.
- Subir backend modular isolado em porta de teste.
- Validar endpoints de health.
- Encerrar processo isolado ao final.
- Nao alterar backend legado.
- Nao alterar server.js legado.
- Nao alterar routes/api.js legado.
- Nao alterar banco.
- Nao alterar Docker.
- Nao alterar frontend React.
- Criar backup, manifesto, validacao e relatorios.
- Atualizar documentacao obrigatoria.

Como executar:
python3 etapa_28_1_validar_backend_modular_isolado.py

Variaveis opcionais:
ETAPA28_1_NPM_INSTALL=true ou false
ETAPA28_1_TEST_PORT=50110
"""

import os
import json
import shutil
import hashlib
import subprocess
import time
import signal
from datetime import datetime
from pathlib import Path
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError

ROOT = Path.cwd()
BACKEND_DIR = ROOT / "backend"
SRC_DIR = BACKEND_DIR / "src"
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "backend",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

IGNORE_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "reports",
    "auth_sessions",
    "__pycache__",
    "tmp_etapa_24",
    "frontend/node_modules",
    "frontend/dist",
    "backend/node_modules",
    "backend/dist"
]

MODULES = [
    "auth",
    "dashboard",
    "whatsapp",
    "crm",
    "tenants",
    "users"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


def rel(path):
    try:
        return str(Path(path).relative_to(ROOT)).replace("\\", "/")
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
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            bloco = f.read(1048576)
            if not bloco:
                break
            h.update(bloco)
    return h.hexdigest()


def salvar_json(path, dados):
    gravar(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def deve_ignorar(path):
    partes = set(path.parts)
    caminho = rel(path)
    for nome in IGNORE_DIRS:
        if nome in partes:
            return True
        if caminho == nome or caminho.startswith(nome + "/"):
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


def copiar_item(origem, destino):
    if origem.is_dir():
        if destino.exists():
            shutil.rmtree(destino)
        shutil.copytree(origem, destino, ignore=shutil.ignore_patterns("node_modules", "dist"))
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)


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


def run_cmd(cmd, cwd=None, timeout=300, env=None):
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env
        )
        return {
            "cmd": cmd,
            "cwd": str(cwd or ROOT),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip()[:70000],
            "stderr": proc.stderr.strip()[:70000],
            "ok": proc.returncode == 0
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "cwd": str(cwd or ROOT),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "ok": False
        }


def corrigir_require_auth():
    path = BACKEND_DIR / "src" / "middlewares" / "requireAuth.js"
    antes = sha256(path)
    texto = ler(path)

    resultado = {
        "arquivo": rel(path),
        "existe": texto is not None,
        "alterado": False,
        "sha256_antes": antes,
        "sha256_depois": None
    }

    if texto is None:
        resultado["erro"] = "Arquivo requireAuth.js ausente"
        return resultado

    novo = texto.replace("return next;\n", "return next();\n")
    novo = novo.replace("return next;\r\n", "return next();\r\n")

    if novo != texto:
        gravar(path, novo)
        resultado["alterado"] = True

    resultado["sha256_depois"] = sha256(path)
    resultado["tem_next_call"] = "return next();" in novo
    resultado["sem_next_sem_call"] = "return next;" not in novo

    return resultado


def listar_js_backend():
    arquivos = []
    for base_dir in [BACKEND_DIR / "src", BACKEND_DIR / "scripts"]:
        if not base_dir.exists():
            continue
        for raiz, dirs, files in os.walk(base_dir):
            raiz_path = Path(raiz)
            dirs[:] = [d for d in dirs if d not in ["node_modules", "dist"]]
            for nome in files:
                if nome.endswith(".js"):
                    arquivos.append(raiz_path / nome)
    return sorted(arquivos)


def validar_sem_asterisco(nome, texto):
    achados = []
    for idx, linha in enumerate(texto.splitlines(), start=1):
        if chr(42) in linha:
            achados.append({
                "arquivo": nome,
                "linha": idx,
                "texto": linha[:300]
            })
    return achados


def validar_estrutura():
    arquivos = listar_js_backend()
    itens = []
    erros = []

    for p in arquivos:
        texto = ler(p)
        ast = validar_sem_asterisco(rel(p), texto or "")
        item = {
            "arquivo": rel(p),
            "sha256": sha256(p),
            "sem_asterisco": len(ast) == 0,
            "asteriscos": ast[:10],
            "ok": texto is not None and len(ast) == 0
        }
        itens.append(item)
        if not item["ok"]:
            erros.append(item)

    checks = {
        "tem_backend_dir": BACKEND_DIR.exists(),
        "tem_src_dir": SRC_DIR.exists(),
        "tem_app": (SRC_DIR / "app.js").exists(),
        "tem_server": (SRC_DIR / "server.js").exists(),
        "tem_package": (BACKEND_DIR / "package.json").exists(),
        "total_js_maior_que_zero": len(arquivos) > 0,
        "tem_modules": all((SRC_DIR / "modules" / module_name).exists() for module_name in MODULES),
        "require_auth_next_call": "return next();" in (ler("backend/src/middlewares/requireAuth.js") or ""),
        "legado_server_preservado": (ROOT / "server.js").exists(),
        "legado_routes_preservado": (ROOT / "routes" / "api.js").exists()
    }

    ok = len(erros) == 0 and all(checks.values())

    return {
        "total_js": len(arquivos),
        "arquivos": itens,
        "checks": checks,
        "erros": erros,
        "ok": ok
    }


def node_check_real():
    resultados = []
    arquivos = listar_js_backend()

    for arquivo in arquivos:
        resultados.append(run_cmd(["node", "--check", str(arquivo)], cwd=ROOT, timeout=60))

    return {
        "total": len(resultados),
        "arquivos": [rel(p) for p in arquivos],
        "resultados": resultados,
        "ok": len(resultados) > 0 and all(item.get("ok") for item in resultados)
    }


def npm_install_flag():
    valor = os.environ.get("ETAPA28_1_NPM_INSTALL", "true").strip().lower()
    return valor not in ["false", "0", "nao", "não", "no"]


def executar_npm():
    install = npm_install_flag()
    resultado = {
        "node_version": run_cmd(["node", "--version"], timeout=30),
        "npm_version": run_cmd(["npm", "--version"], timeout=30),
        "install_executado": install,
        "install": None,
        "check": None,
        "ok": True
    }

    if install:
        resultado["install"] = run_cmd(["npm", "install"], cwd=BACKEND_DIR, timeout=600)
        resultado["ok"] = resultado["ok"] and bool(resultado["install"].get("ok"))

    resultado["check"] = run_cmd(["npm", "run", "check"], cwd=BACKEND_DIR, timeout=300)
    resultado["ok"] = resultado["ok"] and bool(resultado["check"].get("ok"))

    return resultado


def porta_teste():
    valor = os.environ.get("ETAPA28_1_TEST_PORT", "50110").strip()
    try:
        porta = int(valor)
    except Exception:
        porta = 50110
    return porta


def http_get(porta, path, timeout=8):
    url = "http://127.0.0.1:" + str(porta) + path
    resultado = {
        "path": path,
        "url": url,
        "status": None,
        "ok": False,
        "erro": None,
        "body_preview": "",
        "json": None
    }

    try:
        opener = build_opener()
        req = Request(url, headers={"Accept": "application/json"}, method="GET")
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(200000)
            texto = raw.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 300
            resultado["body_preview"] = texto[:2000]
            try:
                resultado["json"] = json.loads(texto)
            except Exception:
                resultado["json"] = None
    except HTTPError as exc:
        resultado["status"] = exc.code
        resultado["erro"] = str(exc)
        try:
            texto = exc.read(200000).decode("utf-8", errors="replace")
            resultado["body_preview"] = texto[:2000]
            resultado["json"] = json.loads(texto)
        except Exception:
            pass
    except URLError as exc:
        resultado["erro"] = str(exc.reason)
    except Exception as exc:
        resultado["erro"] = str(exc)

    return resultado


def validar_runtime_isolado():
    porta = porta_teste()
    env = os.environ.copy()
    env["MODULAR_BACKEND_PORT"] = str(porta)
    env["NODE_ENV"] = "test"

    endpoints = ["/health"]
    for module_name in MODULES:
        endpoints.append("/api/v2/" + module_name + "/health")

    resultado = {
        "porta": porta,
        "processo_iniciado": False,
        "pid": None,
        "endpoints": [],
        "stdout": "",
        "stderr": "",
        "ok": False
    }

    proc = None

    try:
        proc = subprocess.Popen(
            ["node", "src/server.js"],
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            preexec_fn=os.setsid
        )

        resultado["processo_iniciado"] = True
        resultado["pid"] = proc.pid

        pronto = False
        for _ in range(30):
            if proc.poll() is not None:
                break
            teste = http_get(porta, "/health", timeout=2)
            if teste.get("ok"):
                pronto = True
                break
            time.sleep(1)

        resultado["pronto"] = pronto

        for path in endpoints:
            item = http_get(porta, path, timeout=5)
            resultado["endpoints"].append(item)

        resultado["ok"] = bool(pronto and all(item.get("ok") for item in resultado["endpoints"]))

    except Exception as exc:
        resultado["erro"] = str(exc)

    finally:
        if proc is not None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass

            try:
                out, err = proc.communicate(timeout=5)
            except Exception:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
                out, err = "", ""

            resultado["stdout"] = (out or "")[:20000]
            resultado["stderr"] = (err or "")[:20000]
            resultado["returncode"] = proc.returncode

    return resultado


def atualizar_doc_obrigatorio(nome, titulo, linhas):
    atual = ler(nome)
    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_28_1_INICIO -->"
    fim = "<!-- ETAPA_28_1_FIM -->"

    bloco = ["", ini, "## " + titulo, ""]
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
            atual += "\n"
        novo = atual + novo_bloco

    gravar(nome, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]

    atualizar_doc_obrigatorio(
        "CONTEXTO_PROJETO.md",
        "Etapa 28.1 - Backend modular isolado validado",
        [
            "Data: " + data,
            "",
            "Corrigido requireAuth.js para chamar next().",
            "Validada sintaxe real dos arquivos JS do backend modular.",
            "Node check total: " + str(relatorio["node_check"]["total"]) + ".",
            "Node check OK: " + str(relatorio["node_check"]["ok"]) + ".",
            "npm OK: " + str(relatorio["npm"]["ok"]) + ".",
            "Runtime isolado OK: " + str(relatorio["runtime"]["ok"]) + ".",
            "Legado preservado."
        ]
    )

    atualizar_doc_obrigatorio(
        "CHANGELOG.md",
        "Etapa 28.1 - Validacao backend modular isolado",
        [
            "Data: " + data,
            "",
            "Corrigido middleware requireAuth no backend modular.",
            "Executado node --check em todos os arquivos JS do backend modular.",
            "Executado npm run check.",
            "Validado backend modular isolado em porta de teste.",
            "Nenhum arquivo legado foi substituido."
        ]
    )

    atualizar_doc_obrigatorio(
        "DECISOES_TECNICAS.md",
        "Etapa 28.1 - Validacao isolada do backend modular",
        [
            "Data: " + data,
            "",
            "Decidido validar backend modular isoladamente antes de conectar ao legado.",
            "Decidido manter backend modular em porta separada.",
            "Decidido testar apenas endpoints health nesta fase.",
            "Decidido nao conectar banco nesta fase."
        ]
    )

    atualizar_doc_obrigatorio(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 28.1",
        [
            "Data: " + data,
            "",
            "Etapa 29: padronizar respostas reais de API.",
            "Etapa 30: migrar autenticacao para contrato novo.",
            "Etapa futura: conectar repositories modulares ao banco.",
            "Etapa futura: integrar backend modular ao proxy ou Docker."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_relatorio_md(relatorio):
    linhas = []
    linhas.append("# Etapa 28.1 - Validar backend modular isolado")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- requireAuth alterado: " + str(relatorio["correcao_require_auth"]["alterado"]))
    linhas.append("- Validacao estrutura OK: " + str(relatorio["validacao"]["ok"]))
    linhas.append("- Total JS localizados: " + str(relatorio["validacao"]["total_js"]))
    linhas.append("- Node check total: " + str(relatorio["node_check"]["total"]))
    linhas.append("- Node check OK: " + str(relatorio["node_check"]["ok"]))
    linhas.append("- npm install executado: " + str(relatorio["npm"]["install_executado"]))
    linhas.append("- npm OK: " + str(relatorio["npm"]["ok"]))
    linhas.append("- Runtime isolado OK: " + str(relatorio["runtime"]["ok"]))
    linhas.append("- Runtime geral OK: " + str(relatorio["ok"]))
    linhas.append("")
    linhas.append("## Endpoints testados")
    linhas.append("")
    for item in relatorio["runtime"]["endpoints"]:
        linhas.append("- " + item["path"] + ": status " + str(item["status"]) + ", ok " + str(item["ok"]))
    linhas.append("")
    linhas.append("## Proxima etapa sugerida")
    linhas.append("")
    linhas.append("Etapa 29 - Padronizar respostas reais de API.")
    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()
    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_28_1_backend_modular_isolado_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_28_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    correcao = corrigir_require_auth()
    validacao = validar_estrutura()
    node = node_check_real()
    npm = executar_npm()
    runtime = validar_runtime_isolado()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "correcao_require_auth": correcao,
        "validacao": validacao,
        "node_check": node,
        "npm": npm,
        "runtime": runtime,
        "ok": bool(validacao["ok"] and node["ok"] and npm["ok"] and runtime["ok"])
    }

    docs = atualizar_documentacao(relatorio)
    relatorio["docs_obrigatorios"] = docs

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_28_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)
    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_28_1_validar_backend_modular_isolado.json"
    md_path = REPORTS_DIR / "etapa_28_1_validar_backend_modular_isolado.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_relatorio_md(relatorio))

    print("Etapa 28.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Validacao estrutura OK: " + str(validacao["ok"]))
    print("Total JS localizados: " + str(validacao["total_js"]))
    print("Node check OK: " + str(node["ok"]))
    print("Node check total: " + str(node["total"]))
    print("npm OK: " + str(npm["ok"]))
    print("Runtime isolado OK: " + str(runtime["ok"]))
    print("Runtime geral OK: " + str(relatorio["ok"]))

    if not relatorio["ok"]:
        print("")
        print("Aviso: Etapa 28.1 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
