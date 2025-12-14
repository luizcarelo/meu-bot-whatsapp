// ============================================
// Arquivo: controllers/WhatsAppController.js
// Descrição: Controlador Central de WhatsApp & Regras de Negócio
// Versão: 5.1 - Integração Enterprise Horários
// ============================================

const fs = require('fs');
const path = require('path');
const { verificarHorarioAtendimento } = require('../src/utils/atendimento');

class WhatsAppController {
    /**
     * Construtor do WhatsAppController
     * @param {Object} db - Pool de conexão MySQL
     * @param {Object} sessionManager - Instância do SessionManager
     */
    constructor(db, sessionManager) {
        this.db = db;
        this.sm = sessionManager;
    }

    // ============================================
    // CONEXÃO WHATSAPP
    // ============================================

    /**
     * Inicia sessão WhatsApp para a empresa
     * POST /whatsapp/start
     */
    async startSession(req, res) {
        try {
            const empresaId = req.empresaId || req.body.empresaId || req.params.companyId;
            
            if (!empresaId) {
                return res.status(400).json({ 
                    error: 'ID da empresa não fornecido',
                    success: false 
                });
            }

            console.log(`[WhatsAppController] Iniciando sessão para empresa ${empresaId}`);
            
            // Inicia a sessão no Gerenciador
            await this.sm.startSession(parseInt(empresaId));

            // Configura os ouvintes de eventos (incluindo Horário de Atendimento)
            // Pequeno delay para garantir que o objeto client foi instanciado
            setTimeout(() => {
                this.monitorarAtendimento(parseInt(empresaId));
            }, 2000);
            
            res.json({ 
                success: true,
                message: 'Sessão iniciada. Monitoramento de horários ativo.'
            });
        } catch (e) {
            console.error('[WhatsAppController] Erro ao iniciar sessão:', e.message);
            res.status(500).json({ 
                error: e.message,
                success: false 
            });
        }
    }

    /**
     * Configura o monitoramento de mensagens recebidas para aplicar regras de negócio
     * (Horário de Atendimento, Anti-Spam, etc)
     */
    async monitorarAtendimento(empresaId) {
        const sock = this.sm.getSession(empresaId);
        
        if (!sock) {
            console.warn(`[WhatsAppController] Sessão não encontrada para empresa ${empresaId} ao configurar monitoramento.`);
            return;
        }

        // Evita duplicar listeners se a função for chamada múltiplas vezes
        if (sock.listenerCount('message') > 5) { // Limite de segurança
             sock.removeAllListeners('message');
        }

        console.log(`[WhatsAppController] Monitoramento de Atendimento ATIVO para Empresa ${empresaId}`);

        sock.on('message', async (msg) => {
            await this.processarMensagemRecebida(sock, msg, empresaId);
        });
    }

    /**
     * Núcleo de Processamento de Mensagens
     * Filtra horários e encaminha para IA ou CRM
     */
    async processarMensagemRecebida(sock, msg, empresaId) {
        try {
            // 1. Ignorar mensagens próprias, de status ou grupos
            if (msg.fromMe || msg.from === 'status@broadcast' || msg.from.includes('@g.us')) return;

            const contato = msg.from;

            // 2. Verificar Horário de Atendimento (NOVO MÓDULO)
            const statusAtendimento = await verificarHorarioAtendimento(this.db, empresaId);

            if (!statusAtendimento.dentroDoHorario) {
                console.log(`[Atendimento] Empresa ${empresaId} FECHADA. Bloqueando interação com ${contato}`);
                
                // Enviar mensagem de ausência
                if (statusAtendimento.mensagem) {
                    await sock.sendMessage(contato, { text: statusAtendimento.mensagem });
                }
                
                // Retorna para NÃO processar IA nem salvar como interação ativa
                return;
            }

            // 3. Se estiver aberto, continua o fluxo (Salvar DB, Acionar OpenAI, etc)
            // Nota: Se você tiver lógica de salvar mensagem recebida, ela deve vir AQUI.
            
            // Exemplo de log de passagem
            // console.log(`[Atendimento] Mensagem de ${contato} autorizada (Horário Comercial).`);

        } catch (error) {
            console.error(`[WhatsAppController] Erro no processamento de mensagem: ${error.message}`);
        }
    }

    /**
     * Encerra sessão WhatsApp (logout)
     * POST /whatsapp/logout
     */
    async logoutSession(req, res) {
        try {
            const empresaId = req.empresaId || req.body.empresaId || req.params.companyId;
            
            if (!empresaId) {
                return res.status(400).json({ error: 'ID da empresa não fornecido', success: false });
            }

            console.log(`[WhatsAppController] Encerrando sessão para empresa ${empresaId}`);
            
            await this.sm.deleteSession(parseInt(empresaId));
            
            res.json({ 
                success: true,
                message: 'Sessão encerrada com sucesso.'
            });
        } catch (e) {
            console.error('[WhatsAppController] Erro ao encerrar sessão:', e.message);
            res.status(500).json({ error: e.message, success: false });
        }
    }

