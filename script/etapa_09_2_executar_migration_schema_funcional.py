#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 09.2 - Executar migration de schema funcional PostgreSQL

Objetivo:
- Criar backup antes de alterar documentacao.
- Gerar manifesto antes e depois.
- Validar arquivo SQL da Etapa 09.1.
- Bloquear execucao se houver marcador HTML br no SQL.
- Criar backup logico do PostgreSQL via pg_dump quando possivel.
- Executar migration via docker compose exec -T db psql.
- Revalidar setores.ordem, horarios_atendimento e indice.
- Revalidar tabelas e colunas pendentes da Etapa 09.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Executa somente o SQL aprovado da migration funcional.
- Nao altera codigo JS.
- Nao altera .env.
- Nao altera docker-compose.yml.
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

MIGRATION_NAME = "20260706_schema_funcional_setores_horarios.sql"
MIGRATION_PATH = MIGRATIONS_DIR / MIGRATION_NAME

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
    "PENDENCIAS.md",
    "database/migrations/20260706_schema_funcional_setores_horarios.sql"
]

TABELAS_VALIDAR = [
    "empresas",
    "usuarios_painel",
    "contatos",
    "mensagens",
    "setores",
    "horarios_atendimento"
]

COLUNAS_VALIDAR = {
    "setores": [
        "id",
        "empresa_id",
        "nome",
        "ordem"
    ],
    "horarios_atendimento": [
        "id",
        "empresa_id",
        "dia_semana",
        "horario_abertura",
        "horario_fechamento",
        "inicio_almoco",
        "fim_almoco",
        "ativo",
        "created_at",
        "updated_at"
    ]
}

IGNORAR_MANIFESTO_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "public/uploads"
]


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


def run_cmd(cmd, timeout=60, input_text=None):
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )

        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": redigir(proc.stdout.strip())[:6000],
            "stderr": redigir(proc.stderr.strip())[:6000],
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


def run_cmd_binary_to_file(cmd, output_path, timeout=120):
    try:
        with open(output_path, "wb") as f:
            proc = subprocess.run(
                cmd,
                cwd=str(ROOT),
                stdout=f,
                stderr=subprocess.PIPE,
                timeout=timeout
            )

        stderr = proc.stderr.decode("utf-8", errors="replace")

        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout_file": rel(output_path),
            "stderr": redigir(stderr.strip())[:4000],
            "ok": proc.returncode == 0,
            "sha256": sha256_arquivo(output_path) if output_path.exists() else None,
            "tamanho_bytes": output_path.stat().st_size if output_path.exists() else None
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "returncode": None,
            "stdout_file": rel(output_path),
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


def executar_psql_stdin(sql_texto, db_user, db_name):
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        db_user,
        "-d",
        db_name
    ]

    return run_cmd(cmd, 120, input_text=sql_texto)


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


def validar_sql_migration():
    texto = ler_texto(MIGRATION_PATH)

    resultado = {
        "arquivo": rel(MIGRATION_PATH),
        "existe": MIGRATION_PATH.exists(),
        "ok": False,
        "erros": [],
        "sha256": sha256_arquivo(MIGRATION_PATH) if MIGRATION_PATH.exists() else None
    }

    if texto is None:
        resultado["erros"].append("Arquivo SQL ausente ou ilegivel")
        return resultado

    if "<br>" in texto:
        resultado["erros"].append("Arquivo SQL contem marcador HTML <br>")

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
        "TRUNCATE",
        "UPDATE "
    ]

    for termo in obrigatorios:
        if termo not in texto:
            resultado["erros"].append("Termo obrigatorio ausente: " + termo)

    upper = texto.upper()
    for termo in proibidos:
        if termo.upper() in upper:
            resultado["erros"].append("Termo proibido encontrado: " + termo)

    resultado["ok"] = len(resultado["erros"]) == 0
    return resultado


def criar_pg_dump(backup_dir, db_user, db_name):
    dump_path = backup_dir / ("pg_dump_pre_etapa_09_2_" + agora_stamp() + ".dump")

    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "pg_dump",
        "-U",
        db_user,
        "-d",
        db_name,
        "-Fc"
    ]

    return run_cmd_binary_to_file(cmd, dump_path, 180)


