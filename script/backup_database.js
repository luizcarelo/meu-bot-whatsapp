// Arquivo: backup_database.js
// Script para fazer backup do banco de dados antes de resetar
// Útil para não perder dados importantes

require('dotenv').config();
const mysql = require('mysql2/promise');
const fs = require('fs').promises;
const path = require('path');

async function backupDatabase() {
    console.log('\n========================================');
    console.log('💾 BACKUP DO BANCO DE DADOS');
    console.log('========================================\n');

    let connection;

    try {
        // Conecta ao banco
        connection = await mysql.createConnection({
            host: process.env.DB_HOST,
            user: process.env.DB_USER,
            password: process.env.DB_PASS,
            database: process.env.DB_NAME
        });

        console.log('✅ Conectado ao banco de dados:', process.env.DB_NAME);

        // Cria pasta de backups
        const backupDir = path.join(process.cwd(), 'backups');
        try {
            await fs.access(backupDir);
        } catch {
            await fs.mkdir(backupDir);
            console.log('📁 Pasta "backups" criada');
        }

        // Nome do arquivo com timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0] + '_' + 
                         new Date().toTimeString().split(' ')[0].replace(/:/g, '-');
        const fileName = `backup_${process.env.DB_NAME}_${timestamp}.sql`;
        const filePath = path.join(backupDir, fileName);

        console.log('\n📋 Fazendo backup das tabelas...');

        let sqlDump = `-- Backup do banco de dados: ${process.env.DB_NAME}\n`;
        sqlDump += `-- Data: ${new Date().toLocaleString('pt-BR')}\n\n`;
        sqlDump += `SET FOREIGN_KEY_CHECKS = 0;\n\n`;

        // Lista de tabelas na ordem correta (respeita foreign keys)
        const tables = [
            'empresas',
            'usuarios_painel', 
            'setores',
            'contatos',
            'mensagens',
            'mensagens_rapidas',
            'usuarios_setores',
            'avaliacoes'
        ];

        for (const table of tables) {
            try {
                // Estrutura da tabela
                const [createTable] = await connection.query(`SHOW CREATE TABLE ${table}`);
                sqlDump += `-- Estrutura da tabela ${table}\n`;
                sqlDump += `DROP TABLE IF EXISTS \`${table}\`;\n`;
                sqlDump += createTable[0]['Create Table'] + ';\n\n';

                // Dados da tabela
                const [rows] = await connection.query(`SELECT * FROM ${table}`);
                
                if (rows.length > 0) {
                    sqlDump += `-- Dados da tabela ${table}\n`;
                    sqlDump += `INSERT INTO \`${table}\` VALUES\n`;

                    const values = rows.map(row => {
                        const vals = Object.values(row).map(val => {
                            if (val === null) return 'NULL';
                            if (typeof val === 'string') return `'${val.replace(/'/g, "''")}'`;
                            if (val instanceof Date) return `'${val.toISOString().slice(0, 19).replace('T', ' ')}'`;
                            if (typeof val === 'boolean') return val ? '1' : '0';
                            return val;
                        });
                        return `(${vals.join(', ')})`;
                    });

                    sqlDump += values.join(',\n') + ';\n\n';
                    console.log(`   ✓ ${table}: ${rows.length} registro(s)`);
                } else {
                    console.log(`   ✓ ${table}: 0 registros`);
                }

            } catch (e) {
                console.log(`   ⚠️  ${table}: tabela não existe`);
            }
        }

        sqlDump += `SET FOREIGN_KEY_CHECKS = 1;\n`;

        // Salva o arquivo
        await fs.writeFile(filePath, sqlDump, 'utf8');

        console.log('\n✅ BACKUP CONCLUÍDO COM SUCESSO!');
        console.log(`\n📦 Arquivo: ${fileName}`);
        console.log(`📁 Local: ${filePath}`);
        console.log(`📊 Tamanho: ${(await fs.stat(filePath)).size} bytes`);

        console.log('\n💡 Para restaurar o backup:');
        console.log(`   mysql -u ${process.env.DB_USER} -p ${process.env.DB_NAME} < ${filePath}\n`);

    } catch (error) {
        console.error('\n❌ ERRO:', error.message);
        console.error('\nDetalhes completos:', error);
    } finally {
        if (connection) {
            await connection.end();
        }
    }
}

// Executa o script
backupDatabase();