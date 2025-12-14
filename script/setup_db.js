require('dotenv').config();
const mysql = require('mysql2/promise');

async function instalarBanco() {
    console.log("🔄 A verificar banco de dados...");

    const connection = await mysql.createConnection({
        host: process.env.DB_HOST,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        multipleStatements: true
    });

    try {
        await connection.query(`CREATE DATABASE IF NOT EXISTS ${process.env.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`);
        await connection.query(`USE ${process.env.DB_NAME}`);

        const sql = `
            CREATE TABLE IF NOT EXISTS empresas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                nome_sistema VARCHAR(100),
                plano ENUM('gratis', 'pro', 'enterprise') DEFAULT 'gratis',
                limite_usuarios INT DEFAULT 3,
                ativo BOOLEAN DEFAULT 1,
                logo_url TEXT,
                cor_primaria VARCHAR(7) DEFAULT '#4f46e5',
                mensagens_padrao JSON,
                msg_ausencia TEXT,
                msg_avaliacao TEXT,
                openai_key VARCHAR(255),
                openai_prompt TEXT,
                openai_ativo BOOLEAN DEFAULT 0,
                horario_inicio TIME DEFAULT '08:00:00',
                horario_fim TIME DEFAULT '18:00:00',
                dias_funcionamento JSON,
                welcome_media_url TEXT,
                welcome_media_type VARCHAR(20),
                whatsapp_numero VARCHAR(50),
                whatsapp_status VARCHAR(20) DEFAULT 'DESCONECTADO',
                whatsapp_updated_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS setores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT,
                nome VARCHAR(50) NOT NULL,
                mensagem_saudacao TEXT,
                padrao BOOLEAN DEFAULT 0,
                media_url TEXT,
                media_type VARCHAR(20),
                cor VARCHAR(7) DEFAULT '#cbd5e1', /* NOVO: Cor para identificar o setor */
                ordem INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS usuarios_painel (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT,
                nome VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                senha VARCHAR(255),
                telefone VARCHAR(20), /* NOVO */
                cargo VARCHAR(50),    /* NOVO */
                ativo BOOLEAN DEFAULT 1, /* NOVO */
                is_super_admin BOOLEAN DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                reset_token VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS usuarios_setores (
                usuario_id INT,
                setor_id INT,
                PRIMARY KEY (usuario_id, setor_id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios_painel(id) ON DELETE CASCADE,
                FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            /* TABELA NOVA: MENSAGENS RÁPIDAS */
            CREATE TABLE IF NOT EXISTS mensagens_rapidas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT,
                titulo VARCHAR(50),
                conteudo TEXT,
                atalho VARCHAR(20), /* Ex: /pix */
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS contatos (
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
                setor_id INT DEFAULT NULL,
                atendente_id INT DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_contato (empresa_id, telefone),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE SET NULL,
                FOREIGN KEY (atendente_id) REFERENCES usuarios_painel(id) ON DELETE SET NULL
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS mensagens (
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

            CREATE TABLE IF NOT EXISTS avaliacoes (
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

        console.log("⚙️ Verificando atualizações de estrutura...");
        const migrations = [
            "ALTER TABLE empresas ADD COLUMN nome_sistema VARCHAR(100)",
            "ALTER TABLE empresas ADD COLUMN msg_avaliacao TEXT",
            "ALTER TABLE empresas ADD COLUMN openai_key VARCHAR(255)",
            "ALTER TABLE empresas ADD COLUMN openai_prompt TEXT",
            "ALTER TABLE empresas ADD COLUMN openai_ativo BOOLEAN DEFAULT 0",
            "ALTER TABLE usuarios_painel ADD COLUMN telefone VARCHAR(20)",
            "ALTER TABLE usuarios_painel ADD COLUMN cargo VARCHAR(50)",
            "ALTER TABLE usuarios_painel ADD COLUMN ativo BOOLEAN DEFAULT 1",
            "ALTER TABLE setores ADD COLUMN cor VARCHAR(7) DEFAULT '#cbd5e1'"
        ];

        for (const query of migrations) {
            try { await connection.query(query); console.log(`✅ Correção aplicada: ${query}`); }
            catch (e) { if (!e.message.includes('Duplicate')) console.log(`ℹ️ Info: ${e.message}`); }
        }

        // Garante Super Admin
        await connection.query(`INSERT IGNORE INTO empresas (id, nome, plano, limite_usuarios) VALUES (1, 'Super Admin', 'enterprise', 999)`);
        await connection.query(`INSERT IGNORE INTO usuarios_painel (id, empresa_id, nome, email, senha, is_super_admin, is_admin) VALUES (1, 1, 'Administrador', 'admin@saas.com', '123456', 1, 1)`);
        await connection.query("UPDATE usuarios_painel SET is_admin = 1 WHERE is_super_admin = 1");

        console.log("✅ Banco de dados pronto e atualizado!");

    } catch (error) { console.error("❌ Erro Banco:", error.message); } finally { await connection.end(); }
}

instalarBanco();