// Arquivo: setup_db_v2.js
// Script para criar/atualizar a estrutura do banco de dados

require('dotenv').config();
const mysql = require('mysql2/promise');

async function setupDatabase() {
    console.log('\n========================================');
    console.log('🔧 SETUP DO BANCO DE DADOS');
    console.log('========================================\n');

    let connection;

    try {
        // Conecta ao banco
        connection = await mysql.createConnection({
            host: process.env.DB_HOST,
            user: process.env.DB_USER,
            password: process.env.DB_PASS,
            database: process.env.DB_NAME,
            multipleStatements: true
        });

        console.log('✅ Conectado ao banco de dados:', process.env.DB_NAME);

        // ===========================
        // TABELA: empresas
        // ===========================
        console.log('\n📋 Criando tabela: empresas');
        await connection.query(`
            CREATE TABLE IF NOT EXISTS empresas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                nome_sistema VARCHAR(100),
                logo_url VARCHAR(255),
                cor_primaria VARCHAR(7) DEFAULT '#4f46e5',
                plano ENUM('gratis', 'pro', 'enterprise') DEFAULT 'pro',
                limite_usuarios INT DEFAULT 5,
                ativo BOOLEAN DEFAULT TRUE,
                whatsapp_numero VARCHAR(50),
                whatsapp_status ENUM('DESCONECTADO', 'AGUARDANDO_QR', 'CONECTADO') DEFAULT 'DESCONECTADO',
                whatsapp_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                mensagens_padrao JSON,
                msg_ausencia TEXT,
                msg_avaliacao TEXT,
                horario_inicio TIME DEFAULT '08:00:00',
                horario_fim TIME DEFAULT '18:00:00',
                dias_funcionamento JSON,
                welcome_media_url VARCHAR(255),
                welcome_media_type VARCHAR(20),
                openai_key VARCHAR(255),
                openai_prompt TEXT,
                openai_ativo BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_nome (nome),
                INDEX idx_ativo (ativo)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `);
        console.log('   ✓ Tabela empresas OK');

        // ===========================
        // TABELA: usuarios_painel
        // ===========================
        console.log('\n📋 Criando tabela: usuarios_painel');
        await connection.query(`
            CREATE TABLE IF NOT EXISTS usuarios_painel (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT NOT NULL,
                nome VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                senha VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                telefone VARCHAR(20),
                cargo VARCHAR(50),
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                UNIQUE KEY unique_email_empresa (email, empresa_id),
                INDEX idx_email (email),
                INDEX idx_empresa (empresa_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `);
        console.log('   ✓ Tabela usuarios_painel OK');

        // ===========================
        // TABELA: setores
        // ===========================
        console.log('\n📋 Criando tabela: setores');
        await connection.query(`
            CREATE TABLE IF NOT EXISTS setores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT NOT NULL,
                nome VARCHAR(100) NOT NULL,
                mensagem_saudacao TEXT,
                padrao BOOLEAN DEFAULT FALSE,
                ordem INT DEFAULT 0,
                media_url VARCHAR(255),
                media_type VARCHAR(20),
                cor VARCHAR(7) DEFAULT '#cbd5e1',
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                INDEX idx_empresa (empresa_id),
                INDEX idx_ordem (ordem)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `);
        console.log('   ✓ Tabela setores OK');

        // ===========================
        // TABELA: contatos
        // ===========================
        console.log('\n📋 Criando tabela: contatos');
        await connection.query(`
            CREATE TABLE IF NOT EXISTS contatos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT NOT NULL,
                telefone VARCHAR(50) NOT NULL,
                nome VARCHAR(100),
                cnpj_cpf VARCHAR(20),
                email VARCHAR(100),
                endereco TEXT,
                anotacoes TEXT,
                foto_perfil TEXT,
                setor_id INT,
                status_atendimento ENUM('ABERTO', 'FILA', 'ATENDENDO', 'AGUARDANDO_AVALIACAO', 'FINALIZADO') DEFAULT 'ABERTO',
                atendente_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE SET NULL,
                FOREIGN KEY (atendente_id) REFERENCES usuarios_painel(id) ON DELETE SET NULL,
                UNIQUE KEY unique_telefone_empresa (telefone, empresa_id),
                INDEX idx_status (status_atendimento),
                INDEX idx_setor (setor_id),
                INDEX idx_atendente (atendente_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `);
        console.log('   ✓ Tabela contatos OK');

        // ===========================
        // TABELA: mensagens
        // ===========================
        console.log('\n📋 Criando tabela: mensagens');
        await connection.query(`
            CREATE TABLE IF NOT EXISTS mensagens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT NOT NULL,
                remote_jid VARCHAR(50) NOT NULL,
                from_me BOOLEAN DEFAULT FALSE,
                tipo ENUM('texto', 'imagem', 'video', 'audio', 'documento', 'sticker', 'sistema') DEFAULT 'texto',
                conteudo TEXT,
                url_midia TEXT,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                INDEX idx_empresa_jid (empresa_id, remote_jid),
                INDEX idx_data (data_hora)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `);
        console.log('   ✓ Tabela mensagens OK');

        // ===========================
        // TABELA: mensagens_rapidas
        // ===========================
        console.log('\n📋 Criando tabela: mensagens_rapidas');
        await connection.query(`
            CREATE TABLE IF NOT EXISTS mensagens_rapidas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT NOT NULL,
                titulo VARCHAR(100) NOT NULL,
                conteudo TEXT NOT NULL,
                atalho VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                INDEX idx_empresa (empresa_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `);
        console.log('   ✓ Tabela mensagens_rapidas OK');

        // ===========================
        // TABELA: usuarios_setores
        // ===========================
        console.log('\n📋 Criando tabela: usuarios_setores');
        await connection.query(`
            CREATE TABLE IF NOT EXISTS usuarios_setores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NOT NULL,
                setor_id INT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios_painel(id) ON DELETE CASCADE,
                FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE CASCADE,
                UNIQUE KEY unique_usuario_setor (usuario_id, setor_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `);
        console.log('   ✓ Tabela usuarios_setores OK');

        // ===========================
        // TABELA: avaliacoes
        // ===========================
        console.log('\n📋 Criando tabela: avaliacoes');
        await connection.query(`
            CREATE TABLE IF NOT EXISTS avaliacoes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT NOT NULL,
                contato_telefone VARCHAR(50) NOT NULL,
                atendente_id INT,
                nota INT NOT NULL CHECK (nota BETWEEN 1 AND 5),
                comentario TEXT,
                data_avaliacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (atendente_id) REFERENCES usuarios_painel(id) ON DELETE SET NULL,
                INDEX idx_empresa (empresa_id),
                INDEX idx_data (data_avaliacao)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `);
        console.log('   ✓ Tabela avaliacoes OK');

        // ===========================
        // DADOS INICIAIS
        // ===========================
        console.log('\n📦 Verificando dados iniciais...');

        const [empresas] = await connection.query('SELECT COUNT(*) as total FROM empresas WHERE id = 1');
        
        if (empresas[0].total === 0) {
            await connection.query(`
                INSERT INTO empresas (id, nome, nome_sistema, ativo, plano, limite_usuarios)
                VALUES (1, 'Sistema Master', 'Sistema Master', 1, 'enterprise', 999);
            `);
            console.log('   ✓ Empresa "Sistema Master" criada (ID: 1)');
        } else {
            console.log('   ✓ Empresa "Sistema Master" já existe');
        }

        console.log('\n✅ BANCO DE DADOS CONFIGURADO COM SUCESSO!\n');
        console.log('📋 Próximos passos:');
        console.log('   1. Execute: npm start');
        console.log('   2. Acesse: http://localhost:4000/login');
        console.log('   3. Use Super Admin:');
        console.log('      Email: admin@saas.com');
        console.log('      Senha: 123456\n');

    } catch (error) {
        console.error('\n❌ ERRO:', error.message);
        
        if (error.code === 'ER_BAD_DB_ERROR') {
            console.error('\n⚠️  O banco de dados não existe!');
            console.error('   Execute no MySQL:');
            console.error(`   CREATE DATABASE ${process.env.DB_NAME};`);
        } else if (error.code === 'ER_ACCESS_DENIED_ERROR') {
            console.error('\n⚠️  Acesso negado ao MySQL!');
            console.error('   Verifique as credenciais no arquivo .env');
        } else {
            console.error('\nDetalhes completos:', error);
        }
    } finally {
        if (connection) {
            await connection.end();
        }
    }
}

// Executa o script
setupDatabase();
