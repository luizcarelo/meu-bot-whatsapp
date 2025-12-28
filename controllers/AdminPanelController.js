/**
 * controllers/AdminPanelController.js
 * Descrição: Controller do Painel Admin (Renderização EJS + APIs do Dashboard)
 * Versão: 5.2 - Refatorado para Singleton DB & Sessão
 */

const db = require('../src/config/db');  // Novo Singleton

class AdminPanelController {
    /**
     * Construtor
     * @param {Object} injectedDb - Opcional para manter compatibilidade com injeção manual
     */
    constructor(injectedDb) {
        this.db = injectedDb || db;
    }

    // ============================================
    // 1. RENDERIZAÇÃO DE VIEWS (SSR - EJS)
    // ============================================

    /**
     * Renderiza o painel administrativo da empresa (HTML)
     * GET /admin/painel
     */
    async renderPanel(req, res) {
        try {
            // Recupera IDs da sessão (prioridade) ou da requisição
            const userId = req.session?.user?.id || req.userId;
            const empresaId = req.session?.empresaId || req.empresaId;

            if (!userId || !empresaId) {
                // Se a sessão caiu, redireciona para login em vez de crashar
                return res.redirect('/');
            }

            // 1. Buscar dados do usuário logado
            // Nota: db.query retorna as linhas diretamente (sem destructuring [rows])
            const users = await this.db.query(
                'SELECT id, is_admin, nome, email, cargo, ativo FROM usuarios_painel WHERE id = ?',
                [userId]
            );

            if (users.length === 0) {
                return res.redirect('/auth/logout');
            }
            const user = users[0];

            // 2. Buscar dados da empresa
            const empresas = await this.db.query(
                `SELECT nome, nome_sistema, logo_url, cor_primaria, msg_ausencia, 
                        horario_inicio, horario_fim, dias_funcionamento,
                        whatsapp_status, whatsapp_numero, plano, limite_usuarios
                 FROM empresas WHERE id = ?`,
                [empresaId]
            );
            const empresa = empresas[0] || {};
            
            // Fallback visual para nome do sistema (UX)
            empresa.nome_exibicao = empresa.nome_sistema || empresa.nome;

            // 3. Buscar equipe completa (para listagem na view inicial)
            const equipe = await this.db.query(
                'SELECT id, nome, email, is_admin, cargo, ativo, telefone FROM usuarios_painel WHERE empresa_id = ? ORDER BY nome ASC',
                [empresaId]
            );

            // 4. Renderizar a View (EJS)
            res.render('admin-panel', {
                titulo: 'Painel Administrativo',
                empresa: empresa,
                equipe: equipe,
                user: user,
                // Passa o caminho para destacar o menu lateral
                path: req.path 
            });

        } catch (e) {
            console.error('[AdminPanelController] Erro ao carregar painel:', e);
            // Renderiza uma página de erro amigável se possível, ou texto
            res.status(500).send(`
                <h1>Erro 500</h1>
                <p>Ocorreu um erro ao carregar o painel administrativo.</p>
                <p><a href="/">Voltar para Login</a></p>
            `);
        }
    }

    // ============================================
    // 2. API ENDPOINTS (JSON para AJAX/Dashboard)
    // ============================================

    /**
     * API: Estatísticas rápidas para o Dashboard (Cards de topo)
     * GET /admin/dashboard-stats
     */
    async getStats(req, res) {
        const empresaId = req.session?.empresaId || req.empresaId;
        
        if (!empresaId) {
            return res.status(401).json({ success: false, error: 'Sessão inválida' });
        }

        try {
            // Executa queries em paralelo para máxima performance
            const [msgs, contatos, equipe] = await Promise.all([
                this.db.query("SELECT COUNT(*) as t FROM mensagens WHERE empresa_id = ?", [empresaId]),
                this.db.query("SELECT COUNT(*) as t FROM contatos WHERE empresa_id = ?", [empresaId]),
                this.db.query("SELECT COUNT(*) as t FROM usuarios_painel WHERE empresa_id = ?", [empresaId])
            ]);
            
            res.json({
                success: true,
                mensagens: msgs[0].t,
                contatos: contatos[0].t,
                equipe: equipe[0].t
            });
        } catch (e) {
            console.error('[AdminPanel] Erro Stats:', e);
            res.status(500).json({ success: false, error: e.message });
        }
    }

    /**
     * API: Lista de Usuários (JSON)
     * GET /admin/users
     */
    async getUsers(req, res) {
        const empresaId = req.session?.empresaId || req.empresaId;
        
        try {
            const users = await this.db.query(
                `SELECT id, nome, email, is_admin, cargo, ativo, telefone, created_at 
                 FROM usuarios_painel 
                 WHERE empresa_id = ? 
                 ORDER BY nome ASC`,
                [empresaId]
            );
            
            res.json({ success: true, data: users });
        } catch (e) {
            console.error('[AdminPanel] Erro Users:', e);
            res.status(500).json({ success: false, error: e.message });
        }
    }
}

module.exports = AdminPanelController;