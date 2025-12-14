require('dotenv').config();
const mysql = require('mysql2/promise');

async function resetBanco() {
    console.log("🚨 INICIANDO RESET TOTAL DO BANCO DE DADOS...");
    console.log("⚠️  ATENÇÃO: TODOS OS DADOS SERÃO APAGADOS!");

    const connection = await mysql.createConnection({
        host: process.env.DB_HOST,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        multipleStatements: true
    });

    try {
        // 1. APAGAR BANCO EXISTENTE (Drop)
        await connection.query(`DROP DATABASE IF EXISTS ${process.env.DB_NAME}`);
        console.log("🗑️  Banco antigo apagado.");

        // 2. RECRIAR BANCO LIMPO (Create)
        await connection.query(`CREATE DATABASE ${process.env.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`);
        await connection.query(`USE ${process.env.DB_NAME}`);
        console.log("✨ Novo banco criado.");

        // 3. CRIAR TABELAS (Estrutura SaaS Completa)
        const sql = `
            -- Empresas (Tenants)
            CREATE TABLE empresas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                plano ENUM('gratis', 'pro', 'enterprise') DEFAULT 'gratis',
                limite_usuarios INT DEFAULT 3,
                ativo BOOLEAN DEFAULT 1,
                logo_url TEXT,
                cor_primaria VARCHAR(7) DEFAULT '#4f46e5',
                mensagens_padrao JSON,
                msg_ausencia TEXT,
                horario_inicio TIME DEFAULT '08:00:00',
                horario_fim TIME DEFAULT '18:00:00',
                dias_funcionamento JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            -- Setores
            CREATE TABLE setores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT,
                nome VARCHAR(50) NOT NULL,
                mensagem_saudacao TEXT,
                padrao BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            -- Usuários (Painel)
            CREATE TABLE usuarios_painel (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT,
                nome VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                senha VARCHAR(255),
                is_super_admin BOOLEAN DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                setor_id INT DEFAULT NULL,
                reset_token VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE SET NULL
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            -- Contatos (CRM)
            CREATE TABLE contatos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT,
                telefone VARCHAR(100),
                nome VARCHAR(100),
                cnpj_cpf VARCHAR(20),
                email VARCHAR(100),
                endereco TEXT,
                anotacoes TEXT,
                foto_perfil TEXT,
                status_atendimento VARCHAR(20) DEFAULT 'ABERTO',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_contato (empresa_id, telefone),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            -- Mensagens (Histórico)
            CREATE TABLE mensagens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT,
                remote_jid VARCHAR(100) NOT NULL,
                from_me BOOLEAN,
                tipo VARCHAR(20),
                conteudo TEXT,
                url_midia TEXT,
                data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            -- Avaliações (NPS)
            CREATE TABLE avaliacoes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT,
                contato_telefone VARCHAR(100),
                atendente_id INT,
                nota INT,
                comentario TEXT,
                data_avaliacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        `;
        await connection.query(sql);
        console.log("🏗️  Tabelas criadas com sucesso.");

        // 4. INSERIR DADOS PADRÃO (Super Admin)
        console.log("👤 Criando Super Admin...");
        
        // Cria a "Empresa" do Super Admin
        await connection.query(`
            INSERT INTO empresas (id, nome, plano, limite_usuarios) 
            VALUES (1, 'Super Admin', 'enterprise', 999)
        `);
        
        // Cria o Usuário Super Admin
        await connection.query(`
            INSERT INTO usuarios_painel (id, empresa_id, nome, email, senha, is_super_admin, is_admin) 
            VALUES (1, 1, 'Administrador', 'admin@saas.com', '123456', 1, 1)
        `);

        console.log("✅ RESET CONCLUÍDO! Banco pronto para uso.");
        console.log("🔑 Login: admin@saas.com / 123456");

    } catch (error) {
        console.error("❌ ERRO FATAL:", error.message);
    } finally {
        await connection.end();
    }
}

resetBanco();