#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 03 - Corrigir Docker para MySQL

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Substituir docker-compose.yml com configuracao MySQL coerente com .env.
- Preservar Redis.
- Atualizar .env.example com MYSQL_ROOT_PASSWORD se necessario.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorio JSON e Markdown em reports/.

Escopo:
- Nao altera controllers.
- Nao altera config/db.js.
- Nao altera package.json.
- Nao executa Docker.
"""

import os
import re
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "docker-compose.yml",
    ".env.example",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

MAX_LEITURA = 2097152


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


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
        if path.stat().st_size > MAX_LEITURA:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def gravar_texto(path, conteudo):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8")


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
    if "node_modules" in partes:
        return True
    if ".git" in partes:
        return True
    if "backups" in partes:
        return True
    if "auth_sessions" in partes:
        return True
    return False


def listar_arquivos_manifesto():
    arquivos = []
    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)

        novos_dirs = []
        for d in dirs:
            p = base_path / d
            if deve_ignorar_manifesto(p):
                continue
            novos_dirs.append(d)
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
    gravar_texto(
        path,
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n"
    )


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
            destino_item.parent.mkdir(parents=True, exist_ok=True)
            if origem.is_dir():
                shutil.copytree(origem, destino_item, dirs_exist_ok=True)
            else:
                shutil.copy2(origem, destino_item)
            copiados.append(nome)
        except Exception as exc:
            erros.append({
                "arquivo": nome,
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def validar_sem_asterisco_indevido(conteudo, nome):
    if "*" in conteudo:
        raise ValueError(
            "Validacao bloqueou a geracao de "
            + nome
            + " por conter caractere asterisco."
        )


def conteudo_docker_compose_mysql():
    conteudo = """version: '3.8'

services:
  app:
    build: .
    container_name: whatsapp_bot_app
    restart: always
    env_file:
      - .env
    ports:
      - "${PORT:-50010}:50010"
    volumes:
      - .:/usr/src/app
      - ./auth_sessions:/usr/src/app/auth_sessions
      - ./public/uploads:/usr/src/app/public/uploads
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  db:
    image: mysql:8.0
    container_name: whatsapp_bot_db
    restart: always
    command: --default-authentication-plugin=mysql_native_password
    environment:
      MYSQL_DATABASE: ${DB_NAME}
      MYSQL_USER: ${DB_USER}
      MYSQL_PASSWORD: ${DB_PASS}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-root_altere_aqui}
      TZ: America/Sao_Paulo
    ports:
      - "3306:3306"
    volumes:
      - mysqldata:/var/lib/mysql
    healthcheck:
      test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -u root -p$${MYSQL_ROOT_PASSWORD} || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

  redis:
    image: redis:7-alpine
    container_name: whatsapp_bot_redis
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD:-redis_altere_aqui}
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

volumes:
  mysqldata:
  redisdata:
