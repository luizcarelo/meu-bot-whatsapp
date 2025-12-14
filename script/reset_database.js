// Arquivo: reset_database.js
// Script para APAGAR e RECRIAR todo o banco de dados
// ⚠️ ATENÇÃO: Este script deleta TODOS os dados permanentemente!

require('dotenv').config();
const mysql = require('mysql2/promise');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

// Função para perguntar ao usuário
function question(query) {
    return new Promise(resolve => rl.question(query, resolve));
}

async function resetDatabase() {
    console.log('\n========================================');
    console.log('🔴 SCRIPT DE RESET TOTAL DO BANCO DE DADOS');
    console.log('========================================\n');
    console.log('⚠️  ATENÇÃO: Este script irá:');
    console.log('   - Deletar TODAS as tabelas');
    console.log('   - Apagar TODOS os dados de empresas, usuários, mensagens, etc.');
    console.log('   - Recriar a estrutura do banco zerada\n');

    const confirmacao = await question('Digite "SIM APAGAR TUDO" para confirmar: ');

    if (confirmacao !== 'SIM APAGAR TUDO') {
        console.log('❌ Operação cancelada.');
        rl.close();
        process.exit(0);
    }

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

        console.log('\n✅ Conectado ao banco de dados');

        // ===========================
        // PASSO 1: DELETAR TODAS AS TABELAS
        // ===========================
        console.log('\n🗑️  Deletando tabelas existentes...');

        const dropTables = `
            SET FOREIGN_KEY_CHECKS = 0;

            DROP TABLE IF EXISTS avaliacoes;
            DROP TABLE IF EXISTS mensagens;
            DROP TABLE IF EXISTS mensagens_rapidas;
            DROP TABLE IF EXISTS usuarios_setores;
            DROP TABLE IF EXISTS setores;
            DROP TABLE IF EXISTS contatos;
            DROP TABLE IF EXISTS usuarios_painel;
            DROP TABLE IF EXISTS empresas;

            SET FOREIGN_KEY_CHECKS = 1;
        `;

        await connection.query(dropTables);
        console.log('   ✓ Todas as tabelas foram deletadas');

        // ===========================
        // PASSO 2: RECRIAR ESTRUTURA DO BANCO
        // ===========================
        console.log('\n🔨 Recriando estrutura do banco de dados...');

        // Tabela: empresas
        await connection.query(`
            CREATE TABLE empresas (
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
        console.log('   ✓ Tabela empresas criada');

        // Tabela: usuarios_painel
        await connection.query(`
            CREATE TABLE usuarios_painel (
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
        console.log('   ✓ Tabela usuarios_painel criada');

        // Tabela: setores
        await connection.query(`
            CREATE TABLE setores (
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
        console.log('   ✓ Tabela setores criada');

        // Tabela: contatos
        await connection.query(`
            CREATE TABLE contatos (
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
        console.log('   ✓ Tabela contatos criada');

        // Tabela: mensagens
        await connection.query(`
            CREATE TABLE mensagens (
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
        console.log('   ✓ Tabela mensagens criada');

        // Tabela: mensagens_rapidas
        await connection.query(`
            CREATE TABLE mensagens_rapidas (
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
        console.log('   ✓ Tabela mensagens_rapidas criada');

        // Tabela: usuarios_setores
        await connection.query(`
            CREATE TABLE usuarios_setores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NOT NULL,
                setor_id INT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios_painel(id) ON DELETE CASCADE,
                FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE CASCADE,
                UNIQUE KEY unique_usuario_setor (usuario_id, setor_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `);
        console.log('   ✓ Tabela usuarios_setores criada');

        // Tabela: avaliacoes
        await connection.query(`
            CREATE TABLE avaliacoes (
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
        console.log('   ✓ Tabela avaliacoes criada');

        // ===========================
        // PASSO 3: INSERIR EMPRESA PADRÃO (SISTEMA)
        // ===========================
        console.log('\n📦 Criando empresa padrão...');

        await connection.query(`
            INSERT INTO empresas (id, nome, nome_sistema, ativo, plano, limite_usuarios)
            VALUES (1, 'Sistema Master', 'Sistema Master', 1, 'enterprise', 999);
        `);
        console.log('   ✓ Empresa "Sistema Master" criada (ID: 1)');

        console.log('\n✅ BANCO DE DADOS RESETADO COM SUCESSO!');
        console.log('\n📋 Próximos passos:');
        console.log('   1. Execute: npm start');
        console.log('   2. Acesse: http://localhost:4000/login');
        console.log('   3. Use Super Admin: admin@saas.com / 123456');
        console.log('   4. Crie sua primeira empresa no painel\n');

    } catch (error) {
        console.error('\n❌ ERRO:', error.message);
        console.error('\nDetalhes completos:', error);
    } finally {
        if (connection) {
            await connection.end();
        }
        rl.close();
    }
}

// Executa o script
resetDatabase();