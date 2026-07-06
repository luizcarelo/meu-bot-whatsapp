/**
 * controllers/WhatsAppController.js
 * Descrição: Controlador Central de WhatsApp & Regras de Negócio
 * Versão: 5.2 - Refatorado para Arquitetura Singleton DB
 * Adaptação: Compatibilidade com novo db.js (query/run) e SessionManager
 */

const fs = require('fs');
const path = require('path');
// Importação da lógica de horários (Deve ser compatível com o novo objeto db)
const { verificarHorarioAtendimento } = require('../src/utils/atendimento');

class WhatsAppController {
    /**
     * Construtor do WhatsAppController
     * @param {Object} db - Instância Singleton do Banco de Dados (wrapper)
     * @param {Object} sessionManager - Instância do SessionManager
     */
    constructor(db, sessionManager) {
        this.db = db;
        this.sm = sessionManager;
    }

    // ============================================
    // 1. GESTÃO DE SESSÃO (CONEXÃO)
    // ============================================

    /**
     * Inicia sessão WhatsApp para a empresa
     * POST /whatsapp/start
     */
    async startSession(req, res) {
        try {
            // Prioridade: Sessão Backend > Header > Body > Params
            const empresaId = req.session?.empresaId || req.headers['x-empresa-id'] || req.body.empresaId || req.params.companyId;
            
            if (!empresaId) {
                return res.status(400).json({ 
                    success: false, 
                    error: 'ID da empresa não identificado. Faça login novamente.' 
                });
            }

            console.log(`[WhatsAppController] 🚀 Iniciando sessão para empresa ID: ${empresaId}`);
            
            // Inicia a sessão no SessionManager (Baileys/WPPConnect)
            await this.sm.startSession(parseInt(empresaId));

            // Configura os ouvintes de eventos (incluindo Horário de Atendimento e IA)
            // Pequeno delay para garantir que a promessa de conexão foi resolvida internamente
            setTimeout(() => {
                this.monitorarAtendimento(parseInt(empresaId));
            }, 3000);
            
            res.json({ 
                success: true,
                message: 'Processo de conexão iniciado. Aguarde o QR Code ou a conexão automática.'
            });

        } catch (e) {
            console.error(`[WhatsAppController] ❌ Erro crítico ao iniciar sessão (Empresa ${req.body.empresaId}):`, e.message);
            res.status(500).json({ 
                success: false, 
                error: 'Falha interna ao iniciar serviço de WhatsApp.',
                details: e.message
            });
        }
    }

