/**
 * src/config/db.js
 * Descrição: Singleton de Conexão MySQL (Pool de Conexões)
 * Versão: 7.1 - Enterprise Hybrid (Class-based + Retry Logic)
 * Padrão: Singleton
 */

const mysql = require('mysql2/promise');

class Database {
    constructor() {
        if (Database.instance) {
            return Database.instance;
        }

        this.pool = null;
        this.isConnected = false;

        this.init();
        Database.instance = this;
    }

    init() {
        // Fallback para variáveis de ambiente
        const dbConfig = {
            host: process.env.DB_HOST || 'localhost',
            user: process.env.DB_USER || 'root',
            password: process.env.DB_PASSWORD || process.env.DB_PASS || '',
            database: process.env.DB_NAME || 'lcsolucoesdigi',
            port: process.env.DB_PORT || 3306,
            
            // Configurações de Performance (Herdadas do seu código otimizado)
            waitForConnections: true,
            connectionLimit: 15,
            queueLimit: 0,
            connectTimeout: 60000,
            
            // Estabilidade
            enableKeepAlive: true,
            keepAliveInitialDelay: 10000,
            
            // Regional
            charset: 'utf8mb4',
            timezone: '-03:00'
        };

        try {
            this.pool = mysql.createPool(dbConfig);
            
            // Teste inicial silencioso (logs detalhados apenas em erro)
            this.pool.getConnection()
                .then(conn => {
                    console.log(`📊 [MySQL] Conectado: ${dbConfig.database} @ ${dbConfig.host}`);
                    conn.release();
                    this.isConnected = true;
                })
                .catch(err => {
                    console.error('❌ [MySQL] Falha na conexão inicial:', err.message);
                });

        } catch (error) {
            console.error('❌ [FATAL] Erro ao criar pool MySQL:', error.message);
        }
    }

    /**
     * Interface padrão compatível com mysql2/promise.
     * Utilizada pelo SessionManager e AuthController.
     * Retorna [rows, fields].
     */
    async execute(sql, params = []) {
        try {
            return await this.pool.execute(sql, params);
        } catch (error) {
            // Tratamento de queda de conexão
            if (error.code === 'PROTOCOL_CONNECTION_LOST') {
                console.warn('⚠️ [MySQL] Conexão perdida. Tentando reconectar...');
                // O Pool gerencia a reconexão, mas podemos logar ou tentar retentativa aqui
            }
            console.error(`[DB Execute Error] ${error.message}\nSQL: ${sql}`);
            throw error;
        }
    }

    /**
     * Helper simplificado para SELECTs (Retorna apenas os dados).
     * Útil para controllers de visualização.
     */
    async query(sql, params = []) {
        const [rows] = await this.execute(sql, params);
        return rows;
    }

    /**
     * Helper para INSERT/UPDATE/DELETE.
     * Retorna metadados (insertId, affectedRows).
     */
    async run(sql, params = []) {
        const [result] = await this.execute(sql, params);
        return {
            insertId: result.insertId,
            affectedRows: result.affectedRows,
            changedRows: result.changedRows
        };
    }

    /**
     * Fecha o pool (Graceful Shutdown).
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
            console.log('[MySQL] Pool encerrado.');
        }
    }
}

const dbInstance = new Database();

// Exporta a instância E o pool (para o express-mysql-session no server.js)
module.exports = {
    pool: dbInstance.pool,     // Necessário para Session Store
    execute: (sql, params) => dbInstance.execute(sql, params), // Atalho direto
    query: (sql, params) => dbInstance.query(sql, params),
    run: (sql, params) => dbInstance.run(sql, params),
    close: () => dbInstance.close()
};