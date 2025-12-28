/**
 * routes/index.js
 * Descrição: Rotas de Navegação (Frontend) com Debug
 * Autor: Sistemas de Gestão
 */

const express = require('express');
const router = express.Router();
const { isAuthenticated } = require('../src/middleware/auth');
const db = require('../src/config/db');

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
        console.log(`🖥️ [DASHBOARD] Acesso permitido para: ${req.session.user.email} (Empresa: ${req.session.empresaId})`);

        const empresaId = req.session.empresaId;

        if (!empresaId) {
            console.error('❌ [DASHBOARD] Sessão corrompida: User existe mas empresaId é nulo.');
            req.session.destroy();
            return res.redirect('/login?error=sessao_invalida');
        }

        // 1. Busca Dados da Empresa
        const [empresas] = await db.query('SELECT * FROM empresas WHERE id = ? LIMIT 1', [empresaId]);
        const empresa = empresas ? empresas[0] : null;

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

router.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/login');
});

module.exports = router;