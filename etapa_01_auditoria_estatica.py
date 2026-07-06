#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 01 - Auditoria estatica do projeto WhatsApp CRM
Objetivo:
- Nao altera arquivos existentes do projeto.
- Cria relatorios em reports/.
- Detecta riscos de seguranca, estrutura, dependencias e inconsistencias.
- Mantem saida em PT-BR.
"""

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
JSON_REPORT = REPORTS_DIR / "etapa_01_auditoria_estatica.json"
MD_REPORT = REPORTS_DIR / "etapa_01_auditoria_estatica.md"

IGNORAR_DIRS = {
    "node_modules",
    ".git",
    "auth_sessions",
    "backups",
    "public/uploads",
    ".vscode",
    "reports"
}

ARQUIVOS_SENSIVEIS = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_dsa",
    "credentials.json",
    "service-account.json"
}

PADROES_SEGREDOS = [
    ("Possivel senha", r"(?i)(pass|password|senha|secret|token|key)\s*=\s*.+"),
    ("Possivel URI com credencial", r"(?i)(mysql|postgres|mongodb|redis):\/\/[^ \n]+"),
    ("Possivel chave JWT/API", r"(?i)(jwt_secret|api_key|openai|smtp_pass|redis_password)\s*=\s*.+"),
]

DEPENDENCIAS_ALERTA = {
    "multer": "Multer 1.x possui historico de vulnerabilidades corrigidas na linha 2.x.",
    "fluent-ffmpeg": "Pacote sem suporte ativo segundo avisos comuns do npm.",
    "puppeteer": "Versoes antigas podem trazer Chromium desatualizado e risco operacional.",
    "glob": "Glob antigo pode indicar arvore de dependencias legada.",
    "rimraf": "Rimraf antigo pode indicar arvore de dependencias legada.",
    "fstream": "Pacote depreciado.",
    "npmlog": "Pacote depreciado.",
    "gauge": "Pacote depreciado.",
    "inflight": "Pacote depreciado e com alerta de vazamento de memoria."
}

EXTENSOES_TEXTO = {
    ".js", ".json", ".md", ".txt", ".env", ".yml", ".yaml",
    ".ejs", ".css", ".html", ".sql", ".sh", ".dockerfile"
}


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def caminho_relativo(path):
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def deve_ignorar(path):
    rel = caminho_relativo(path)
    partes = rel.split("/")
    if not partes:
        return False

    for ignorado in IGNORAR_DIRS:
        if rel == ignorado or rel.startswith(ignorado + "/"):
            return True

    return False


def hash_arquivo(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for bloco in iter(lambda: f.read(1024 * 1024), b""):
                h.update(bloco)
        return h.hexdigest()
    except Exception:
        return None


def ler_texto(path, limite_bytes=1024 * 1024):
    try:
        if path.stat().st_size > limite_bytes:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def listar_arquivos():
    arquivos = []
    for path in ROOT.rglob("*"):
        if path.is_file() and not deve_ignorar(path):
            arquivos.append(path)
    return sorted(arquivos)


def auditar_estrutura(arquivos):
    resultado = {
        "total_arquivos_analisados": len(arquivos),
        "arquivos_por_extensao": {},
        "arquivos_grandes": [],
        "arquivos_sensiveis": [],
        "git_presente": (ROOT / ".git").exists(),
        "node_modules_presente": (ROOT / "node_modules").exists()
    }

    for path in arquivos:
        ext = path.suffix.lower() or "[sem_extensao]"
        resultado["arquivos_por_extensao"][ext] = resultado["arquivos_por_extensao"].get(ext, 0) + 1

        tamanho = path.stat().st_size
        if tamanho > 1024 * 1024:
            resultado["arquivos_grandes"].append({
                "arquivo": caminho_relativo(path),
                "tamanho_bytes": tamanho,
                "sha256": hash_arquivo(path)
            })

        if path.name in ARQUIVOS_SENSIVEIS:
            resultado["arquivos_sensiveis"].append({
                "arquivo": caminho_relativo(path),
                "tamanho_bytes": tamanho
            })

    return resultado


def auditar_segredos(arquivos):
    achados = []

    for path in arquivos:
        nome = path.name.lower()
        ext = path.suffix.lower()

        if ext not in EXTENSOES_TEXTO and nome not in ARQUIVOS_SENSIVEIS:
            continue

        texto = ler_texto(path)
        if texto is None:
            continue

        linhas = texto.splitlines()
        for idx, linha in enumerate(linhas, start=1):
            for tipo, padrao in PADROES_SEGREDOS:
                if re.search(padrao, linha):
                    achados.append({
                        "arquivo": caminho_relativo(path),
                        "linha": idx,
                        "tipo": tipo,
                        "conteudo_redigido": redigir_linha(linha)
                    })

    return achados


def redigir_linha(linha):
    if "=" in linha:
        chave = linha.split("=", 1)[0].strip()
        return chave + "=<REDIGIDO>"
    return "<REDIGIDO>"


def carregar_package_json():
    package_path = ROOT / "package.json"
    if not package_path.exists():
        return None

    texto = ler_texto(package_path)
    if not texto:
        return None

    try:
        return json.loads(texto)
    except Exception:
        return None


def auditar_dependencias():
    package = carregar_package_json()
    if not package:
        return {
            "package_json_encontrado": False,
            "alertas": []
        }

    deps = {}
    deps.update(package.get("dependencies", {}))
    deps.update(package.get("devDependencies", {}))

    alertas = []
    for nome, versao in sorted(deps.items()):
        if nome in DEPENDENCIAS_ALERTA:
            alertas.append({
                "pacote": nome,
                "versao_declarada": versao,
                "observacao": DEPENDENCIAS_ALERTA[nome]
            })

    return {
        "package_json_encontrado": True,
        "nome": package.get("name"),
        "versao": package.get("version"),
        "engines": package.get("engines", {}),
        "total_dependencias": len(deps),
        "alertas": alertas
    }


def auditar_banco_docker():
    env_path = ROOT / ".env"
    compose_path = ROOT / "docker-compose.yml"

    env_texto = ler_texto(env_path) if env_path.exists() else ""
    compose_texto = ler_texto(compose_path) if compose_path.exists() else ""

    sinais_mysql = []
    sinais_postgres = []

    if env_texto:
        if "DB_HOST" in env_texto or "mysql" in env_texto.lower():
            sinais_mysql.append(".env indica configuracao compativel com MySQL")

    if compose_texto:
        if "postgres" in compose_texto.lower():
            sinais_postgres.append("docker-compose.yml usa imagem ou variaveis de PostgreSQL")
        if "mysql" in compose_texto.lower():
            sinais_mysql.append("docker-compose.yml menciona MySQL")

    inconsistente = bool(sinais_mysql and sinais_postgres)

    return {
        "env_existe": env_path.exists(),
        "docker_compose_existe": compose_path.exists(),
        "sinais_mysql": sinais_mysql,
        "sinais_postgres": sinais_postgres,
        "inconsistencia_detectada": inconsistente
    }


def auditar_controllers(arquivos):
    achados = []

    for path in arquivos:
        rel = caminho_relativo(path)
        if not rel.startswith("controllers/") or path.suffix.lower() != ".js":
            continue

        texto = ler_texto(path)
        if texto is None:
            continue

        linhas_nao_vazias = [
            l.strip()
            for l in texto.splitlines()
            if l.strip() and not l.strip().startswith("//")
        ]

        sinais = []

        if re.search(r"class\s+\w+\s*\{\s*\}", texto, re.DOTALL):
            sinais.append("classe aparentemente vazia")

        if re.search(r"constructor\s*\([^)]*\)\s*$", texto, re.MULTILINE):
            sinais.append("constructor sem corpo na mesma estrutura")

        if "const  = require" in texto:
            sinais.append("require com identificador ausente")

        if len(linhas_nao_vazias) < 12:
            sinais.append("arquivo muito pequeno para controller funcional")

        if sinais:
            achados.append({
                "arquivo": rel,
                "sinais": sinais,
                "linhas_nao_vazias": len(linhas_nao_vazias)
            })

    return achados


def auditar_js_basico(arquivos):
    achados = []

    for path in arquivos:
        if path.suffix.lower() != ".js":
            continue

        texto = ler_texto(path)
        if texto is None:
            continue

        rel = caminho_relativo(path)

        if re.search(r"const\s*=\s*require", texto):
            achados.append({
                "arquivo": rel,
                "tipo": "sintaxe_suspeita",
                "detalhe": "Declaracao const sem identificador antes de require."
            })

        if re.search(r"module\.exports\s*=\s*new\s+\w+\(\)\s*;", texto):
            achados.append({
                "arquivo": rel,
                "tipo": "export_singleton",
                "detalhe": "Exporta instancia unica. Verificar consistencia com injecao de dependencias."
            })

    return achados


def calcular_prioridade(relatorio):
    criticos = 0
    altos = 0
    medios = 0

    if relatorio["estrutura"]["arquivos_sensiveis"]:
        criticos += 1

    if relatorio["estrutura"]["git_presente"]:
        altos += 1

    if relatorio["banco_docker"]["inconsistencia_detectada"]:
        altos += 1

    if relatorio["controllers_suspeitos"]:
        altos += 1

    if relatorio["segredos"]:
        criticos += 1

    if relatorio["dependencias"]["alertas"]:
        medios += 1

    return {
        "criticos": criticos,
        "altos": altos,
        "medios": medios
    }


def gerar_markdown(relatorio):
    linhas = []

    linhas.append("# Etapa 01 - Auditoria estatica")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo executivo")
    linhas.append("")
    linhas.append("- Projeto analisado: " + str(relatorio["raiz"]))
    linhas.append("- Arquivos analisados: " + str(relatorio["estrutura"]["total_arquivos_analisados"]))
    linhas.append("- Achados criticos: " + str(relatorio["prioridade"]["criticos"]))
    linhas.append("- Achados altos: " + str(relatorio["prioridade"]["altos"]))
    linhas.append("- Achados medios: " + str(relatorio["prioridade"]["medios"]))
    linhas.append("")

    linhas.append("## Achados de seguranca")
    linhas.append("")
    if relatorio["estrutura"]["arquivos_sensiveis"]:
        linhas.append("- Arquivos sensiveis encontrados:")
        for item in relatorio["estrutura"]["arquivos_sensiveis"]:
            linhas.append("  - " + item["arquivo"])
    else:
        linhas.append("- Nenhum arquivo sensivel conhecido encontrado.")
    linhas.append("")

    if relatorio["segredos"]:
        linhas.append("- Possiveis segredos encontrados, com valores redigidos:")
        for item in relatorio["segredos"]:
            linhas.append(
                "  - "
                + item["arquivo"]
                + ":"
                + str(item["linha"])
                + " - "
                + item["tipo"]
                + " - "
                + item["conteudo_redigido"]
            )
    else:
        linhas.append("- Nenhum padrao simples de segredo encontrado.")
    linhas.append("")

    linhas.append("## Banco de dados e Docker")
    linhas.append("")
    bd = relatorio["banco_docker"]
    linhas.append("- .env existe: " + str(bd["env_existe"]))
    linhas.append("- docker-compose.yml existe: " + str(bd["docker_compose_existe"]))
    linhas.append("- Inconsistencia detectada: " + str(bd["inconsistencia_detectada"]))
    for item in bd["sinais_mysql"]:
        linhas.append("  - " + item)
    for item in bd["sinais_postgres"]:
        linhas.append("  - " + item)
    linhas.append("")

    linhas.append("## Controllers suspeitos")
    linhas.append("")
    if relatorio["controllers_suspeitos"]:
        for item in relatorio["controllers_suspeitos"]:
            linhas.append("- " + item["arquivo"])
            for sinal in item["sinais"]:
                linhas.append("  - " + sinal)
    else:
        linhas.append("- Nenhum controller suspeito encontrado pelos criterios simples.")
    linhas.append("")

    linhas.append("## Dependencias com alerta")
    linhas.append("")
    deps = relatorio["dependencias"]
    if deps.get("package_json_encontrado"):
        linhas.append("- package.json: encontrado")
        linhas.append("- Total de dependencias: " + str(deps["total_dependencias"]))
        if deps["alertas"]:
            for item in deps["alertas"]:
                linhas.append(
                    "- "
                    + item["pacote"]
                    + " "
                    + str(item["versao_declarada"])
                    + ": "
                    + item["observacao"]
                )
        else:
            linhas.append("- Nenhuma dependencia da lista de alerta foi encontrada.")
    else:
        linhas.append("- package.json nao encontrado ou invalido.")
    linhas.append("")

    linhas.append("## JavaScript com sinais suspeitos")
    linhas.append("")
    if relatorio["js_suspeito"]:
        for item in relatorio["js_suspeito"]:
            linhas.append("- " + item["arquivo"] + ": " + item["detalhe"])
    else:
        linhas.append("- Nenhum sinal simples encontrado.")
    linhas.append("")

    linhas.append("## Recomendacao da proxima etapa")
    linhas.append("")
    linhas.append("- Etapa 02 deve criar backup, manifesto e sanitizacao do pacote.")
    linhas.append("- Etapa 03 deve corrigir estrutura de ambiente, Docker e banco.")
    linhas.append("- Etapa 04 deve validar sintaxe e reconstruir controllers quebrados.")
    linhas.append("- Etapa 05 deve endurecer seguranca, CORS, rate limit e logs.")
    linhas.append("")

    return "\n".join(linhas) + "\n"


def main():
    REPORTS_DIR.mkdir(exist_ok=True)

    arquivos = listar_arquivos()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "estrutura": auditar_estrutura(arquivos),
        "segredos": auditar_segredos(arquivos),
        "dependencias": auditar_dependencias(),
        "banco_docker": auditar_banco_docker(),
        "controllers_suspeitos": auditar_controllers(arquivos),
        "js_suspeito": auditar_js_basico(arquivos)
    }

    relatorio["prioridade"] = calcular_prioridade(relatorio)

    JSON_REPORT.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    MD_REPORT.write_text(
        gerar_markdown(relatorio),
        encoding="utf-8"
    )

    print("Auditoria concluida.")
    print("Relatorio JSON: " + caminho_relativo(JSON_REPORT))
    print("Relatorio Markdown: " + caminho_relativo(MD_REPORT))
    print("Criticos: " + str(relatorio["prioridade"]["criticos"]))
    print("Altos: " + str(relatorio["prioridade"]["altos"]))
    print("Medios: " + str(relatorio["prioridade"]["medios"]))


if __name__ == "__main__":
    main()
