#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 09.1 - Corrigir schema funcional PostgreSQL

Objetivo:
- Criar backup antes de alterar documentacao e migrations.
- Gerar manifesto antes e depois.
- Preparar migration PostgreSQL idempotente para:
  - adicionar coluna ordem em setores se nao existir
  - criar tabela horarios_atendimento se nao existir
  - criar indice por empresa e dia da semana
- Validar runtime via Docker quando possivel.
- Nao executar migration automaticamente.
- Nao alterar dados.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Observacao:
- Se precisar acessar Docker, execute com sudo:
  sudo python3 etapa_09_1_corrigir_schema_funcional_postgres.py
"""

import os
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"
MIGRATIONS_DIR = ROOT / "database" / "migrations"

MAX_LEITURA = 3145728

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
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
    "public/uploads"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_data():
    return datetime.now().strftime("%Y%m%d")


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
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)


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
    gravar_texto(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def copiar_item(origem, destino):
    if origem.is_dir():
        shutil.copytree(origem, destino, dirs_exist_ok=True)
    else:
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

    if MIGRATIONS_DIR.exists():
        try:
            copiar_item(MIGRATIONS_DIR, destino / "database" / "migrations")
            copiados.append("database/migrations/")
        except Exception as exc:
            erros.append({
                "item": "database/migrations/",
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def parse_env():
    env_path = ROOT / ".env"
    texto = ler_texto(env_path)
    dados = {}

    if texto is None:
        return dados

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

    return dados


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

    return valores


def redigir(texto):
    if texto is None:
        return texto

    out = str(texto)

    for valor in valores_sensiveis_env():
        if valor:
            out = out.replace(valor, "<REDIGIDO>")

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
            "stdout": redigir(proc.stdout.strip())[:5000],
            "stderr": redigir(proc.stderr.strip())[:5000],
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


def executar_psql(sql, db_user, db_name):
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-At",
        "-F",
        "|",
        "-c",
        sql
    ]

    return run_cmd(cmd, 60)


def linha_bool(stdout):
    linhas = str(stdout or "").strip().splitlines()
    if not linhas:
        return None

    valor = linhas[-1].strip().lower()

    if valor in ["t", "true", "1"]:
        return True

    if valor in ["f", "false", "0"]:
        return False

    return None


def linha_int(stdout):
    linhas = str(stdout or "").strip().splitlines()
    if not linhas:
        return None

    try:
        return int(linhas[-1].strip())
    except Exception:
        return None


def verificar_docker():
    return {
        "docker_version": run_cmd(["docker", "--version"], 20),
        "docker_compose_version": run_cmd(["docker", "compose", "version"], 20),
        "docker_compose_ps": run_cmd(["docker", "compose", "ps"], 30)
    }


def validar_runtime_atual():
    env = parse_env()
    db_user = env.get("DB_USER") or "postgres"
    db_name = env.get("DB_NAME") or "postgres"

    resultado = {
        "env_encontrado": (ROOT / ".env").exists(),
        "db_user_configurado": bool(env.get("DB_USER")),
        "db_name_configurado": bool(env.get("DB_NAME")),
        "checks": {},
        "comandos": {},
        "ok": False
    }

    comandos = {
        "setores_existe": "SELECT to_regclass('public.setores') IS NOT NULL",
        "setores_ordem_existe": (
            "SELECT COUNT(1) FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name = 'setores' "
            "AND column_name = 'ordem'"
        ),
        "horarios_existe": "SELECT to_regclass('public.horarios_atendimento') IS NOT NULL",
        "horarios_colunas": (
            "SELECT COUNT(1) FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name = 'horarios_atendimento' "
            "AND column_name IN ('id', 'empresa_id', 'dia_semana', 'horario_abertura', 'horario_fechamento', 'ativo')"
        )
    }

    r_setores = executar_psql(comandos["setores_existe"], db_user, db_name)
    resultado["comandos"]["setores_existe"] = r_setores
    resultado["checks"]["setores_existe"] = linha_bool(r_setores.get("stdout"))

    r_ordem = executar_psql(comandos["setores_ordem_existe"], db_user, db_name)
    resultado["comandos"]["setores_ordem_existe"] = r_ordem
    ordem_count = linha_int(r_ordem.get("stdout"))
    resultado["checks"]["setores_ordem_existe"] = ordem_count == 1

    r_horarios = executar_psql(comandos["horarios_existe"], db_user, db_name)
    resultado["comandos"]["horarios_existe"] = r_horarios
    resultado["checks"]["horarios_atendimento_existe"] = linha_bool(r_horarios.get("stdout"))

    r_h_cols = executar_psql(comandos["horarios_colunas"], db_user, db_name)
    resultado["comandos"]["horarios_colunas"] = r_h_cols
    h_cols_count = linha_int(r_h_cols.get("stdout"))
    resultado["checks"]["horarios_colunas_essenciais_total"] = h_cols_count
    resultado["checks"]["horarios_colunas_essenciais_ok"] = h_cols_count == 6

    comandos_ok = True
    for item in resultado["comandos"].values():
        if not item.get("ok"):
            comandos_ok = False

    resultado["ok"] = comandos_ok

    return resultado


def conteudo_migration():
    conteudo = """-- Etapa 09.1 - Schema funcional PostgreSQL
