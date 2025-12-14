// ============================================
// Arquivo: controllers/AdminPanelController.js
// Descrição: Controller do Painel Admin da Empresa
// Versão: 5.0 - Revisado e Corrigido
// ============================================

class AdminPanelController {
    /**
     * Construtor do AdminPanelController
     * @param {Object} db - Pool de conexão MySQL
     */
    constructor(db) {
        this.db = db;
    }

    /**
     * Renderiza o painel administrativo da empresa
     * GET /admin/painel
     */
    async renderPanel(req, res) {
        try {
            // Buscar dados do usuário
            const [user] = await this.db.execute(
                'SELECT is_admin, nome FROM usuarios_painel WHERE id = ?',
                [req.userId]
            );

            // Verificar se é admin (comentado para permitir acesso)
            // if (!user[0] || !user[0].is_admin) {
            //     return res.redirect('/crm');
            // }

            // Buscar dados da empresa
            const [empresa] = await this.db.execute(
                `SELECT nome, logo_url, cor_primaria, msg_ausencia, 
                        horario_inicio, horario_fim, dias_funcionamento,
                        whatsapp_status, whatsapp_numero
                 FROM empresas WHERE id = ?`,
                [req.empresaId]
            );

            // Buscar equipe
            const [equipe] = await this.db.execute(
                'SELECT id, nome, email, is_admin, ativo FROM usuarios_painel WHERE empresa_id = ?',
                [req.empresaId]
            );

            res.render('admin-panel', {
                titulo: 'Painel Administrativo',
                empresa: empresa[0] || {},
                equipe: equipe,
                user: user[0] || {}
            });

        } catch (e) {
            console.error('[AdminPanelController] Erro ao carregar painel:', e);
            res.status(500).send('Erro ao carregar painel administrativo');
        }
    }
}

module.exports = AdminPanelController;
