#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 09 - Validacao funcional controlada PostgreSQL

Objetivo:
- Criar backup antes de alterar documentacao.
- Gerar manifesto antes e depois.
- Rodar node --check nos principais arquivos JS.
- Verificar Docker e Docker Compose.
- Verificar containers via docker compose ps.
- Validar PostgreSQL via docker compose exec no servico db.
- Executar consultas somente leitura em tabelas essenciais.
- Validar colunas usadas nas queries corrigidas.
- Nao inserir, atualizar ou excluir dados.
- Nao executar migrations.
- Nao alterar banco.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Observacao:
- Se o usuario atual nao tiver permissao no Docker, execute com sudo:
  sudo python3 etapa_09_validar_funcional_postgres.py
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

ARQUIVOS_NODE_CHECK = [
    "server.js",
    "routes/api.js",
    "routes/index.js",
    "controllers/AdminController.js",
    "controllers/AdminPanelController.js",
    "controllers/AuthController.js",
    "controllers/CrmController.js",
    "controllers/ScheduleController.js",
    "controllers/WhatsAppController.js",
    "src/config/db.js",
    "src/managers/SessionManager.js",
    "src/managers/OpenAIManager.js",
    "src/middleware/auth.js",
    "src/utils/atendimento.js",
    "script/export_full.js",
    "script/backup_database.js"
]

TABELAS_ESSENCIAIS = [
    "empresas",
    "usuarios_painel",
    "contatos",
    "mensagens",
    "setores",
    "horarios_atendimento"
]

