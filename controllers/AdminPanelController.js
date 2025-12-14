class AdminPanelController {
    constructor(db) { this.db = db; }

    async renderPanel(req, res) {
        try {
            // Verifica se é admin
            const [user] = await this.db.execute('SELECT is_admin, nome FROM usuarios_painel WHERE id = ?', [req.userId]); // Assumindo que o middleware coloca userId no req

            // if (!user[0] || !user[0].is_admin) {
            //     return res.redirect('/crm'); // Redireciona se não for admin
            // }

            // Busca dados da empresa
            const [empresa] = await this.db.execute(
                'SELECT nome, logo_url, cor_primaria, msg_ausencia, horario_inicio, horario_fim, dias_funcionamento FROM empresas WHERE id = ?',
                [req.empresaId]
            );

            // Busca equipe
            const [equipe] = await this.db.execute('SELECT id, nome, email, is_admin FROM usuarios_painel WHERE empresa_id = ?', [req.empresaId]);

            res.render('admin-panel', {
                titulo: 'Painel Administrativo',
                empresa: empresa[0],
                equipe: equipe,
                user: user[0]
            });
        } catch (e) {
            console.error(e);
            res.status(500).send('Erro ao carregar painel');
        }
    }
}

module.exports = AdminPanelController;