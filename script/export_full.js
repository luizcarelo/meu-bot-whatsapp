
// Arquivo: script/export_full.js
// Objetivo: Exportar DADOS (DML) de todas as tabelas do banco MySQL configurado no .env
// Formato: arquivo .sql contendo INSERTs por tabela
// Uso:
//   node script/export_full.js                 -> gera ./backups/data_<DB>_<timestamp>.sql
//   node script/export_full.js --tables t1,t2  -> exporta somente as tabelas informadas
//   node script/export_full.js --no-structure  -> não inclui DROP/CREATE (apenas INSERTs)
//   node script/export_full.js --limit 1000    -> lê em páginas (LIMIT) para tabelas muito grandes
// Requisitos:
//   - .env com DB_HOST, DB_USER, DB_PASS, DB_NAME
//   - mysql2/promise instalado

require('dotenv').config();
const mysql = require('mysql2/promise');
const fs = require('fs');
const fsp = fs.promises;
const path = require('path');

// Util para escapar valores manualmente (para segurança e compatibilidade)
function sqlEscape(val) {
  if (val === null || val === undefined) return 'NULL';
  if (Buffer.isBuffer(val)) return `'${val.toString('hex')}'`; // hex dentro de string simples
  if (typeof val === 'number') return String(val);
  if (typeof val === 'object') val = JSON.stringify(val);
  return `'${String(val).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
}

function chunkArray(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

async function exportFull() {
  console.log('\n========================================');
  console.log('💾 EXPORTAR DADOS (DML) DO BANCO');
  console.log('========================================\n');
  let conn;
  try {
    // 1) Conectar
    conn = await mysql.createConnection({
      host: process.env.DB_HOST,
      user: process.env.DB_USER,
      password: process.env.DB_PASS,
      database: process.env.DB_NAME,
      multipleStatements: true
    });
    console.log('✅ Conectado ao banco:', process.env.DB_NAME);

    // 2) Args
    const args = process.argv.slice(2);
    const tablesArg = (args.find(a => a.startsWith('--tables=')) || '').split('=')[1] || '';
    const tablesFilter = tablesArg ? tablesArg.split(',').map(s => s.trim()).filter(Boolean) : null;
    const includeStructure = !args.includes('--no-structure');
    const limitArg = (args.find(a => a.startsWith('--limit=')) || '').split('=')[1];
    const pageSize = limitArg ? parseInt(limitArg) : 0; // 0 = sem paginação

    // 3) Pasta de backups
    const backupDir = path.join(process.cwd(), 'backups');
    try { await fsp.access(backupDir); } catch { await fsp.mkdir(backupDir, { recursive: true }); }

    // 4) Nome do arquivo
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_').slice(0,19);
    const fileName = `data_${process.env.DB_NAME}_${timestamp}.sql`;
    const filePath = path.join(backupDir, fileName);

    // 5) Obter tabelas
    const [tables] = await conn.query('SHOW TABLES');
    const tableKey = `Tables_in_${process.env.DB_NAME}`;
    const tableNames = tables.map(r => r[tableKey]).filter(Boolean);
    const targetTables = tablesFilter ? tableNames.filter(t => tablesFilter.includes(t)) : tableNames;

    const header = `-- Data dump do banco: ${process.env.DB_NAME}\n` +
                   `-- Data: ${new Date().toLocaleString('pt-BR')}\n\n` +
                   `SET FOREIGN_KEY_CHECKS = 0;\n` +
                   `SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';\n` +
                   `SET AUTOCOMMIT = 0;\n` +
                   `START TRANSACTION;\n\n`;

    await fsp.writeFile(filePath, header, 'utf8');

    for (const t of targetTables) {
      console.log(`→ Processando tabela: ${t}`);
      // Estrutura opcional (DROP/CREATE)
      if (includeStructure) {
        try {
          const [createRes] = await conn.query(`SHOW CREATE TABLE \`${t}\``);
          const createStmt = createRes[0]['Create Table'] + ';\n\n';
          await fsp.appendFile(filePath, `-- Estrutura da tabela ${t}\nDROP TABLE IF EXISTS \`${t}\`;\n${createStmt}`);
        } catch (e) {
          console.log(` ⚠️ ${t}: falha ao obter estrutura (${e.message}). Continuando com dados...`);
        }
      }

      // Dados
      // Obter colunas para montar INSERT
      const [colsRes] = await conn.query(`SHOW COLUMNS FROM \`${t}\``);
      const cols = colsRes.map(c => c.Field);
      const colList = cols.map(c => `\`${c}\``).join(', ');

      const writer = fs.createWriteStream(filePath, { flags: 'a' });

      const writeInserts = async (rows) => {
        if (!rows.length) return;
        const values = rows.map(r => `(${cols.map(c => sqlEscape(r[c])).join(', ')})`);
        const insertSql = `INSERT INTO \`${t}\` (${colList}) VALUES\n` + values.join(',\n') + ';\n\n';
        await new Promise((resolve, reject) => {
          writer.write(insertSql, err => err ? reject(err) : resolve());
        });
      };

      if (pageSize && pageSize > 0) {
        // Paginar
        let offset = 0;
        while (true) {
          const [rows] = await conn.query(`SELECT * FROM \`${t}\` LIMIT ${pageSize} OFFSET ${offset}`);
          if (!rows.length) break;
          await writeInserts(rows);
          offset += pageSize;
          console.log(`   ✓ ${t}: +${rows.length} registros (offset=${offset})`);
        }
      } else {
        // Sem paginação: carrega tudo (cuidado com tabelas muito grandes)
        const [rows] = await conn.query(`SELECT * FROM \`${t}\``);
        await writeInserts(rows);
        console.log(`   ✓ ${t}: ${rows.length} registros exportados`);
      }

      await new Promise((resolve) => writer.end(resolve));
    }

    const footer = `COMMIT;\nSET FOREIGN_KEY_CHECKS = 1;\n`;
    await fsp.appendFile(filePath, footer);

    const stats = await fsp.stat(filePath);
    console.log('\n✅ DADOS EXPORTADOS COM SUCESSO!');
    console.log(`📦 Arquivo: ${fileName}`);
    console.log(`📁 Local: ${filePath}`);
    console.log(`📊 Tamanho: ${stats.size} bytes`);
    console.log('\n💡 Para restaurar:');
    console.log('   mysql -u USUARIO -p BANCO < backups/' + fileName);
  } catch (error) {
    console.error('\n❌ ERRO:', error.message);
    console.error('\nDetalhes:', error);
  } finally {
    if (conn) await conn.end();
  }
}