    /**
     * Obtém status da conexão WhatsApp
     * GET /whatsapp/status
     */
    async getStatus(req, res) {
        try {
            const empresaId = req.empresaId || req.params.companyId;
            
            if (!empresaId) {
                return res.status(400).json({ error: 'ID da empresa não fornecido' });
            }

            const status = this.sm.getStatus(parseInt(empresaId));
            
            res.json({
                success: true,
                ...status
            });
        } catch (e) {
            console.error('[WhatsAppController] Erro ao obter status:', e.message);
            res.status(500).json({ error: e.message });
        }
    }

    /**
     * Obtém QR Code atual
     * GET /whatsapp/qrcode
     */
    async getQrCode(req, res) {
        try {
            const empresaId = req.empresaId || req.params.companyId;
            
            if (!empresaId) {
                return res.status(400).json({ error: 'ID da empresa não fornecido' });
            }

            const qr = this.sm.getQRCode(parseInt(empresaId));
            
            if (qr) {
                res.json({ success: true, qr: qr, qrBase64: qr });
            } else {
                res.json({ success: false, message: 'QR Code não disponível. Inicie a conexão primeiro.' });
            }
        } catch (e) {
            console.error('[WhatsAppController] Erro ao obter QR Code:', e.message);
            res.status(500).json({ error: e.message });
        }
    }

    // ============================================
    // UTILITÁRIOS
    // ============================================

    async getNomeAtendente(userId) {
        if (!userId) return null;
        try {
            const [rows] = await this.db.execute(
                'SELECT nome FROM usuarios_painel WHERE id = ?',
                [userId]
            );
            return rows.length > 0 ? rows[0].nome : null;
        } catch (e) {
            console.error('[WhatsAppController] Erro ao buscar atendente:', e.message);
            return null;
        }
    }

    // ============================================
    // ENVIO DE MENSAGENS (Saída)
    // ============================================

    /**
     * Envia mensagem de texto
     * POST /api/crm/enviar
     */
    async sendText(req, res) {
        const { telefone, texto } = req.body;
        const userId = req.headers['x-user-id'];
        const empresaId = req.empresaId;

        const sock = this.sm.getSession(empresaId);
        if (!sock) {
            return res.status(400).json({ error: 'WhatsApp não está conectado', success: false });
        }

        try {
            const jid = telefone.includes('@') ? telefone : `${telefone}@s.whatsapp.net`;
            
            // Nota: Mensagens enviadas pelo painel (Atendentes) NÃO passam pela validação de horário
            // pois assume-se que o humano tem autonomia para responder fora de hora se desejar.

            await sock.sendMessage(jid, { text: texto });

            await this.db.execute(
                `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`,
                [empresaId, jid, texto]
            );

            await this.db.execute(
                `INSERT IGNORE INTO contatos (empresa_id, telefone, nome) VALUES (?, ?, ?)`,
                [empresaId, jid, jid.split('@')[0]]
            );

            this.sm.emitirMensagemEnviada(empresaId, jid, texto, 'texto', null, true);

            res.json({ success: true });
        } catch (e) {
            console.error('[WhatsAppController] Erro ao enviar texto:', e.message);
            res.status(500).json({ error: 'Falha ao enviar mensagem', success: false });
        }
    }

    /**
     * Envia mídia
     * POST /api/crm/enviar-midia
     */
    async sendMedia(req, res) {
        const { telefone, caption } = req.body;
        const userId = req.headers['x-user-id'];
        const empresaId = req.empresaId;

        const sock = this.sm.getSession(empresaId);
        if (!sock) {
            return res.status(400).json({ error: 'WhatsApp não está conectado', success: false });
        }

        if (!req.file) {
            return res.status(400).json({ error: 'Nenhum arquivo enviado', success: false });
        }

        try {
            const jid = telefone.includes('@') ? telefone : `${telefone}@s.whatsapp.net`;
            const urlRelativa = `/uploads/empresa_${empresaId}/${req.file.filename}`;
            const filePath = req.file.path;
            const mime = req.file.mimetype;
            let captionFinal = caption || '';

            let msgSend = {};
            let tipo = 'documento';
            const fileBuffer = fs.readFileSync(filePath);

            if (mime.startsWith('image')) {
                msgSend = { image: fileBuffer, caption: captionFinal };
                tipo = 'imagem';
            } else if (mime.startsWith('video')) {
                msgSend = { video: fileBuffer, caption: captionFinal };
                tipo = 'video';
            } else if (mime.startsWith('audio')) {
                msgSend = { audio: fileBuffer, mimetype: 'audio/mp4', ptt: true };
                tipo = 'audio';
            } else {
                msgSend = { document: fileBuffer, mimetype: mime, fileName: req.file.originalname, caption: captionFinal };
                tipo = 'documento';
            }

            await sock.sendMessage(jid, msgSend);

            const conteudoSalvo = tipo === 'audio' ? (caption || 'Áudio enviado') : captionFinal || req.file.originalname;

            await this.db.execute(
                `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo, url_midia) VALUES (?, ?, 1, ?, ?, ?)`,
                [empresaId, jid, tipo, conteudoSalvo, urlRelativa]
            );

            this.sm.emitirMensagemEnviada(empresaId, jid, conteudoSalvo, tipo, urlRelativa, true);

            res.json({ success: true, url: urlRelativa });
        } catch (e) {
            console.error('[WhatsAppController] Erro ao enviar mídia:', e.message);
            res.status(500).json({ error: e.message, success: false });
        }
    }
}

module.exports = WhatsAppController;