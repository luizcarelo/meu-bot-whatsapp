// ============================================
// Arquivo: routes/api.js
// Descrição: Rotas da API REST
// Versão: 5.0 - Revisado e Corrigido
// ============================================

const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');

// ============================================
// CONFIGURAÇÃO DO MULTER (UPLOAD DE ARQUIVOS)
// ============================================

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const empresaId = req.headers['x-empresa-id'] || req.empresaId || 'temp';
        const uploadPath = path.join(process.cwd(), 'public', 'uploads', `empresa_${empresaId}`);
        
        // Criar diretório se não existir
        if (!fs.existsSync(uploadPath)) {
            fs.mkdirSync(uploadPath, { recursive: true });
        }
        
        cb(null, uploadPath);
    },
    filename: (req, file, cb) => {
        // Sanitizar nome do arquivo
        const sanitized = file.originalname
            .replace(/[^a-zA-Z0-9.-]/g, '_')
            .substring(0, 100);
        const uniqueName = `${Date.now()}_${sanitized}`;
        cb(null, uniqueName);
    }
});

// Filtro de tipos de arquivo permitidos
const fileFilter = (req, file, cb) => {
    const allowedMimes = [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'video/mp4', 'video/webm', 'video/quicktime',
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/webm',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/zip',
        'text/plain'
    ];

    if (allowedMimes.includes(file.mimetype)) {
        cb(null, true);
    } else {
        cb(new Error(`Tipo de arquivo não permitido: ${file.mimetype}`), false);
    }
};

const upload = multer({
    storage,
    fileFilter,
    limits: {
        fileSize: 50 * 1024 * 1024 // 50MB
    }
});

// Upload com múltiplos campos
const uploadFields = upload.fields([
    { name: 'file', maxCount: 1 },
    { name: 'logo', maxCount: 1 },
    { name: 'welcome_media', maxCount: 1 },
    { name: 'media', maxCount: 1 }
]);

// ============================================
// MIDDLEWARE DE AUTENTICAÇÃO
// ============================================

function authMiddleware(req, res, next) {
    const empresaId = req.headers['x-empresa-id'];
    const userId = req.headers['x-user-id'];

    if (!empresaId) {
        return res.status(401).json({ 
            error: 'Empresa não identificada',
            message: 'Header x-empresa-id é obrigatório'
        });
    }

    req.empresaId = parseInt(empresaId);
    req.userId = userId ? parseInt(userId) : null;
    next();
}

// ============================================
// EXPORTAR FUNÇÃO DE CONFIGURAÇÃO
// ============================================

/**
 * Configura as rotas da API com as dependências necessárias
 * @param {Object} db - Pool de conexão MySQL
 * @param {Object} sessionManager - Instância do SessionManager
 * @returns {Router}
 */
