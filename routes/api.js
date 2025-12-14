// ============================================
// Arquivo: routes/api.js
// Descrição: Rotas da API REST
// ============================================

const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');

// ============================================
// IMPORTAÇÃO DOS CONTROLLERS
// ============================================
const AuthController = require('../controllers/AuthController');
const AdminController = require('../controllers/AdminController');
const CrmController = require('../controllers/CrmController');
const WhatsAppController = require('../controllers/WhatsAppController');

// ============================================
// CONFIGURAÇÃO DO MULTER (UPLOAD DE ARQUIVOS)
// ============================================
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        // Define pasta baseada na empresa
        const folder = req.empresaId ? `empresa_${req.empresaId}` : 'temp';
        const dir = path.join(process.cwd(), 'public', 'uploads', folder);
        
        // Cria pasta se não existir
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        
        cb(null, dir);
    },
    filename: (req, file, cb) => {
        // Remove espaços e caracteres especiais
        const sanitized = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_');
        const filename = `${Date.now()}_${sanitized}`;
        cb(null, filename);
    }
});

// Filtro de tipos de arquivo permitidos
const fileFilter = (req, file, cb) => {
    const allowedTypes = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'video/mp4',
        'video/mpeg',
        'audio/mpeg',
        'audio/mp3',
        'audio/ogg',
        'audio/wav',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ];

    if (allowedTypes.includes(file.mimetype)) {
        cb(null, true);
    } else {
        cb(new Error('Tipo de arquivo não permitido'), false);
    }
};

const upload = multer({ 
    storage,
    limits: {
        fileSize: 50 * 1024 * 1024 // 50MB
    },
    fileFilter
});

