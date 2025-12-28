/**
 * routes/api.js
 * Descrição: Rotas da API REST (Backend Central)
 * Versão: 7.0 - Enterprise (Redis Queues + Singleton Injection)
 * Autor: Sistemas de Gestão
 */

const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');

// --- 1. Importações de Infraestrutura ---
const db = require('../src/config/db'); // Singleton DB
// Removido: const sessionManager... (Já vem injetado em req.whatsapp)
const { isAuthenticated, isAdmin, isSuperAdmin } = require('../src/middleware/auth');

// --- 2. Importação dos Controladores Legados (DB CRUD) ---
// Mantemos estes controllers pois lidam com lógica de banco de dados, não com o socket direto
const AuthController = require('../controllers/AuthController');
const AdminController = require('../controllers/AdminController');
const AdminPanelController = require('../controllers/AdminPanelController');
// const WhatsAppController = require('../controllers/WhatsAppController'); // SUBSTITUÍDO pela lógica v7 direta
const CrmController = require('../controllers/CrmController');
const ScheduleController = require('../controllers/ScheduleController');

// --- 3. Instanciação dos Controladores ---
const adminCtrl = new AdminController(db);
const adminPanelCtrl = new AdminPanelController(db);
const crmCtrl = new CrmController(db);
const scheduleController = new ScheduleController(db);

// ============================================
// CONFIGURAÇÃO DO MULTER (OTIMIZADA v7)
// ============================================

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        // Organização por Data (YYYY-MM-DD) para evitar diretórios gigantes
        const empresaId = req.session?.empresaId || req.headers['x-empresa-id'] || req.body.empresaId || 'temp';
        const dateDir = new Date().toISOString().split('T')[0];
        
        const uploadPath = path.join(process.cwd(), 'public', 'uploads', `empresa_${empresaId}`, dateDir);
        
        if (!fs.existsSync(uploadPath)) {
            fs.mkdirSync(uploadPath, { recursive: true });
        }
        
        cb(null, uploadPath);
    },
    filename: (req, file, cb) => {
        // Sanitização e Unique ID
        const sanitized = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_').substring(0, 50);
        const uniqueName = `${Date.now()}_${sanitized}`;
        cb(null, uniqueName);
    }
});

const upload = multer({ 
    storage: storage,
    limits: { fileSize: 50 * 1024 * 1024 }, // 50MB
    fileFilter: (req, file, cb) => {
        const allowedMimes = [
            'image/jpeg', 'image/png', 'image/webp',
            'application/pdf',
            'video/mp4',
            'audio/mpeg', 'audio/mp4', 'audio/ogg', 'audio/wav', 'audio/x-wav'
        ];
        if (allowedMimes.includes(file.mimetype)) cb(null, true);
        else cb(new Error('Tipo de arquivo não suportado'), false);
    }
});

// ============================================
// ROTAS DE WHATSAPP (CORE v7)
// ============================================
// Estas rotas substituem o antigo WhatsAppController para garantir uso do SessionManager v7