module.exports = function(db, sessionManager) {
    
    // Importar controllers
    const AuthController = require('../controllers/AuthController');
    const CrmController = require('../controllers/CrmController');
    const WhatsAppController = require('../controllers/WhatsAppController');
    const AdminController = require('../controllers/AdminController');

    // Instanciar controllers
    const authCtrl = new AuthController(db);
    const crmCtrl = new CrmController(db, sessionManager);
    const waCtrl = new WhatsAppController(db, sessionManager);
    const adminCtrl = new AdminController(db, sessionManager);
    const whatsappController = new WhatsAppController(db, sessionManager);
    const crmController = new CrmController(db);
    const scheduleController = new ScheduleController(db);



    // ============================================
    // ROTAS DE AUTENTICAÇÃO (PÚBLICAS)
    // ============================================

    router.post('/auth/login', (req, res) => authCtrl.login(req, res));
    router.post('/auth/esqueci-senha', (req, res) => authCtrl.esqueciSenha(req, res));
    router.post('/auth/trocar-senha', authMiddleware, (req, res) => authCtrl.trocarSenha(req, res));

    // ============================================
    // ROTAS WHATSAPP (CONEXÃO)
    // ============================================

    router.post('/whatsapp/start', authMiddleware, (req, res) => waCtrl.startSession(req, res));
    router.post('/whatsapp/logout', authMiddleware, (req, res) => waCtrl.logoutSession(req, res));
    router.get('/whatsapp/status', authMiddleware, (req, res) => waCtrl.getStatus(req, res));
    router.get('/whatsapp/qrcode', authMiddleware, (req, res) => waCtrl.getQrCode(req, res));

    // Rotas alternativas (compatibilidade)
    router.get('/whatsapp/start/:companyId', (req, res) => {
        req.empresaId = parseInt(req.params.companyId);
        waCtrl.startSession(req, res);
    });
    router.get('/whatsapp/status/:companyId', (req, res) => {
        req.empresaId = parseInt(req.params.companyId);
        waCtrl.getStatus(req, res);
    });
    router.get('/whatsapp/qrcode/:companyId', (req, res) => {
        req.empresaId = parseInt(req.params.companyId);
        waCtrl.getQrCode(req, res);
    });
    router.post('/whatsapp/logout/:companyId', (req, res) => {
        req.empresaId = parseInt(req.params.companyId);
        waCtrl.logoutSession(req, res);
    });

    // ============================================
    // ROTAS CRM - MENSAGENS
    // ============================================

    router.get('/crm/mensagens/:telefone', authMiddleware, (req, res) => crmCtrl.getMensagens(req, res));
    router.post('/crm/enviar', authMiddleware, (req, res) => waCtrl.sendText(req, res));
    router.post('/crm/enviar-midia', authMiddleware, upload.single('file'), (req, res) => waCtrl.sendMedia(req, res));

    // ============================================
    // ROTAS CRM - CONTATOS
    // ============================================

    router.get('/crm/contatos', authMiddleware, (req, res) => crmCtrl.getContatos(req, res));
    router.post('/crm/contatos', authMiddleware, (req, res) => crmCtrl.createContato(req, res));
    router.put('/crm/contatos', authMiddleware, (req, res) => crmCtrl.updateContato(req, res));
    router.get('/crm/agenda', authMiddleware, (req, res) => crmCtrl.getAgenda(req, res));

    // ============================================
    // ROTAS CRM - ATENDIMENTO
    // ============================================

    router.post('/crm/atendimento/assumir', authMiddleware, (req, res) => crmCtrl.assumirAtendimento(req, res));
    router.post('/crm/atendimento/encerrar', authMiddleware, (req, res) => crmCtrl.encerrarAtendimento(req, res));
    router.post('/crm/atendimento/transferir', authMiddleware, (req, res) => crmCtrl.transferirAtendimento(req, res));
    router.post('/crm/atendimento/transferir-usuario', authMiddleware, (req, res) => crmCtrl.transferirParaUsuario(req, res));

    // ============================================
    // ROTAS CRM - CONFIGURAÇÕES
    // ============================================

    router.get('/crm/config', authMiddleware, (req, res) => crmCtrl.getConfig(req, res));
    router.put('/crm/config', authMiddleware, uploadFields, (req, res) => crmCtrl.updateConfig(req, res));
    router.put('/crm/config/ia', authMiddleware, (req, res) => crmCtrl.updateConfigIA(req, res));
    router.get('/crm/dashboard', authMiddleware, (req, res) => crmCtrl.getClientDashboard(req, res));
    router.get('/crm/avaliacoes', authMiddleware, (req, res) => crmCtrl.getAvaliacoes(req, res));

    // ============================================
    // ROTAS CRM - SETORES
    // ============================================

    router.get('/crm/setores', authMiddleware, (req, res) => crmCtrl.getSetores(req, res));
    router.post('/crm/setores', authMiddleware, upload.single('media'), (req, res) => crmCtrl.createSetor(req, res));
    router.put('/crm/setores/:id', authMiddleware, upload.single('media'), (req, res) => crmCtrl.updateSetor(req, res));
    router.delete('/crm/setores/:id', authMiddleware, (req, res) => crmCtrl.deleteSetor(req, res));
    router.post('/crm/setores/reordenar', authMiddleware, (req, res) => crmCtrl.reordenarSetores(req, res));

    // ============================================
    // ROTAS CRM - MENSAGENS RÁPIDAS
    // ============================================

    router.get('/crm/mensagens-rapidas', authMiddleware, (req, res) => crmCtrl.getQuickMessages(req, res));
    router.post('/crm/mensagens-rapidas', authMiddleware, (req, res) => crmCtrl.createQuickMessage(req, res));
    router.delete('/crm/mensagens-rapidas/:id', authMiddleware, (req, res) => crmCtrl.deleteQuickMessage(req, res));

    // ============================================
    // ROTAS CRM - EQUIPE
    // ============================================

    router.get('/crm/atendentes', authMiddleware, (req, res) => crmCtrl.getAtendentes(req, res));
    router.post('/crm/atendentes', authMiddleware, (req, res) => crmCtrl.createAtendente(req, res));
    router.delete('/crm/atendentes/:id', authMiddleware, (req, res) => crmCtrl.deleteAtendente(req, res));

    // ============================================
    // ROTAS CRM - ETIQUETAS
    // ============================================

    router.get('/crm/etiquetas', authMiddleware, (req, res) => crmCtrl.getEtiquetas(req, res));
    router.post('/crm/etiquetas', authMiddleware, (req, res) => crmCtrl.createEtiqueta(req, res));
    router.delete('/crm/etiquetas/:id', authMiddleware, (req, res) => crmCtrl.deleteEtiqueta(req, res));
    router.post('/crm/etiquetas/toggle', authMiddleware, (req, res) => crmCtrl.toggleEtiquetaContato(req, res));

    // ============================================
    // ROTAS CRM - BROADCAST
    // ============================================

    router.post('/crm/broadcast', authMiddleware, (req, res) => crmCtrl.sendBroadcast(req, res));

    // ============================================
    // ROTAS SUPER ADMIN
    // ============================================

    router.get('/super-admin/analytics', (req, res) => adminCtrl.getAnalytics(req, res));
    router.post('/super-admin/empresas', (req, res) => adminCtrl.createEmpresa(req, res));
    router.put('/super-admin/empresas/update', (req, res) => adminCtrl.updateEmpresa(req, res));
    router.post('/super-admin/empresas/:id/status', (req, res) => adminCtrl.toggleStatus(req, res));
    router.post('/super-admin/empresas/:id/delete', (req, res) => adminCtrl.deleteEmpresa(req, res));
    router.post('/super-admin/empresas/:id/reset', (req, res) => adminCtrl.resetSession(req, res));

    // --- Rotas de Configuração de Horários (Enterprise) ---
    router.get('/settings/schedules/:empresaId', (req, res) => scheduleController.getSchedules(req, res));
    router.post('/settings/schedules/:empresaId', (req, res) => scheduleController.updateSchedules(req, res));

    // ============================================
    // TRATAMENTO DE ERROS DE UPLOAD
    // ============================================

    router.use((err, req, res, next) => {
        if (err instanceof multer.MulterError) {
            if (err.code === 'LIMIT_FILE_SIZE') {
                return res.status(413).json({ 
                    error: 'Arquivo muito grande',
                    message: 'O arquivo excede o limite de 50MB'
                });
            }
            return res.status(400).json({ 
                error: 'Erro no upload',
                message: err.message 
            });
        }
        
        if (err) {
            return res.status(500).json({ 
                error: 'Erro interno',
                message: err.message 
            });
        }
        
        next();
    });

    return router;
};
