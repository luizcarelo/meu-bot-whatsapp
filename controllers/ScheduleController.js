/**
 * controllers/ScheduleController.js
 * Descrição: Gestão de Horários de Atendimento (Tabela horarios_atendimento)
 * Versão: 5.0 - Refatorado para Singleton DB com Transações
 */

const db = require('../src/config/db');

class ScheduleController {
    
    constructor(injectedDb) {
        this.db = injectedDb || db;
    }

    /**
     * Obtém a grade de horários
     * GET /api/settings/schedules/:empresaId
     */
    async getSchedules(req, res) {
        const empresaId = req.params.empresaId || req.session?.empresaId;

        if (!empresaId) {
            return res.status(400).json({ success: false, error: 'ID da empresa obrigatório' });
        }

        try {
            // Busca horários ordenados (0 = Domingo)
            // Uso de db.query (novo padrão)
            const rows = await this.db.query(
                `SELECT * FROM horarios_atendimento WHERE empresa_id = ? ORDER BY dia_semana ASC`,
                [empresaId]
            );

            // Se ainda não existirem horários (migração), retorna vazio e o front deve tratar
            // Ou o AdminController.createEmpresa já deve ter criado
            res.json({ success: true, data: rows });

        } catch (error) {
            console.error('[ScheduleController] Erro ao buscar horários:', error);
            res.status(500).json({ success: false, error: 'Erro interno ao buscar horários.' });
        }
    }

    /**
     * Atualiza a grade completa
     * POST /api/settings/schedules/:empresaId
     * Body: { schedules: [ { dia_semana, horario_abertura, ... }, ... ] }
     */
    async updateSchedules(req, res) {
        const empresaId = req.params.empresaId || req.session?.empresaId;
        const { schedules } = req.body;

        if (!schedules || !Array.isArray(schedules)) {
            return res.status(400).json({ success: false, error: 'Formato de horários inválido.' });
        }

        // Para transações, precisamos de uma conexão dedicada do pool
        const connection = await this.db.pool.getConnection();

        try {
            await connection.beginTransaction();

            const updateQuery = `
                UPDATE horarios_atendimento 
                SET horario_abertura = ?, 
                    horario_fechamento = ?, 
                    inicio_almoco = ?, 
                    fim_almoco = ?, 
                    ativo = ?
                WHERE empresa_id = ? AND dia_semana = ?
            `;

            for (const item of schedules) {
                // Tratamento de nulos (strings vazias viram null)
                const inicioAlmoco = item.inicio_almoco === '' ? null : item.inicio_almoco;
                const fimAlmoco = item.fim_almoco === '' ? null : item.fim_almoco;
                const ativo = item.ativo ? 1 : 0;

                await connection.execute(updateQuery, [
                    item.horario_abertura,
                    item.horario_fechamento,
                    inicioAlmoco,
                    fimAlmoco,
                    ativo,
                    empresaId,
                    item.dia_semana
                ]);
            }

            await connection.commit();
            res.json({ success: true, message: 'Horários atualizados com sucesso!' });

        } catch (error) {
            await connection.rollback();
            console.error('[ScheduleController] Erro na transação:', error);
            res.status(500).json({ success: false, error: 'Falha ao salvar horários.' });
        } finally {
            connection.release(); // Importante: liberar conexão de volta pro pool
        }
    }
}

module.exports = ScheduleController;