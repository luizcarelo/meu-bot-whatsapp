// ============================================
// Arquivo: config/db.js
// Descrição: Configuração do Pool MySQL
// Versão: 5.0 - Revisado e Corrigido
// ============================================

const mysql = require('mysql2/promise');

// ============================================
// CONFIGURAÇÃO DO POOL
// ============================================

const pool = mysql.createPool({
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASS || '',
    database: process.env.DB_NAME || 'saas_whatsapp',
    port: parseInt(process.env.DB_PORT) || 3306,
    
    // Configurações de pool
    waitForConnections: true,
    connectionLimit: 20,
    queueLimit: 0,
    
    // Configurações de conexão
    connectTimeout: 30000,
    acquireTimeout: 30000,
    
    // Charset para emojis e caracteres especiais
    charset: 'utf8mb4',
    
    // Timezone
    timezone: 'local',
    
    // Suporte a múltiplas queries
    multipleStatements: false,
    
    // Manter conexão viva
    enableKeepAlive: true,
    keepAliveInitialDelay: 30000
});

// ============================================
// TESTE DE CONEXÃO INICIAL
// ============================================

(async () => {
    try {
        const connection = await pool.getConnection();
        console.log('✅ [MySQL] Conexão estabelecida com sucesso');
        console.log(`📊 [MySQL] Database: ${process.env.DB_NAME || 'saas_whatsapp'}`);
        console.log(`🖥️  [MySQL] Host: ${process.env.DB_HOST || 'localhost'}`);
        connection.release();
    } catch (error) {
        console.error('❌ [MySQL] Erro ao conectar:', error.message);
        console.error('⚠️  [MySQL] Verifique as configurações do banco de dados no arquivo .env');
    }
})();

// ============================================
// EVENTOS DO POOL
// ============================================

pool.on('connection', (connection) => {
    console.log(`🔗 [MySQL] Nova conexão criada (ID: ${connection.threadId})`);
    
    // Configurar charset
    connection.query("SET NAMES utf8mb4");
});

pool.on('acquire', (connection) => {
    // Log de debug (descomente se precisar)
    // console.log(`📥 [MySQL] Conexão adquirida (ID: ${connection.threadId})`);
});

pool.on('release', (connection) => {
    // Log de debug (descomente se precisar)
    // console.log(`📤 [MySQL] Conexão liberada (ID: ${connection.threadId})`);
});

pool.on('enqueue', () => {
    console.log('⏳ [MySQL] Aguardando conexão disponível...');
});

// ============================================
// FUNÇÕES AUXILIARES
// ============================================

/**
 * Testa a conexão com o banco
 * @returns {Promise<boolean>}
 */
async function testConnection() {
    try {
        const connection = await pool.getConnection();
        await connection.ping();
        connection.release();
        return true;
    } catch (error) {
        console.error('[MySQL] Teste de conexão falhou:', error.message);
        return false;
    }
}

/**
 * Executa query com retry automático
 * @param {string} sql - Query SQL
 * @param {Array} params - Parâmetros
 * @param {number} retries - Número de tentativas
 * @returns {Promise<Array>}
 */
async function executeWithRetry(sql, params = [], retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            return await pool.execute(sql, params);
        } catch (error) {
            if (i === retries - 1) throw error;
            
            console.warn(`[MySQL] Retry ${i + 1}/${retries} para query...`);
            await new Promise(r => setTimeout(r, 1000 * (i + 1)));
        }
    }
}

/**
 * Obtém estatísticas do pool
 * @returns {Object}
 */
function getPoolStats() {
    return {
        totalConnections: pool.pool._allConnections?.length || 0,
        freeConnections: pool.pool._freeConnections?.length || 0,
        connectionQueue: pool.pool._connectionQueue?.length || 0
    };
}

// Exportar pool e funções auxiliares
module.exports = pool;
module.exports.testConnection = testConnection;
module.exports.executeWithRetry = executeWithRetry;
module.exports.getPoolStats = getPoolStats;
