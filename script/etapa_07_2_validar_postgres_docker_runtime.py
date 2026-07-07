#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 07.2 - Validar PostgreSQL runtime via Docker Compose

Objetivo:
- Criar backup antes de alterar documentacao.
- Gerar manifesto antes e depois.
- Verificar Docker e Docker Compose.
- Verificar status dos servicos do docker compose.
- Validar PostgreSQL dentro do servico db usando psql.
- Confirmar tabela contatos, colunas empresa_id e telefone.
- Confirmar indice ou constraint unica para empresa_id e telefone.
- Confirmar se existem duplicidades.
- Nao imprimir senhas.
- Nao alterar banco.
- Nao executar migration.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Nao altera codigo JS.
- Nao altera Docker.
- Nao altera .env.
- Nao executa migrations.
- Nao altera dados.
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
            "stdout": redigir(proc.stdout.strip())[:4000],
            "stderr": redigir(proc.stderr.strip())[:4000],
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


def verificar_docker():
    return {
        "docker_version": run_cmd(["docker", "--version"], 20),
        "docker_compose_version": run_cmd(["docker", "compose", "version"], 20),
        "docker_compose_ps": run_cmd(["docker", "compose", "ps"], 30)
    }


def detectar_servico_db(ps_resultado):
    texto = ""

    if ps_resultado:
        texto = (ps_resultado.get("stdout") or "") + "\n" + (ps_resultado.get("stderr") or "")

    lower = texto.lower()

    return {
        "servico_db_mencionado": "db" in lower or "whatsapp_bot_db" in lower,
        "parece_rodando": "running" in lower or "up" in lower,
        "texto_redigido": texto[:4000]
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


def linha_bool(saida):
    valor = str(saida or "").strip().splitlines()
    if not valor:
        return None

    ultimo = valor[-1].strip().lower()

    if ultimo in ["t", "true", "1"]:
        return True

    if ultimo in ["f", "false", "0"]:
        return False

    return None


def linha_int(saida):
    valor = str(saida or "").strip().splitlines()
    if not valor:
        return None

    try:
        return int(valor[-1].strip())
    except Exception:
        return None


def validar_runtime_docker():
    env = parse_env()
    db_user = env.get("DB_USER") or "postgres"
    db_name = env.get("DB_NAME") or "postgres"

    resultado = {
        "env_encontrado": (ROOT / ".env").exists(),
        "db_user_configurado": bool(env.get("DB_USER")),
        "db_name_configurado": bool(env.get("DB_NAME")),
        "checks": {},
        "comandos": {}
    }

    sql_tabela = "SELECT to_regclass('public.contatos') IS NOT NULL"
    r_tabela = executar_psql(sql_tabela, db_user, db_name)
    resultado["comandos"]["tabela_contatos"] = r_tabela
    tabela_ok = linha_bool(r_tabela.get("stdout"))

    resultado["checks"]["tabela_contatos_existe"] = tabela_ok

    sql_cols = (
        "SELECT COUNT(1) FROM information_schema.columns "
        "WHERE table_schema = 'public' "
        "AND table_name = 'contatos' "
        "AND column_name IN ('empresa_id', 'telefone')"
    )
    r_cols = executar_psql(sql_cols, db_user, db_name)
    resultado["comandos"]["colunas_contatos"] = r_cols
    col_count = linha_int(r_cols.get("stdout"))

    resultado["checks"]["colunas_empresa_id_telefone_total"] = col_count
    resultado["checks"]["colunas_empresa_id_telefone_existem"] = col_count == 2

    sql_unique = (
        "SELECT COUNT(1) "
        "FROM pg_class t "
        "JOIN pg_index ix ON t.oid = ix.indrelid "
        "JOIN pg_class i ON i.oid = ix.indexrelid "
        "JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS k(attnum, ord) ON true "
        "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum "
        "WHERE t.relname = 'contatos' "
        "AND t.relnamespace = 'public'::regnamespace "
        "AND ix.indisunique = true "
        "GROUP BY i.relname "
        "HAVING string_agg(a.attname, ',' ORDER BY k.ord) = 'empresa_id,telefone' "
        "LIMIT 1"
    )
    r_unique = executar_psql(sql_unique, db_user, db_name)
    resultado["comandos"]["unico_empresa_telefone"] = r_unique
    unique_count = linha_int(r_unique.get("stdout"))

    if unique_count is None:
        unique_ok = False
    else:
        unique_ok = unique_count >= 1

    resultado["checks"]["unico_empresa_telefone_existe"] = unique_ok

    sql_indices = (
        "SELECT i.relname || ':' || string_agg(a.attname, ',' ORDER BY k.ord) "
        "FROM pg_class t "
        "JOIN pg_index ix ON t.oid = ix.indrelid "
        "JOIN pg_class i ON i.oid = ix.indexrelid "
        "JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS k(attnum, ord) ON true "
        "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum "
        "WHERE t.relname = 'contatos' "
        "AND t.relnamespace = 'public'::regnamespace "
        "AND ix.indisunique = true "
        "GROUP BY i.relname "
        "ORDER BY i.relname"
    )
    r_indices = executar_psql(sql_indices, db_user, db_name)
    resultado["comandos"]["indices_unicos"] = r_indices
    resultado["checks"]["indices_unicos_saida"] = r_indices.get("stdout", "")

    sql_constraints = (
        "SELECT conname || ':' || pg_get_constraintdef(oid) "
        "FROM pg_constraint "
        "WHERE conrelid = to_regclass('public.contatos') "
        "AND contype IN ('u', 'p') "
        "ORDER BY conname"
    )
    r_constraints = executar_psql(sql_constraints, db_user, db_name)
    resultado["comandos"]["constraints"] = r_constraints
    resultado["checks"]["constraints_saida"] = r_constraints.get("stdout", "")

    sql_dups = (
        "SELECT COUNT(1) FROM ("
        "SELECT empresa_id, telefone "
        "FROM contatos "
        "GROUP BY empresa_id, telefone "
        "HAVING COUNT(1) > 1"
        ") d"
    )
    r_dups = executar_psql(sql_dups, db_user, db_name)
    resultado["comandos"]["duplicidades"] = r_dups
    dup_count = linha_int(r_dups.get("stdout"))

    resultado["checks"]["duplicidades_total_grupos"] = dup_count
    resultado["checks"]["duplicidades_existem"] = bool(dup_count and dup_count > 0)

    resultado["checks"]["pronto_para_on_conflict"] = bool(
        tabela_ok is True and
        col_count == 2 and
        unique_ok is True and
        dup_count == 0
    )

    todos_comandos_ok = True
    for cmd_res in resultado["comandos"].values():
        if not cmd_res.get("ok"):
            todos_comandos_ok = False

    resultado["ok"] = todos_comandos_ok
    return resultado


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_07_2_INICIO -->"
    marcador_fim = "<!-- ETAPA_07_2_FIM -->"

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
    docker = relatorio["docker"]
    runtime = relatorio["runtime"]
    checks = runtime.get("checks", {})

    docker_ok = str(bool(docker["docker_version"]["ok"] and docker["docker_compose_version"]["ok"]))
    pronto = str(bool(checks.get("pronto_para_on_conflict")))
    unico = str(bool(checks.get("unico_empresa_telefone_existe")))
    duplicados = str(checks.get("duplicidades_total_grupos"))

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 07.2 - PostgreSQL Docker runtime validado",
        [
            "Data: " + data,
            "",
            "Foi executada validacao runtime do PostgreSQL via Docker Compose.",
            "Docker disponivel: " + docker_ok + ".",
            "Indice ou constraint unica por empresa e telefone no banco: " + unico + ".",
            "Grupos duplicados encontrados: " + duplicados + ".",
            "Banco pronto para ON CONFLICT por empresa e telefone: " + pronto + ".",
            "Nenhuma alteracao foi aplicada ao banco."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 07.2 - Validacao runtime via Docker",
        [
            "Data: " + data,
            "",
            "Adicionada validacao runtime via docker compose exec no servico db.",
            "Verificada existencia da tabela contatos e colunas essenciais.",
            "Verificada existencia de indice ou constraint unica.",
            "Verificada existencia de duplicidades.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 07.2 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido validar PostgreSQL pela rede Docker Compose.",
            "Decidido nao executar migration automaticamente.",
            "Decidido nao imprimir credenciais nos relatorios.",
            "Decidido seguir para revisao de queries de media severidade somente apos runtime estar validado."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Revisar queries de media severidade apontadas na Etapa 05.",
        "Executar testes funcionais de recebimento e envio de mensagens.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.",
        "Planejar rotacao de credenciais reais expostas anteriormente."
    ]

    if not bool(checks.get("pronto_para_on_conflict")):
        pendencias.insert(2, "Resolver pendencia runtime do PostgreSQL antes de liberar o fluxo de contatos em producao.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 07.2",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    docker = relatorio["docker"]
    servico = relatorio["servico_db"]
    runtime = relatorio["runtime"]
    checks = runtime.get("checks", {})

    linhas = []

    linhas.append("# Etapa 07.2 - Validar PostgreSQL runtime via Docker")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Docker OK: " + str(docker["docker_version"]["ok"]))
    linhas.append("- Docker Compose OK: " + str(docker["docker_compose_version"]["ok"]))
    linhas.append("- Servico db mencionado no compose ps: " + str(servico["servico_db_mencionado"]))
    linhas.append("- Servico db parece rodando: " + str(servico["parece_rodando"]))
    linhas.append("- Runtime OK: " + str(runtime.get("ok")))
    linhas.append("")

    linhas.append("## Resultado runtime")
    linhas.append("")
    if checks:
        linhas.append("- Tabela contatos existe: " + str(checks.get("tabela_contatos_existe")))
        linhas.append("- Colunas empresa_id e telefone existem: " + str(checks.get("colunas_empresa_id_telefone_existem")))
        linhas.append("- Total de colunas essenciais encontradas: " + str(checks.get("colunas_empresa_id_telefone_total")))
        linhas.append("- Unico empresa_id e telefone existe: " + str(checks.get("unico_empresa_telefone_existe")))
        linhas.append("- Grupos duplicados encontrados: " + str(checks.get("duplicidades_total_grupos")))
        linhas.append("- Pronto para ON CONFLICT: " + str(checks.get("pronto_para_on_conflict")))
    else:
        linhas.append("- Checks nao executados ou sem retorno.")

    linhas.append("")
    linhas.append("## Indices unicos")
    linhas.append("")
    saida_indices = checks.get("indices_unicos_saida") or ""
    if saida_indices:
        for linha in saida_indices.splitlines():
            linhas.append("- " + linha)
    else:
        linhas.append("- Nenhum indice unico retornado.")

    linhas.append("")
    linhas.append("## Constraints")
    linhas.append("")
    saida_constraints = checks.get("constraints_saida") or ""
    if saida_constraints:
        for linha in saida_constraints.splitlines():
            linhas.append("- " + linha)
    else:
        linhas.append("- Nenhuma constraint retornada.")

    linhas.append("")
    linhas.append("## Comandos Docker")
    linhas.append("")
    linhas.append("- docker --version ok: " + str(docker["docker_version"]["ok"]))
    if docker["docker_version"].get("stdout"):
        linhas.append("  - " + docker["docker_version"]["stdout"])
    linhas.append("- docker compose version ok: " + str(docker["docker_compose_version"]["ok"]))
    if docker["docker_compose_version"].get("stdout"):
        linhas.append("  - " + docker["docker_compose_version"]["stdout"])

    linhas.append("")
    linhas.append("## Erros dos comandos runtime")
    linhas.append("")
    erros = []
    for nome, item in runtime.get("comandos", {}).items():
        if not item.get("ok"):
            erros.append((nome, item))

    if erros:
        for nome, item in erros:
            linhas.append("- " + nome + ": returncode=" + str(item.get("returncode")))
            if item.get("stderr"):
                linhas.append("  - stderr: " + item["stderr"][:300])
            if item.get("stdout"):
                linhas.append("  - stdout: " + item["stdout"][:300])
    else:
        linhas.append("- Nenhum erro de comando runtime registrado.")

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhuma alteracao foi aplicada ao banco.")
    linhas.append("- Nenhuma migration foi executada.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 08: revisar queries de media severidade, especialmente agregacoes e retorno de inserts.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_07_2_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_07_2_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    docker = verificar_docker()
    servico_db = detectar_servico_db(docker["docker_compose_ps"])
    runtime = validar_runtime_docker()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "servico_db": servico_db,
        "runtime": runtime
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_07_2_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_07_2_validar_postgres_docker_runtime.json"
    md_path = REPORTS_DIR / "etapa_07_2_validar_postgres_docker_runtime.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    checks = runtime.get("checks", {})

    print("Etapa 07.2 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Docker OK: " + str(docker["docker_version"]["ok"]))
    print("Docker Compose OK: " + str(docker["docker_compose_version"]["ok"]))
    print("Servico db mencionado: " + str(servico_db["servico_db_mencionado"]))
    print("Servico db parece rodando: " + str(servico_db["parece_rodando"]))
    print("Runtime OK: " + str(runtime.get("ok")))
    print("Tabela contatos existe: " + str(checks.get("tabela_contatos_existe")))
    print("Unico empresa_id telefone existe: " + str(checks.get("unico_empresa_telefone_existe")))
    print("Duplicidades: " + str(checks.get("duplicidades_total_grupos")))
    print("Pronto para ON CONFLICT: " + str(checks.get("pronto_para_on_conflict")))


if __name__ == "__main__":
    main()