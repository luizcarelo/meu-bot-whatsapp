#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 04 - Limpar MySQL e validar PostgreSQL

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Limpar documentacao principal com referencias antigas a MySQL.
- Atualizar .github/copilot-instructions.md para PostgreSQL.
- Corrigir comentarios tecnicos em arquivos JS.
- Converter scripts auxiliares script/export_full.js e script/backup_database.js para pg.
- Validar package.json para PostgreSQL.
- Rodar node --check nos JS principais.
- Gerar relatorio de rastros restantes ignorando falsos positivos.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.

Escopo:
- Nao altera regras de negocio do chatbot.
- Nao altera .env real.
- Nao executa banco.
- Nao executa Docker.
"""

import os
import re
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

MAX_LEITURA = 2097152

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "README.md",
    "MELHORIAS.md",
    ".github/copilot-instructions.md",
    "controllers/AuthController.js",
    "controllers/CrmController.js",
    "src/config/db.js",
    "src/utils/atendimento.js",
    "script/export_full.js",
    "script/backup_database.js",
    "package.json",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_DOC_LIMPEZA = [
    "README.md",
    "MELHORIAS.md",
    ".github/copilot-instructions.md"
]

ARQUIVOS_JS_COMENTARIOS = [
    "controllers/AuthController.js",
    "controllers/CrmController.js",
    "src/config/db.js",
    "src/utils/atendimento.js"
]

ARQUIVOS_JS_CHECK = [
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

EXTENSOES_SCAN = [
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
    ".sh"
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

IGNORAR_SCAN_DIRS = [
    "reports",
    "backups",
    "node_modules",
    ".git",
    "auth_sessions",
    "public/uploads"
]

IGNORAR_SCAN_ARQUIVOS_PREFIXOS = [
    "etapa_"
]

IGNORAR_SCAN_ARQUIVOS_EXATOS = [
    "etapa_03_corrigir_docker_mysql.py",
    "etapa_03_1_padronizar_postgres.py",
    "etapa_03_1_hotfix_relatorio.py"
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
    for nome in ["node_modules", ".git", "backups", "auth_sessions"]:
        if nome in partes:
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
                "arquivo": nome,
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def aplicar_replaces(texto, replaces):
    novo = texto
    alteracoes = 0

    for antigo, novo_valor in replaces:
        if antigo in novo:
            qtd = novo.count(antigo)
            novo = novo.replace(antigo, novo_valor)
            alteracoes += qtd

    return novo, alteracoes


def limpar_documentacao():
    resultados = []

    replaces = [
        ("MySQL ≥ 5.7", "PostgreSQL 15 ou superior"),
        ("MySQL >= 5.7", "PostgreSQL 15 ou superior"),
        ("MariaDB ≥ 10.3", "PostgreSQL 15 ou superior"),
        ("MariaDB >= 10.3", "PostgreSQL 15 ou superior"),
        ("Conexão MySQL", "Conexao PostgreSQL"),
        ("Conexao MySQL", "Conexao PostgreSQL"),
        ("pool MySQL", "pool PostgreSQL"),
        ("Pool de conexão MySQL", "Pool de conexao PostgreSQL"),
        ("Pool de conexao MySQL", "Pool de conexao PostgreSQL"),
        ("MySQL/SMTP/SUPER_ADMIN_PASS", "PostgreSQL/SMTP/SUPER_ADMIN_PASS"),
        ("MySQL e helpers", "PostgreSQL e helpers"),
        ("MySQL via config/db.js", "PostgreSQL via src/config/db.js"),
        ("MySQL", "PostgreSQL"),
        ("mysql", "postgres"),
        ("MariaDB", "PostgreSQL"),
        ("mariadb", "postgres")
    ]

    for nome in ARQUIVOS_DOC_LIMPEZA:
        path = ROOT / nome
        texto = ler_texto(path)

        if texto is None:
            resultados.append({
                "arquivo": nome,
                "existe": path.exists(),
                "alterado": False,
                "alteracoes": 0,
                "motivo": "Arquivo ausente ou ilegivel"
            })
            continue

        novo, alteracoes = aplicar_replaces(texto, replaces)
        novo = novo.replace(chr(42), "")

        if novo != texto:
            validar_sem_asterisco_indevido(novo, nome)
            gravar_texto(path, novo)

        resultados.append({
            "arquivo": nome,
            "existe": True,
            "alterado": novo != texto,
            "alteracoes": alteracoes
        })

    return resultados

def limpar_comentarios_js():
    resultados = []

    replaces = [
        ("PostgreSQL retorna true/false, MySQL retornava 1/0",
         "PostgreSQL retorna valores booleanos nativos"),
        ("Pool de conexão MySQL", "Pool de conexao PostgreSQL"),
        ("Pool de conexao MySQL", "Pool de conexao PostgreSQL"),
        ("Pool do MySQL/MariaDB", "Pool do PostgreSQL"),
        ("Conexão Pool do MySQL/MariaDB", "Conexao Pool do PostgreSQL"),
        ("Conexao Pool do MySQL/MariaDB", "Conexao Pool do PostgreSQL"),
        ("Traduz consultas com \"?\" do MySQL para \"$1, $2\" do PostgreSQL",
         "Normaliza parametros posicionais para PostgreSQL quando necessario"),
        ("Mantém compatibilidade com o MySQL", "Mantem compatibilidade com chamadas legadas do projeto"),
        ("Mantem compatibilidade com o MySQL", "Mantem compatibilidade com chamadas legadas do projeto"),
        ("MySQL", "PostgreSQL"),
        ("mysql", "postgres"),
        ("MariaDB", "PostgreSQL"),
        ("mariadb", "postgres")
    ]

    for nome in ARQUIVOS_JS_COMENTARIOS:
        path = ROOT / nome
        texto = ler_texto(path)

        if texto is None:
            resultados.append({
                "arquivo": nome,
                "existe": path.exists(),
                "alterado": False,
                "alteracoes": 0,
                "motivo": "Arquivo ausente ou ilegivel"
            })
            continue

        novo, alteracoes = aplicar_replaces(texto, replaces)

        if novo != texto:
            gravar_texto(path, novo)

        resultados.append({
            "arquivo": nome,
            "existe": True,
            "alterado": novo != texto,
            "alteracoes": alteracoes
        })

    return resultados


def conteudo_export_full_pg():
    conteudo = r'''// script/export_full.js
// Objetivo: Exportar dados DML de todas as tabelas do banco PostgreSQL configurado no .env
// Uso: node script/export_full.js

require('dotenv').config();

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

function quoteIdent(name) {
  return '"' + String(name).replace(/"/g, '""') + '"';
}

function sqlValue(value) {
  if (value === null || value === undefined) {
    return 'NULL';
  }

  if (value instanceof Date) {
    return "'" + value.toISOString().replace(/'/g, "''") + "'";
  }

  if (Buffer.isBuffer(value)) {
    return "'\\\\x" + value.toString('hex') + "'";
  }

  if (typeof value === 'number') {
    if (Number.isFinite(value)) {
      return String(value);
    }
    return 'NULL';
  }

  if (typeof value === 'boolean') {
    return value ? 'TRUE' : 'FALSE';
  }

  if (typeof value === 'object') {
    return "'" + JSON.stringify(value).replace(/'/g, "''") + "'";
  }

  return "'" + String(value).replace(/'/g, "''") + "'";
}

async function listarTabelas(client) {
  const sql = [
    'SELECT table_schema, table_name',
    'FROM information_schema.tables',
    "WHERE table_type = 'BASE TABLE'",
    "AND table_schema NOT IN ('pg_catalog', 'information_schema')",
    'ORDER BY table_schema, table_name'
  ].join(' ');

  const result = await client.query(sql);
  return result.rows;
}

async function listarColunas(client, schema, table) {
  const sql = [
    'SELECT column_name',
    'FROM information_schema.columns',
    'WHERE table_schema = $1 AND table_name = $2',
    'ORDER BY ordinal_position'
  ].join(' ');

  const result = await client.query(sql, [schema, table]);
  return result.rows.map(function(row) {
    return row.column_name;
  });
}

async function exportar() {
  const client = new Client({
    host: process.env.DB_HOST || 'localhost',
    port: Number(process.env.DB_PORT || 5432),
    user: process.env.DB_USER,
    password: process.env.DB_PASS,
    database: process.env.DB_NAME
  });

  await client.connect();

  try {
    const tabelas = await listarTabelas(client);
    const backupDir = path.join(process.cwd(), 'backups');
    fs.mkdirSync(backupDir, { recursive: true });

    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const fileName = 'export_postgres_' + stamp + '.sql';
    const filePath = path.join(backupDir, fileName);

    const linhas = [];
    linhas.push('-- Exportacao DML PostgreSQL');
    linhas.push('-- Gerado em ' + new Date().toISOString());
    linhas.push('BEGIN;');

    for (const tabela of tabelas) {
      const schema = tabela.table_schema;
      const table = tabela.table_name;
      const colunas = await listarColunas(client, schema, table);

      if (colunas.length === 0) {
        continue;
      }

      const selectSql = 'SELECT ' + colunas.map(quoteIdent).join(', ') +
        ' FROM ' + quoteIdent(schema) + '.' + quoteIdent(table);

      const rows = await client.query(selectSql);
      const destino = quoteIdent(schema) + '.' + quoteIdent(table);
      const colunasSql = colunas.map(quoteIdent).join(', ');

      for (const row of rows.rows) {
        const valores = colunas.map(function(coluna) {
          return sqlValue(row[coluna]);
        }).join(', ');

        linhas.push('INSERT INTO ' + destino + ' (' + colunasSql + ') VALUES (' + valores + ');');
      }
    }

    linhas.push('COMMIT;');
    fs.writeFileSync(filePath, linhas.join('\n') + '\n', 'utf8');

    console.log('Exportacao PostgreSQL concluida.');
    console.log('Arquivo: ' + filePath);
    console.log('Restaurar com:');
    console.log('psql -U USUARIO -d BANCO -f ' + filePath);
  } finally {
    await client.end();
  }
}

exportar().catch(function(err) {
  console.error('Falha ao exportar PostgreSQL:', err.message);
  process.exit(1);
});
'''
    validar_sem_asterisco_indevido(conteudo, "script/export_full.js")
    return conteudo


def conteudo_backup_database_pg():
    conteudo = r'''// script/backup_database.js
// Objetivo: Criar backup DML do banco PostgreSQL configurado no .env
// Uso: node script/backup_database.js

require('dotenv').config();

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

function quoteIdent(name) {
  return '"' + String(name).replace(/"/g, '""') + '"';
}

function sqlValue(value) {
  if (value === null || value === undefined) {
    return 'NULL';
  }

  if (value instanceof Date) {
    return "'" + value.toISOString().replace(/'/g, "''") + "'";
  }

  if (Buffer.isBuffer(value)) {
    return "'\\\\x" + value.toString('hex') + "'";
  }

  if (typeof value === 'number') {
    if (Number.isFinite(value)) {
      return String(value);
    }
    return 'NULL';
  }

  if (typeof value === 'boolean') {
    return value ? 'TRUE' : 'FALSE';
  }

  if (typeof value === 'object') {
    return "'" + JSON.stringify(value).replace(/'/g, "''") + "'";
  }

  return "'" + String(value).replace(/'/g, "''") + "'";
}

async function queryTabelas(client) {
  const sql = [
    'SELECT table_schema, table_name',
    'FROM information_schema.tables',
    "WHERE table_type = 'BASE TABLE'",
    "AND table_schema NOT IN ('pg_catalog', 'information_schema')",
    'ORDER BY table_schema, table_name'
  ].join(' ');

  const result = await client.query(sql);
  return result.rows;
}

async function queryColunas(client, schema, table) {
  const sql = [
    'SELECT column_name',
    'FROM information_schema.columns',
    'WHERE table_schema = $1 AND table_name = $2',
    'ORDER BY ordinal_position'
  ].join(' ');

  const result = await client.query(sql, [schema, table]);
  return result.rows.map(function(row) {
    return row.column_name;
  });
}

async function backup() {
  const client = new Client({
    host: process.env.DB_HOST || 'localhost',
    port: Number(process.env.DB_PORT || 5432),
    user: process.env.DB_USER,
    password: process.env.DB_PASS,
    database: process.env.DB_NAME
  });

  await client.connect();

  try {
    const tabelas = await queryTabelas(client);
    const backupDir = path.join(process.cwd(), 'backups');
    fs.mkdirSync(backupDir, { recursive: true });

    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filePath = path.join(backupDir, 'backup_postgres_' + stamp + '.sql');

    const linhas = [];
    linhas.push('-- Backup DML PostgreSQL');
    linhas.push('-- Gerado em ' + new Date().toISOString());
    linhas.push('BEGIN;');

    for (const tabela of tabelas) {
      const schema = tabela.table_schema;
      const table = tabela.table_name;
      const colunas = await queryColunas(client, schema, table);

      if (colunas.length === 0) {
        continue;
      }

      const selectSql = 'SELECT ' + colunas.map(quoteIdent).join(', ') +
        ' FROM ' + quoteIdent(schema) + '.' + quoteIdent(table);

      const result = await client.query(selectSql);
      const destino = quoteIdent(schema) + '.' + quoteIdent(table);
      const colunasSql = colunas.map(quoteIdent).join(', ');

      for (const row of result.rows) {
        const valores = colunas.map(function(coluna) {
          return sqlValue(row[coluna]);
        }).join(', ');

        linhas.push('INSERT INTO ' + destino + ' (' + colunasSql + ') VALUES (' + valores + ');');
      }
    }

    linhas.push('COMMIT;');
    fs.writeFileSync(filePath, linhas.join('\n') + '\n', 'utf8');

    console.log('Backup PostgreSQL concluido.');
    console.log('Arquivo: ' + filePath);
    console.log('Restaurar com:');
    console.log('psql -U ' + String(process.env.DB_USER || 'USUARIO') + ' -d ' + String(process.env.DB_NAME || 'BANCO') + ' -f ' + filePath);
  } finally {
    await client.end();
  }
}

backup().catch(function(err) {
  console.error('Falha ao gerar backup PostgreSQL:', err.message);
  process.exit(1);
});
'''
    validar_sem_asterisco_indevido(conteudo, "script/backup_database.js")
    return conteudo


def converter_scripts_auxiliares():
    resultados = []

    scripts = [
        ("script/export_full.js", conteudo_export_full_pg()),
        ("script/backup_database.js", conteudo_backup_database_pg())
    ]

    for nome, novo in scripts:
        path = ROOT / nome
        anterior = ler_texto(path)
        gravar_texto(path, novo)

        resultados.append({
            "arquivo": nome,
            "existia_antes": anterior is not None,
            "alterado": anterior != novo,
            "sha256_depois": sha256_arquivo(path)
        })

    return resultados


def validar_package_json():
    path = ROOT / "package.json"
    texto = ler_texto(path)

    if texto is None:
        return {
            "ok": False,
            "erros": ["package.json ausente ou ilegivel"],
            "avisos": []
        }

    erros = []
    avisos = []

    try:
        pkg = json.loads(texto)
    except Exception as exc:
        return {
            "ok": False,
            "erros": ["package.json invalido: " + str(exc)],
            "avisos": []
        }

    deps = {}
    deps.update(pkg.get("dependencies", {}))
    deps.update(pkg.get("devDependencies", {}))

    if "pg" not in deps:
        erros.append("Dependencia pg nao encontrada em package.json")

    if "mysql2" in deps:
        erros.append("Dependencia mysql2 ainda encontrada em package.json")

    if "mysql" in deps:
        erros.append("Dependencia mysql ainda encontrada em package.json")

    if "sequelize" in deps:
        avisos.append("sequelize encontrado. Validar dialect PostgreSQL se estiver em uso.")

    return {
        "ok": len(erros) == 0,
        "erros": erros,
        "avisos": avisos,
        "pg_version": deps.get("pg"),
        "total_dependencias": len(deps)
    }


def node_disponivel():
    try:
        result = subprocess.run(
            ["node", "--version"],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception:
        return False, None


def node_check():
    disponivel, versao = node_disponivel()

    resultados = {
        "node_disponivel": disponivel,
        "node_versao": versao,
        "arquivos": []
    }

    if not disponivel:
        resultados["aviso"] = "Node nao disponivel para node --check"
        return resultados

    for nome in ARQUIVOS_JS_CHECK:
        path = ROOT / nome

        if not path.exists():
            resultados["arquivos"].append({
                "arquivo": nome,
                "existe": False,
                "ok": False,
                "erro": "Arquivo ausente"
            })
            continue

        try:
            result = subprocess.run(
                ["node", "--check", str(path)],
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=40
            )

            resultados["arquivos"].append({
                "arquivo": nome,
                "existe": True,
                "ok": result.returncode == 0,
                "stdout": result.stdout.strip()[:500],
                "stderr": result.stderr.strip()[:1000]
            })
        except Exception as exc:
            resultados["arquivos"].append({
                "arquivo": nome,
                "existe": True,
                "ok": False,
                "erro": str(exc)
            })

    return resultados


def deve_ignorar_scan(path):
    partes = set(path.parts)

    for nome in IGNORAR_SCAN_DIRS:
        partes_nome = nome.split("/")
        if len(partes_nome) == 1 and partes_nome[0] in partes:
            return True

    rel_path = rel(path)

    for nome in IGNORAR_SCAN_DIRS:
        if "/" in nome:
            if rel_path == nome or rel_path.startswith(nome + "/"):
                return True

    base = path.name

    if base in IGNORAR_SCAN_ARQUIVOS_EXATOS:
        return True

    for prefixo in IGNORAR_SCAN_ARQUIVOS_PREFIXOS:
        if base.startswith(prefixo) and base.endswith(".py"):
            return True

    return False


def linha_redigida(linha):
    if "=" not in linha:
        return linha.strip()[:160]

    esquerda = linha.split("=", 1)[0].strip()
    esquerda_upper = esquerda.upper()

    for termo in ["PASS", "PASSWORD", "SECRET", "TOKEN", "KEY", "SENHA"]:
        if termo in esquerda_upper:
            return esquerda + "=<REDIGIDO>"

    return linha.strip()[:160]


def escanear_rastros_mysql_filtrado():
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
            if ext not in EXTENSOES_SCAN and p.name not in [".env.example"]:
                continue

            texto = ler_texto(p)
            if texto is None:
                continue

            for numero, linha in enumerate(texto.splitlines(), start=1):
                linha_lower = linha.lower()
                termos = []

                for termo in TERMOS_MYSQL:
                    if termo.lower() in linha_lower:
                        termos.append(termo)

                if termos:
                    achados.append({
                        "arquivo": rel(p),
                        "linha": numero,
                        "termos": termos,
                        "conteudo_redigido": linha_redigida(linha)
                    })

    return achados


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_04_INICIO -->"
    marcador_fim = "<!-- ETAPA_04_FIM -->"

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
    rastros = str(len(relatorio["rastros_mysql_filtrados"]))

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 04 - Limpeza PostgreSQL",
        [
            "Data: " + data,
            "",
            "Foram limpas referencias antigas de MySQL em documentacao e comentarios tecnicos.",
            "Os scripts auxiliares de exportacao e backup foram convertidos para PostgreSQL usando pg.",
            "O package.json foi validado quanto ao uso de pg.",
            "Foi executada validacao de sintaxe com node --check quando Node estava disponivel.",
            "Rastros filtrados restantes: " + rastros + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 04 - Limpeza PostgreSQL",
        [
            "Data: " + data,
            "",
            "Atualizada documentacao principal para PostgreSQL.",
            "Atualizadas instrucoes internas em .github/copilot-instructions.md.",
            "Corrigidos comentarios tecnicos em controllers e utilitarios.",
            "Convertidos script/export_full.js e script/backup_database.js para pg.",
            "Gerado relatorio filtrado de rastros restantes.",
            "Executado node --check nos arquivos JS principais."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 04 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido manter PostgreSQL como banco oficial do projeto.",
            "Decidido converter scripts auxiliares para pg sem alterar regras de negocio.",
            "Decidido ignorar reports, backups e scripts de etapas anteriores no scan de rastros.",
            "Decidido manter validacao de sintaxe separada de testes funcionais de banco."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 04",
        [
            "Data: " + data,
            "",
            "Revisar eventuais rastros PostgreSQL pendentes listados no relatorio da Etapa 04.",
            "Executar testes funcionais com banco PostgreSQL em ambiente controlado.",
            "Validar setup_db.js e migrations em detalhes.",
            "Revisar queries complexas em controllers e managers.",
            "Planejar rotacao de credenciais reais expostas anteriormente.",
            "Planejar etapa de hardening de seguranca HTTP, CORS e rate limit."
        ]
    )

    return DOCS_OBRIGATORIOS


def resumo_node_check(node_resultado):
    total = len(node_resultado.get("arquivos", []))
    ok = 0
    falhas = 0
    ausentes = 0

    for item in node_resultado.get("arquivos", []):
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


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 04 - Limpar MySQL e validar PostgreSQL")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Validacao package.json OK: " + str(relatorio["validacao_package_json"]["ok"]))
    linhas.append("- Rastros filtrados restantes: " + str(len(relatorio["rastros_mysql_filtrados"])))
    linhas.append("")

    linhas.append("## Documentacao limpa")
    linhas.append("")
    for item in relatorio["limpeza_documentacao"]:
        linhas.append("- " + item["arquivo"] + ": alterado=" + str(item["alterado"]) + ", alteracoes=" + str(item["alteracoes"]))

    linhas.append("")
    linhas.append("## Comentarios JS limpos")
    linhas.append("")
    for item in relatorio["limpeza_comentarios_js"]:
        linhas.append("- " + item["arquivo"] + ": alterado=" + str(item["alterado"]) + ", alteracoes=" + str(item["alteracoes"]))

    linhas.append("")
    linhas.append("## Scripts auxiliares convertidos")
    linhas.append("")
    for item in relatorio["scripts_convertidos"]:
        linhas.append("- " + item["arquivo"] + ": alterado=" + str(item["alterado"]))

    linhas.append("")
    linhas.append("## Validacao package.json")
    linhas.append("")
    vp = relatorio["validacao_package_json"]
    linhas.append("- OK: " + str(vp["ok"]))
    linhas.append("- pg: " + str(vp.get("pg_version")))
    if vp["erros"]:
        linhas.append("- Erros:")
        for erro in vp["erros"]:
            linhas.append("  - " + erro)
    else:
        linhas.append("- Erros: nenhum")
    if vp["avisos"]:
        linhas.append("- Avisos:")
        for aviso in vp["avisos"]:
            linhas.append("  - " + aviso)
    else:
        linhas.append("- Avisos: nenhum")

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    resumo = relatorio["resumo_node_check"]
    linhas.append("- Node disponivel: " + str(relatorio["node_check"]["node_disponivel"]))
    linhas.append("- Node versao: " + str(relatorio["node_check"].get("node_versao")))
    linhas.append("- Arquivos verificados: " + str(resumo["total"]))
    linhas.append("- OK: " + str(resumo["ok"]))
    linhas.append("- Falhas: " + str(resumo["falhas"]))
    linhas.append("- Ausentes: " + str(resumo["ausentes"]))

    falhas = []
    for item in relatorio["node_check"].get("arquivos", []):
        if item.get("existe") and not item.get("ok"):
            falhas.append(item)

    if falhas:
        linhas.append("")
        linhas.append("### Falhas node --check")
        linhas.append("")
        for item in falhas:
            detalhe = item.get("stderr") or item.get("erro") or "Falha sem detalhe"
            detalhe = detalhe.replace(chr(42), "[asterisco]")
            linhas.append("- " + item["arquivo"] + ": " + detalhe[:300])

    linhas.append("")
    linhas.append("## Rastros filtrados restantes")
    linhas.append("")
    if relatorio["rastros_mysql_filtrados"]:
        limite = 80
        for item in relatorio["rastros_mysql_filtrados"][:limite]:
            trecho = item["conteudo_redigido"].replace(chr(42), "[asterisco]")
            linhas.append(
                "- "
                + item["arquivo"]
                + ":"
                + str(item["linha"])
                + " termos="
                + ", ".join(item["termos"])
                + " trecho="
                + trecho
            )
        if len(relatorio["rastros_mysql_filtrados"]) > limite:
            linhas.append("- Lista truncada no Markdown. Consulte o JSON completo.")
    else:
        linhas.append("- Nenhum rastro MySQL funcional encontrado apos filtros.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 05: validar setup_db.js, queries, rotas e fluxo funcional com PostgreSQL.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_04_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_04_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    limpeza_doc = limpar_documentacao()
    limpeza_js = limpar_comentarios_js()
    scripts_convertidos = converter_scripts_auxiliares()
    validacao_package = validar_package_json()
    node_resultado = node_check()
    rastros = escanear_rastros_mysql_filtrado()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "limpeza_documentacao": limpeza_doc,
        "limpeza_comentarios_js": limpeza_js,
        "scripts_convertidos": scripts_convertidos,
        "validacao_package_json": validacao_package,
        "node_check": node_resultado,
        "resumo_node_check": resumo_node_check(node_resultado),
        "rastros_mysql_filtrados": rastros
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_04_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_04_limpar_mysql_e_validar_postgres.json"
    md_path = REPORTS_DIR / "etapa_04_limpar_mysql_e_validar_postgres.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 04 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Package JSON OK: " + str(validacao_package["ok"]))
    print("Node disponivel: " + str(node_resultado["node_disponivel"]))
    print("Node check falhas: " + str(relatorio["resumo_node_check"]["falhas"]))
    print("Rastros filtrados restantes: " + str(len(rastros)))

    if not validacao_package["ok"]:
        print("")
        print("Erros em package.json:")
        for erro in validacao_package["erros"]:
            print("- " + erro)

    if relatorio["resumo_node_check"]["falhas"] > 0:
        print("")
        print("Falhas em node --check. Consulte o relatorio Markdown.")

    if not validacao_package["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()