-- Objetivo: complementar schema usado pelas telas e rotas de atendimento
-- Revisar em ambiente controlado antes de executar em producao

BEGIN;

ALTER TABLE setores
ADD COLUMN IF NOT EXISTS ordem INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS horarios_atendimento (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    dia_semana INTEGER NOT NULL,
    horario_abertura TIME,
    horario_fechamento TIME,
    inicio_almoco TIME,
    fim_almoco TIME,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_horarios_atendimento_empresa_dia
ON horarios_atendimento (empresa_id, dia_semana);

COMMIT;
"""
    validar_sem_asterisco_indevido(conteudo, "migration schema funcional")
    return conteudo


def criar_migration(runtime):
    nome_arquivo = agora_data() + "_schema_funcional_setores_horarios.sql"
    path = MIGRATIONS_DIR / nome_arquivo

    resultado = {
        "arquivo": rel(path),
        "criada": False,
        "existia_antes": path.exists(),
        "sha256_depois": None
    }

    if path.exists():
        resultado["sha256_depois"] = sha256_arquivo(path)
        return resultado

    conteudo = conteudo_migration()
    gravar_texto(path, conteudo)

    resultado["criada"] = True
    resultado["sha256_depois"] = sha256_arquivo(path)

    return resultado


def validar_migration(path_rel):
    path = ROOT / path_rel
    texto = ler_texto(path)

    if texto is None:
        return {
            "ok": False,
            "erros": ["Arquivo de migration ausente ou ilegivel"]
        }

    erros = []

    obrigatorios = [
        "ALTER TABLE setores",
        "ADD COLUMN IF NOT EXISTS ordem",
        "CREATE TABLE IF NOT EXISTS horarios_atendimento",
        "CREATE INDEX IF NOT EXISTS idx_horarios_atendimento_empresa_dia",
        "ON horarios_atendimento (empresa_id, dia_semana)"
    ]

    proibidos = [
        "DROP TABLE",
        "DROP COLUMN",
        "DELETE FROM",
        "UPDATE ",
        "INSERT INTO"
    ]

    for termo in obrigatorios:
        if termo not in texto:
            erros.append("Termo obrigatorio ausente: " + termo)

    upper = texto.upper()
    for termo in proibidos:
        if termo.upper() in upper:
            erros.append("Termo proibido encontrado: " + termo)

    return {
        "ok": len(erros) == 0,
        "erros": erros
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_09_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_09_1_FIM -->"

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
    runtime = relatorio["runtime"]
    checks = runtime.get("checks", {})
    migration = relatorio["migration"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 09.1 - Schema funcional preparado",
        [
            "Data: " + data,
            "",
            "Foi preparada migration PostgreSQL para complementar o schema funcional.",
            "setores.ordem existente no runtime: " + str(checks.get("setores_ordem_existe")) + ".",
            "horarios_atendimento existente no runtime: " + str(checks.get("horarios_atendimento_existe")) + ".",
            "Migration criada: " + str(migration["criada"]) + ".",
            "Arquivo: " + str(migration["arquivo"]) + ".",
            "A migration nao foi executada automaticamente."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 09.1 - Migration de schema funcional",
        [
            "Data: " + data,
            "",
            "Criada migration idempotente para coluna ordem em setores.",
            "Criada migration idempotente para tabela horarios_atendimento.",
            "Criado indice para horarios_atendimento por empresa e dia da semana.",
            "Gerados backup, manifestos e relatorios da etapa.",
            "Nenhuma alteracao foi aplicada ao banco."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 09.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido preparar migration sem execucao automatica.",
            "Decidido usar ADD COLUMN IF NOT EXISTS e CREATE TABLE IF NOT EXISTS.",
            "Decidido incluir campos de almoco por compatibilidade com utilitario de atendimento.",
            "Decidido validar novamente em etapa posterior apos execucao controlada."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 09.1",
        [
            "Data: " + data,
            "",
            "Revisar a migration criada antes de executar.",
            "Executar a migration em ambiente controlado.",
            "Repetir validacao somente leitura da Etapa 09 apos aplicar migration.",
            "Executar testes funcionais com escrita em ambiente controlado.",
            "Validar telas de setores e horarios de atendimento."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    runtime = relatorio["runtime"]
    checks = runtime.get("checks", {})
    migration = relatorio["migration"]
    validacao = relatorio["validacao_migration"]

    linhas = []

    linhas.append("# Etapa 09.1 - Corrigir schema funcional PostgreSQL")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Runtime validado: " + str(runtime["ok"]))
    linhas.append("- setores existe: " + str(checks.get("setores_existe")))
    linhas.append("- setores.ordem existe: " + str(checks.get("setores_ordem_existe")))
    linhas.append("- horarios_atendimento existe: " + str(checks.get("horarios_atendimento_existe")))
    linhas.append("- Migration criada: " + str(migration["criada"]))
    linhas.append("- Arquivo migration: " + str(migration["arquivo"]))
    linhas.append("- Validacao migration OK: " + str(validacao["ok"]))
    linhas.append("")

    linhas.append("## Migration preparada")
    linhas.append("")
    linhas.append("- Arquivo: " + str(migration["arquivo"]))
    linhas.append("- Criada nesta etapa: " + str(migration["criada"]))
    linhas.append("- Existia antes: " + str(migration["existia_antes"]))
    linhas.append("- SHA256: " + str(migration["sha256_depois"]))

    linhas.append("")
    linhas.append("## Validacao da migration")
    linhas.append("")
    linhas.append("- OK: " + str(validacao["ok"]))
    if validacao["erros"]:
        for erro in validacao["erros"]:
            linhas.append("  - " + erro)
    else:
        linhas.append("- Erros: nenhum")

    linhas.append("")
    linhas.append("## Conteudo da migration")
    linhas.append("")
    linhas.append("Arquivo gerado em: " + str(migration["arquivo"]))
    linhas.append("")
    linhas.append("```sql")
    texto_migration = ler_texto(ROOT / migration["arquivo"]) or ""
    texto_migration = texto_migration.replace(chr(42), "[asterisco]")
    linhas.append(texto_migration.rstrip())
    linhas.append("```")

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma alteracao foi aplicada ao banco.")
    linhas.append("- Nenhuma migration foi executada automaticamente.")
    linhas.append("- A execucao deve ser feita somente apos revisao.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 9.2: executar a migration em ambiente controlado e repetir a validacao somente leitura.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_09_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_09_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    docker = verificar_docker()
    runtime = validar_runtime_atual()
    migration = criar_migration(runtime)
    validacao_migration = validar_migration(migration["arquivo"])

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "runtime": runtime,
        "migration": migration,
        "validacao_migration": validacao_migration
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_09_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_09_1_corrigir_schema_funcional_postgres.json"
    md_path = REPORTS_DIR / "etapa_09_1_corrigir_schema_funcional_postgres.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    checks = runtime.get("checks", {})

    print("Etapa 09.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Runtime OK: " + str(runtime["ok"]))
    print("setores existe: " + str(checks.get("setores_existe")))
    print("setores.ordem existe: " + str(checks.get("setores_ordem_existe")))
    print("horarios_atendimento existe: " + str(checks.get("horarios_atendimento_existe")))
    print("Migration criada: " + str(migration["criada"]))
    print("Migration arquivo: " + str(migration["arquivo"]))
    print("Validacao migration OK: " + str(validacao_migration["ok"]))
    print("IMPORTANTE: a migration nao foi executada automaticamente.")


if __name__ == "__main__":
    main()