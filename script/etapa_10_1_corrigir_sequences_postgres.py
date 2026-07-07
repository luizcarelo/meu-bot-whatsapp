#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 10.1 - Corrigir sequences PostgreSQL

Objetivo:
- Criar backup documental.
- Criar backup logico do PostgreSQL antes de qualquer correcao.
- Auditar sequences das tabelas principais.
- Comparar MAX(id), last_value e proximo valor esperado.
- Corrigir sequences desalinhadas com setval.
- Revalidar apos correcao.
- Nao inserir dados de teste.
- Nao alterar codigo JS.
- Nao alterar .env.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Observacao:
- Como acessa Docker e altera sequences, execute com sudo se necessario:
  sudo python3 etapa_10_1_corrigir_sequences_postgres.py
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

TABELAS = [
    "empresas",
    "usuarios_painel",
    "contatos",
    "mensagens",
    "setores",
    "horarios_atendimento"
]

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
            "stdout": redigir(proc.stdout.strip())[:8000],
            "stderr": redigir(proc.stderr.strip())[:8000],
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


def run_cmd_binary_to_file(cmd, output_path, timeout=180):
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
            "stderr": redigir(stderr.strip())[:5000],
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

    return run_cmd(cmd, 180, input_text=sql_texto)


def linha_int(stdout):
    linhas = str(stdout or "").strip().splitlines()
    if not linhas:
        return None

    try:
        return int(linhas[-1].strip())
    except Exception:
        return None


def criar_pg_dump(backup_dir, db_user, db_name):
    dump_path = backup_dir / ("pg_dump_pre_etapa_10_1_" + agora_stamp() + ".dump")

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


def verificar_docker():
    return {
        "docker_version": run_cmd(["docker", "--version"], 20),
        "docker_compose_version": run_cmd(["docker", "compose", "version"], 20),
        "docker_compose_ps": run_cmd(["docker", "compose", "ps"], 30)
    }


def auditar_tabela(tabela, db_user, db_name):
    resultado = {
        "tabela": tabela,
        "existe": False,
        "sequence": None,
        "max_id": None,
        "last_value": None,
        "is_called": None,
        "proximo_valor_estimado": None,
        "desalinhada": False,
        "erro": None
    }

    r_existe = executar_psql(
        "SELECT to_regclass('public." + tabela + "') IS NOT NULL",
        db_user,
        db_name
    )

    if not r_existe.get("ok"):
        resultado["erro"] = r_existe.get("stderr") or r_existe.get("stdout")
        return resultado

    existe = str(r_existe.get("stdout") or "").strip().lower() in ["t", "true", "1"]
    resultado["existe"] = existe

    if not existe:
        return resultado

    r_seq = executar_psql(
        "SELECT pg_get_serial_sequence('public." + tabela + "', 'id')",
        db_user,
        db_name
    )

    if not r_seq.get("ok"):
        resultado["erro"] = r_seq.get("stderr") or r_seq.get("stdout")
        return resultado

    seq = str(r_seq.get("stdout") or "").strip()
    if not seq:
        resultado["erro"] = "Sequence nao encontrada para " + tabela + ".id"
        return resultado

    resultado["sequence"] = seq

    r_max = executar_psql(
        "SELECT COALESCE(MAX(id), 0) FROM " + tabela,
        db_user,
        db_name
    )

    if not r_max.get("ok"):
        resultado["erro"] = r_max.get("stderr") or r_max.get("stdout")
        return resultado

    max_id = linha_int(r_max.get("stdout"))
    resultado["max_id"] = max_id

    r_state = executar_psql(
        "SELECT last_value, is_called FROM " + seq,
        db_user,
        db_name
    )

    if not r_state.get("ok"):
        resultado["erro"] = r_state.get("stderr") or r_state.get("stdout")
        return resultado

    partes = str(r_state.get("stdout") or "").strip().split("|")
    if len(partes) >= 2:
        try:
            resultado["last_value"] = int(partes[0])
        except Exception:
            resultado["last_value"] = None
        resultado["is_called"] = partes[1].strip().lower() in ["t", "true", "1"]

    if resultado["last_value"] is not None:
        if resultado["is_called"]:
            resultado["proximo_valor_estimado"] = resultado["last_value"] + 1
        else:
            resultado["proximo_valor_estimado"] = resultado["last_value"]

    if max_id is not None and resultado["proximo_valor_estimado"] is not None:
        if resultado["proximo_valor_estimado"] <= max_id:
            resultado["desalinhada"] = True

    return resultado


