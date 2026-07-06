#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 03.1 - Padronizar projeto para PostgreSQL

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Corrigir docker-compose.yml para PostgreSQL.
- Atualizar .env.example para PostgreSQL.
- Remover MYSQL_ROOT_PASSWORD do .env.example.
- Gerar relatorio de rastros MySQL ainda presentes no projeto.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Nao altera .env real.
- Nao altera controllers.
- Nao altera config/db.js.
- Nao altera setup_db.js.
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

EXTENSOES_ANALISE = [
    ".js",
    ".json",
    ".md",
    ".yml",
    ".yaml",
    ".env",
    ".ejs",
    ".sql",
    ".txt",
    ".css",
    ".sh",
    ".py"
]

TERMOS_MYSQL = [
    "mysql",
    "mysql2",
    "mariadb",
    "MYSQL_",
    "mysqldata",
    "mysqladmin",
    "DB_PORT=3306",
    "3306"
]

TERMOS_PROIBIDOS_DOCKER = [
    "mysql:8.0",
    "mysql_native_password",
    "MYSQL_DATABASE",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_ROOT_PASSWORD",
    "mysqldata",
    "mysqladmin"
]

TERMOS_OBRIGATORIOS_DOCKER = [
    "postgres:15-alpine",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "pg_isready",
    "pgdata"
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


def validar_sem_asterisco_indevido(conteudo, nome):
    if chr(42) in conteudo:
        raise ValueError(
            "Validacao bloqueou a geracao de "
            + nome
            + " por conter caractere asterisco."
        )


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


def conteudo_docker_compose_postgres():
    conteudo = """services:
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
    image: postgres:15-alpine
    container_name: whatsapp_bot_db
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASS}
      POSTGRES_DB: ${DB_NAME}
      TZ: America/Sao_Paulo
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
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
  pgdata:
  redisdata:
"""
    validar_sem_asterisco_indevido(conteudo, "docker-compose.yml")
    return conteudo


def aplicar_docker_compose():
    path = ROOT / "docker-compose.yml"
    anterior = ler_texto(path)
    novo = conteudo_docker_compose_postgres()

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

    erros = []
    avisos = []
    texto_lower = texto.lower()

    for termo in TERMOS_PROIBIDOS_DOCKER:
        if termo.lower() in texto_lower:
            erros.append("Termo MySQL ainda presente no Docker: " + termo)

    for termo in TERMOS_OBRIGATORIOS_DOCKER:
        if termo not in texto:
            erros.append("Termo PostgreSQL obrigatorio ausente: " + termo)

    if "version:" in texto_lower:
        avisos.append("Atributo version ainda presente no compose")

    if "${DB_USER}" not in texto:
        erros.append("Variavel DB_USER ausente no compose")

    if "${DB_PASS}" not in texto:
        erros.append("Variavel DB_PASS ausente no compose")

    if "${DB_NAME}" not in texto:
        erros.append("Variavel DB_NAME ausente no compose")

    if "${DB_PORT:-5432}" not in texto:
        avisos.append("Fallback DB_PORT 5432 nao encontrado no formato esperado")

    return {
        "ok": len(erros) == 0,
        "erros": erros,
        "avisos": avisos
    }


def gerar_env_example_postgres():
    conteudo = """# ============================================
# Exemplo de variaveis de ambiente
# Copie este arquivo para .env e preencha valores reais
# Nunca commite o arquivo .env
# ============================================

# Banco de dados PostgreSQL
DB_HOST=db
DB_PORT=5432
DB_USER=postgres
DB_PASS=altere_aqui
DB_NAME=postgres

# Servidor
PORT=50010
NODE_ENV=production

# Email SMTP
SMTP_HOST=smtp.exemplo.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=nao-responda@exemplo.com
SMTP_PASS=altere_aqui

# Seguranca
SUPER_ADMIN_PASS=altere_aqui
JWT_SECRET=gere_uma_chave_forte
SESSION_SECRET=gere_uma_chave_forte

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=altere_aqui
"""
    validar_sem_asterisco_indevido(conteudo, ".env.example")
    return conteudo


def aplicar_env_example():
    path = ROOT / ".env.example"
    anterior = ler_texto(path)
    novo = gerar_env_example_postgres()

    gravar_texto(path, novo)

    return {
        "arquivo": ".env.example",
        "existia_antes": anterior is not None,
        "alterado": anterior != novo,
        "sha256_depois": sha256_arquivo(path)
    }


def validar_env_example():
    path = ROOT / ".env.example"
    texto = ler_texto(path)

    if texto is None:
        return {
            "ok": False,
            "erros": [".env.example nao encontrado ou ilegivel"],
            "avisos": []
        }

    erros = []
    avisos = []

    obrigatorios = [
        "DB_HOST=db",
        "DB_PORT=5432",
        "DB_USER=postgres",
        "DB_PASS=altere_aqui",
        "DB_NAME=postgres",
        "REDIS_HOST=redis"
    ]

    proibidos = [
        "MYSQL_ROOT_PASSWORD",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "DB_PORT=3306"
    ]

    texto_lower = texto.lower()

    for termo in obrigatorios:
        if termo not in texto:
            erros.append("Linha obrigatoria ausente em .env.example: " + termo)

    for termo in proibidos:
        if termo.lower() in texto_lower:
            erros.append("Linha MySQL proibida em .env.example: " + termo)

    return {
        "ok": len(erros) == 0,
        "erros": erros,
        "avisos": avisos
    }


def deve_ignorar_scan(path):
    partes = set(path.parts)

    if "node_modules" in partes:
        return True
    if ".git" in partes:
        return True
    if "backups" in partes:
        return True
    if "auth_sessions" in partes:
        return True

    nome = path.name
    if nome.endswith(".lock"):
        return True

    return False


def linha_redigida(linha):
    if "=" not in linha:
        return linha.strip()[:160]

    esquerda = linha.split("=", 1)[0].strip()
    esquerda_upper = esquerda.upper()

    sensiveis = [
        "PASS",
        "PASSWORD",
        "SECRET",
        "TOKEN",
        "KEY",
        "SENHA"
    ]

    for termo in sensiveis:
        if termo in esquerda_upper:
            return esquerda + "=<REDIGIDO>"

    return linha.strip()[:160]


def escanear_rastros_mysql():
    achados = []

    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)

        novos_dirs = []
        for nome_dir in dirs:
            p = base_path / nome_dir
            if deve_ignorar_scan(p):
                continue
            novos_dirs.append(nome_dir)
        dirs[:] = novos_dirs

        for nome in files:
            p = base_path / nome

            if deve_ignorar_scan(p):
                continue

            ext = p.suffix.lower()
            if ext not in EXTENSOES_ANALISE and p.name not in [".env", ".env.example"]:
                continue

            texto = ler_texto(p)
            if texto is None:
                continue

            linhas = texto.splitlines()
            for numero, linha in enumerate(linhas, start=1):
                linha_lower = linha.lower()
                termos_encontrados = []

                for termo in TERMOS_MYSQL:
                    if termo.lower() in linha_lower:
                        termos_encontrados.append(termo)

                if termos_encontrados:
                    achados.append({
                        "arquivo": rel(p),
                        "linha": numero,
                        "termos": termos_encontrados,
                        "conteudo_redigido": linha_redigida(linha)
                    })

    return achados


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_03_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_03_1_FIM -->"

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
        + r".+?"
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
    total_rastros = str(len(relatorio["rastros_mysql"]))

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 03.1 - Padronizacao PostgreSQL",
        [
            "Data: " + data,
            "",
            "A decisao tecnica foi revisada: o banco oficial do projeto passa a ser PostgreSQL.",
            "O docker-compose.yml foi padronizado para PostgreSQL 15 Alpine.",
            "O .env.example foi padronizado para DB_PORT 5432 e variaveis DB compatveis com PostgreSQL.",
            "Esta etapa nao alterou .env real, controllers, config/db.js, setup_db.js, package.json ou regras de negocio.",
            "Foram encontrados " + total_rastros + " rastros de MySQL para analise na proxima etapa."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 03.1 - Padronizacao PostgreSQL",
        [
            "Data: " + data,
            "",
            "Corrigido docker-compose.yml para usar postgres:15-alpine.",
            "Removidas configuracoes MySQL do docker-compose.yml.",
            "Substituido volume mysqldata por pgdata.",
            "Ajustado healthcheck do banco para pg_isready.",
            "Atualizado .env.example para PostgreSQL.",
            "Gerado relatorio de rastros MySQL ainda presentes no projeto."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 03.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido padronizar PostgreSQL como banco oficial do projeto.",
            "Decidido nao alterar o .env real automaticamente para evitar perda de credenciais locais.",
            "Decidido manter a correcao de codigo e queries para a Etapa 04.",
            "Decidido preservar Redis e apenas alinhar sua referencia no .env.example.",
            "Decidido remover o atributo version do docker-compose.yml para evitar aviso do Docker Compose atual."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 03.1",
        [
            "Data: " + data,
            "",
            "Revisar rastros MySQL listados no relatorio da Etapa 03.1.",
            "Validar config/db.js para PostgreSQL.",
            "Validar setup_db.js e scripts SQL para PostgreSQL.",
            "Validar controllers, rotas, imports e queries.",
            "Executar docker compose config apos a etapa.",
            "Planejar rotacao de credenciais reais expostas anteriormente."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 03.1 - Padronizar PostgreSQL")
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
    linhas.append("## Validacao do .env.example")
    linhas.append("")
    linhas.append("- Validacao OK: " + str(relatorio["validacao_env_example"]["ok"]))

    if relatorio["validacao_env_example"]["erros"]:
        linhas.append("- Erros:")
        for erro in relatorio["validacao_env_example"]["erros"]:
            linhas.append("  - " + erro)
    else:
        linhas.append("- Erros: nenhum")

    if relatorio["validacao_env_example"]["avisos"]:
        linhas.append("- Avisos:")
        for aviso in relatorio["validacao_env_example"]["avisos"]:
            linhas.append("  - " + aviso)
    else:
        linhas.append("- Avisos: nenhum")

    linhas.append("")
    linhas.append("## Rastros MySQL encontrados")
    linhas.append("")
    linhas.append("- Total: " + str(len(relatorio["rastros_mysql"])))

    if relatorio["rastros_mysql"]:
        limite = 80
        for item in relatorio["rastros_mysql"][:limite]:
            linhas.append(
                "- "
                + item["arquivo"]
                + ":"
                + str(item["linha"])
                + " termos="
                + ", ".join(item["termos"])
                + " trecho="
                + item["conteudo_redigido"]
            )
        if len(relatorio["rastros_mysql"]) > limite:
            linhas.append("- Lista truncada no Markdown. Consulte o JSON completo.")
    else:
        linhas.append("- Nenhum rastro MySQL encontrado.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 04: validar e corrigir config/db.js, setup_db.js, controllers, rotas, imports e queries para PostgreSQL.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_03_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_03_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    docker_resultado = aplicar_docker_compose()
    env_resultado = aplicar_env_example()

    validacao_docker = validar_docker_compose()
    validacao_env = validar_env_example()
    rastros_mysql = escanear_rastros_mysql()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker_compose": docker_resultado,
        "env_example": env_resultado,
        "validacao_docker": validacao_docker,
        "validacao_env_example": validacao_env,
        "rastros_mysql": rastros_mysql
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_03_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_03_1_padronizar_postgres.json"
    md_path = REPORTS_DIR / "etapa_03_1_padronizar_postgres.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 03.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Validacao Docker OK: " + str(validacao_docker["ok"]))
    print("Validacao .env.example OK: " + str(validacao_env["ok"]))
    print("Rastros MySQL encontrados: " + str(len(rastros_mysql)))

    if validacao_docker["erros"]:
        print("")
        print("Erros no Docker:")
        for erro in validacao_docker["erros"]:
            print("- " + erro)

    if validacao_env["erros"]:
        print("")
        print("Erros no .env.example:")
        for erro in validacao_env["erros"]:
            print("- " + erro)

    if not validacao_docker["ok"]:
        raise SystemExit(1)

    if not validacao_env["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