    /**
     * Configura o monitoramento de mensagens recebidas
     * Aplica regras de negócio: Horário, Anti-Spam e Gatilhos de IA
     */
    async monitorarAtendimento(empresaId) {
        const sock = this.sm.getSession(empresaId);
        
        if (!sock) {
            console.warn(`[WhatsAppController] ⚠️ Sessão não encontrada para empresa ${empresaId} ao tentar monitorar.`);
            return;
        }

        // Prevenção de múltiplos listeners (Memory Leak)
        // Se já houver muitos ouvintes, removemos os anteriores para renovar
        if (sock.listenerCount && sock.listenerCount('message') > 5) {
             sock.removeAllListeners('message');
        }

        console.log(`[WhatsAppController] 👂 Monitoramento de Atendimento ATIVO para Empresa ${empresaId}`);

        // Ouve eventos de mensagem (padrão do SessionManager deve emitir 'message')
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
            // 1. Filtros de Ignorância:
            // - Mensagens enviadas por mim (fromMe)
            // - Status (Stories)
            // - Grupos (Se o foco for atendimento individual)
            if (msg.fromMe || msg.from === 'status@broadcast' || msg.from.includes('@g.us')) return;

            const contato = msg.from;

            // 2. Verificar Horário de Atendimento (Módulo Externo)
            // Passamos 'this.db' que agora é o Singleton Wrapper
            const statusAtendimento = await verificarHorarioAtendimento(this.db, empresaId);

            if (!statusAtendimento.dentroDoHorario) {
                console.log(`[Atendimento] 🌙 Empresa ${empresaId} FECHADA. Contato: ${contato}`);
                
                // Enviar mensagem de ausência se configurada
                if (statusAtendimento.mensagem) {
                    await sock.sendMessage(contato, { text: statusAtendimento.mensagem });
                }
                
                // Interrompe o fluxo: Não processa IA, nem notifica atendentes
                return;
            }

            // 3. Fluxo de Atendimento Aberto (Horário Comercial)
            // AQUI entraria a lógica de:
            // - Salvar mensagem no banco (Tabela mensagens)
            // - Verificar se é cliente novo (Upsert tabela contatos)
            // - Acionar OpenAI (se habilitado para a empresa)
            
            // console.log(`[Atendimento] ✅ Mensagem de ${contato} processada.`);

        } catch (error) {
            console.error(`[WhatsAppController] ❌ Erro no processamento de mensagem: ${error.message}`);
        }
    }

    /**
     * Encerra sessão WhatsApp (logout)
     * POST /whatsapp/logout
     */
    async logoutSession(req, res) {
        try {
            const empresaId = req.session?.empresaId || req.body.empresaId || req.params.companyId;
            
            if (!empresaId) {
                return res.status(400).json({ success: false, error: 'ID da empresa não fornecido.' });
            }

            console.log(`[WhatsAppController] 🛑 Encerrando sessão para empresa ${empresaId}`);
            
            await this.sm.deleteSession(parseInt(empresaId));
            
            res.json({ 
                success: true,
                message: 'Sessão do WhatsApp desconectada e dados locais limpos.'
            });
        } catch (e) {
            console.error('[WhatsAppController] Erro ao encerrar sessão:', e.message);
            res.status(500).json({ success: false, error: e.message });
        }
    }

    /**
     * Obtém status da conexão WhatsApp
     * GET /whatsapp/status/:companyId
     */
    async getStatus(req, res) {
        try {
            const empresaId = req.session?.empresaId || req.params.companyId;
            
            if (!empresaId) {
                return res.status(400).json({ success: false, error: 'ID da empresa obrigatório.' });
            }

            // Consulta o SessionManager
            const status = this.sm.getStatus(parseInt(empresaId));
            
            res.json({
                success: true,
                ...status // Retorna { status: 'CONNECTED', qr: null, ... }
            });
        } catch (e) {
            console.error('[WhatsAppController] Erro ao obter status:', e.message);
            res.status(500).json({ success: false, error: e.message });
        }
    }

    /**
     * Obtém QR Code atual
     * GET /whatsapp/qrcode/:companyId
     */
    async getQrCode(req, res) {
        try {
            const empresaId = req.session?.empresaId || req.params.companyId;
            
            if (!empresaId) {
                return res.status(400).json({ success: false, error: 'ID da empresa obrigatório.' });
            }

            const qr = this.sm.getQRCode(parseInt(empresaId));
            
            if (qr) {
                res.json({ success: true, qr: qr, qrBase64: qr });
            } else {
                res.json({ 
                    success: false, 
                    message: 'QR Code indisponível. Verifique se a sessão foi iniciada ou se já está conectada.' 
                });
            }
        } catch (e) {
            console.error('[WhatsAppController] Erro ao obter QR Code:', e.message);
            res.status(500).json({ success: false, error: e.message });
        }
    }

    // ============================================
    // 2. MÉTODOS AUXILIARES
    // ============================================

    async getNomeAtendente(userId) {
        if (!userId) return null;
        try {
            // ATUALIZAÇÃO: Uso de this.db.query (Novo DB Wrapper)
            // query retorna as linhas diretamente, não um array [rows, fields]
            const rows = await this.db.query(
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
    // 3. ENVIO DE MENSAGENS (Saída CRM)
    // ============================================

    /**
     * Envia mensagem de texto via CRM
     * POST /api/crm/enviar
     */
    async sendText(req, res) {
        // Recupera dados do corpo e sessão
        const { telefone, texto } = req.body;
        const empresaId = req.session?.empresaId || req.empresaId || req.body.empresaId;
        const userId = req.session?.user?.id || req.headers['x-user-id'];

        // Validação de Sessão WA
        const sock = this.sm.getSession(empresaId);
        if (!sock) {
            return res.status(400).json({ success: false, error: 'WhatsApp Desconectado. Reconecte no painel.' });
        }

        if (!telefone || !texto) {
            return res.status(400).json({ success: false, error: 'Telefone e texto são obrigatórios.' });
        }

        try {
            // Formata JID (ex: 552199999999 -> 552199999999@s.whatsapp.net)
            const jid = telefone.includes('@') ? telefone : `${telefone}@s.whatsapp.net`;
            
            // Envia via Socket (Baileys)
            await sock.sendMessage(jid, { text: texto });

            // ATUALIZAÇÃO: Uso de this.db.run para INSERT (Novo DB Wrapper)
            // 1. Registra no Histórico de Mensagens
            await this.db.run(
                `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`,
                [empresaId, jid, texto]
            );

            // 2. Garante que o contato existe (Upsert PostgreSQL via ON CONFLICT)
            await this.db.run(
                `INSERT INTO contatos (empresa_id, telefone, nome) VALUES (?, ?, ?) ON CONFLICT (empresa_id, telefone) DO NOTHING`,
                [empresaId, jid, jid.split('@')[0]]
            );

            // Emite evento para atualizar o Front-end em tempo real (Socket.io se existir)
            if (this.sm.emitirMensagemEnviada) {
                this.sm.emitirMensagemEnviada(empresaId, jid, texto, 'texto', null, true);
            }

            res.json({ success: true, message: 'Mensagem enviada.' });

        } catch (e) {
            console.error('[WhatsAppController] ❌ Erro ao enviar texto:', e.message);
            res.status(500).json({ success: false, error: 'Falha técnica ao enviar mensagem.' });
        }
    }

    /**
     * Envia mídia (Imagem, Vídeo, Áudio, Doc) via CRM
     * POST /api/crm/enviar-midia
     */
    async sendMedia(req, res) {
        const { telefone, caption } = req.body;
        const empresaId = req.session?.empresaId || req.empresaId || req.body.empresaId;

        const sock = this.sm.getSession(empresaId);
        if (!sock) {
            return res.status(400).json({ success: false, error: 'WhatsApp Desconectado.' });
        }

        if (!req.file) {
            return res.status(400).json({ success: false, error: 'Arquivo de mídia não recebido.' });
        }

        try {
            const jid = telefone.includes('@') ? telefone : `${telefone}@s.whatsapp.net`;
            // Caminho relativo para salvar no banco (acessível via public)
            const urlRelativa = `/uploads/empresa_${empresaId}/${req.file.filename}`;
            const filePath = req.file.path;
            const mime = req.file.mimetype;
            const captionFinal = caption || '';

            let msgSend = {};
            let tipo = 'documento';
            
            // Leitura do arquivo para Buffer (Baileys exige Buffer ou URL)
            const fileBuffer = fs.readFileSync(filePath);

            // Definição do Tipo de Mensagem para o Baileys
            if (mime.startsWith('image')) {
                msgSend = { image: fileBuffer, caption: captionFinal };
                tipo = 'imagem';
            } else if (mime.startsWith('video')) {
                msgSend = { video: fileBuffer, caption: captionFinal };
                tipo = 'video';
            } else if (mime.startsWith('audio')) {
                // ptt: true envia como "Nota de Voz" (waveform)
                msgSend = { audio: fileBuffer, mimetype: 'audio/mp4', ptt: true };
                tipo = 'audio';
            } else {
                msgSend = { 
                    document: fileBuffer, 
                    mimetype: mime, 
                    fileName: req.file.originalname, 
                    caption: captionFinal 
                };
                tipo = 'documento';
            }

            // Envia
            await sock.sendMessage(jid, msgSend);

            // Define conteúdo textual para o banco (para pesquisa)
            const conteudoSalvo = tipo === 'audio' ? (caption || 'Áudio enviado') : (captionFinal || req.file.originalname);

            // ATUALIZAÇÃO: Uso de this.db.run (Novo DB Wrapper)
            await this.db.run(
                `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo, url_midia) VALUES (?, ?, 1, ?, ?, ?)`,
                [empresaId, jid, tipo, conteudoSalvo, urlRelativa]
            );

            if (this.sm.emitirMensagemEnviada) {
                this.sm.emitirMensagemEnviada(empresaId, jid, conteudoSalvo, tipo, urlRelativa, true);
            }

            res.json({ success: true, url: urlRelativa });

        } catch (e) {
            console.error('[WhatsAppController] ❌ Erro ao enviar mídia:', e.message);
            res.status(500).json({ success: false, error: e.message });
        }
    }
}

module.exports = WhatsAppController;