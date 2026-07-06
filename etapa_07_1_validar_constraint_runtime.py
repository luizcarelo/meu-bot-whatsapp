#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 07.1 - Validar constraint runtime no PostgreSQL

Objetivo:
- Criar backup antes de alterar documentacao.
- Gerar manifesto antes e depois.
- Conectar ao PostgreSQL usando .env, sem imprimir senhas.
- Validar no banco real:
  - tabela contatos existe
  - colunas empresa_id e telefone existem
  - existe indice ou constraint unica para empresa_id e telefone
  - existem duplicidades em contatos para empresa_id e telefone
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


def ler_env_para_redacao():
    env_path = ROOT / ".env"
    texto = ler_texto(env_path)
    valores = []

    if texto is None:
        return valores

    for linha in texto.splitlines():
        if "=" not in linha:
            continue

        chave, valor = linha.split("=", 1)
        chave_upper = chave.strip().upper()
        valor = valor.strip().strip("'").strip('"')

        sensivel = False
        for termo in ["PASS", "PASSWORD", "SECRET", "TOKEN", "KEY", "SENHA"]:
            if termo in chave_upper:
                sensivel = True

        if sensivel and valor:
            valores.append(valor)

    return valores


def redigir_texto(texto):
    if texto is None:
        return texto

    novo = str(texto)
    for valor in ler_env_para_redacao():
        if valor:
            novo = novo.replace(valor, "<REDIGIDO>")

    return novo


