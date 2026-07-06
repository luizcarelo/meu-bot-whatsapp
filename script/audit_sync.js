require('dotenv').config({ path: require('path').join(__dirname, '../.env') });
const { Client } = require('pg');

async function auditAndFix() {
    const client = new Client({
        host: process.env.DB_HOST,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        database: process.env.DB_NAME
    });

    try {
        await client.connect();
        console.log("🔍 [Auditoria] Conectado ao banco. Verificando tabelas...");

        // Ajuste 1: Adicionar colunas faltantes na tabela usuarios_painel
        await client.query(`
            ALTER TABLE usuarios_painel 
            ADD COLUMN IF NOT EXISTS cargo VARCHAR(50),
            ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;
        `);
        console.log("✅ [Ajuste] Tabela 'usuarios_painel' sincronizada.");

        // Ajuste 2: Adicionar colunas em empresas
        await client.query(`
            ALTER TABLE empresas 
            ADD COLUMN IF NOT EXISTS whatsapp_status VARCHAR(50),
            ADD COLUMN IF NOT EXISTS whatsapp_numero VARCHAR(50),
            ADD COLUMN IF NOT EXISTS whatsapp_updated_at TIMESTAMP;
        `);
        console.log("✅ [Ajuste] Tabela 'empresas' sincronizada.");

        // Ajuste 3: Garantir que contatos tem ultima_msg
        await client.query(`
            ALTER TABLE contatos 
            ADD COLUMN IF NOT EXISTS ultima_msg TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        `);
        console.log("✅ [Ajuste] Tabela 'contatos' sincronizada.");

        console.log("✨ Auditoria concluída com sucesso! Banco compatível com o Back-end.");
    } catch (err) {
        console.error("❌ ERRO NA AUDITORIA:", err.message);
    } finally {
        await client.end();
    }
}

auditAndFix();