const path = require('path');
const fs = require('fs');

// 1. FAREJADOR DE .ENV (Procura na raiz e na pasta script)
let envPath = path.join(__dirname, '../.env'); // Tenta na raiz primeiro
if (!fs.existsSync(envPath)) {
    envPath = path.join(__dirname, '.env'); // Tenta na pasta script depois
}
require('dotenv').config({ path: envPath });

const { Client } = require('pg');

async function resetBanco() {
    console.log("🚨 INICIANDO RESET TOTAL DO BANCO DE DADOS (POSTGRESQL)...");
    console.log(`🔍 [DEBUG] Lendo variáveis do arquivo: ${envPath}`);
    console.log(`🔍 [DEBUG] Host: ${process.env.DB_HOST} | Usuário: ${process.env.DB_USER}`);
    console.log(`🔍 [DEBUG] Senha carregada: ${process.env.DB_PASS ? "SIM (******)" : "NÃO ❌ (Vazio - Verifique o arquivo .env)"}`);
    console.log("⚠️  ATENÇÃO: TODOS OS DADOS SERÃO APAGADOS!");

    if (!process.env.DB_PASS) {
        console.error("❌ ERRO: O script não encontrou a senha no .env. Implantação abortada.");
        return;
    }

    const adminClient = new Client({
        host: process.env.DB_HOST,
        port: process.env.DB_PORT,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        database: 'postgres' // O banco padrão do servidor
    });

    try {
        await adminClient.connect();
        const dbName = process.env.DB_NAME;
        
        console.log(`🗑️  Tentando apagar o banco ${dbName}...`);
        
        await adminClient.query(`
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '${dbName}' AND pid <> pg_backend_pid();
        `);
        
        await adminClient.query(`DROP DATABASE IF EXISTS "${dbName}"`);
        console.log("🗑️  Banco antigo apagado.");

        await adminClient.query(`CREATE DATABASE "${dbName}"`);
        console.log("✨ Novo banco criado.");
    } catch (err) {
        console.error("❌ Erro ao recriar banco:", err.message);
    } finally {
        await adminClient.end();
    }

    // PASSO 2: Conecta diretamente no NOVO banco criado
    const dbClient = new Client({
        host: process.env.DB_HOST,
        port: process.env.DB_PORT,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        database: process.env.DB_NAME
    });

    try {
        await dbClient.connect();

        const sql = `
            CREATE TABLE empresas (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                plano VARCHAR(20) DEFAULT 'gratis',
                limite_usuarios INT DEFAULT 3,
                ativo BOOLEAN DEFAULT TRUE,
                logo_url TEXT,
                cor_primaria VARCHAR(7) DEFAULT '#4f46e5',
                mensagens_padrao JSONB,
                msg_ausencia TEXT,
                horario_inicio TIME DEFAULT '08:00:00',
                horario_fim TIME DEFAULT '18:00:00',
                dias_funcionamento JSONB,
                whatsapp_status VARCHAR(50),
                whatsapp_numero VARCHAR(50),
                whatsapp_updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE setores (
                id SERIAL PRIMARY KEY,
                empresa_id INT,
                nome VARCHAR(50) NOT NULL,
                mensagem_saudacao TEXT,
                padrao BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            );

            CREATE TABLE usuarios_painel (
                id SERIAL PRIMARY KEY,
                empresa_id INT,
                nome VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                senha VARCHAR(255),
                cargo VARCHAR(50), 
                is_super_admin BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                ativo BOOLEAN DEFAULT TRUE,
                setor_id INT DEFAULT NULL,
                reset_token VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            );

            CREATE TABLE contatos (
                id SERIAL PRIMARY KEY,
                empresa_id INT,
                telefone VARCHAR(100),
                nome VARCHAR(100),
                cnpj_cpf VARCHAR(20),
                email VARCHAR(100),
                endereco TEXT,
                anotacoes TEXT,
                foto_perfil TEXT,
                status_atendimento VARCHAR(20) DEFAULT 'ABERTO',
                ultima_msg TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, telefone),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            );

            CREATE TABLE mensagens (
                id SERIAL PRIMARY KEY,
                empresa_id INT,
                remote_jid VARCHAR(100) NOT NULL,
                from_me BOOLEAN,
                tipo VARCHAR(20),
                conteudo TEXT,
                url_midia TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            );
        `;
        
        await dbClient.query(sql);
        console.log("🏗️  Tabelas criadas com sucesso.");

        console.log("👤 Criando Super Admin...");
        await dbClient.query(`
            INSERT INTO empresas (id, nome, plano, limite_usuarios)
            VALUES (1, 'Super Admin', 'enterprise', 999)
        `);

        await dbClient.query(`
            INSERT INTO usuarios_painel (id, empresa_id, nome, email, senha, is_super_admin, is_admin)
            VALUES (1, 1, 'Administrador', 'admin@saas.com', '123456', TRUE, TRUE)
        `);

        console.log("✅ RESET CONCLUÍDO! Banco PostgreSQL pronto para uso.");
        console.log("🔑 Login: admin@saas.com / 123456");

    } catch (error) {
        console.error("❌ ERRO FATAL NAS TABELAS:", error.message);
    } finally {
        await dbClient.end();
    }
}

resetBanco();