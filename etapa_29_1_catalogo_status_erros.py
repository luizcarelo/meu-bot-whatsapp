#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
BACKEND = ROOT / "backend"
REPORTS = ROOT / "reports"
BACKUPS = ROOT / "backups"
DOCS = ROOT / "docs"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_GERADOS = [
    "backend/src/shared/http/statusCodes.js",
    "backend/src/shared/http/errorCodes.js",
    "docs/PADRAO_RESPOSTAS_API.md",
    "docs/CONTRATOS_API.md"
]

BACKUP_FILES = ARQUIVOS_GERADOS + DOCS_OBRIGATORIOS

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


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def garantir_dirs():
    REPORTS.mkdir(exist_ok=True)
    BACKUPS.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    (BACKEND / "src" / "shared" / "http").mkdir(parents=True, exist_ok=True)


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
            b = f.read(1048576)
            if not b:
                break
            h.update(b)

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


def run_cmd(cmd, cwd=None, timeout=120):
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )

        return {
            "cmd": cmd,
            "cwd": str(cwd or ROOT),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip()[:30000],
            "stderr": proc.stderr.strip()[:30000],
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

def status_codes_js():
    return """const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  INTERNAL_SERVER_ERROR: 500
};

module.exports = {
  HTTP_STATUS
};
"""


def error_codes_js():
    return """const ERROR_CODES = {
  AUTH_REQUIRED: 'AUTH_REQUIRED',
  AUTH_INVALID_CREDENTIALS: 'AUTH_INVALID_CREDENTIALS',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  RESOURCE_NOT_FOUND: 'RESOURCE_NOT_FOUND',
  WHATSAPP_DISCONNECTED: 'WHATSAPP_DISCONNECTED',
  WHATSAPP_STATUS_UNAVAILABLE: 'WHATSAPP_STATUS_UNAVAILABLE',
  TENANT_NOT_FOUND: 'TENANT_NOT_FOUND',
  USER_NOT_FOUND: 'USER_NOT_FOUND',
  INTERNAL_ERROR: 'INTERNAL_ERROR'
};

module.exports = {
  ERROR_CODES
};
"""


def padrao_respostas_api_md():
    return """# Padrao de Respostas de API

Data: """ + agora_iso() + """

## Objetivo

Definir o catalogo inicial de status HTTP e codigos de erro do backend modular.

Esta fase nao altera rotas, handlers, banco, Docker, frontend React ou backend legado.

## Formato de sucesso

JSON de sucesso:

{
  "success": true,
  "data": {},
  "error": null
}

## Formato de erro

JSON de erro:

{
  "success": false,
  "data": null,
  "error": {
    "code": "CODIGO_DO_ERRO",
    "message": "Mensagem amigavel em PT-BR"
  }
}

## Status HTTP catalogados

OK
CREATED
BAD_REQUEST
UNAUTHORIZED
FORBIDDEN
NOT_FOUND
CONFLICT
UNPROCESSABLE_ENTITY
INTERNAL_SERVER_ERROR

## Codigos de erro catalogados

AUTH_REQUIRED
AUTH_INVALID_CREDENTIALS
VALIDATION_ERROR
RESOURCE_NOT_FOUND
WHATSAPP_DISCONNECTED
WHATSAPP_STATUS_UNAVAILABLE
TENANT_NOT_FOUND
USER_NOT_FOUND
INTERNAL_ERROR

## Proximas fases

Etapa 29.2: reforcar apiResponse.js e errors.js.

Etapa 29.3: padronizar errorHandler e notFoundHandler.

Etapa 29.4: validar endpoints health com contrato padronizado.
"""


def contratos_api_atualizado():
    atual = ler("docs/CONTRATOS_API.md")

    if atual is None:
        atual = "# Contratos de API\n"

    ini = "<!-- ETAPA_29_1_INICIO -->"
    fim = "<!-- ETAPA_29_1_FIM -->"

    bloco = """
""" + ini + """
## Etapa 29.1 - Catalogo de status e erros

Criado catalogo inicial para padronizacao de respostas reais de API.

### Arquivos criados

backend/src/shared/http/statusCodes.js
backend/src/shared/http/errorCodes.js
docs/PADRAO_RESPOSTAS_API.md

### Codigos de erro catalogados

AUTH_REQUIRED
AUTH_INVALID_CREDENTIALS
VALIDATION_ERROR
RESOURCE_NOT_FOUND
WHATSAPP_DISCONNECTED
WHATSAPP_STATUS_UNAVAILABLE
TENANT_NOT_FOUND
USER_NOT_FOUND
INTERNAL_ERROR
""" + fim + """
"""

    pos_ini = atual.find(ini)
    pos_fim = atual.find(fim)

    if pos_ini >= 0 and pos_fim >= pos_ini:
        pos_fim = pos_fim + len(fim)
        novo = atual[:pos_ini] + bloco.strip() + atual[pos_fim:]
    else:
        if not atual.endswith("\n"):
            atual += "\n"
        novo = atual + "\n" + bloco.strip() + "\n"

    return novo


def arquivos_etapa():
    return {
        "backend/src/shared/http/statusCodes.js": status_codes_js(),
        "backend/src/shared/http/errorCodes.js": error_codes_js(),
        "docs/PADRAO_RESPOSTAS_API.md": padrao_respostas_api_md(),
        "docs/CONTRATOS_API.md": contratos_api_atualizado()
    }


def aplicar_alteracoes():
    resultados = []

    for nome, texto in arquivos_etapa().items():
        antes = sha256(nome)
        atual = ler(nome)
        alterado = atual != texto

        if alterado:
            gravar(nome, texto)

        depois = sha256(nome)

        resultados.append({
            "arquivo": nome,
            "alterado": alterado,
            "sha256_antes": antes,
            "sha256_depois": depois,
            "tamanho": len(texto)
        })

    return resultados


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
    itens = []
    erros = []

    for nome in ARQUIVOS_GERADOS:
        texto = ler(nome)
        existe = texto is not None
        ast = validar_sem_asterisco(nome, texto or "")

        item = {
            "arquivo": nome,
            "existe": existe,
            "sha256": sha256(nome),
            "sem_asterisco": len(ast) == 0,
            "asteriscos": ast[:10],
            "ok": existe and len(ast) == 0
        }

        itens.append(item)

        if not item["ok"]:
            erros.append(item)

    status_texto = ler("backend/src/shared/http/statusCodes.js") or ""
    error_texto = ler("backend/src/shared/http/errorCodes.js") or ""
    doc_texto = ler("docs/PADRAO_RESPOSTAS_API.md") or ""
    contratos = ler("docs/CONTRATOS_API.md") or ""

    checks = {
        "tem_backend_dir": BACKEND.exists(),
        "tem_status_codes": "HTTP_STATUS" in status_texto,
        "tem_error_codes": "ERROR_CODES" in error_texto,
        "tem_resource_not_found": "RESOURCE_NOT_FOUND" in error_texto,
        "tem_internal_error": "INTERNAL_ERROR" in error_texto,
        "doc_tem_success": '"success": true' in doc_texto,
        "doc_tem_error": '"error"' in doc_texto,
        "contratos_api_atualizado": "Etapa 29.1 - Catalogo de status e erros" in contratos
    }

    ok = len(erros) == 0 and all(checks.values())

    return {
        "arquivos": itens,
        "checks": checks,
        "erros": erros,
        "ok": ok
    }


def node_check():
    arquivos = [
        "backend/src/shared/http/statusCodes.js",
        "backend/src/shared/http/errorCodes.js"
    ]

    resultados = []

    for nome in arquivos:
        resultados.append(run_cmd(["node", "--check", nome], cwd=ROOT, timeout=60))

    return {
        "total": len(resultados),
        "resultados": resultados,
        "ok": len(resultados) == len(arquivos) and all(item.get("ok") for item in resultados)
    }

def atualizar_doc_obrigatorio(nome, titulo, linhas):
    atual = ler(nome)

    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_29_1_INICIO -->"
    fim = "<!-- ETAPA_29_1_FIM -->"

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
        "Etapa 29.1 - Catalogo de status e erros",
        [
            "Data: " + data,
            "",
            "Criados statusCodes.js e errorCodes.js no backend modular.",
            "Criado docs/PADRAO_RESPOSTAS_API.md.",
            "Atualizado docs/CONTRATOS_API.md.",
            "Nenhum fluxo real foi alterado nesta fase.",
            "Validacao estrutural OK: " + str(relatorio["validacao"]["ok"]) + ".",
            "Node check OK: " + str(relatorio["node_check"]["ok"]) + "."
        ]
    )

    atualizar_doc_obrigatorio(
        "CHANGELOG.md",
        "Etapa 29.1 - Catalogo base de API",
        [
            "Data: " + data,
            "",
            "Adicionado catalogo de status HTTP.",
            "Adicionado catalogo de codigos de erro.",
            "Adicionada documentacao do padrao de respostas.",
            "Sem alteracao de rotas, handlers, banco, Docker, frontend ou legado."
        ]
    )

    atualizar_doc_obrigatorio(
        "DECISOES_TECNICAS.md",
        "Etapa 29.1 - Padronizacao iniciada por catalogos",
        [
            "Data: " + data,
            "",
            "Decidido iniciar a padronizacao por catalogos isolados.",
            "Decidido nao alterar apiResponse, errorHandler ou app.js nesta fase.",
            "Decidido manter mensagens de erro em PT-BR."
        ]
    )

    atualizar_doc_obrigatorio(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 29.1",
        [
            "Data: " + data,
            "",
            "Etapa 29.2: reforcar apiResponse.js e errors.js.",
            "Etapa 29.3: padronizar errorHandler e notFoundHandler.",
            "Etapa 29.4: validar endpoints health com contrato padronizado."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_relatorio_md(relatorio):
    linhas = []
    linhas.append("# Etapa 29.1 - Catalogo de status e erros")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivos alterados: " + str(sum(1 for item in relatorio["alteracoes"] if item["alterado"])))
    linhas.append("- Validacao estrutura OK: " + str(relatorio["validacao"]["ok"]))
    linhas.append("- Node check OK: " + str(relatorio["node_check"]["ok"]))
    linhas.append("- Runtime geral OK: " + str(relatorio["ok"]))
    linhas.append("")
    linhas.append("## Arquivos da fase")
    linhas.append("")

    for item in relatorio["alteracoes"]:
        linhas.append("- " + item["arquivo"] + " alterado: " + str(item["alterado"]))

    linhas.append("")
    linhas.append("## Proxima fase sugerida")
    linhas.append("")
    linhas.append("Etapa 29.2 - Reforcar apiResponse e errors.")

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS / ("etapa_29_1_catalogo_status_erros_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS / "etapa_29_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    alteracoes = aplicar_alteracoes()
    validacao = validar_estrutura()
    node = node_check()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "alteracoes": alteracoes,
        "validacao": validacao,
        "node_check": node,
        "ok": bool(validacao["ok"] and node["ok"])
    }

    docs = atualizar_documentacao(relatorio)
    relatorio["docs_obrigatorios"] = docs

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS / "etapa_29_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS / "etapa_29_1_catalogo_status_erros.json"
    md_path = REPORTS / "etapa_29_1_catalogo_status_erros.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_relatorio_md(relatorio))

    print("Etapa 29.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Validacao estrutura OK: " + str(validacao["ok"]))
    print("Node check OK: " + str(node["ok"]))
    print("Runtime geral OK: " + str(relatorio["ok"]))

    if not relatorio["ok"]:
        print("")
        print("Aviso: Etapa 29.1 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