"""
    validar_sem_asterisco_indevido(conteudo, "docker-compose.yml")
    return conteudo


def aplicar_docker_compose():
    path = ROOT / "docker-compose.yml"
    anterior = ler_texto(path)
    novo = conteudo_docker_compose_mysql()

    gravar_texto(path, novo)

    return {
        "arquivo": "docker-compose.yml",
        "existia_antes": anterior is not None,
        "alterado": anterior != novo,
        "sha256_depois": sha256_arquivo(path)
    }


def validar_docker_compose():
    path = ROOT / "docker-compose.yml"
    texto = ler_texto(path)

    if texto is None:
        return {
            "ok": False,
            "erros": ["docker-compose.yml nao encontrado ou ilegivel"],
            "avisos": []
        }

    proibidos = [
        "postgres",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "pgdata"
    ]

    obrigatorios = [
        "mysql:8.0",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_ROOT_PASSWORD",
        "mysqldata",
        "mysqladmin ping"
    ]

    erros = []
    avisos = []

    texto_lower = texto.lower()

    for termo in proibidos:
        if termo.lower() in texto_lower:
            erros.append("Termo proibido ainda presente: " + termo)

    for termo in obrigatorios:
        if termo not in texto:
            erros.append("Termo obrigatorio ausente: " + termo)

    if "${DB_NAME}" not in texto:
        erros.append("Variavel DB_NAME nao encontrada no compose")

    if "${DB_USER}" not in texto:
        erros.append("Variavel DB_USER nao encontrada no compose")

    if "${DB_PASS}" not in texto:
        erros.append("Variavel DB_PASS nao encontrada no compose")

    if "${REDIS_PASSWORD:-redis_altere_aqui}" not in texto:
        avisos.append("Fallback de REDIS_PASSWORD nao encontrado no formato esperado")

    return {
        "ok": len(erros) == 0,
        "erros": erros,
        "avisos": avisos
    }


def atualizar_env_example():
    path = ROOT / ".env.example"
    texto = ler_texto(path)

    if texto is None:
        texto = ""

    alterado = False

    if "MYSQL_ROOT_PASSWORD=" not in texto:
        if texto and not texto.endswith("\n"):
            texto += "\n"
        texto += "\n# MySQL Docker\n"
        texto += "MYSQL_ROOT_PASSWORD=root_altere_aqui\n"
        alterado = True

    validar_sem_asterisco_indevido(texto, ".env.example")
    gravar_texto(path, texto)

    return {
        "arquivo": ".env.example",
        "alterado": alterado,
        "sha256_depois": sha256_arquivo(path)
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_03_INICIO -->"
    marcador_fim = "<!-- ETAPA_03_FIM -->"

    secao = []
    secao.append("")
    secao.append(marcador_inicio)
    secao.append("## " + titulo)
    secao.append("")
    secao.extend(corpo)
    secao.append(marcador_fim)
    secao.append("")

    bloco = "\n".join(secao)

    padrao = re.compile(
        re.escape(marcador_inicio)
        + r".*?"
        + re.escape(marcador_fim),
        re.DOTALL
    )

    if padrao.search(texto_atual):
        novo = padrao.sub(bloco.strip(), texto_atual)
    else:
        if not texto_atual.endswith("\n"):
            texto_atual += "\n"
        novo = texto_atual + bloco

    validar_sem_asterisco_indevido(novo, nome)
    gravar_texto(path, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 03 - Docker alinhado ao MySQL",
        [
            "Data: " + data,
            "",
            "Foi corrigida a configuracao do docker-compose.yml para usar MySQL 8.",
            "A decisao foi manter o padrao de variaveis DB_HOST, DB_USER, DB_PASS e DB_NAME ja usado pelo projeto.",
            "O Redis foi preservado no docker-compose.yml.",
            "Esta etapa nao alterou controllers, rotas, banco em codigo, package.json ou regras de negocio."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 03 - Correcao do Docker para MySQL",
        [
            "Data: " + data,
            "",
            "Substituido servico db baseado em PostgreSQL por MySQL 8.",
            "Substituido volume pgdata por mysqldata.",
            "Ajustado healthcheck do banco para mysqladmin ping.",
            "Preservado servico Redis.",
            "Atualizado .env.example com MYSQL_ROOT_PASSWORD quando necessario.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 03 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido alinhar Docker ao MySQL porque o ambiente do projeto usa variaveis DB_HOST, DB_USER, DB_PASS e DB_NAME.",
            "Decidido nao alterar config/db.js nesta etapa para reduzir risco.",
            "Decidido preservar Redis e apenas padronizar fallback de senha.",
            "Decidido manter Docker e validacao de sintaxe JavaScript em etapas separadas."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 03",
        [
            "Data: " + data,
            "",
            "Validar docker compose config no servidor.",
            "Validar subida dos containers em ambiente controlado.",
            "Confirmar se a porta 3306 deve ficar exposta publicamente ou apenas internamente.",
            "Revisar config/db.js e setup_db.js na proxima etapa.",
            "Validar sintaxe, imports, controllers, rotas e fluxo de inicializacao.",
            "Planejar atualizacao de dependencias com alerta em etapa separada."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 03 - Corrigir Docker para MySQL")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Docker alterado: " + str(relatorio["docker_compose"]["alterado"]))
    linhas.append("- .env.example alterado: " + str(relatorio["env_example"]["alterado"]))
    linhas.append("")

    linhas.append("## Validacao do docker-compose.yml")
    linhas.append("")
    linhas.append("- Validacao OK: " + str(relatorio["validacao_docker"]["ok"]))

    if relatorio["validacao_docker"]["erros"]:
        linhas.append("- Erros:")
        for erro in relatorio["validacao_docker"]["erros"]:
            linhas.append("  - " + erro)
    else:
        linhas.append("- Erros: nenhum")

    if relatorio["validacao_docker"]["avisos"]:
        linhas.append("- Avisos:")
        for aviso in relatorio["validacao_docker"]["avisos"]:
            linhas.append("  - " + aviso)
    else:
        linhas.append("- Avisos: nenhum")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Arquivos principais")
    linhas.append("")
    linhas.append("- docker-compose.yml")
    linhas.append("- .env.example")
    linhas.append("- reports/etapa_03_corrigir_docker_mysql.json")
    linhas.append("- reports/etapa_03_corrigir_docker_mysql.md")
    linhas.append("")

    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 04: validar sintaxe, imports, estrutura de DB, setup_db.js, controllers e rotas.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_03_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_03_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    docker_resultado = aplicar_docker_compose()
    env_resultado = atualizar_env_example()
    validacao = validar_docker_compose()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker_compose": docker_resultado,
        "env_example": env_resultado,
        "validacao_docker": validacao
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_03_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_03_corrigir_docker_mysql.json"
    md_path = REPORTS_DIR / "etapa_03_corrigir_docker_mysql.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 03 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Validacao Docker OK: " + str(validacao["ok"]))

    if validacao["erros"]:
        print("")
        print("Erros encontrados:")
        for erro in validacao["erros"]:
            print("- " + erro)

    if validacao["avisos"]:
        print("")
        print("Avisos:")
        for aviso in validacao["avisos"]:
            print("- " + aviso)

    if not validacao["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()