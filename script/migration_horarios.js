/**
 * migration_horarios.js
 * Script de Migração de Banco de Dados - Módulo de Horários
 * Desenvolvido por: Sistemas de Gestão
 * * Objetivo: Criar tabela de horários robusta e popular padrões iniciais.
 */

require('dotenv').config({ path: '.env' }); // Ajuste o path conforme onde você roda o script
const mysql = require('mysql2/promise');
const moment = require('moment');

// Configuração da Conexão (Pegando do .env ou hardcoded para o script)
const dbConfig = {
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASS || '',
    database: process.env.DB_NAME || 'lcsolucoesdigi'
};

async function migrate() {
    let connection;
    try {
        console.log('>>> Iniciando Migração do Módulo de Horários...');
        connection = await mysql.createConnection(dbConfig);

        // 1. Criar Tabela horarios_atendimento
        const createTableQuery = `
            CREATE TABLE IF NOT EXISTS horarios_atendimento (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa_id INT NOT NULL,
                dia_semana INT NOT NULL COMMENT '0=Domingo, 1=Segunda, ..., 6=Sábado',
                horario_abertura TIME NOT NULL DEFAULT '08:00:00',
                horario_fechamento TIME NOT NULL DEFAULT '18:00:00',
                inicio_almoco TIME DEFAULT NULL,
                fim_almoco TIME DEFAULT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                UNIQUE KEY unique_dia_empresa (empresa_id, dia_semana)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        `;

        await connection.execute(createTableQuery);
        console.log('>>> Tabela [horarios_atendimento] verificada/criada com sucesso.');

        // 2. Popular dados padrão para empresas existentes que não têm horários
        // Padrão: Seg a Sex, 08:00 as 18:00. Sab e Dom fechado.
        
        const [empresas] = await connection.execute('SELECT id FROM empresas');
        
        for (const empresa of empresas) {
            const [horariosExistentes] = await connection.execute(
                'SELECT count(*) as total FROM horarios_atendimento WHERE empresa_id = ?', 
                [empresa.id]
            );

            if (horariosExistentes[0].total === 0) {
                console.log(`>>> Gerando horários padrão para Empresa ID: ${empresa.id}`);
                
                const inserts = [];
                // 0 = Domingo (Fechado)
                inserts.push([empresa.id, 0, '00:00', '00:00', null, null, false]);
                
                // 1 a 5 = Segunda a Sexta (Aberto 08:00 - 18:00)
                for (let dia = 1; dia <= 5; dia++) {
                    inserts.push([empresa.id, dia, '08:00', '18:00', '12:00', '13:00', true]);
                }
                
                // 6 = Sábado (Aberto 08:00 - 12:00)
                inserts.push([empresa.id, 6, '08:00', '12:00', null, null, true]);

                const queryInsert = `
                    INSERT INTO horarios_atendimento 
                    (empresa_id, dia_semana, horario_abertura, horario_fechamento, inicio_almoco, fim_almoco, ativo) 
                    VALUES ?
                `;
                
                await connection.query(queryInsert, [inserts]);
            }
        }

        console.log('>>> Migração concluída com sucesso!');

    } catch (error) {
        console.error('>>> ERRO CRÍTICO NA MIGRAÇÃO:', error);
    } finally {
        if (connection) await connection.end();
    }
}

migrate();