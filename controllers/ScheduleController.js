/**
 * controllers/ScheduleController.js
 * Controlador responsável pela gestão de horários de atendimento (Enterprise)
 * Desenvolvido por: Sistemas de Gestão
 */

const moment = require('moment');

class ScheduleController {
    
    constructor(db) {
        this.db = db;
    }

    /**
     * Obtém a grade de horários de uma empresa
     * GET /api/settings/schedules/:empresaId
     */
    async getSchedules(req, res) {
        const empresaId = req.params.empresaId;

        if (!empresaId) {
            return res.status(400).json({ success: false, error: 'ID da empresa obrigatório' });
        }

        try {
            // Busca horários ordenados de Domingo (0) a Sábado (6)
            const [rows] = await this.db.execute(
                `SELECT * FROM horarios_atendimento WHERE empresa_id = ? ORDER BY dia_semana ASC`,
                [empresaId]
            );

            // Se não houver registros, retorna array vazio (o front deve lidar ou o migration já populou)
            res.json({ success: true, data: rows });

        } catch (error) {
            console.error('[ScheduleController] Erro ao buscar horários:', error);
            res.status(500).json({ success: false, error: 'Erro interno ao buscar horários.' });
        }
    }

    /**
     * Atualiza a grade de horários completa
     * POST /api/settings/schedules/:empresaId
     * Body: { schedules: [ { dia_semana, horario_abertura, ... }, ... ] }
     */
    async updateSchedules(req, res) {
        const empresaId = req.params.empresaId;
        const { schedules } = req.body;

        if (!empresaId || !schedules || !Array.isArray(schedules)) {
            return res.status(400).json({ success: false, error: 'Dados inválidos.' });
        }

        const connection = await this.db.getConnection(); // Pega conexão para transação

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
                // Tratamento de dados nulos para o banco
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
            console.error('[ScheduleController] Erro ao atualizar horários:', error);
            res.status(500).json({ success: false, error: 'Falha ao salvar horários.' });
        } finally {
            connection.release();
        }
    }
}

module.exports = ScheduleController;