def montar_node_probe():
    linhas = []

    linhas.append("const fs = require('fs');")
    linhas.append("const path = require('path');")
    linhas.append("let Client = null;")
    linhas.append("try { Client = require('pg').Client; } catch (e) {")
    linhas.append("  console.log(JSON.stringify({ ok: false, etapa: 'require_pg', erro: e.message }));")
    linhas.append("  process.exit(0);")
    linhas.append("}")
    linhas.append("")
    linhas.append("function parseEnv(filePath) {")
    linhas.append("  const out = {};")
    linhas.append("  if (!fs.existsSync(filePath)) return out;")
    linhas.append("  const text = fs.readFileSync(filePath, 'utf8');")
    linhas.append("  for (const rawLine of text.split(/\\r?\\n/)) {")
    linhas.append("    const line = rawLine.trim();")
    linhas.append("    if (!line || line.startsWith('#')) continue;")
    linhas.append("    const idx = line.indexOf('=');")
    linhas.append("    if (idx < 0) continue;")
    linhas.append("    const key = line.slice(0, idx).trim();")
    linhas.append("    let value = line.slice(idx + 1).trim();")
    linhas.append("    if ((value.startsWith('\"') && value.endsWith('\"')) || (value.startsWith(\"'\") && value.endsWith(\"'\"))) {")
    linhas.append("      value = value.slice(1, -1);")
    linhas.append("    }")
    linhas.append("    out[key] = value;")
    linhas.append("  }")
    linhas.append("  return out;")
    linhas.append("}")
    linhas.append("")
    linhas.append("function uniqueList(items) {")
    linhas.append("  const seen = {};")
    linhas.append("  const out = [];")
    linhas.append("  for (const item of items) {")
    linhas.append("    if (!item) continue;")
    linhas.append("    if (seen[item]) continue;")
    linhas.append("    seen[item] = true;")
    linhas.append("    out.push(item);")
    linhas.append("  }")
    linhas.append("  return out;")
    linhas.append("}")
    linhas.append("")
    linhas.append("function makeConfig(env, host) {")
    linhas.append("  return {")
    linhas.append("    host: host,")
    linhas.append("    port: Number(env.DB_PORT || 5432),")
    linhas.append("    user: env.DB_USER,")
    linhas.append("    password: env.DB_PASS,")
    linhas.append("    database: env.DB_NAME")
    linhas.append("  };")
    linhas.append("}")
    linhas.append("")
    linhas.append("async function runChecks(client) {")
    linhas.append("  const result = {};")
    linhas.append("  const tableSql = \"SELECT to_regclass('public.contatos') IS NOT NULL AS exists\";")
    linhas.append("  const tableRes = await client.query(tableSql);")
    linhas.append("  result.tabela_contatos_existe = !!tableRes.rows[0].exists;")
    linhas.append("")
    linhas.append("  const colSql = [")
    linhas.append("    \"SELECT column_name\",")
    linhas.append("    \"FROM information_schema.columns\",")
    linhas.append("    \"WHERE table_schema = 'public'\",")
    linhas.append("    \"AND table_name = 'contatos'\",")
    linhas.append("    \"AND column_name IN ('empresa_id', 'telefone')\",")
    linhas.append("    \"ORDER BY column_name\"")
    linhas.append("  ].join(' ');")
    linhas.append("  const colRes = await client.query(colSql);")
    linhas.append("  result.colunas_encontradas = colRes.rows.map(function(r) { return r.column_name; });")
    linhas.append("  result.coluna_empresa_id_existe = result.colunas_encontradas.indexOf('empresa_id') >= 0;")
    linhas.append("  result.coluna_telefone_existe = result.colunas_encontradas.indexOf('telefone') >= 0;")
    linhas.append("")
    linhas.append("  const idxSql = [")
    linhas.append("    \"SELECT i.relname AS index_name, ix.indisunique,\",")
    linhas.append("    \"array_agg(a.attname ORDER BY k.ord) AS columns\",")
    linhas.append("    \"FROM pg_class t\",")
    linhas.append("    \"JOIN pg_index ix ON t.oid = ix.indrelid\",")
    linhas.append("    \"JOIN pg_class i ON i.oid = ix.indexrelid\",")
    linhas.append("    \"JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS k(attnum, ord) ON true\",")
    linhas.append("    \"JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum\",")
    linhas.append("    \"WHERE t.relname = 'contatos'\",")
    linhas.append("    \"AND t.relnamespace = 'public'::regnamespace\",")
    linhas.append("    \"AND ix.indisunique = true\",")
    linhas.append("    \"GROUP BY i.relname, ix.indisunique\"")
    linhas.append("  ].join(' ');")
    linhas.append("  const idxRes = await client.query(idxSql);")
    linhas.append("  result.indices_unicos = idxRes.rows.map(function(r) {")
    linhas.append("    return { index_name: r.index_name, columns: r.columns };")
    linhas.append("  });")
    linhas.append("")
    linhas.append("  const conSql = [")
    linhas.append("    \"SELECT conname, contype, pg_get_constraintdef(oid) AS definition\",")
    linhas.append("    \"FROM pg_constraint\",")
    linhas.append("    \"WHERE conrelid = to_regclass('public.contatos')\",")
    linhas.append("    \"AND contype IN ('u', 'p')\",")
    linhas.append("    \"ORDER BY conname\"")
    linhas.append("  ].join(' ');")
    linhas.append("  const conRes = await client.query(conSql);")
    linhas.append("  result.constraints = conRes.rows;")
    linhas.append("")
    linhas.append("  function hasExactPair(cols) {")
    linhas.append("    if (!Array.isArray(cols)) return false;")
    linhas.append("    if (cols.length !== 2) return false;")
    linhas.append("    return cols[0] === 'empresa_id' && cols[1] === 'telefone';")
    linhas.append("  }")
    linhas.append("")
    linhas.append("  let uniquePair = false;")
    linhas.append("  for (const idx of result.indices_unicos) {")
    linhas.append("    if (hasExactPair(idx.columns)) uniquePair = true;")
    linhas.append("  }")
    linhas.append("  for (const con of result.constraints) {")
    linhas.append("    const def = String(con.definition || '').toLowerCase().replace(/\\s+/g, ' ');")
    linhas.append("    if (def.indexOf('unique (empresa_id, telefone)') >= 0) uniquePair = true;")
    linhas.append("  }")
    linhas.append("  result.unico_empresa_telefone_existe = uniquePair;")
    linhas.append("")
    linhas.append("  result.duplicados = [];")
    linhas.append("  result.duplicados_total_grupos = 0;")
    linhas.append("  if (result.tabela_contatos_existe && result.coluna_empresa_id_existe && result.coluna_telefone_existe) {")
    linhas.append("    const star = String.fromCharCode(42);")
    linhas.append("    const dupSql = [")
    linhas.append("      \"SELECT empresa_id, telefone, COUNT(\" + star + \")::int AS total\",")
    linhas.append("      \"FROM contatos\",")
    linhas.append("      \"GROUP BY empresa_id, telefone\",")
    linhas.append("      \"HAVING COUNT(\" + star + \") > 1\",")
    linhas.append("      \"ORDER BY total DESC\",")
    linhas.append("      \"LIMIT 20\"")
    linhas.append("    ].join(' ');")
    linhas.append("    const dupRes = await client.query(dupSql);")
    linhas.append("    result.duplicados = dupRes.rows;")
    linhas.append("    result.duplicados_total_grupos = dupRes.rows.length;")
    linhas.append("  }")
    linhas.append("")
    linhas.append("  result.pronto_para_on_conflict = !!(")
    linhas.append("    result.tabela_contatos_existe &&")
    linhas.append("    result.coluna_empresa_id_existe &&")
    linhas.append("    result.coluna_telefone_existe &&")
    linhas.append("    result.unico_empresa_telefone_existe &&")
    linhas.append("    result.duplicados_total_grupos === 0")
    linhas.append("  );")
    linhas.append("")
    linhas.append("  return result;")
    linhas.append("}")
    linhas.append("")
    linhas.append("async function main() {")
    linhas.append("  const env = parseEnv(path.join(process.cwd(), '.env'));")
    linhas.append("  const hosts = uniqueList([env.DB_HOST, env.DB_HOST === 'db' ? '127.0.0.1' : null, env.DB_HOST === 'db' ? 'localhost' : null]);")
    linhas.append("  const finalResult = {")
    linhas.append("    ok: false,")
    linhas.append("    etapa: 'runtime_constraint_check',")
    linhas.append("    env_encontrado: fs.existsSync(path.join(process.cwd(), '.env')),")
    linhas.append("    db_port_configurado: env.DB_PORT ? true : false,")
    linhas.append("    db_name_configurado: env.DB_NAME ? true : false,")
    linhas.append("    db_user_configurado: env.DB_USER ? true : false,")
    linhas.append("    hosts_tentados: [],")
    linhas.append("    conectado: false,")
    linhas.append("    host_usado: null,")
    linhas.append("    checks: null")
    linhas.append("  };")
    linhas.append("")
    linhas.append("  if (hosts.length === 0) hosts.push('localhost');")
    linhas.append("")
    linhas.append("  for (const host of hosts) {")
    linhas.append("    const client = new Client(makeConfig(env, host));")
    linhas.append("    try {")
    linhas.append("      await client.connect();")
    linhas.append("      finalResult.conectado = true;")
    linhas.append("      finalResult.host_usado = host;")
    linhas.append("      finalResult.hosts_tentados.push({ host: host, conectado: true });")
    linhas.append("      finalResult.checks = await runChecks(client);")
    linhas.append("      finalResult.ok = true;")
    linhas.append("      await client.end();")
    linhas.append("      break;")
    linhas.append("    } catch (e) {")
    linhas.append("      finalResult.hosts_tentados.push({ host: host, conectado: false, codigo: e.code || null, erro: e.message });")
    linhas.append("      try { await client.end(); } catch (endErr) {}")
    linhas.append("    }")
    linhas.append("  }")
    linhas.append("")
    linhas.append("  console.log(JSON.stringify(finalResult));")
    linhas.append("}")
    linhas.append("")
    linhas.append("main().catch(function(e) {")
    linhas.append("  console.log(JSON.stringify({ ok: false, etapa: 'runtime_constraint_check', erro: e.message }));")
    linhas.append("});")

    return "\n".join(linhas)


