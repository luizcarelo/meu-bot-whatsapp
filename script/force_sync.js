require('dotenv').config({ path: require('path').join(__dirname, '../.env') });
const { Client } = require('pg');

async function forceSync() {
    const client = new Client({
        host: process.env.DB_HOST,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        database: process.env.DB_NAME
    });

    try {
        await client.connect();
        console.log("🚀 [Force Sync] Iniciando criação de tabelas...");

        const schema = `
            CREATE TABLE IF NOT EXISTS empresas (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                plano VARCHAR(20) DEFAULT 'gratis',
                limite_usuarios INT DEFAULT 3,
                ativo BOOLEAN DEFAULT TRUE,
                logo_url TEXT,
                cor_primaria VARCHAR(7) DEFAULT '#4f46e5',
                mensagens_padrao JSONB,
                whatsapp_status VARCHAR(50),
                whatsapp_numero VARCHAR(50),
                whatsapp_updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS usuarios_painel (
                id SERIAL PRIMARY KEY,
                empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
                nome VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                senha VARCHAR(255),
                cargo VARCHAR(50),
                is_super_admin BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS contatos (
                id SERIAL PRIMARY KEY,
                empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
                telefone VARCHAR(100),
                nome VARCHAR(100),
                status_atendimento VARCHAR(20) DEFAULT 'ABERTO',
                ultima_msg TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, telefone)
            );

            CREATE TABLE IF NOT EXISTS mensagens (
                id SERIAL PRIMARY KEY,
                empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
                remote_jid VARCHAR(100) NOT NULL,
                from_me BOOLEAN,
                conteudo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        `;

        await client.query(schema);
        console.log("✅ [Force Sync] Todas as tabelas foram verificadas/criadas com sucesso.");
    } catch (err) {
        console.error("❌ ERRO NO SYNC:", err.stack);
    } finally {
        await client.end();
    }
}

forceSync();