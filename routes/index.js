// ============================================
// Arquivo: routes/index.js
// Descrição: Rotas principais da aplicação
// ============================================

const express = require('express');
const router = express.Router();

// ============================================
// REDIRECIONAMENTO INICIAL
// ============================================
router.get('/', (req, res) => {
    res.redirect('/login');
});

// ============================================
// ROTA DE LOGIN
// ============================================
router.get('/login', (req, res) => {
    res.render('login', { 
        titulo: 'Acesso SaaS',
        erro: null 
    });
});

// ============================================
// PAINEL SUPER ADMIN
// ============================================
router.get('/super-admin', (req, res) => {
    res.render('super-admin', { 
        titulo: 'Gestão Master' 
    });
});

// ============================================
// ROTAS DO CRM (COM DETECÇÃO MOBILE)
// ============================================

/**
 * Detecta se o dispositivo é mobile através do User-Agent
 * @param {string} userAgent - String do User-Agent
 * @returns {boolean} - True se for dispositivo mobile
 */
function isMobileDevice(userAgent) {
    return /mobile|android|iphone|ipad|phone|tablet/i.test(userAgent || '');
}

// Rota Desktop (Padrão)
router.get('/crm', (req, res) => {
    const ua = req.headers['user-agent'] || '';
    const isMobile = isMobileDevice(ua);

    // Se for mobile, redireciona para a rota específica
    if (isMobile) {
        return res.redirect('/app');
    }

    res.render('crm', { 
        titulo: 'CRM Desktop', 
        isMobile: false 
    });
});

// Rota Mobile (Específica para dispositivos móveis)
router.get('/app', (req, res) => {
    res.render('crm', { 
        titulo: 'CRM App Mobile', 
        isMobile: true 
    });
});

// ============================================
// PAINEL DE ADMINISTRAÇÃO (CONFIGURAÇÕES)
// ============================================
router.get('/admin/painel', (req, res) => {
    res.render('admin-panel', { 
        titulo: 'Configurações da Empresa' 
    }); 
});

// ============================================
// ROTA DE HEALTH CHECK
// ============================================
router.get('/health', (req, res) => {
    res.json({ 
        status: 'OK', 
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

// ============================================
// ROTA DE STATUS DO SISTEMA
// ============================================
router.get('/status', (req, res) => {
    res.json({
        status: 'online',
        version: require('../package.json').version,
        node: process.version,
        platform: process.platform,
        memory: {
            used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + ' MB',
            total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024) + ' MB'
        }
    });
});

module.exports = router;