// ============================================
// Arquivo: routes/index.js
// Descrição: Rotas principais da aplicação
// ============================================

const express = require('express');
const router = express.Router();

// Importação de Middlewares e Controllers
// Certifique-se de que estes arquivos existem na pasta controllers
const WhatsAppController = require('../controllers/WhatsAppController'); 
const AuthMiddleware = require('../src/middleware/auth'); // Ajuste o caminho conforme sua estrutura

// ============================================
// ROTAS PÚBLICAS
// ============================================
router.get('/', (req, res) => res.redirect('/login'));

router.get('/login', (req, res) => {
    res.render('login', {
        titulo: 'Acesso SaaS',
        erro: null
    });
});

// ============================================
// ROTAS DA API WHATSAPP (CORREÇÃO DO ERRO 404)
// ============================================
// Estas rotas estavam faltando no seu arquivo anterior, causando falha no painel

// Iniciar Sessão
router.get('/whatsapp/start/:companyId', AuthMiddleware, WhatsAppController.startSession);

// Verificar Status
router.get('/whatsapp/status/:companyId', AuthMiddleware, WhatsAppController.getStatus);

// Obter QR Code
router.get('/whatsapp/qrcode/:companyId', AuthMiddleware, WhatsAppController.getQrCode);

// Logout
router.post('/whatsapp/logout/:companyId', AuthMiddleware, WhatsAppController.logoutSession);

// Rota de fallback para erros de chamada sem ID
router.get('/whatsapp/start', (req, res) => {
    res.status(400).json({ error: 'ID da empresa obrigatório na URL' });
});


// ============================================
// ROTAS DO CRM E PAINEL
// ============================================
router.get('/crm', AuthMiddleware, (req, res) => {
    res.render('crm', {
        titulo: 'CRM Desktop',
        isMobile: false
    });
});

router.get('/app', AuthMiddleware, (req, res) => {
    res.render('crm', {
        titulo: 'CRM App Mobile',
        isMobile: true
    });
});

router.get('/admin/painel', AuthMiddleware, (req, res) => {
    res.render('admin-panel', {
        titulo: 'Configurações da Empresa'
    });
});

router.get('/super-admin', AuthMiddleware, (req, res) => {
    res.render('super-admin', {
        titulo: 'Gestão Master'
    });
});

// ============================================
// ROTAS DE API GERAIS
// ============================================
// Se você tiver um arquivo api.js, importe aqui:
const apiRoutes = require('./api'); 
router.use('/api', apiRoutes);

module.exports = router;