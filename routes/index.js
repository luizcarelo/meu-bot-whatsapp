/**
 * routes/index.js
 * Descrição: Rotas de Navegação (Frontend) com Debug
 * Autor: Sistemas de Gestão
 */

const express = require('express');
const router = express.Router();
const { isAuthenticated, isSuperAdmin } = require('../src/middleware/auth');
const db = require('../src/config/db');
const AdminPanelController = require('../controllers/AdminPanelController');
const adminPanelController = new AdminPanelController(db);

// Rota Raiz
router.get('/', (req, res) => {
    if (req.session && req.session.user) return res.redirect('/dashboard');
    res.redirect('/login');
});

// Login Page
router.get('/login', (req, res) => {
    if (req.session && req.session.user) return res.redirect('/dashboard');
    res.render('login', { error: null });
});

// ============================================
// DASHBOARD (Com Diagnóstico de Erro)
// ============================================
router.get('/dashboard', isAuthenticated, async (req, res) => {
    try {
        // [DEBUG] Diagnóstico
        console.log(`[DASHBOARD] Acesso permitido empresa_id=${req.session?.empresaId || 'N/A'}`);

        const empresaId = req.session.empresaId;

        if (!empresaId) {
            console.error('❌ [DASHBOARD] Sessão corrompida: User existe mas empresaId é nulo.');
            req.session.destroy();
            return res.redirect('/login?error=sessao_invalida');
        }

        // 1. Busca Dados da Empresa
// 1. Busca Dados da Empresa
        const result = await db.query('SELECT * FROM empresas WHERE id = ? LIMIT 1', [empresaId]);
        
        // No Postgres, o db.query geralmente retorna o array de linhas diretamente
        // Verificamos se result é um array ou se tem a propriedade 'rows' (padrão do pg)
        const empresa = Array.isArray(result) ? result[0] : (result.rows ? result.rows[0] : null);

        if (!empresa) {
            console.error(`❌ [DASHBOARD] Empresa ID ${empresaId} não encontrada no DB.`);
            return res.status(404).send('Empresa não encontrada.');
        }

        // 2. Busca Dados Auxiliares (Tolerante a falhas)
        let setores = [], contatos = [];
        try {
            [setores] = await db.query('SELECT * FROM setores WHERE empresa_id = ? ORDER BY ordem ASC', [empresaId]);
            [contatos] = await db.query('SELECT * FROM contatos WHERE empresa_id = ? ORDER BY ultima_msg DESC LIMIT 50', [empresaId]);
        } catch (dbErr) {
            console.warn('⚠️ [DASHBOARD] Aviso: Erro ao buscar setores/contatos (tabelas existem?).', dbErr.message);
        }

        // 3. Renderiza
        res.render('dashboard', {
            user: req.session.user,
            empresa: empresa,
            setores: setores || [],
            contatos: contatos || [],
            socketUrl: process.env.SOCKET_URL || ''
        });

    } catch (error) {
        console.error('🔥 [DASHBOARD FATAL ERROR]', error);
        res.status(500).render('login', { error: 'Erro crítico no sistema: ' + error.message });
    }
});


// ETAPA20_1_ROTA_CRM_INICIO
router.get('/crm', isAuthenticated, async (req, res) => {
    try {
        const empresaId = req.session.empresaId;

        if (!empresaId) {
            req.session.destroy();
            return res.redirect('/login?error=sessao_invalida');
        }

        const result = await db.query(
            'SELECT * FROM empresas WHERE id = ? LIMIT 1',
            [empresaId]
        );

        const empresa = Array.isArray(result) ? result[0] : (result.rows ? result.rows[0] : null);

        if (!empresa) {
            return res.status(404).send('Empresa não encontrada.');
        }

        return res.render('crm', {
            titulo: 'CRM - Atendimento',
            user: req.session.user,
            empresa: empresa,
            isMobile: false,
            socketUrl: process.env.SOCKET_URL || ''
        });
    } catch (error) {
        console.error('[CRM PAGE] Erro ao carregar CRM:', error);
        return res.status(500).render('login', {
            error: 'Erro ao carregar CRM: ' + error.message
        });
    }
});
// ETAPA20_1_ROTA_CRM_FIM


// ETAPA21_1_ROTA_ADMIN_PANEL_INICIO
router.get('/admin/painel', isAuthenticated, async (req, res) => {
    return adminPanelController.renderPanel(req, res);
});
// ETAPA21_1_ROTA_ADMIN_PANEL_FIM


// ETAPA22_1_ROTA_SUPER_ADMIN_INICIO
router.get('/super-admin', isAuthenticated, isSuperAdmin, async (req, res) => {
    return res.render('super-admin');
});
// ETAPA22_1_ROTA_SUPER_ADMIN_FIM

router.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/login');
});

module.exports = router;
