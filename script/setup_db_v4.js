// Arquivo: script/setup_db_v4.js
// Descrição: Atualiza ENUM da tabela mensagens para suportar novos tipos
// Tipos adicionados: localizacao, contato, enquete, evento

const path = require('path');
const dotenvPath = path.resolve(__dirname, '.env');
require('dotenv').config({ path: dotenvPath });

if (!process.env.DB_HOST) {
    require('dotenv').config({ path: path.resolve(__dirname, '../.env') });
}

const mysql = require('mysql2/promise');

async function atualizarTiposMensagem() {
    console.log('\n========================================');
    console.log('🚀 MIGRAÇÃO V4: NOVOS TIPOS DE MENSAGEM');
    console.log('========================================\n');

    let connection;

    try {
        connection = await mysql.createConnection({
            host: process.env.DB_HOST,
            user: process.env.DB_USER,
            password: process.env.DB_PASS,
            database: process.env.DB_NAME,
            multipleStatements: true
        });

        console.log(`✅ Conectado: ${process.env.DB_NAME}`);

        // Alterar a coluna TIPO para incluir novos formatos
        // Tipos atuais: 'texto','imagem','video','audio','documento','sticker','sistema'
        // Novos: 'localizacao', 'contato', 'enquete', 'evento'
        
        console.log('➡️  Atualizando estrutura da tabela "mensagens"...');
        
        const sql = `
            ALTER TABLE mensagens 
            MODIFY COLUMN tipo 
            ENUM('texto', 'imagem', 'video', 'audio', 'documento', 'sticker', 'sistema', 'localizacao', 'contato', 'enquete', 'evento') 
            DEFAULT 'texto';
        `;

        await connection.query(sql);
        
        console.log('   ✓ Tabela atualizada com sucesso.');
        console.log('\n✅ MIGRAÇÃO V4 CONCLUÍDA!');

    } catch (error) {
        console.error('\n❌ ERRO:', error.message);
    } finally {
        if (connection) await connection.end();
    }
}

atualizarTiposMensagem();