def validar_runtime(db_user, db_name):
    resultado = {
        "checks": {},
        "comandos": {},
        "ok": False
    }

    comandos = {
        "ping": "SELECT 1",
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
            "AND column_name IN ("
            "'id', 'empresa_id', 'dia_semana', 'horario_abertura', "
            "'horario_fechamento', 'inicio_almoco', 'fim_almoco', "
            "'ativo', 'created_at', 'updated_at'"
            ")"
        ),
        "indice_horarios": (
            "SELECT COUNT(1) "
            "FROM pg_class t "
            "JOIN pg_index ix ON t.oid = ix.indrelid "
            "JOIN pg_class i ON i.oid = ix.indexrelid "
            "WHERE t.relname = 'horarios_atendimento' "
            "AND i.relname = 'idx_horarios_atendimento_empresa_dia'"
        )
    }

    r_ping = executar_psql(comandos["ping"], db_user, db_name)
    resultado["comandos"]["ping"] = r_ping
    resultado["checks"]["ping_ok"] = r_ping.get("ok") and str(r_ping.get("stdout")).strip() == "1"

    r_ordem = executar_psql(comandos["setores_ordem_existe"], db_user, db_name)
    resultado["comandos"]["setores_ordem_existe"] = r_ordem
    ordem_count = linha_int(r_ordem.get("stdout"))
    resultado["checks"]["setores_ordem_existe"] = ordem_count == 1

    r_horarios = executar_psql(comandos["horarios_existe"], db_user, db_name)
    resultado["comandos"]["horarios_existe"] = r_horarios
    resultado["checks"]["horarios_atendimento_existe"] = linha_bool(r_horarios.get("stdout"))

    r_cols = executar_psql(comandos["horarios_colunas"], db_user, db_name)
    resultado["comandos"]["horarios_colunas"] = r_cols
    col_count = linha_int(r_cols.get("stdout"))
    resultado["checks"]["horarios_colunas_total"] = col_count
    resultado["checks"]["horarios_colunas_ok"] = col_count == 10

    r_idx = executar_psql(comandos["indice_horarios"], db_user, db_name)
    resultado["comandos"]["indice_horarios"] = r_idx
    idx_count = linha_int(r_idx.get("stdout"))
    resultado["checks"]["indice_horarios_existe"] = bool(idx_count and idx_count >= 1)

    comandos_ok = True
    for item in resultado["comandos"].values():
        if not item.get("ok"):
            comandos_ok = False

    resultado["ok"] = bool(
        comandos_ok and
        resultado["checks"]["ping_ok"] and
        resultado["checks"]["setores_ordem_existe"] and
        resultado["checks"]["horarios_atendimento_existe"] and
        resultado["checks"]["horarios_colunas_ok"] and
        resultado["checks"]["indice_horarios_existe"]
    )

    return resultado


def validar_tabelas_essenciais(db_user, db_name):
    resultado = {
        "tabelas": [],
        "ok": False
    }

    tudo_ok = True

    for tabela in TABELAS_VALIDAR:
        r_exists = executar_psql(
            "SELECT to_regclass('public." + tabela + "') IS NOT NULL",
            db_user,
            db_name
        )

        existe = linha_bool(r_exists.get("stdout"))

        r_count = {
            "ok": False,
            "stdout": "",
            "stderr": ""
        }
        total = None

        if existe is True:
            r_count = executar_psql("SELECT COUNT(1) FROM " + tabela, db_user, db_name)
            total = linha_int(r_count.get("stdout"))

        item = {
            "tabela": tabela,
            "existe": existe,
            "count_ok": r_count.get("ok") if existe is True else False,
            "total_registros": total,
            "erro_exists": r_exists.get("stderr") if not r_exists.get("ok") else "",
            "erro_count": r_count.get("stderr") if existe is True and not r_count.get("ok") else ""
        }

        if item["existe"] is not True or item["count_ok"] is not True:
            tudo_ok = False

        resultado["tabelas"].append(item)

    resultado["ok"] = tudo_ok
    return resultado


