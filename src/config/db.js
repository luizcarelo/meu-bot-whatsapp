/**
 * src/config/db.js
 * Descrição: Singleton de Conexão PostgreSQL
 */

const { Pool } = require('pg');

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
        const dbConfig = {
            host: process.env.DB_HOST || '127.0.0.1',
            user: process.env.DB_USER || 'postgres',
            password: process.env.DB_PASSWORD || process.env.DB_PASS || '',
            database: process.env.DB_NAME || 'whatsappbot-db',
            port: process.env.DB_PORT || 5432,
            max: 15,
            idleTimeoutMillis: 30000,
            connectionTimeoutMillis: 10000,
        };

        try {
            this.pool = new Pool(dbConfig);
            
            this.pool.connect()
                .then(client => {
                    console.log(`📊 [PostgreSQL] Conectado: ${dbConfig.database} @ ${dbConfig.host}`);
                    client.release();
                    this.isConnected = true;
                })
                .catch(err => {
                    console.error('❌ [PostgreSQL] Falha na conexão inicial:', err.message);
                });
        } catch (error) {
            console.error('❌ [FATAL] Erro ao criar pool PostgreSQL:', error.message);
        }
    }

    // Normaliza parametros posicionais para PostgreSQL quando necessario
    convertQueryToPg(sql) {
        let index = 1;
        return sql.replace(/\?/g, () => `$${index++}`);
    }

    async execute(sql, params = []) {
        try {
            const pgSql = this.convertQueryToPg(sql);
            const result = await this.pool.query(pgSql, params);
            return [result.rows, result.fields]; // Mantem compatibilidade com chamadas legadas do projeto
        } catch (error) {
            console.error(`[DB Execute Error] ${error.message}\nSQL: ${sql}`);
            throw error;
        }
    }

    async query(sql, params = []) {
        const [rows] = await this.execute(sql, params);
        return rows;
    }

    async run(sql, params = []) {
        const pgSql = this.convertQueryToPg(sql);
        const result = await this.pool.query(pgSql, params);
        return {
            insertId: result.rows.length > 0 ? (result.rows[0].id || null) : null,
            affectedRows: result.rowCount,
            changedRows: result.rowCount
        };
    }

    async close() {
        if (this.pool) {
            await this.pool.end();
            console.log('[PostgreSQL] Pool encerrado.');
        }
    }
}

const dbInstance = new Database();

module.exports = {
    pool: dbInstance.pool,
    execute: (sql, params) => dbInstance.execute(sql, params),
    query: (sql, params) => dbInstance.query(sql, params),
    run: (sql, params) => dbInstance.run(sql, params),
    close: () => dbInstance.close()
};