// script/backup_database.js
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