def auditar_sequences(db_user, db_name):
    itens = []

    for tabela in TABELAS:
        itens.append(auditar_tabela(tabela, db_user, db_name))

    total_desalinhadas = 0
    for item in itens:
        if item.get("desalinhada"):
            total_desalinhadas += 1

    return {
        "tabelas": itens,
        "total_desalinhadas": total_desalinhadas,
        "ok": total_desalinhadas == 0
    }


def sql_corrigir_sequences(auditoria):
    linhas = []
    linhas.append("BEGIN;")
    linhas.append("")

    corrigidas = []

    for item in auditoria["tabelas"]:
        if not item.get("desalinhada"):
            continue

        tabela = item["tabela"]
        linhas.append(
            "SELECT setval("
            + "pg_get_serial_sequence('public."
            + tabela
            + "', 'id'), "
            + "GREATEST((SELECT COALESCE(MAX(id), 0) FROM "
            + tabela
            + "), 1), "
            + "true"
            + ");"
        )
        corrigidas.append(tabela)

    linhas.append("")
    linhas.append("COMMIT;")
    linhas.append("")

    sql = "\n".join(linhas)
    validar_sem_asterisco_indevido(sql, "sql corrigir sequences")

    return {
        "sql": sql,
        "tabelas_corrigir": corrigidas
    }


