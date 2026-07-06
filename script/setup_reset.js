require('dotenv').config();
const { Client } = require('pg');

async function resetBanco() {
    console.log("🚨 INICIANDO RESET TOTAL DO BANCO DE DADOS (POSTGRESQL)...");
    console.log("⚠️  ATENÇÃO: TODOS OS DADOS SERÃO APAGADOS!");

    // PASSO 1: Conecta no banco raiz do servidor para poder apagar/criar o nosso banco
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
        
        // Desconecta possíveis usuários pendurados no banco antes de apagar
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
        console.error("❌ Erro ao recriar banco (O banco pode ainda não existir, o que é normal na primeira vez):", err.message);
    } finally {
        await adminClient.end();
    }

    // PASSO 2: Conecta diretamente no NOVO banco criado para estruturar as tabelas
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
            -- Empresas (Tenants)
            CREATE TABLE empresas (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                plano VARCHAR(20) DEFAULT 'gratis' CHECK (plano IN ('gratis', 'pro', 'enterprise')),
                limite_usuarios INT DEFAULT 3,
                ativo BOOLEAN DEFAULT TRUE,
                logo_url TEXT,
                cor_primaria VARCHAR(7) DEFAULT '#4f46e5',
                mensagens_padrao JSONB,
                msg_ausencia TEXT,
                horario_inicio TIME DEFAULT '08:00:00',
                horario_fim TIME DEFAULT '18:00:00',
                dias_funcionamento JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Setores
            CREATE TABLE setores (
                id SERIAL PRIMARY KEY,
                empresa_id INT,
                nome VARCHAR(50) NOT NULL,
                mensagem_saudacao TEXT,
                padrao BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            );

            -- Usuários (Painel)
            CREATE TABLE usuarios_painel (
                id SERIAL PRIMARY KEY,
                empresa_id INT,
                nome VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                senha VARCHAR(255),
                is_super_admin BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                setor_id INT DEFAULT NULL,
                reset_token VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE SET NULL
            );

            -- Contatos (CRM)
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, telefone),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            );

            -- Mensagens (Histórico)
            CREATE TABLE mensagens (
                id SERIAL PRIMARY KEY,
                empresa_id INT,
                remote_jid VARCHAR(100) NOT NULL,
                from_me BOOLEAN,
                tipo VARCHAR(20),
                conteudo TEXT,
                url_midia TEXT,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            );

            -- Avaliações (NPS)
            CREATE TABLE avaliacoes (
                id SERIAL PRIMARY KEY,
                empresa_id INT,
                contato_telefone VARCHAR(100),
                atendente_id INT,
                nota INT,
                comentario TEXT,
                data_avaliacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            );
        `;
        
        await dbClient.query(sql);
        console.log("🏗️  Tabelas criadas com sucesso.");

        console.log("👤 Criando Super Admin...");

        // Insere a empresa
        await dbClient.query(`
            INSERT INTO empresas (id, nome, plano, limite_usuarios)
            VALUES (1, 'Super Admin', 'enterprise', 999)
        `);

        // Insere o administrador
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