def executar_probe_runtime():
    node_code = montar_node_probe()

    try:
        proc = subprocess.run(
            ["node", "-e", node_code],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
    except Exception as exc:
        return {
            "ok": False,
            "erro": redigir_texto(str(exc)),
            "stdout": "",
            "stderr": ""
        }

    stdout = redigir_texto(proc.stdout.strip())
    stderr = redigir_texto(proc.stderr.strip())

    resultado = {
        "ok": False,
        "returncode": proc.returncode,
        "stdout": stdout[:2000],
        "stderr": stderr[:2000],
        "json": None
    }

    if stdout:
        try:
            resultado["json"] = json.loads(stdout.splitlines()[-1])
            resultado["ok"] = bool(resultado["json"].get("ok"))
        except Exception as exc:
            resultado["erro_parse_json"] = str(exc)

    return resultado


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_07_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_07_1_FIM -->"

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


def extrair_checks(relatorio):
    probe_json = relatorio.get("probe_runtime", {}).get("json")
    if not probe_json:
        return {}

    checks = probe_json.get("checks")
    if not checks:
        return {}

    return checks


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    probe_json = relatorio.get("probe_runtime", {}).get("json") or {}
    checks = extrair_checks(relatorio)

    conectado = str(bool(probe_json.get("conectado")))
    pronto = str(bool(checks.get("pronto_para_on_conflict")))
    duplicados = str(checks.get("duplicados_total_grupos", "nao_validado"))
    unico = str(bool(checks.get("unico_empresa_telefone_existe")))

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 07.1 - Constraint runtime validada",
        [
            "Data: " + data,
            "",
            "Foi executada validacao runtime no PostgreSQL usando configuracao local.",
            "Conexao realizada: " + conectado + ".",
            "Indice ou constraint unica por empresa e telefone no banco real: " + unico + ".",
            "Grupos duplicados encontrados: " + duplicados + ".",
            "Banco pronto para ON CONFLICT por empresa e telefone: " + pronto + ".",
            "Nenhuma alteracao foi aplicada ao banco."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 07.1 - Validacao runtime de constraint",
        [
            "Data: " + data,
            "",
            "Adicionada validacao runtime da tabela contatos no PostgreSQL.",
            "Verificada existencia das colunas empresa_id e telefone.",
            "Verificada existencia de indice ou constraint unica.",
            "Verificada existencia de duplicidades.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 07.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido validar o banco real antes de prosseguir para revisao de queries de media severidade.",
            "Decidido nao executar migration automaticamente nesta etapa.",
            "Decidido nao imprimir credenciais nos relatorios.",
            "Decidido tratar duplicidades ou ausencia de constraint em etapa separada, se necessario."
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
        pendencias.insert(2, "Resolver pendencia runtime de constraint ou duplicidade em contatos antes de usar o fluxo em producao.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 07.1",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    probe = relatorio["probe_runtime"]
    probe_json = probe.get("json") or {}
    checks = probe_json.get("checks") or {}

    linhas = []

    linhas.append("# Etapa 07.1 - Validar constraint runtime PostgreSQL")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Probe executado OK: " + str(probe["ok"]))
    linhas.append("- Conectado ao banco: " + str(bool(probe_json.get("conectado"))))
    linhas.append("- Host usado: " + str(probe_json.get("host_usado")))
    linhas.append("")

    linhas.append("## Resultado runtime")
    linhas.append("")
    if checks:
        linhas.append("- Tabela contatos existe: " + str(checks.get("tabela_contatos_existe")))
        linhas.append("- Coluna empresa_id existe: " + str(checks.get("coluna_empresa_id_existe")))
        linhas.append("- Coluna telefone existe: " + str(checks.get("coluna_telefone_existe")))
        linhas.append("- Unico empresa_id e telefone existe: " + str(checks.get("unico_empresa_telefone_existe")))
        linhas.append("- Grupos duplicados encontrados: " + str(checks.get("duplicados_total_grupos")))
        linhas.append("- Pronto para ON CONFLICT: " + str(checks.get("pronto_para_on_conflict")))
    else:
        linhas.append("- Checks nao executados ou sem retorno.")

    linhas.append("")
    linhas.append("## Hosts tentados")
    linhas.append("")
    for item in probe_json.get("hosts_tentados", []):
        linha = "- host=" + str(item.get("host")) + " conectado=" + str(item.get("conectado"))
        if item.get("codigo"):
            linha += " codigo=" + str(item.get("codigo"))
        if item.get("erro"):
            linha += " erro=" + redigir_texto(str(item.get("erro")))[:160]
        linhas.append(linha)

    linhas.append("")
    linhas.append("## Indices unicos encontrados")
    linhas.append("")
    indices = checks.get("indices_unicos") or []
    if indices:
        for item in indices:
            linhas.append("- " + str(item.get("index_name")) + " colunas=" + ", ".join(item.get("columns") or []))
    else:
        linhas.append("- Nenhum indice unico retornado.")

    linhas.append("")
    linhas.append("## Constraints encontradas")
    linhas.append("")
    constraints = checks.get("constraints") or []
    if constraints:
        for item in constraints:
            linhas.append("- " + str(item.get("conname")) + " tipo=" + str(item.get("contype")) + " def=" + str(item.get("definition")))
    else:
        linhas.append("- Nenhuma constraint retornada.")

    linhas.append("")
    linhas.append("## Duplicidades")
    linhas.append("")
    duplicados = checks.get("duplicados") or []
    if duplicados:
        for item in duplicados:
            linhas.append(
                "- empresa_id="
                + str(item.get("empresa_id"))
                + " telefone="
                + str(item.get("telefone"))
                + " total="
                + str(item.get("total"))
            )
    else:
        linhas.append("- Nenhuma duplicidade retornada.")

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
    backup_dir = BACKUPS_DIR / ("etapa_07_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_07_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    probe = executar_probe_runtime()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "probe_runtime": probe
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_07_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_07_1_validar_constraint_runtime.json"
    md_path = REPORTS_DIR / "etapa_07_1_validar_constraint_runtime.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    probe_json = probe.get("json") or {}
    checks = probe_json.get("checks") or {}

    print("Etapa 07.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Probe OK: " + str(probe["ok"]))
    print("Conectado: " + str(bool(probe_json.get("conectado"))))
    print("Host usado: " + str(probe_json.get("host_usado")))
    print("Tabela contatos existe: " + str(checks.get("tabela_contatos_existe")))
    print("Unico empresa_id telefone existe: " + str(checks.get("unico_empresa_telefone_existe")))
    print("Duplicidades: " + str(checks.get("duplicados_total_grupos")))
    print("Pronto para ON CONFLICT: " + str(checks.get("pronto_para_on_conflict")))


if __name__ == "__main__":
    main()