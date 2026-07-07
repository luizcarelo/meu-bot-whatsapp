#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 10 - Testes funcionais com escrita controlada PostgreSQL

Objetivo:
- Criar backup documental e manifesto antes e depois.
- Criar backup logico do PostgreSQL antes dos testes.
- Executar testes de escrita em transacao.
- Fazer ROLLBACK ao final para nao manter dados de teste.
- Validar:
  - criacao de empresa teste com RETURNING id
  - criacao de usuario admin teste
  - criacao de setor com ordem
  - criacao de horario de atendimento
  - upsert de contato com ON CONFLICT
  - insercao de mensagem
  - rollback e limpeza dos dados de teste
- Nao alterar codigo JS.
- Nao alterar .env.
- Nao alterar docker-compose.yml.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Observacao:
- Como envolve Docker e banco, execute com sudo se necessario:
  sudo python3 etapa_10_testes_funcionais_escrita_postgres.py
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


def verificar_docker():
    return {
        "docker_version": run_cmd(["docker", "--version"], 20),
        "docker_compose_version": run_cmd(["docker", "compose", "version"], 20),
        "docker_compose_ps": run_cmd(["docker", "compose", "ps"], 30)
    }


def criar_pg_dump(backup_dir, db_user, db_name):
    dump_path = backup_dir / ("pg_dump_pre_etapa_10_" + agora_stamp() + ".dump")

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