def corrigir_sequences(auditoria, db_user, db_name):
    plano = sql_corrigir_sequences(auditoria)

    resultado = {
        "necessario": len(plano["tabelas_corrigir"]) > 0,
        "tabelas_corrigidas_planejadas": plano["tabelas_corrigir"],
        "executado": False,
        "execucao": None,
        "sql_sha256": hashlib.sha256(plano["sql"].encode("utf-8")).hexdigest()
    }

    if not resultado["necessario"]:
        resultado["execucao"] = {
            "ok": True,
            "stdout": "Nenhuma sequence desalinhada encontrada.",
            "stderr": "",
            "returncode": 0
        }
        return resultado

    execucao = executar_psql_stdin(plano["sql"], db_user, db_name)
    resultado["execucao"] = execucao
    resultado["executado"] = True

    return resultado


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_10_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_10_1_FIM -->"

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

    antes = relatorio["auditoria_antes"]
    depois = relatorio["auditoria_depois"]
    correcao = relatorio["correcao"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 10.1 - Sequences PostgreSQL",
        [
            "Data: " + data,
            "",
            "Foi executada auditoria das sequences PostgreSQL das tabelas principais.",
            "Sequences desalinhadas antes: " + str(antes["total_desalinhadas"]) + ".",
            "Correcao executada: " + str(correcao["executado"]) + ".",
            "Sequences desalinhadas depois: " + str(depois["total_desalinhadas"]) + ".",
            "Backup logico criado antes da correcao: " + str(relatorio["pg_dump"]["ok"]) + ".",
            "A Etapa 10 deve ser repetida apos esta correcao."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 10.1 - Correcao de sequences",
        [
            "Data: " + data,
            "",
            "Auditadas sequences de empresas, usuarios_painel, contatos, mensagens, setores e horarios_atendimento.",
            "Corrigidas sequences desalinhadas usando setval quando necessario.",
            "Revalidadas sequences apos correcao.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 10.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido corrigir sequences antes de repetir testes funcionais de escrita.",
            "Decidido usar setval com GREATEST entre MAX(id) e 1.",
            "Decidido nao inserir dados de teste nesta etapa.",
            "Decidido gerar backup logico antes de alterar sequences."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Reexecutar a Etapa 10 de testes funcionais com escrita.",
        "Validar se o insert em usuarios_painel avanca sem violar chave primaria.",
        "Executar testes funcionais pela interface web apos Etapa 10 passar.",
        "Revisar achados de baixa severidade, especialmente booleanos numericos.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes."
    ]

    if depois["total_desalinhadas"] > 0:
        pendencias.insert(2, "Corrigir sequences ainda desalinhadas listadas no relatorio da Etapa 10.1.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 10.1",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    antes = relatorio["auditoria_antes"]
    depois = relatorio["auditoria_depois"]
    correcao = relatorio["correcao"]

    linhas.append("# Etapa 10.1 - Corrigir sequences PostgreSQL")
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
    linhas.append("- Sequences desalinhadas antes: " + str(antes["total_desalinhadas"]))
    linhas.append("- Correcao necessaria: " + str(correcao["necessario"]))
    linhas.append("- Correcao executada: " + str(correcao["executado"]))
    linhas.append("- Sequences desalinhadas depois: " + str(depois["total_desalinhadas"]))
    linhas.append("")

    linhas.append("## Auditoria antes")
    linhas.append("")
    for item in antes["tabelas"]:
        linhas.append(
            "- "
            + item["tabela"]
            + ": existe="
            + str(item["existe"])
            + ", sequence="
            + str(item["sequence"])
            + ", max_id="
            + str(item["max_id"])
            + ", last_value="
            + str(item["last_value"])
            + ", proximo="
            + str(item["proximo_valor_estimado"])
            + ", desalinhada="
            + str(item["desalinhada"])
        )
        if item.get("erro"):
            linhas.append("  - erro: " + item["erro"][:240])

    linhas.append("")
    linhas.append("## Correcao")
    linhas.append("")
    linhas.append("- Necessaria: " + str(correcao["necessario"]))
    linhas.append("- Executada: " + str(correcao["executado"]))
    linhas.append("- Tabelas planejadas: " + ", ".join(correcao["tabelas_corrigidas_planejadas"]))
    linhas.append("- SQL SHA256: " + str(correcao["sql_sha256"]))

    if correcao["execucao"]:
        linhas.append("- Execucao OK: " + str(correcao["execucao"].get("ok")))
        if correcao["execucao"].get("stdout"):
            linhas.append("- stdout:")
            for linha in correcao["execucao"]["stdout"].splitlines():
                linhas.append("  - " + linha[:240])
        if correcao["execucao"].get("stderr"):
            linhas.append("- stderr:")
            for linha in correcao["execucao"]["stderr"].splitlines():
                linhas.append("  - " + linha[:240])

    linhas.append("")
    linhas.append("## Auditoria depois")
    linhas.append("")
    for item in depois["tabelas"]:
        linhas.append(
            "- "
            + item["tabela"]
            + ": existe="
            + str(item["existe"])
            + ", sequence="
            + str(item["sequence"])
            + ", max_id="
            + str(item["max_id"])
            + ", last_value="
            + str(item["last_value"])
            + ", proximo="
            + str(item["proximo_valor_estimado"])
            + ", desalinhada="
            + str(item["desalinhada"])
        )
        if item.get("erro"):
            linhas.append("  - erro: " + item["erro"][:240])

    linhas.append("")
    linhas.append("## Backup logico")
    linhas.append("")
    linhas.append("- OK: " + str(relatorio["pg_dump"]["ok"]))
    linhas.append("- Arquivo: " + str(relatorio["pg_dump"].get("stdout_file")))
    linhas.append("- SHA256: " + str(relatorio["pg_dump"].get("sha256")))
    linhas.append("- Tamanho bytes: " + str(relatorio["pg_dump"].get("tamanho_bytes")))

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhum dado de teste foi inserido nesta etapa.")
    linhas.append("- A alteracao executada foi limitada a ajuste de sequences.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Reexecutar a Etapa 10 de testes funcionais com escrita controlada.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_10_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_10_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    env = parse_env()
    db_user = env.get("DB_USER") or "postgres"
    db_name = env.get("DB_NAME") or "postgres"

    docker = verificar_docker()
    pg_dump = criar_pg_dump(backup_dir, db_user, db_name)

    auditoria_antes = auditar_sequences(db_user, db_name)
    correcao = corrigir_sequences(auditoria_antes, db_user, db_name)
    auditoria_depois = auditar_sequences(db_user, db_name)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "pg_dump": pg_dump,
        "auditoria_antes": auditoria_antes,
        "correcao": correcao,
        "auditoria_depois": auditoria_depois
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_10_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_10_1_corrigir_sequences_postgres.json"
    md_path = REPORTS_DIR / "etapa_10_1_corrigir_sequences_postgres.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 10.1 concluida.")
    print("Backup documental: " + backup["destino"])
    print("Backup logico OK: " + str(pg_dump["ok"]))
    print("Backup logico arquivo: " + str(pg_dump.get("stdout_file")))
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Sequences desalinhadas antes: " + str(auditoria_antes["total_desalinhadas"]))
    print("Correcao necessaria: " + str(correcao["necessario"]))
    print("Correcao executada: " + str(correcao["executado"]))
    print("Sequences desalinhadas depois: " + str(auditoria_depois["total_desalinhadas"]))

    if auditoria_depois["total_desalinhadas"] > 0:
        print("")
        print("Ainda existem sequences desalinhadas. Consulte o relatorio.")
    else:
        print("")
        print("Agora reexecute a Etapa 10:")
        print("sudo python3 etapa_10_testes_funcionais_escrita_postgres.py")


if __name__ == "__main__":
    main()