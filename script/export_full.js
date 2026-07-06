// script/export_full.js
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