def validar_schema_minimo(db_user, db_name):
    checks = {}

    consultas = {
        "empresas": "SELECT to_regclass('public.empresas') IS NOT NULL",
        "usuarios_painel": "SELECT to_regclass('public.usuarios_painel') IS NOT NULL",
        "setores": "SELECT to_regclass('public.setores') IS NOT NULL",
        "horarios_atendimento": "SELECT to_regclass('public.horarios_atendimento') IS NOT NULL",
        "contatos": "SELECT to_regclass('public.contatos') IS NOT NULL",
        "mensagens": "SELECT to_regclass('public.mensagens') IS NOT NULL",
        "setores_ordem": (
            "SELECT COUNT(1) FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name = 'setores' "
            "AND column_name = 'ordem'"
        ),
        "contatos_unique": (
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
    }

    comandos = {}
    ok = True

    for nome, sql in consultas.items():
        r = executar_psql(sql, db_user, db_name)
        comandos[nome] = r

        valor = str(r.get("stdout") or "").strip().lower()
        if nome == "setores_ordem" or nome == "contatos_unique":
            checks[nome] = linha_int(r.get("stdout"))
            if not r.get("ok") or checks[nome] is None or checks[nome] < 1:
                ok = False
        else:
            checks[nome] = valor in ["t", "true", "1"]
            if (not r.get("ok")) or (not checks[nome]):
                ok = False

    return {
        "ok": ok,
        "checks": checks,
        "comandos": comandos
    }


def sql_testes_funcionais(marcador):
    nome_empresa = "ETAPA10_TESTE_EMPRESA_" + marcador
    email_admin = "etapa10_" + marcador + "@teste.local"
    telefone = "55999990000" + marcador[-4:]
    remote_jid = telefone + "@s.whatsapp.net"

    sql = """
BEGIN;

CREATE TEMP TABLE etapa10_ids (
    chave TEXT PRIMARY KEY,
    valor INTEGER
) ON COMMIT DROP;

WITH e AS (
    INSERT INTO empresas (nome, ativo, whatsapp_status)
    VALUES ('NOME_EMPRESA', TRUE, 'DESCONECTADO')
    RETURNING id
)
INSERT INTO etapa10_ids (chave, valor)
SELECT 'empresa_id', id FROM e;

SELECT 'empresa_id|' || valor FROM etapa10_ids WHERE chave = 'empresa_id';

WITH u AS (
    INSERT INTO usuarios_painel (
        empresa_id,
        nome,
        email,
        senha,
        is_admin,
        ativo,
        cargo
    )
    SELECT
        valor,
        'Admin Teste Etapa 10',
        'EMAIL_ADMIN',
        'senha_teste_hash_nao_usar',
        TRUE,
        TRUE,
        'Admin Teste'
    FROM etapa10_ids
    WHERE chave = 'empresa_id'
    RETURNING id
)
INSERT INTO etapa10_ids (chave, valor)
SELECT 'usuario_id', id FROM u;

SELECT 'usuario_id|' || valor FROM etapa10_ids WHERE chave = 'usuario_id';

WITH s AS (
    INSERT INTO setores (
        empresa_id,
        nome,
        mensagem_saudacao,
        padrao,
        ordem
    )
    SELECT
        valor,
        'Setor Teste Etapa 10',
        'Mensagem de teste Etapa 10',
        FALSE,
        10
    FROM etapa10_ids
    WHERE chave = 'empresa_id'
    RETURNING id
)
INSERT INTO etapa10_ids (chave, valor)
SELECT 'setor_id', id FROM s;

SELECT 'setor_id|' || valor FROM etapa10_ids WHERE chave = 'setor_id';

WITH h AS (
    INSERT INTO horarios_atendimento (
        empresa_id,
        dia_semana,
        horario_abertura,
        horario_fechamento,
        inicio_almoco,
        fim_almoco,
        ativo
    )
    SELECT
        valor,
        1,
        '08:00',
        '18:00',
        '12:00',
        '13:00',
        TRUE
    FROM etapa10_ids
    WHERE chave = 'empresa_id'
    RETURNING id
)
INSERT INTO etapa10_ids (chave, valor)
SELECT 'horario_id', id FROM h;

SELECT 'horario_id|' || valor FROM etapa10_ids WHERE chave = 'horario_id';

INSERT INTO contatos (
    empresa_id,
    telefone,
    nome,
    foto_perfil,
    status_atendimento,
    created_at,
    ultima_msg
)
SELECT
    valor,
    'TELEFONE_TESTE',
    'Contato Teste Etapa 10',
    NULL,
    'ABERTO',
    NOW(),
    NOW()
FROM etapa10_ids
WHERE chave = 'empresa_id'
ON CONFLICT (empresa_id, telefone) DO UPDATE SET
    nome = EXCLUDED.nome,
    foto_perfil = COALESCE(EXCLUDED.foto_perfil, contatos.foto_perfil),
    ultima_msg = NOW();

INSERT INTO contatos (
    empresa_id,
    telefone,
    nome,
    foto_perfil,
    status_atendimento,
    created_at,
    ultima_msg
)
SELECT
    valor,
    'TELEFONE_TESTE',
    'Contato Teste Etapa 10 Atualizado',
    NULL,
    'ABERTO',
    NOW(),
    NOW()
FROM etapa10_ids
WHERE chave = 'empresa_id'
ON CONFLICT (empresa_id, telefone) DO UPDATE SET
    nome = EXCLUDED.nome,
    foto_perfil = COALESCE(EXCLUDED.foto_perfil, contatos.foto_perfil),
    ultima_msg = NOW();

WITH c AS (
    SELECT id
    FROM contatos
    WHERE empresa_id = (SELECT valor FROM etapa10_ids WHERE chave = 'empresa_id')
    AND telefone = 'TELEFONE_TESTE'
)
SELECT 'contato_total|' || COUNT(1) FROM c;

INSERT INTO mensagens (
    empresa_id,
    remote_jid,
    from_me,
    tipo,
    conteudo
)
SELECT
    valor,
    'REMOTE_JID_TESTE',
    TRUE,
    'texto',
    'Mensagem teste Etapa 10'
FROM etapa10_ids
WHERE chave = 'empresa_id';

SELECT 'mensagens_total|' || COUNT(1)
FROM mensagens
WHERE empresa_id = (SELECT valor FROM etapa10_ids WHERE chave = 'empresa_id')
AND remote_jid = 'REMOTE_JID_TESTE';

SELECT 'validacao_transacao|ok';

ROLLBACK;

SELECT 'empresas_pos_rollback|' || COUNT(1)
FROM empresas
WHERE nome = 'NOME_EMPRESA';

SELECT 'usuarios_pos_rollback|' || COUNT(1)
FROM usuarios_painel
WHERE email = 'EMAIL_ADMIN';

SELECT 'contatos_pos_rollback|' || COUNT(1)
FROM contatos
WHERE telefone = 'TELEFONE_TESTE';

SELECT 'mensagens_pos_rollback|' || COUNT(1)
FROM mensagens
WHERE remote_jid = 'REMOTE_JID_TESTE';
"""

    sql = sql.replace("NOME_EMPRESA", nome_empresa)
    sql = sql.replace("EMAIL_ADMIN", email_admin)
    sql = sql.replace("TELEFONE_TESTE", telefone)
    sql = sql.replace("REMOTE_JID_TESTE", remote_jid)

    return sql


def parse_saida_testes(stdout):
    resultado = {
        "linhas": [],
        "valores": {},
        "ok_logico": False,
        "rollback_ok": False
    }

    for linha in str(stdout or "").splitlines():
        linha = linha.strip()

        if not linha:
            continue

        resultado["linhas"].append(linha)

        if "|" in linha:
            chave, valor = linha.split("|", 1)
            resultado["valores"][chave] = valor

    valores = resultado["valores"]

    ok_logico = True

    exigidos_maiores_zero = [
        "empresa_id",
        "usuario_id",
        "setor_id",
        "horario_id"
    ]

    for chave in exigidos_maiores_zero:
        try:
            if int(valores.get(chave, "0")) <= 0:
                ok_logico = False
        except Exception:
            ok_logico = False

    if valores.get("contato_total") != "1":
        ok_logico = False

    if valores.get("mensagens_total") != "1":
        ok_logico = False

    if valores.get("validacao_transacao") != "ok":
        ok_logico = False

    rollback_ok = (
        valores.get("empresas_pos_rollback") == "0" and
        valores.get("usuarios_pos_rollback") == "0" and
        valores.get("contatos_pos_rollback") == "0" and
        valores.get("mensagens_pos_rollback") == "0"
    )

    resultado["ok_logico"] = ok_logico
    resultado["rollback_ok"] = rollback_ok

    return resultado


def executar_testes_funcionais(db_user, db_name):
    marcador = agora_stamp()
    sql = sql_testes_funcionais(marcador)
    validar_sem_asterisco_indevido(sql, "sql testes funcionais etapa 10")

    execucao = executar_psql_stdin(sql, db_user, db_name)
    parse = parse_saida_testes(execucao.get("stdout"))

    return {
        "marcador": marcador,
        "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        "execucao": execucao,
        "parse": parse,
        "ok": bool(execucao.get("ok") and parse["ok_logico"] and parse["rollback_ok"])
    }


def validar_limpeza_final(db_user, db_name, marcador):
    nome_empresa = "ETAPA10_TESTE_EMPRESA_" + marcador
    email_admin = "etapa10_" + marcador + "@teste.local"
    telefone = "55999990000" + marcador[-4:]
    remote_jid = telefone + "@s.whatsapp.net"

    consultas = {
        "empresas": "SELECT COUNT(1) FROM empresas WHERE nome = '" + nome_empresa + "'",
        "usuarios": "SELECT COUNT(1) FROM usuarios_painel WHERE email = '" + email_admin + "'",
        "contatos": "SELECT COUNT(1) FROM contatos WHERE telefone = '" + telefone + "'",
        "mensagens": "SELECT COUNT(1) FROM mensagens WHERE remote_jid = '" + remote_jid + "'"
    }

    resultados = {}
    ok = True

    for nome, sql in consultas.items():
        r = executar_psql(sql, db_user, db_name)
        total = linha_int(r.get("stdout"))
        resultados[nome] = {
            "ok": r.get("ok"),
            "total": total,
            "stderr": r.get("stderr")
        }

        if not r.get("ok") or total != 0:
            ok = False

    return {
        "ok": ok,
        "resultados": resultados
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_10_INICIO -->"
    marcador_fim = "<!-- ETAPA_10_FIM -->"

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
    testes = relatorio["testes_funcionais"]
    limpeza = relatorio["limpeza_final"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 10 - Testes funcionais com escrita PostgreSQL",
        [
            "Data: " + data,
            "",
            "Foram executados testes funcionais com escrita controlada em transacao.",
            "A transacao usou dados de teste marcados e executou ROLLBACK ao final.",
            "Testes funcionais OK: " + str(testes["ok"]) + ".",
            "Rollback validado: " + str(testes["parse"]["rollback_ok"]) + ".",
            "Limpeza final OK: " + str(limpeza["ok"]) + ".",
            "Backup logico criado antes dos testes: " + str(relatorio["pg_dump"]["ok"]) + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 10 - Testes funcionais de escrita",
        [
            "Data: " + data,
            "",
            "Executados testes de criacao de empresa, usuario, setor e horario.",
            "Executado teste de upsert de contato com ON CONFLICT.",
            "Executado teste de insercao de mensagem.",
            "Executado rollback e validacao de limpeza dos dados de teste.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 10 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido executar testes de escrita somente dentro de transacao com rollback.",
            "Decidido usar dados de teste marcados com identificador da etapa.",
            "Decidido validar limpeza apos rollback com consultas separadas.",
            "Decidido manter testes sem chamadas externas ao WhatsApp ou SMTP."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Executar testes funcionais pela interface web.",
        "Validar fluxo real de login e painel administrativo.",
        "Validar envio e recebimento real de mensagens com ambiente controlado.",
        "Revisar achados de baixa severidade, especialmente booleanos numericos.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.",
        "Planejar rotacao de credenciais reais expostas anteriormente."
    ]

    if not testes["ok"] or not limpeza["ok"]:
        pendencias.insert(2, "Corrigir falhas dos testes funcionais da Etapa 10 antes de avancar.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 10",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    testes = relatorio["testes_funcionais"]
    parse = testes["parse"]
    limpeza = relatorio["limpeza_final"]

    linhas.append("# Etapa 10 - Testes funcionais com escrita PostgreSQL")
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
    linhas.append("- Docker OK: " + str(relatorio["docker"]["docker_version"]["ok"]))
    linhas.append("- Schema minimo OK: " + str(relatorio["schema_minimo"]["ok"]))
    linhas.append("- Testes funcionais OK: " + str(testes["ok"]))
    linhas.append("- Validacao logica OK: " + str(parse["ok_logico"]))
    linhas.append("- Rollback OK: " + str(parse["rollback_ok"]))
    linhas.append("- Limpeza final OK: " + str(limpeza["ok"]))
    linhas.append("")

    linhas.append("## Testes executados")
    linhas.append("")
    linhas.append("- Criacao de empresa teste com RETURNING id.")
    linhas.append("- Criacao de usuario admin teste.")
    linhas.append("- Criacao de setor com ordem.")
    linhas.append("- Criacao de horario de atendimento.")
    linhas.append("- Upsert de contato com ON CONFLICT.")
    linhas.append("- Insercao de mensagem.")
    linhas.append("- ROLLBACK da transacao.")
    linhas.append("- Validacao posterior de limpeza.")

    linhas.append("")
    linhas.append("## Valores retornados")
    linhas.append("")
    for chave in sorted(parse["valores"].keys()):
        linhas.append("- " + chave + ": " + str(parse["valores"][chave]))

    linhas.append("")
    linhas.append("## Execucao SQL")
    linhas.append("")
    linhas.append("- OK: " + str(testes["execucao"]["ok"]))
    linhas.append("- Return code: " + str(testes["execucao"]["returncode"]))
    if testes["execucao"].get("stderr"):
        linhas.append("- stderr:")
        for linha in testes["execucao"]["stderr"].splitlines():
            linhas.append("  - " + linha[:240])

    linhas.append("")
    linhas.append("## Limpeza final")
    linhas.append("")
    for nome, item in limpeza["resultados"].items():
        linhas.append(
            "- "
            + nome
            + ": ok="
            + str(item["ok"])
            + ", total="
            + str(item["total"])
        )

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
    linhas.append("- Os dados de teste foram criados dentro de transacao.")
    linhas.append("- A transacao foi revertida com ROLLBACK.")
    linhas.append("- O script nao chamou WhatsApp, SMTP ou servicos externos.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 11: validar interface web e endpoints principais em ambiente controlado.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_10_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_10_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    env = parse_env()
    db_user = env.get("DB_USER") or "postgres"
    db_name = env.get("DB_NAME") or "postgres"

    docker = verificar_docker()
    pg_dump = criar_pg_dump(backup_dir, db_user, db_name)
    schema_minimo = validar_schema_minimo(db_user, db_name)
    testes = executar_testes_funcionais(db_user, db_name)
    limpeza = validar_limpeza_final(db_user, db_name, testes["marcador"])

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "docker": docker,
        "pg_dump": pg_dump,
        "schema_minimo": schema_minimo,
        "testes_funcionais": testes,
        "limpeza_final": limpeza
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_10_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_10_testes_funcionais_escrita_postgres.json"
    md_path = REPORTS_DIR / "etapa_10_testes_funcionais_escrita_postgres.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 10 concluida.")
    print("Backup documental: " + backup["destino"])
    print("Backup logico OK: " + str(pg_dump["ok"]))
    print("Backup logico arquivo: " + str(pg_dump.get("stdout_file")))
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Docker OK: " + str(docker["docker_version"]["ok"]))
    print("Schema minimo OK: " + str(schema_minimo["ok"]))
    print("Testes funcionais OK: " + str(testes["ok"]))
    print("Validacao logica OK: " + str(testes["parse"]["ok_logico"]))
    print("Rollback OK: " + str(testes["parse"]["rollback_ok"]))
    print("Limpeza final OK: " + str(limpeza["ok"]))

    if not testes["ok"] or not limpeza["ok"]:
        print("")
        print("Existem falhas nos testes funcionais. Consulte o relatorio.")


if __name__ == "__main__":
    main()