def validar_colunas_pendentes(db_user, db_name):
    resultado = {
        "tabelas": [],
        "ok": False
    }

    tudo_ok = True

    for tabela, colunas in COLUNAS_VALIDAR.items():
        lista = "', '".join(colunas)
        sql = (
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name = '" + tabela + "' "
            "AND column_name IN ('" + lista + "') "
            "ORDER BY column_name"
        )

        r = executar_psql(sql, db_user, db_name)

        encontradas = []
        if r.get("stdout"):
            encontradas = [x.strip() for x in r["stdout"].splitlines() if x.strip()]

        faltantes = []
        for col in colunas:
            if col not in encontradas:
                faltantes.append(col)

        item = {
            "tabela": tabela,
            "esperadas": colunas,
            "encontradas": encontradas,
            "faltantes": faltantes,
            "ok": r.get("ok") and len(faltantes) == 0,
            "erro": r.get("stderr") if not r.get("ok") else ""
        }

        if not item["ok"]:
            tudo_ok = False

        resultado["tabelas"].append(item)

    resultado["ok"] = tudo_ok
    return resultado


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_09_2_INICIO -->"
    marcador_fim = "<!-- ETAPA_09_2_FIM -->"

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
    pre = relatorio["runtime_antes"]["checks"]
    pos = relatorio["runtime_depois"]["checks"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 09.2 - Migration funcional executada",
        [
            "Data: " + data,
            "",
            "Foi executada a migration de schema funcional PostgreSQL aprovada na Etapa 09.1.",
            "setores.ordem antes: " + str(pre.get("setores_ordem_existe")) + ".",
            "setores.ordem depois: " + str(pos.get("setores_ordem_existe")) + ".",
            "horarios_atendimento antes: " + str(pre.get("horarios_atendimento_existe")) + ".",
            "horarios_atendimento depois: " + str(pos.get("horarios_atendimento_existe")) + ".",
            "Indice de horarios depois: " + str(pos.get("indice_horarios_existe")) + ".",
            "Validacao runtime final OK: " + str(relatorio["runtime_depois"]["ok"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 09.2 - Execucao de migration funcional",
        [
            "Data: " + data,
            "",
            "Executada migration para complementar schema funcional.",
            "Adicionada coluna ordem em setores quando ausente.",
            "Criada tabela horarios_atendimento quando ausente.",
            "Criado indice de horarios por empresa e dia.",
            "Repetida validacao somente leitura apos execucao.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 09.2 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido executar a migration idempotente aprovada na Etapa 09.1.",
            "Decidido usar psql com ON_ERROR_STOP para interromper em erro.",
            "Decidido gerar backup logico antes da execucao quando pg_dump estiver disponivel.",
            "Decidido repetir validacao somente leitura apos aplicar o schema."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Executar testes funcionais com escrita em ambiente controlado.",
        "Validar criacao de empresa e usuario admin.",
        "Validar fluxo de recebimento de mensagem e upsert de contato.",
        "Validar fluxo de envio de mensagem e registro no historico.",
        "Validar telas de setores e horarios de atendimento.",
        "Revisar achados de baixa severidade, especialmente booleanos numericos."
    ]

    if not relatorio["runtime_depois"]["ok"]:
        pendencias.insert(2, "Corrigir pendencias da validacao runtime final da Etapa 09.2.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 09.2",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    pre = relatorio["runtime_antes"]["checks"]
    pos = relatorio["runtime_depois"]["checks"]

    linhas.append("# Etapa 09.2 - Executar migration de schema funcional")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup documental criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Backup logico criado: " + str(relatorio["pg_dump"]["ok"]))
    linhas.append("- Arquivo backup logico: " + str(relatorio["pg_dump"].get("stdout_file")))
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- SQL validado: " + str(relatorio["validacao_sql"]["ok"]))
    linhas.append("- Migration executada OK: " + str(relatorio["execucao_migration"]["ok"]))
    linhas.append("- Runtime antes OK: " + str(relatorio["runtime_antes"]["ok"]))
    linhas.append("- Runtime depois OK: " + str(relatorio["runtime_depois"]["ok"]))
    linhas.append("- Tabelas essenciais OK: " + str(relatorio["validacao_tabelas"]["ok"]))
    linhas.append("- Colunas pendentes OK: " + str(relatorio["validacao_colunas"]["ok"]))
    linhas.append("")

    linhas.append("## Validacao antes e depois")
    linhas.append("")
    linhas.append("- setores.ordem antes: " + str(pre.get("setores_ordem_existe")))
    linhas.append("- setores.ordem depois: " + str(pos.get("setores_ordem_existe")))
    linhas.append("- horarios_atendimento antes: " + str(pre.get("horarios_atendimento_existe")))
    linhas.append("- horarios_atendimento depois: " + str(pos.get("horarios_atendimento_existe")))
    linhas.append("- horarios colunas depois total: " + str(pos.get("horarios_colunas_total")))
    linhas.append("- indice horarios depois: " + str(pos.get("indice_horarios_existe")))

    linhas.append("")
    linhas.append("## Validacao do SQL")
    linhas.append("")
    linhas.append("- Arquivo: " + relatorio["validacao_sql"]["arquivo"])
    linhas.append("- SHA256: " + str(relatorio["validacao_sql"]["sha256"]))
    linhas.append("- OK: " + str(relatorio["validacao_sql"]["ok"]))
    if relatorio["validacao_sql"]["erros"]:
        for erro in relatorio["validacao_sql"]["erros"]:
            linhas.append("  - " + erro)
    else:
        linhas.append("- Erros: nenhum")

    linhas.append("")
    linhas.append("## Execucao da migration")
    linhas.append("")
    linhas.append("- OK: " + str(relatorio["execucao_migration"]["ok"]))
    linhas.append("- Return code: " + str(relatorio["execucao_migration"]["returncode"]))
    if relatorio["execucao_migration"].get("stdout"):
        linhas.append("- stdout:")
        for linha in relatorio["execucao_migration"]["stdout"].splitlines():
            linhas.append("  - " + linha[:240])
    if relatorio["execucao_migration"].get("stderr"):
        linhas.append("- stderr:")
        for linha in relatorio["execucao_migration"]["stderr"].splitlines():
            linhas.append("  - " + linha[:240])

    linhas.append("")
    linhas.append("## Tabelas essenciais")
    linhas.append("")
    for item in relatorio["validacao_tabelas"]["tabelas"]:
        linhas.append(
            "- "
            + item["tabela"]
            + ": existe="
            + str(item["existe"])
            + ", count_ok="
            + str(item["count_ok"])
            + ", total="
            + str(item["total_registros"])
        )

    linhas.append("")
    linhas.append("## Colunas pendentes")
    linhas.append("")
    for item in relatorio["validacao_colunas"]["tabelas"]:
        linhas.append(
            "- "
            + item["tabela"]
            + ": ok="
            + str(item["ok"])
            + ", faltantes="
            + ", ".join(item["faltantes"])
        )

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- A migration executada foi a migration aprovada na Etapa 09.1.")
    linhas.append("- Apos a execucao, a validacao foi feita somente leitura.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 10: executar testes funcionais com escrita em ambiente controlado.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_09_2_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_09_2_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    env = parse_env()
    db_user = env.get("DB_USER") or "postgres"
    db_name = env.get("DB_NAME") or "postgres"

    docker = verificar_docker()
    validacao_sql = validar_sql_migration()
    runtime_antes = validar_runtime(db_user, db_name)

    pg_dump = criar_pg_dump(backup_dir, db_user, db_name)

    execucao_migration = {
        "ok": False,
        "returncode": None,
        "stdout": "",
        "stderr": "Migration nao executada porque validacao SQL falhou."
    }

    if validacao_sql["ok"]:
        sql_texto = ler_texto(MIGRATION_PATH)
        execucao_migration = executar_psql_stdin(sql_texto, db_user, db_name)

    runtime_depois = validar_runtime(db_user, db_name)
    validacao_tabelas = validar_tabelas_essenciais(db_user, db_name)
    validacao_colunas = validar_colunas_pendentes(db_user, db_name)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "validacao_sql": validacao_sql,
        "runtime_antes": runtime_antes,
        "pg_dump": pg_dump,
        "execucao_migration": execucao_migration,
        "runtime_depois": runtime_depois,
        "validacao_tabelas": validacao_tabelas,
        "validacao_colunas": validacao_colunas
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_09_2_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_09_2_executar_migration_schema_funcional.json"
    md_path = REPORTS_DIR / "etapa_09_2_executar_migration_schema_funcional.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 09.2 concluida.")
    print("Backup documental: " + backup["destino"])
    print("Backup logico OK: " + str(pg_dump["ok"]))
    print("Backup logico arquivo: " + str(pg_dump.get("stdout_file")))
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("SQL validado OK: " + str(validacao_sql["ok"]))
    print("Migration executada OK: " + str(execucao_migration["ok"]))
    print("Runtime antes OK: " + str(runtime_antes["ok"]))
    print("Runtime depois OK: " + str(runtime_depois["ok"]))
    print("Tabelas essenciais OK: " + str(validacao_tabelas["ok"]))
    print("Colunas pendentes OK: " + str(validacao_colunas["ok"]))

    if not execucao_migration["ok"]:
        print("")
        print("A migration nao foi executada com sucesso. Consulte o relatorio.")

    if not runtime_depois["ok"]:
        print("")
        print("A validacao runtime final ainda possui pendencias. Consulte o relatorio.")


if __name__ == "__main__":
    main()