COLUNAS_ESPERADAS = {
    "empresas": [
        "id",
        "nome",
        "ativo",
        "whatsapp_status"
    ],
    "usuarios_painel": [
        "id",
        "empresa_id",
        "email",
        "senha",
        "is_admin",
        "ativo"
    ],
    "contatos": [
        "id",
        "empresa_id",
        "telefone",
        "nome",
        "status_atendimento",
        "ultima_msg"
    ],
    "mensagens": [
        "id",
        "empresa_id",
        "remote_jid",
        "from_me",
        "tipo",
        "conteudo"
    ],
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
        "ativo"
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


def node_check():
    resultados = []

    for nome in ARQUIVOS_NODE_CHECK:
        path = ROOT / nome

        if not path.exists():
            resultados.append({
                "arquivo": nome,
                "existe": False,
                "ok": False,
                "erro": "Arquivo ausente"
            })
            continue

        r = run_cmd(["node", "--check", str(path)], 40)
        resultados.append({
            "arquivo": nome,
            "existe": True,
            "ok": r["ok"],
            "stdout": r["stdout"][:500],
            "stderr": r["stderr"][:1500]
        })

    return resultados


def resumo_node(resultados):
    total = len(resultados)
    ok = 0
    falhas = 0
    ausentes = 0

    for item in resultados:
        if not item.get("existe"):
            ausentes += 1
        elif item.get("ok"):
            ok += 1
        else:
            falhas += 1

    return {
        "total": total,
        "ok": ok,
        "falhas": falhas,
        "ausentes": ausentes
    }


def verificar_docker():
    return {
        "docker_version": run_cmd(["docker", "--version"], 20),
        "docker_compose_version": run_cmd(["docker", "compose", "version"], 20),
        "docker_compose_ps": run_cmd(["docker", "compose", "ps"], 30)
    }


def detectar_db(ps_resultado):
    texto = (ps_resultado.get("stdout") or "") + "\n" + (ps_resultado.get("stderr") or "")
    lower = texto.lower()

    return {
        "servico_db_mencionado": "db" in lower or "whatsapp_bot_db" in lower,
        "parece_rodando": "running" in lower or "up" in lower,
        "healthy": "healthy" in lower,
        "texto_redigido": texto[:5000]
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


def linha_int(stdout):
    linhas = str(stdout or "").strip().splitlines()
    if not linhas:
        return None

    try:
        return int(linhas[-1].strip())
    except Exception:
        return None


def linha_bool(stdout):
    linhas = str(stdout or "").strip().splitlines()
    if not linhas:
        return None

    v = linhas[-1].strip().lower()

    if v in ["t", "true", "1"]:
        return True

    if v in ["f", "false", "0"]:
        return False

    return None


def validar_banco_somente_leitura():
    env = parse_env()
    db_user = env.get("DB_USER") or "postgres"
    db_name = env.get("DB_NAME") or "postgres"

    resultado = {
        "env_encontrado": (ROOT / ".env").exists(),
        "db_user_configurado": bool(env.get("DB_USER")),
        "db_name_configurado": bool(env.get("DB_NAME")),
        "db_port_configurado": bool(env.get("DB_PORT")),
        "db_host_configurado": bool(env.get("DB_HOST")),
        "tabelas": [],
        "colunas": [],
        "comandos_erros": [],
        "ok": False
    }

    # Teste basico sem expor dados.
    r_ping = executar_psql("SELECT 1", db_user, db_name)
    resultado["ping"] = {
        "ok": r_ping["ok"],
        "stdout": r_ping["stdout"],
        "stderr": r_ping["stderr"],
        "returncode": r_ping["returncode"]
    }

    for tabela in TABELAS_ESSENCIAIS:
        sql_exists = "SELECT to_regclass('public." + tabela + "') IS NOT NULL"
        r_exists = executar_psql(sql_exists, db_user, db_name)
        existe = linha_bool(r_exists.get("stdout"))

        info = {
            "tabela": tabela,
            "existe": existe,
            "count_ok": False,
            "total_registros": None,
            "erro": None
        }

        if not r_exists.get("ok"):
            info["erro"] = r_exists.get("stderr") or r_exists.get("stdout")
            resultado["comandos_erros"].append({
                "tabela": tabela,
                "etapa": "exists",
                "erro": info["erro"]
            })

        if existe is True:
            sql_count = "SELECT COUNT(1) FROM " + tabela
            r_count = executar_psql(sql_count, db_user, db_name)
            total = linha_int(r_count.get("stdout"))

            info["count_ok"] = r_count.get("ok")
            info["total_registros"] = total

            if not r_count.get("ok"):
                resultado["comandos_erros"].append({
                    "tabela": tabela,
                    "etapa": "count",
                    "erro": r_count.get("stderr") or r_count.get("stdout")
                })

        resultado["tabelas"].append(info)

    for tabela, colunas in COLUNAS_ESPERADAS.items():
        lista = "', '".join(colunas)
        sql_cols = (
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name = '" + tabela + "' "
            "AND column_name IN ('" + lista + "') "
            "ORDER BY column_name"
        )
        r_cols = executar_psql(sql_cols, db_user, db_name)
        encontradas = []

        if r_cols.get("stdout"):
            encontradas = [x.strip() for x in r_cols["stdout"].splitlines() if x.strip()]

        faltantes = []
        for col in colunas:
            if col not in encontradas:
                faltantes.append(col)

        resultado["colunas"].append({
            "tabela": tabela,
            "esperadas": colunas,
            "encontradas": encontradas,
            "faltantes": faltantes,
            "ok": r_cols.get("ok") and len(faltantes) == 0,
            "erro": None if r_cols.get("ok") else (r_cols.get("stderr") or r_cols.get("stdout"))
        })

    tabelas_ok = all(item.get("existe") is True and item.get("count_ok") for item in resultado["tabelas"])
    colunas_ok = all(item.get("ok") for item in resultado["colunas"])

    resultado["ok"] = bool(r_ping["ok"] and tabelas_ok and colunas_ok)
    resultado["tabelas_ok"] = tabelas_ok
    resultado["colunas_ok"] = colunas_ok

    return resultado


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_09_INICIO -->"
    marcador_fim = "<!-- ETAPA_09_FIM -->"

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
    node = relatorio["resumo_node_check"]
    banco = relatorio["banco"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 09 - Validacao funcional PostgreSQL",
        [
            "Data: " + data,
            "",
            "Foi executada validacao funcional controlada e somente leitura.",
            "Arquivos JS verificados: " + str(node["total"]) + ".",
            "Falhas em node --check: " + str(node["falhas"]) + ".",
            "Banco validado em modo somente leitura: " + str(banco["ok"]) + ".",
            "Tabelas essenciais OK: " + str(banco.get("tabelas_ok")) + ".",
            "Colunas essenciais OK: " + str(banco.get("colunas_ok")) + ".",
            "Nenhuma alteracao foi aplicada ao banco."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 09 - Validacao funcional controlada",
        [
            "Data: " + data,
            "",
            "Executado node --check nos principais arquivos JS.",
            "Verificado Docker Compose e servico de banco.",
            "Executadas consultas somente leitura em tabelas essenciais.",
            "Validadas colunas usadas pelas queries corrigidas.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 09 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido executar apenas consultas somente leitura nesta etapa.",
            "Decidido validar tabelas e colunas antes de testes funcionais com escrita.",
            "Decidido nao executar migrations, inserts, updates ou deletes.",
            "Decidido tratar falhas encontradas em etapa posterior, se houver."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Executar testes funcionais com escrita em ambiente controlado.",
        "Validar criacao de empresa e usuario admin.",
        "Validar fluxo de recebimento de mensagem e upsert de contato.",
        "Validar fluxo de envio de mensagem e registro no historico.",
        "Revisar achados de baixa severidade, especialmente booleanos numericos.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes."
    ]

    if not banco.get("ok"):
        pendencias.insert(2, "Corrigir pendencias de validacao somente leitura listadas no relatorio da Etapa 09.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 09",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    docker = relatorio["docker"]
    servico = relatorio["servico_db"]
    banco = relatorio["banco"]
    node_resumo = relatorio["resumo_node_check"]

    linhas.append("# Etapa 09 - Validacao funcional controlada PostgreSQL")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Node check falhas: " + str(node_resumo["falhas"]))
    linhas.append("- Node check ausentes: " + str(node_resumo["ausentes"]))
    linhas.append("- Docker OK: " + str(docker["docker_version"]["ok"]))
    linhas.append("- Docker Compose OK: " + str(docker["docker_compose_version"]["ok"]))
    linhas.append("- Servico db parece rodando: " + str(servico["parece_rodando"]))
    linhas.append("- Banco somente leitura OK: " + str(banco["ok"]))
    linhas.append("- Tabelas essenciais OK: " + str(banco.get("tabelas_ok")))
    linhas.append("- Colunas essenciais OK: " + str(banco.get("colunas_ok")))
    linhas.append("")

    linhas.append("## Node check")
    linhas.append("")
    linhas.append("- Arquivos verificados: " + str(node_resumo["total"]))
    linhas.append("- OK: " + str(node_resumo["ok"]))
    linhas.append("- Falhas: " + str(node_resumo["falhas"]))
    linhas.append("- Ausentes: " + str(node_resumo["ausentes"]))

    falhas = []
    for item in relatorio["node_check"]:
        if not item.get("existe") or not item.get("ok"):
            falhas.append(item)

    if falhas:
        linhas.append("")
        linhas.append("### Falhas node --check")
        for item in falhas:
            detalhe = item.get("stderr") or item.get("erro") or "Falha sem detalhe"
            detalhe = detalhe.replace(chr(42), "[asterisco]")
            linhas.append("- " + item["arquivo"] + ": " + detalhe[:300])

    linhas.append("")
    linhas.append("## Docker")
    linhas.append("")
    linhas.append("- docker --version ok: " + str(docker["docker_version"]["ok"]))
    if docker["docker_version"].get("stdout"):
        linhas.append("  - " + docker["docker_version"]["stdout"])
    linhas.append("- docker compose version ok: " + str(docker["docker_compose_version"]["ok"]))
    if docker["docker_compose_version"].get("stdout"):
        linhas.append("  - " + docker["docker_compose_version"]["stdout"])
    linhas.append("- servico db mencionado: " + str(servico["servico_db_mencionado"]))
    linhas.append("- servico db healthy: " + str(servico["healthy"]))

    linhas.append("")
    linhas.append("## Banco - tabelas essenciais")
    linhas.append("")
    for item in banco["tabelas"]:
        linhas.append(
            "- "
            + item["tabela"]
            + ": existe="
            + str(item["existe"])
            + ", count_ok="
            + str(item["count_ok"])
            + ", total_registros="
            + str(item["total_registros"])
        )
        if item.get("erro"):
            linhas.append("  - erro: " + item["erro"][:300])

    linhas.append("")
    linhas.append("## Banco - colunas essenciais")
    linhas.append("")
    for item in banco["colunas"]:
        linhas.append(
            "- "
            + item["tabela"]
            + ": ok="
            + str(item["ok"])
            + ", faltantes="
            + ", ".join(item["faltantes"])
        )
        if item.get("erro"):
            linhas.append("  - erro: " + item["erro"][:300])

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma senha foi impressa pelo script.")
    linhas.append("- Nenhuma alteracao foi aplicada ao banco.")
    linhas.append("- Nenhuma migration foi executada.")
    linhas.append("- Consultas executadas foram somente leitura.")

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
    backup_dir = BACKUPS_DIR / ("etapa_09_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_09_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    node_resultado = node_check()
    node_resumo = resumo_node(node_resultado)
    docker = verificar_docker()
    servico_db = detectar_db(docker["docker_compose_ps"])
    banco = validar_banco_somente_leitura()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "node_check": node_resultado,
        "resumo_node_check": node_resumo,
        "docker": docker,
        "servico_db": servico_db,
        "banco": banco
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_09_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_09_validar_funcional_postgres.json"
    md_path = REPORTS_DIR / "etapa_09_validar_funcional_postgres.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 09 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Node check falhas: " + str(node_resumo["falhas"]))
    print("Node check ausentes: " + str(node_resumo["ausentes"]))
    print("Docker OK: " + str(docker["docker_version"]["ok"]))
    print("Docker Compose OK: " + str(docker["docker_compose_version"]["ok"]))
    print("Servico db parece rodando: " + str(servico_db["parece_rodando"]))
    print("Banco somente leitura OK: " + str(banco["ok"]))
    print("Tabelas essenciais OK: " + str(banco.get("tabelas_ok")))
    print("Colunas essenciais OK: " + str(banco.get("colunas_ok")))

    if node_resumo["falhas"] > 0 or node_resumo["ausentes"] > 0:
        print("")
        print("Existem pendencias em node --check. Consulte o relatorio.")

    if not banco["ok"]:
        print("")
        print("Existem pendencias de validacao do banco. Consulte o relatorio.")


if __name__ == "__main__":
    main()