// ============================================
// EXPORTAÇÃO DA FUNÇÃO DE ROTAS
// ============================================
module.exports = (sessionManager, db) => {
    
    // ============================================
    // INSTANCIAÇÃO DOS CONTROLLERS
    // ============================================
    const authCtrl = new AuthController(db);
    const adminCtrl = new AdminController(db, sessionManager);
    const crmCtrl = new CrmController(db, sessionManager);
    const waCtrl = new WhatsAppController(db, sessionManager);

    // ============================================
    // ROTAS PÚBLICAS (SEM AUTENTICAÇÃO)
    // ============================================
    
    // Autenticação
    router.post('/auth/login', (req, res) => authCtrl.login(req, res));
    router.post('/auth/esqueci-senha', (req, res) => authCtrl.esqueciSenha(req, res));
    router.post('/auth/trocar-senha', (req, res) => authCtrl.trocarSenha(req, res));

    // ============================================
    // MIDDLEWARE DE AUTENTICAÇÃO
    // Aplica autenticação para todas as rotas abaixo
    // ============================================
    router.use(require('../src/middleware/auth'));

    // ============================================
    // ROTAS DO SUPER ADMIN
    // ============================================
    router.get('/super-admin/analytics', (req, res) => 
        adminCtrl.getAnalytics(req, res)
    );
    
    router.post('/super-admin/empresas', (req, res) => 
        adminCtrl.createEmpresa(req, res)
    );
    
    router.put('/super-admin/empresas/update', (req, res) => 
        adminCtrl.updateEmpresa(req, res)
    );
    
    router.post('/super-admin/empresas/:id/status', (req, res) => 
        adminCtrl.toggleStatus(req, res)
    );
    
    router.post('/super-admin/empresas/:id/delete', (req, res) => 
        adminCtrl.deleteEmpresa(req, res)
    );
    
    router.post('/super-admin/empresas/:id/reset', (req, res) => 
        adminCtrl.resetSession(req, res)
    );

    // ============================================
    // ROTAS DO CRM - CONFIGURAÇÕES
    // ============================================
    
    // Configuração de IA
    router.post('/crm/config/ia', (req, res) => 
        crmCtrl.updateConfigIA(req, res)
    );
    
    // Broadcast (envio em massa)
    router.post('/crm/broadcast', (req, res) => 
        crmCtrl.sendBroadcast(req, res)
    );
    
    // Dashboard do cliente
    router.get('/crm/dashboard', (req, res) => 
        crmCtrl.getClientDashboard(req, res)
    );
    
    // Configurações gerais
    router.get('/crm/config', (req, res) => 
        crmCtrl.getConfig(req, res)
    );
    
    router.post('/crm/config/geral', 
        upload.fields([
            { name: 'logo', maxCount: 1 }, 
            { name: 'welcome_media', maxCount: 1 }
        ]), 
        (req, res) => crmCtrl.updateConfig(req, res)
    );
    
    // ============================================
    // ROTAS DO CRM - AGENDA E USUÁRIOS
    // ============================================
    
    router.get('/crm/agenda', (req, res) => 
        crmCtrl.getAgenda(req, res)
    );
    
    router.get('/crm/atendentes', (req, res) => 
        crmCtrl.getAtendentes(req, res)
    );
    
    router.post('/crm/atendentes', (req, res) => 
        crmCtrl.createAtendente(req, res)
    );
    
    router.delete('/crm/atendentes/:id', (req, res) => 
        crmCtrl.deleteAtendente(req, res)
    );

    // ============================================
    // ROTAS DO CRM - MENSAGENS RÁPIDAS
    // ============================================
    
    router.get('/crm/mensagens-rapidas', (req, res) => 
        crmCtrl.getQuickMessages(req, res)
    );
    
    router.post('/crm/mensagens-rapidas', (req, res) => 
        crmCtrl.createQuickMessage(req, res)
    );
    
    router.delete('/crm/mensagens-rapidas/:id', (req, res) => 
        crmCtrl.deleteQuickMessage(req, res)
    );

    // ============================================
    // ROTAS DO CRM - SETORES
    // ============================================
    
    router.get('/crm/setores', (req, res) => 
        crmCtrl.getSetores(req, res)
    );
    
    router.post('/crm/setores', 
        upload.single('media'), 
        (req, res) => crmCtrl.createSetor(req, res)
    );
    
    router.put('/crm/setores/:id', 
        upload.single('media'), 
        (req, res) => crmCtrl.updateSetor(req, res)
    );
    
    router.delete('/crm/setores/:id', (req, res) => 
        crmCtrl.deleteSetor(req, res)
    );
    
    router.post('/crm/setores/reordenar', (req, res) => 
        crmCtrl.reordenarSetores(req, res)
    );

    // ============================================
    // ROTAS DO CRM - CONTATOS E CHAT
    // ============================================
    
    router.get('/crm/contatos', (req, res) => 
        crmCtrl.getContatos(req, res)
    );
    
    router.post('/crm/contatos', (req, res) => 
        crmCtrl.createContato(req, res)
    );
    
    router.post('/crm/contato/update', (req, res) => 
        crmCtrl.updateContato(req, res)
    );
    
    router.get('/crm/avaliacoes', (req, res) => 
        crmCtrl.getAvaliacoes(req, res)
    );
    
    router.get('/crm/mensagens/:telefone', (req, res) => 
        crmCtrl.getMensagens(req, res)
    );

    // ============================================
    // ROTAS DO CRM - ATENDIMENTO
    // ============================================
    
    router.post('/crm/atendimento/assumir', (req, res) => 
        crmCtrl.assumirAtendimento(req, res)
    );
    
    router.post('/crm/atendimento/transferir', (req, res) => 
        crmCtrl.transferirAtendimento(req, res)
    );
    
    router.post('/crm/atendimento/transferir-usuario', (req, res) => 
        crmCtrl.transferirParaUsuario(req, res)
    );
    
    router.post('/crm/atendimento/encerrar', (req, res) => 
        crmCtrl.encerrarAtendimento(req, res)
    );

    // ============================================
    // ROTAS DO WHATSAPP
    // ============================================
    
    router.post('/crm/enviar', (req, res) => 
        waCtrl.sendText(req, res)
    );
    
    router.post('/crm/enviar-midia', 
        upload.single('file'), 
        (req, res) => waCtrl.sendMedia(req, res)
    );
    
    router.post('/whatsapp/start', (req, res) => 
        waCtrl.startSession(req, res)
    );
    
    router.post('/whatsapp/reset-me', (req, res) => 
        waCtrl.logoutSession(req, res)
    );

    // ============================================
    // TRATAMENTO DE ERROS DE UPLOAD
    // ============================================
    router.use((err, req, res, next) => {
        if (err instanceof multer.MulterError) {
            if (err.code === 'LIMIT_FILE_SIZE') {
                return res.status(400).json({ 
                    error: 'Arquivo muito grande. Tamanho máximo: 50MB' 
                });
            }
            return res.status(400).json({ 
                error: 'Erro no upload: ' + err.message 
            });
        } else if (err) {
            return res.status(400).json({ 
                error: err.message 
            });
        }
        next();
    });

    return router;
};