// Iniciar Sessão
router.post('/whatsapp/start', isAuthenticated, isAdmin, async (req, res) => {
    const empresaId = req.body.empresaId || req.user.empresaId;
    try {
        // Usa o Singleton injetado no server.js
        await req.whatsapp.startSession(empresaId);
        res.json({ success: true, message: 'Sessão inicializada. Escaneie o QR Code.' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Logout
router.post('/whatsapp/logout', isAuthenticated, isAdmin, async (req, res) => {
    const empresaId = req.body.empresaId || req.user.empresaId;
    try {
        await req.whatsapp.deleteSession(empresaId);
        res.json({ success: true, message: 'Sessão desconectada.' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Status e QR Code
router.get('/whatsapp/status/:companyId', isAuthenticated, (req, res) => {
    const empresaId = parseInt(req.params.companyId);
    
    const session = req.whatsapp.sessions.get(empresaId);
    const qr = req.whatsapp.qrCodes.get(empresaId);
    const isConnected = session?.user ? true : false;
    
    // Formatação segura do usuário
    const userJid = session?.user?.id ? session.user.id.split(':')[0] : null;

    res.json({
        connected: isConnected,
        status: isConnected ? 'CONECTADO' : (qr ? 'AGUARDANDO_QR' : 'DESCONECTADO'),
        qrcode: (!isConnected && qr) ? qr : null,
        number: userJid
    });
});

// ============================================
// ROTAS DE CRM / MENSAGEM (VIA FILA)
// ============================================

// Enviar Texto Simples
router.post('/crm/enviar', isAuthenticated, async (req, res) => {
    const { empresaId, number, message } = req.body;
    
    if (!empresaId || !number || !message) {
        return res.status(400).json({ error: 'Dados inválidos' });
    }

    try {
        const sock = req.whatsapp.sessions.get(parseInt(empresaId));
        if (!sock) throw new Error('WhatsApp desconectado');

        const jid = number.includes('@') ? number : `${number.replace(/\D/g, '')}@s.whatsapp.net`;
        
        // Envia diretamente (para mensagens de saída, não usamos fila para garantir feedback imediato ao atendente)
        // O SessionManager v7 captura o evento 'messages.upsert' e salva no banco via Worker
        const sent = await sock.sendMessage(jid, { text: message });
        
        res.json({ success: true, messageId: sent.key.id });
    } catch (error) {
        console.error(error);
        res.status(500).json({ success: false, error: 'Erro ao enviar mensagem' });
    }
});

// Enviar Mídia (Upload + Envio)
router.post('/crm/enviar-midia', isAuthenticated, upload.single('file'), async (req, res) => {
    const { empresaId, number, caption, type } = req.body; // type: image, video, document, audio
    const file = req.file;

    if (!file || !empresaId || !number) {
        return res.status(400).json({ error: 'Arquivo ou dados obrigatórios faltando' });
    }

    try {
        const sock = req.whatsapp.sessions.get(parseInt(empresaId));
        if (!sock) throw new Error('WhatsApp desconectado');

        const jid = number.includes('@') ? number : `${number.replace(/\D/g, '')}@s.whatsapp.net`;
        const filePath = file.path;
        
        // Mapeamento de tipos Baileys
        let msgContent = {};
        const mimetype = file.mimetype;

        if (mimetype.startsWith('image/')) {
            msgContent = { image: { url: filePath }, caption: caption };
        } else if (mimetype.startsWith('video/')) {
            msgContent = { video: { url: filePath }, caption: caption };
        } else if (mimetype.startsWith('audio/')) {
            msgContent = { audio: { url: filePath }, mimetype: 'audio/mp4', ptt: type === 'audio_ptt' }; // ptt: true envia como gravação
        } else {
            msgContent = { document: { url: filePath }, mimetype: mimetype, fileName: file.originalname, caption: caption };
        }

        const sent = await sock.sendMessage(jid, msgContent);
        
        // Opcional: Remover arquivo local após envio (se estiver usando S3 ou quiser economizar espaço)
        // fs.unlinkSync(filePath); 

        res.json({ success: true, messageId: sent.key.id });

    } catch (error) {
        console.error('[Upload/Send Error]', error);
        res.status(500).json({ success: false, error: 'Falha ao enviar mídia' });
    }
});


// ============================================
// OUTRAS ROTAS (LEGADO MANTIDO)
// ============================================

// Autenticação
router.post('/auth/login', AuthController.login);
router.post('/auth/recover-password', AuthController.recuperarSenha);
router.get('/auth/check', AuthController.checkSession);
router.post('/auth/logout', isAuthenticated, AuthController.logout);
router.post('/auth/change-password', isAuthenticated, AuthController.trocarSenha);

// Admin / Painel
router.get('/admin/dashboard-stats', isAuthenticated, (req, res) => adminPanelCtrl.getStats(req, res));
router.get('/admin/users', isAuthenticated, (req, res) => adminPanelCtrl.getUsers(req, res));

// Super Admin (Empresas)
router.get('/super-admin/empresas', isAuthenticated, isSuperAdmin, (req, res) => adminCtrl.getEmpresas(req, res));
router.post('/super-admin/empresas', isAuthenticated, isSuperAdmin, (req, res) => adminCtrl.createEmpresa(req, res));
router.post('/super-admin/empresas/update', isAuthenticated, isSuperAdmin, (req, res) => adminCtrl.updateEmpresa(req, res));
router.post('/super-admin/empresas/:id/status', isAuthenticated, isSuperAdmin, (req, res) => adminCtrl.toggleStatus(req, res));
router.post('/super-admin/empresas/:id/delete', isAuthenticated, isSuperAdmin, (req, res) => adminCtrl.deleteEmpresa(req, res));
router.post('/super-admin/empresas/:id/reset', isAuthenticated, isSuperAdmin, (req, res) => adminCtrl.resetSession(req, res));

// Configurações
router.get('/settings/schedules/:empresaId', isAuthenticated, isAdmin, (req, res) => scheduleController.getSchedules(req, res));
router.post('/settings/schedules/:empresaId', isAuthenticated, isAdmin, (req, res) => scheduleController.updateSchedules(req, res));

// ============================================
// TRATAMENTO DE ERROS
// ============================================
router.use((err, req, res, next) => {
    if (err instanceof multer.MulterError) {
        return res.status(400).json({ error: 'Erro de Upload', message: err.message });
    }
    if (err) {
        console.error('[API Router Error]', err);
        return res.status(500).json({ error: 'Erro interno', message: err.message });
    }
    next();
});

router.get('/ping', (req, res) => res.json({ 
    status: 'online', 
    version: '7.0', 
    workers: !!req.whatsapp.messageWorker 
}));

module.exports = router;