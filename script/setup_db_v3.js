// Arquivo: script/setup_db_v3.js
// Descrição: Adiciona e ATUALIZA tabelas para o Sistema de Etiquetas (Tags)
// Compatibilidade: MariaDB/MySQL

// --- CORREÇÃO DE CAMINHO DO .ENV ---
// Tenta carregar do diretório atual (se foi movido para cá) ou volta um nível (raiz)
const path = require('path');
const dotenvPath = path.resolve(__dirname, '.env');
require('dotenv').config({ path: dotenvPath });

// Fallback se não achar na pasta atual, tenta na raiz (padrão)
if (!process.env.DB_HOST) {
    require('dotenv').config({ path: path.resolve(__dirname, '../.env') });
}

const mysql = require('mysql2/promise');

async function migrarTags() {
    console.log('\n========================================');
    console.log('🏷️ MIGRAÇÃO: SISTEMA DE ETIQUETAS (V3)');
    console.log('========================================\n');

    // Diagnóstico de Conexão
    console.log('🔍 Configuração de Conexão:');
    console.log(`   Arquivo .env: ${process.env.DB_HOST ? 'Carregado' : 'NÃO ENCONTRADO'}`);
    console.log(`   Host: ${process.env.DB_HOST || 'NÃO DEFINIDO'}`);
    console.log(`   User: ${process.env.DB_USER || 'NÃO DEFINIDO'}`);
    console.log(`   Database: ${process.env.DB_NAME || 'NÃO DEFINIDO'}`);
    console.log('----------------------------------------\n');

    if (!process.env.DB_HOST) {
        console.error('❌ ERRO: Arquivo .env não encontrado ou variáveis vazias.');
        console.error('   Certifique-se de que o arquivo .env está na pasta "script" ou na raiz do projeto.');
        process.exit(1);
    }

    let connection;

    try {
        connection = await mysql.createConnection({
            host: process.env.DB_HOST,
            user: process.env.DB_USER,
            password: process.env.DB_PASS,
            database: process.env.DB_NAME,
            multipleStatements: true
        });

        console.log(`✅ Conectado ao banco de dados: ${process.env.DB_NAME}`);

        // ===============================================
        // 1. TABELA ETIQUETAS
        // ===============================================
        console.log('➡️  Processando tabela "etiquetas"...');
        
        // Criação básica se não existir
        await connection.query(`
            CREATE TABLE IF NOT EXISTS etiquetas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT NOT NULL,
                nome VARCHAR(50) NOT NULL,
                cor VARCHAR(20) DEFAULT '#64748b',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        `);

        // Atualização de Colunas (Se a tabela já existia incompleta)
        try {
            await connection.query("ALTER TABLE etiquetas ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP");
            await connection.query("ALTER TABLE etiquetas MODIFY COLUMN empresa_id INT NOT NULL");
        } catch (e) {
            if (!e.message.includes("Duplicate column")) console.log(`   ℹ️  Nota sobre etiquetas: ${e.message}`);
        }
        console.log('   ✓ Tabela "etiquetas" verificada.');


        // ===============================================
        // 2. TABELA CONTATOS_ETIQUETAS
        // ===============================================
        console.log('➡️  Processando tabela "contatos_etiquetas"...');

        // Criação básica se não existir
        await connection.query(`
            CREATE TABLE IF NOT EXISTS contatos_etiquetas (
                contato_id INT NOT NULL,
                etiqueta_id INT NOT NULL,
                empresa_id INT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (contato_id, etiqueta_id),
                FOREIGN KEY (contato_id) REFERENCES contatos(id) ON DELETE CASCADE,
                FOREIGN KEY (etiqueta_id) REFERENCES etiquetas(id) ON DELETE CASCADE,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        `);

        // Atualização de Colunas
        try {
            await connection.query("ALTER TABLE contatos_etiquetas ADD COLUMN IF NOT EXISTS empresa_id INT NOT NULL AFTER etiqueta_id");
            await connection.query("ALTER TABLE contatos_etiquetas ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP");

            try {
                await connection.query("ALTER TABLE contatos_etiquetas ADD CONSTRAINT fk_ce_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE");
            } catch (fkErr) { }

        } catch (e) {
            if (e.code === 'ER_DUP_FIELDNAME') {
                console.log('   ✓ Colunas já existem.');
            } else {
                console.log(`   ℹ️  Ajuste contatos_etiquetas: ${e.message}`);
            }
        }
        console.log('   ✓ Tabela "contatos_etiquetas" verificada.');

        console.log('\n✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!');

    } catch (error) {
        console.error('\n❌ ERRO FATAL NA MIGRAÇÃO:');
        
        if (error.code === 'ECONNREFUSED') {
            console.error('   ⚠️  CONEXÃO RECUSADA! O servidor MySQL está rodando?');
            console.error('   Verifique se o host e a porta no arquivo .env estão corretos.');
        } else if (error.code === 'ER_ACCESS_DENIED_ERROR') {
            console.error('   ⚠️  ACESSO NEGADO! Verifique usuário e senha no arquivo .env.');
        } else {
            console.error(`   Mensagem: ${error.message}`);
            console.error(`   Código: ${error.code}`);
        }
    } finally {
        if (connection) await connection.end();
    }
}

migrarTags();