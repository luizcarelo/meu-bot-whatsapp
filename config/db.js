// ============================================
// Arquivo: config/db.js
// Descrição: Configuração da conexão com MySQL
// ============================================

require('dotenv').config();
const mysql = require('mysql2/promise');

// ============================================
// CONFIGURAÇÃO DO POOL DE CONEXÕES
// ============================================
const pool = mysql.createPool({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASS,
    database: process.env.DB_NAME,
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0,
    enableKeepAlive: true,
    keepAliveInitialDelay: 0,
    // Configurações adicionais de segurança e performance
    connectTimeout: 10000,
    // Configurações de timezone
    timezone: '+00:00',
    // Charset
    charset: 'utf8mb4'
});

// ============================================
// HEALTH CHECK DO BANCO DE DADOS
// ============================================
pool.getConnection()
    .then(conn => {
        console.log(`\n${'='.repeat(50)}`);
        console.log(`✅ MySQL Conectado com Sucesso`);
        console.log(`📍 Host: ${process.env.DB_HOST}`);
        console.log(`🗄️  Database: ${process.env.DB_NAME}`);
        console.log(`${'='.repeat(50)}\n`);
        conn.release();
    })
    .catch(err => {
        console.error('\n❌ ERRO FATAL: Falha na conexão com MySQL');
        console.error('Detalhes:', err.message);
        console.error('\nVerifique:');
        console.error('  1. Se o MySQL está rodando');
        console.error('  2. Se as credenciais no .env estão corretas');
        console.error('  3. Se o banco de dados existe');
        console.error('  4. Se há permissões adequadas\n');

        // Em produção, você pode querer encerrar o processo
        if (process.env.NODE_ENV === 'production') {
            process.exit(1);
        }
    });

// ============================================
// TRATAMENTO DE ERROS DO POOL
// ============================================
pool.on('error', (err) => {
    console.error('❌ Erro no pool de conexões MySQL:', err);
    if (err.code === 'PROTOCOL_CONNECTION_LOST') {
        console.error('Conexão com o banco de dados foi perdida.');
    }
    if (err.code === 'ER_CON_COUNT_ERROR') {
        console.error('O banco de dados tem muitas conexões.');
    }
    if (err.code === 'ECONNREFUSED') {
        console.error('Conexão com o banco de dados foi recusada.');
    }
});

// ============================================
// FUNÇÕES AUXILIARES
// ============================================

/**
 * Testa a conexão com o banco de dados
 * @returns {Promise<boolean>}
 */
async function testConnection() {
    try {
        const conn = await pool.getConnection();
        await conn.ping();
        conn.release();
        return true;
    } catch (err) {
        console.error('Erro ao testar conexão:', err.message);
        return false;
    }
}

/**
 * Executa uma query com retry em caso de falha
 * @param {string} sql - Query SQL
 * @param {Array} params - Parâmetros da query
 * @param {number} retries - Número de tentativas
 * @returns {Promise}
 */
async function executeWithRetry(sql, params = [], retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            return await pool.execute(sql, params);
        } catch (err) {
            if (i === retries - 1) throw err;
            console.warn(`Tentativa ${i + 1} falhou, tentando novamente...`);
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        }
    }
}

/**
 * Fecha o pool de conexões gracefully
 * @returns {Promise<void>}
 */
async function closePool() {
    try {
        // Verifica se o pool já está fechado antes de tentar fechar
        // (Pools do mysql2 não expõem propriedade 'closed' pública facilmente, 
        // mas o try/catch captura a tentativa em estado inválido)
        await pool.end();
        console.log('✅ Pool de conexões fechado com sucesso');
    } catch (err) {
        // Ignora erro se já estiver fechado
        if (err.message && err.message.includes('Pool is closed')) return;
        console.error('❌ Erro ao fechar pool de conexões:', err);
    }
}

// REMOVIDOS OS LISTENERS DE PROCESSO AQUI
// O controle de shutdown agora é exclusivo do server.js para evitar conflitos.

// ============================================
// EXPORTAÇÕES
// ============================================
module.exports = pool;
module.exports.testConnection = testConnection;
module.exports.executeWithRetry = executeWithRetry;
module.exports.closePool = closePool;