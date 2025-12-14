// ============================================
// Arquivo: routes/index.js
// Descrição: Rotas Principais da Aplicação
// Versão: 5.0 - Revisado e Corrigido
// ============================================

const express = require('express');
const router = express.Router();

// ============================================
// FUNÇÃO AUXILIAR - DETECTAR MOBILE
// ============================================

function isMobileDevice(req) {
    const userAgent = req.headers['user-agent'] || '';
    const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
    return mobileRegex.test(userAgent);
}

// ============================================
// ROTAS PÚBLICAS (SEM AUTENTICAÇÃO)
// ============================================

/**
 * Rota raiz - Redireciona para login
 */
router.get('/', (req, res) => {
    res.redirect('/login');
});

/**
 * Página de Login
 */
router.get('/login', (req, res) => {
    res.render('login', {
        titulo: 'Acesso ao Sistema',
        erro: null
    });
});

/**
 * Health Check - Verifica se o servidor está rodando
 */
router.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

/**
 * Status do Sistema
 */
router.get('/status', (req, res) => {
    res.json({
        status: 'running',
        version: '5.0.0',
        node: process.version,
        memory: process.memoryUsage()
    });
});

// ============================================
// ROTAS DO CRM (REQUEREM AUTENTICAÇÃO)
// ============================================

/**
 * CRM Desktop/Mobile - Detecta automaticamente
 */
router.get('/crm', (req, res) => {
    const isMobile = isMobileDevice(req);
    res.render('crm', {
        titulo: isMobile ? 'CRM Mobile' : 'CRM Desktop',
        isMobile: isMobile
    });
});

/**
 * CRM Forçado para Mobile
 */
router.get('/app', (req, res) => {
    res.render('crm', {
        titulo: 'CRM Mobile',
        isMobile: true
    });
});

/**
 * CRM Forçado para Desktop
 */
router.get('/desktop', (req, res) => {
    res.render('crm', {
        titulo: 'CRM Desktop',
        isMobile: false
    });
});

// ============================================
// ROTAS DE ADMINISTRAÇÃO
// ============================================

/**
 * Painel Administrativo da Empresa
 */
router.get('/admin/painel', (req, res) => {
    res.render('admin-panel', {
        titulo: 'Configurações da Empresa'
    });
});

/**
 * Painel do Super Admin (Gestão de Clientes)
 */
router.get('/super-admin', (req, res) => {
    res.render('super-admin', {
        titulo: 'Gestão Master SaaS'
    });
});

// ============================================
// EXPORTAR ROUTER
// ============================================

module.exports = router;
