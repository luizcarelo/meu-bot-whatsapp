// ============================================
// Arquivo: src/managers/SessionManager.js
// Descrição: Gerenciador de Sessões WhatsApp (Baileys)
// Versão: 5.0 - Revisado e Corrigido
// ============================================

const {
    makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    downloadMediaMessage,
    makeCacheableSignalKeyStore,
    delay,
    generateWAMessageFromContent,
    proto
} = require('@whiskeysockets/baileys');

const pino = require('pino');
const fs = require('fs');
const path = require('path');
const QRCode = require('qrcode');

// ============================================
// UTILITÁRIOS
// ============================================

/**
 * Verifica se está dentro do horário de atendimento
 * @param {Object} empresa - Dados da empresa
 * @returns {boolean}
 */
function estaNoHorario(empresa) {
    if (!empresa) return true;
    
    try {
        const agora = new Date();
        const diaSemana = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sab'][agora.getDay()];
        
        // Verificar dias de funcionamento
        let diasFuncionamento = [];
        try {
            diasFuncionamento = typeof empresa.dias_funcionamento === 'string' 
                ? JSON.parse(empresa.dias_funcionamento) 
                : (empresa.dias_funcionamento || []);
        } catch (e) {
            diasFuncionamento = ['seg', 'ter', 'qua', 'qui', 'sex'];
        }
        
        if (!diasFuncionamento.includes(diaSemana)) {
            return false;
        }
        
        // Verificar horário
        const horaAtual = agora.getHours() * 60 + agora.getMinutes();
        
        const [hInicio, mInicio] = (empresa.horario_inicio || '08:00').split(':').map(Number);
        const [hFim, mFim] = (empresa.horario_fim || '18:00').split(':').map(Number);
        
        const inicioMinutos = hInicio * 60 + mInicio;
        const fimMinutos = hFim * 60 + mFim;
        
        return horaAtual >= inicioMinutos && horaAtual <= fimMinutos;
    } catch (e) {
        console.error('[Horário] Erro ao verificar:', e.message);
        return true;
    }
}

// ============================================
// CLASSE PRINCIPAL
// ============================================

class SessionManager {
    /**
     * Construtor do SessionManager
     * @param {Object} io - Instância do Socket.IO
     * @param {Object} db - Pool de conexão MySQL
     */
    constructor(io, db) {
        this.io = io;
        this.db = db;
        this.sessions = new Map();           // Map<empresaId, WASocket>
        this.qrCodes = new Map();            // Map<empresaId, qrBase64>
        this.rootDir = process.cwd();
        this.msgRetryCounterCache = new Map();
        this.reconnectAttempts = new Map();
        this.maxReconnectAttempts = 5;

        // Diretório de sessões
        this.authDir = path.join(this.rootDir, 'auth_sessions');
        if (!fs.existsSync(this.authDir)) {
            fs.mkdirSync(this.authDir, { recursive: true });
        }

        // Job de verificação de inatividade (a cada 1 minuto)
        setInterval(() => this.verificarInatividade(), 60000);

        console.log('✅ [SessionManager] Inicializado com sucesso');
    }

    // ============================================
    // EMISSÃO DE EVENTOS
    // ============================================

    /**
     * Emite mensagem enviada para o frontend via Socket.IO
     */
    emitirMensagemEnviada(empresaId, remoteJid, conteudo, tipo = 'texto', urlMidia = null, fromMe = true) {
        if (!this.io) {
            console.warn('[SessionManager] Socket.IO não inicializado');
            return;
        }
        
        try {
            this.io.to(`empresa_${empresaId}`).emit('nova_mensagem', {
                remoteJid,
                fromMe,
                conteudo,
                tipo,
                urlMidia,
                timestamp: Date.now() / 1000,
                status: 'sent'
            });
        } catch (e) {
            console.error('[SessionManager] Erro ao emitir mensagem:', e.message);
        }
    }

    /**
     * Emite atualização de lista de contatos
     */
    emitirAtualizacaoLista(empresaId, action = 'update') {
        if (!this.io) return;
        this.io.to(`empresa_${empresaId}`).emit('atualizar_lista', { action });
    }

    // ============================================
    // FORMATAÇÃO
    // ============================================

    /**
     * Substitui variáveis na mensagem
     */
    formatarMensagem(texto, nomeCliente) {
        if (!texto) return '';
        return texto.replace(/{{nome}}/gi, nomeCliente || 'Cliente');
    }

    // ============================================
    // VERIFICAÇÃO DE INATIVIDADE
    // ============================================

    async verificarInatividade() {
        try {
            const [rows] = await this.db.execute(`
                SELECT c.id, c.empresa_id, c.telefone, c.nome 
                FROM contatos c 
                WHERE c.status_atendimento IN ('ATENDENDO', 'FILA', 'ABERTO') 
                AND (
                    SELECT MAX(data_hora) 
                    FROM mensagens m 
                    WHERE m.remote_jid = c.telefone 
                    AND m.empresa_id = c.empresa_id
                ) < DATE_SUB(NOW(), INTERVAL 30 MINUTE)
            `);

            for (const contato of rows) {
                await this.encerrarPorInatividade(contato);
            }
        } catch (e) {
            console.error('[Inatividade] Erro:', e.message);
        }
    }

    async encerrarPorInatividade(contato) {
        const msg = '⚠️ *Atendimento encerrado por inatividade.*\nCaso precise de mais ajuda, envie uma nova mensagem.';
        const sock = this.sessions.get(contato.empresa_id);

        try {
            if (sock) {
                await sock.sendMessage(contato.telefone, { text: msg });
            }

            await this.db.execute(
                `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'sistema', ?)`,
                [contato.empresa_id, contato.telefone, msg]
            );

            await this.db.execute(
                `UPDATE contatos SET status_atendimento = 'ABERTO', setor_id = NULL, atendente_id = NULL WHERE id = ?`,
                [contato.id]
            );

            this.emitirMensagemEnviada(contato.empresa_id, contato.telefone, msg, 'sistema', null, true);
            this.emitirAtualizacaoLista(contato.empresa_id, 'inatividade');

        } catch (e) {
            console.error('[Inatividade] Erro ao encerrar:', e.message);
        }
    }

    // ============================================
    // RECONEXÃO AUTOMÁTICA
    // ============================================

    async reconnectAllSessions() {
        try {
            console.log('🔄 [SessionManager] Reconectando sessões ativas...');

            const [empresas] = await this.db.execute(
                "SELECT id, nome FROM empresas WHERE ativo = 1 AND whatsapp_status NOT IN ('DESCONECTADO', 'ERRO')"
            );

            for (const empresa of empresas) {
                const authPath = path.join(this.authDir, `empresa_${empresa.id}`);
                
                if (fs.existsSync(authPath)) {
                    console.log(`📱 [SessionManager] Reconectando empresa: ${empresa.nome} (ID: ${empresa.id})`);
                    await this.startSession(empresa.id);
                    await delay(2000); // Delay entre reconexões
                } else {
                    await this.updateDbStatus(empresa.id, 'DESCONECTADO');
                }
            }

            console.log('✅ [SessionManager] Reconexão concluída');
        } catch (e) {
            console.error('[SessionManager] Erro ao reconectar:', e.message);
        }
    }

    // ============================================
    // DELETAR SESSÃO
    // ============================================

    async deleteSession(empresaId) {
        console.log(`🗑️ [SessionManager] Deletando sessão empresa ${empresaId}...`);

        // Fechar socket existente
        if (this.sessions.has(empresaId)) {
            try {
                const sock = this.sessions.get(empresaId);
                sock.end(undefined);
                if (sock.ws) sock.ws.terminate();
            } catch (e) {
                console.error('[SessionManager] Erro ao fechar socket:', e.message);
            }
            this.sessions.delete(empresaId);
        }

        // Limpar QR Code
        this.qrCodes.delete(empresaId);

        // Remover arquivos de autenticação
        const authPath = path.join(this.authDir, `empresa_${empresaId}`);
        if (fs.existsSync(authPath)) {
            try {
                fs.rmSync(authPath, { recursive: true, force: true });
            } catch (e) {
                // Renomear se não conseguir deletar
                try {
                    fs.renameSync(authPath, `${authPath}_deleted_${Date.now()}`);
                } catch (ex) {
                    console.error('[SessionManager] Erro ao remover pasta de auth:', ex.message);
                }
            }
        }

        // Notificar frontend
        if (this.io) {
            this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'offline' });
            this.io.to(`empresa_${empresaId}`).emit('whatsapp_disconnected', { reason: 'logout' });
        }

        // Atualizar banco
        await this.updateDbStatus(empresaId, 'DESCONECTADO');

        console.log(`✅ [SessionManager] Sessão ${empresaId} deletada com sucesso`);
        return true;
    }

    // ============================================
    // INICIAR SESSÃO (PRINCIPAL)
    // ============================================

    async startSession(empresaId) {
        console.log(`🔄 [SessionManager] Iniciando sessão para empresa ${empresaId}...`);

        // Verificar se já existe sessão conectada
        if (this.sessions.has(empresaId)) {
            const existingSock = this.sessions.get(empresaId);
            if (existingSock?.user) {
                console.log(`✅ [SessionManager] Empresa ${empresaId} já está conectada`);
                return existingSock;
            }
            // Remover sessão não conectada
            this.sessions.delete(empresaId);
        }

        // Preparar diretório de autenticação
        const authPath = path.join(this.authDir, `empresa_${empresaId}`);
        if (!fs.existsSync(authPath)) {
            fs.mkdirSync(authPath, { recursive: true });
        }

        try {
            // Carregar estado de autenticação
            const { state, saveCreds } = await useMultiFileAuthState(authPath);
            
            // Buscar versão mais recente do WhatsApp
            const { version } = await fetchLatestBaileysVersion();
            console.log(`📱 [SessionManager] Usando Baileys versão: ${version.join('.')}`);

            // Criar socket WhatsApp
            const sock = makeWASocket({
                version,
                logger: pino({ level: 'silent' }),
                printQRInTerminal: true, // QR no terminal para debug
                auth: {
                    creds: state.creds,
                    keys: makeCacheableSignalKeyStore(state.keys, pino({ level: 'silent' }))
                },
                browser: ['CRM WhatsApp', 'Chrome', '121.0.0'],
                connectTimeoutMs: 60000,
                syncFullHistory: false,
                msgRetryCounterCache: this.msgRetryCounterCache,
                getMessage: async (key) => ({ conversation: 'retry' })
            });

            // ============================================
            // EVENTO: ATUALIZAÇÃO DE CONEXÃO
            // ============================================
            sock.ev.on('connection.update', async (update) => {
                const { connection, lastDisconnect, qr } = update;

                // --- QR CODE RECEBIDO ---
                if (qr) {
                    console.log(`📱 [SessionManager] QR Code gerado para empresa ${empresaId}`);
                    
                    try {
                        // Gerar QR Code como base64
                        const qrBase64 = await QRCode.toDataURL(qr, {
                            errorCorrectionLevel: 'M',
                            type: 'image/png',
                            quality: 0.92,
                            margin: 2,
                            width: 300
                        });

                        // Armazenar QR Code
                        this.qrCodes.set(empresaId, qrBase64);

                        // Emitir para frontend (múltiplos nomes de evento para compatibilidade)
                        if (this.io) {
                            // Formato principal
                            this.io.to(`empresa_${empresaId}`).emit('qr_code', { 
                                qr: qrBase64,
                                empresaId 
                            });
                            
                            // Formatos alternativos para compatibilidade
                            this.io.to(`empresa_${empresaId}`).emit('qrcode', { 
                                qr: qrBase64,
                                qrBase64: qrBase64 
                            });
                        }

                        await this.updateDbStatus(empresaId, 'AGUARDANDO_QR');
                        
                    } catch (err) {
                        console.error('[SessionManager] Erro ao gerar QR Code:', err.message);
                    }
                }

                // --- CONEXÃO FECHADA ---
                if (connection === 'close') {
                    this.sessions.delete(empresaId);
                    this.qrCodes.delete(empresaId);

                    // Notificar frontend
                    if (this.io) {
                        this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'offline' });
                    }

                    const statusCode = lastDisconnect?.error?.output?.statusCode;
                    const reason = lastDisconnect?.error?.output?.payload?.message || 'Desconhecido';
                    console.log(`⚠️ [SessionManager] Conexão fechada empresa ${empresaId}: ${reason} (${statusCode})`);

                    // Verificar se deve reconectar
                    const shouldNotReconnect = [
                        DisconnectReason.loggedOut,
                        401, // Unauthorized
                        403, // Forbidden
                        440  // Login timeout
                    ].includes(statusCode);

                    if (!shouldNotReconnect) {
                        // Tentar reconectar
                        const attempts = (this.reconnectAttempts.get(empresaId) || 0) + 1;
                        this.reconnectAttempts.set(empresaId, attempts);

                        if (attempts <= this.maxReconnectAttempts) {
                            const delayMs = Math.min(attempts * 2000, 30000);
                            console.log(`🔄 [SessionManager] Reconectando em ${delayMs}ms (tentativa ${attempts}/${this.maxReconnectAttempts})`);
                            setTimeout(() => this.startSession(empresaId), delayMs);
                        } else {
                            console.log(`❌ [SessionManager] Máximo de tentativas atingido para empresa ${empresaId}`);
                            await this.updateDbStatus(empresaId, 'ERRO');
                        }
                    } else {
                        // Logout ou erro fatal - limpar sessão
                        console.log(`🚪 [SessionManager] Logout detectado para empresa ${empresaId}`);
                        await this.deleteSession(empresaId);
                    }
                }

                // --- CONEXÃO ABERTA (CONECTADO) ---
                if (connection === 'open') {
                    console.log(`✅ [SessionManager] Empresa ${empresaId} conectada!`);
                    
                    // Resetar tentativas de reconexão
                    this.reconnectAttempts.set(empresaId, 0);
                    
                    // Armazenar sessão
                    this.sessions.set(empresaId, sock);
                    
                    // Limpar QR Code
                    this.qrCodes.delete(empresaId);

                    // Obter número conectado
                    const phoneNumber = sock.user?.id?.split(':')[0] || sock.user?.id?.split('@')[0];

                    // Notificar frontend
                    if (this.io) {
                        this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'online' });
                        this.io.to(`empresa_${empresaId}`).emit('whatsapp_ready', { 
                            numero: phoneNumber,
                            status: 'CONECTADO'
                        });
                    }

                    // Atualizar banco
                    await this.updateDbStatus(empresaId, 'CONECTADO', phoneNumber);
                }

                // --- CONECTANDO ---
                if (connection === 'connecting') {
                    console.log(`🔄 [SessionManager] Empresa ${empresaId} conectando...`);
                    if (this.io) {
                        this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'connecting' });
                    }
                }
            });

            // ============================================
            // EVENTO: SALVAR CREDENCIAIS
            // ============================================
            sock.ev.on('creds.update', saveCreds);

            // ============================================
            // EVENTO: MENSAGENS RECEBIDAS
            // ============================================
            sock.ev.on('messages.upsert', async ({ messages, type }) => {
                if (type !== 'notify') return;

                for (const msg of messages) {
                    await this.processarMensagemRecebida(empresaId, msg, sock);
                }
            });

            // Armazenar sessão temporariamente (até conectar)
            this.sessions.set(empresaId, sock);

            return sock;

        } catch (error) {
            console.error(`❌ [SessionManager] Erro ao iniciar sessão ${empresaId}:`, error.message);
            await this.updateDbStatus(empresaId, 'ERRO');
            throw error;
        }
    }

    // ============================================
    // PROCESSAR MENSAGEM RECEBIDA
    // ============================================

    async processarMensagemRecebida(empresaId, msg, sock) {
        try {
            // Ignorar mensagens inválidas
            if (!msg.message) return;
            if (msg.key.fromMe) return;
            if (msg.key.remoteJid === 'status@broadcast') return;

            const remoteJid = msg.key.remoteJid;
            const pushName = msg.pushName || remoteJid.split('@')[0];

            // Extrair conteúdo da mensagem
            let conteudo = '';
            let tipo = 'texto';
            let urlMidia = null;

            // Tratar ViewOnce (mídia de visualização única)
            let m = msg.message;
            let isViewOnce = false;

            if (m.viewOnceMessageV2) {
                m = m.viewOnceMessageV2.message;
                isViewOnce = true;
            } else if (m.viewOnceMessage) {
                m = m.viewOnceMessage.message;
                isViewOnce = true;
            }

            // Função auxiliar para obter citação
            const getQuote = (obj) => {
                try {
                    const q = obj.contextInfo?.quotedMessage;
                    if (q) {
                        const txt = q.conversation || q.extendedTextMessage?.text || (q.imageMessage ? '[Imagem]' : '[Mídia]');
                        return `> ↳ _${txt.substring(0, 45).replace(/\n/g, ' ')}..._\n\n`;
                    }
                } catch (e) {}
                return '';
            };

            // Determinar tipo e conteúdo
            if (m.conversation) {
                conteudo = m.conversation;
            } else if (m.extendedTextMessage) {
                conteudo = getQuote(m.extendedTextMessage) + m.extendedTextMessage.text;
            } else if (m.imageMessage) {
                tipo = 'imagem';
                const aviso = isViewOnce ? ' (Visualização Única)' : '';
                conteudo = getQuote(m.imageMessage) + (m.imageMessage.caption || '') + aviso;
                urlMidia = await this.salvarMidia({ message: m }, empresaId);
            } else if (m.videoMessage) {
                tipo = 'video';
                const aviso = isViewOnce ? ' (Visualização Única)' : '';
                conteudo = getQuote(m.videoMessage) + (m.videoMessage.caption || '') + aviso;
                urlMidia = await this.salvarMidia({ message: m }, empresaId);
            } else if (m.audioMessage) {
                tipo = 'audio';
                conteudo = '[Áudio]';
                urlMidia = await this.salvarMidia({ message: m }, empresaId);
            } else if (m.documentMessage) {
                tipo = 'documento';
                conteudo = getQuote(m.documentMessage) + (m.documentMessage.fileName || 'Arquivo');
                urlMidia = await this.salvarMidia({ message: m }, empresaId);
            } else if (m.stickerMessage) {
                tipo = 'sticker';
                conteudo = '[Sticker]';
                urlMidia = await this.salvarMidia({ message: m }, empresaId);
            } else if (m.locationMessage) {
                tipo = 'localizacao';
                conteudo = JSON.stringify({
                    lat: m.locationMessage.degreesLatitude,
                    lng: m.locationMessage.degreesLongitude,
                    name: m.locationMessage.name,
                    address: m.locationMessage.address
                });
            } else if (m.contactMessage) {
                tipo = 'contato';
                conteudo = JSON.stringify({
                    displayName: m.contactMessage.displayName,
                    vcard: m.contactMessage.vcard
                });
            } else if (m.pollCreationMessage || m.pollCreationMessageV2 || m.pollCreationMessageV3) {
                tipo = 'enquete';
                const poll = m.pollCreationMessage || m.pollCreationMessageV2 || m.pollCreationMessageV3;
                conteudo = JSON.stringify({
                    name: poll.name,
                    options: (poll.options || []).map(o => o.optionName)
                });
            } else if (m.interactiveResponseMessage) {
                try {
                    const json = JSON.parse(m.interactiveResponseMessage.nativeFlowResponseMessage.paramsJson);
                    conteudo = json.id;
                } catch (e) {
                    conteudo = m.interactiveResponseMessage.body?.text || '';
                }
            } else if (m.listResponseMessage) {
                conteudo = m.listResponseMessage.singleSelectReply?.selectedRowId || '';
            } else if (m.buttonsResponseMessage) {
                conteudo = m.buttonsResponseMessage.selectedButtonId || '';
            }

            // Se não extraiu conteúdo, ignorar
            if (!conteudo && !urlMidia) return;

            // Buscar/criar contato
            const [contatoEx] = await this.db.execute(
                'SELECT id, setor_id, status_atendimento, atendente_id, foto_perfil, last_welcome_at FROM contatos WHERE empresa_id = ? AND telefone = ?',
                [empresaId, remoteJid]
            );

            // Tentar obter foto de perfil
            let fotoPerfil = contatoEx[0]?.foto_perfil || null;
            try {
                const picUrl = await sock.profilePictureUrl(remoteJid, 'image');
                if (picUrl && picUrl !== fotoPerfil) {
                    fotoPerfil = picUrl;
                }
            } catch (e) {
                // Foto não disponível
            }

            // Criar ou atualizar contato
            if (contatoEx.length === 0) {
                await this.db.execute(
                    'INSERT INTO contatos (empresa_id, telefone, nome, status_atendimento, foto_perfil, created_at) VALUES (?, ?, ?, "ABERTO", ?, NOW())',
                    [empresaId, remoteJid, pushName, fotoPerfil]
                );
            } else {
                await this.db.execute(
                    'UPDATE contatos SET foto_perfil = ?, nome = ?, ultima_msg = NOW() WHERE empresa_id = ? AND telefone = ?',
                    [fotoPerfil, pushName, empresaId, remoteJid]
                );
            }

            // Salvar mensagem no banco
            await this.db.execute(
                `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo, url_midia) VALUES (?, ?, 0, ?, ?, ?)`,
                [empresaId, remoteJid, tipo, conteudo, urlMidia]
            );

            // Emitir para frontend
            if (this.io) {
                this.io.to(`empresa_${empresaId}`).emit('nova_mensagem', {
                    remoteJid,
                    fromMe: false,
                    conteudo,
                    tipo,
                    urlMidia,
                    timestamp: Date.now() / 1000,
                    status: 'received',
                    pushName,
                    foto: fotoPerfil
                });
            }

            // Processar fluxo de atendimento
            const contato = contatoEx[0] || { setor_id: null, status_atendimento: 'ABERTO' };
            const tiposSistema = ['localizacao', 'contato', 'enquete', 'evento', 'sticker'];

            if (contato.status_atendimento === 'AGUARDANDO_AVALIACAO') {
                await this.processarAvaliacao(sock, empresaId, remoteJid, conteudo, contato);
            } else if (!tiposSistema.includes(tipo) && ['ABERTO', 'FILA'].includes(contato.status_atendimento)) {
                await this.gerenciarFluxoAtendimento(sock, empresaId, remoteJid, conteudo, contato, pushName);
            }

        } catch (e) {
            console.error('[SessionManager] Erro ao processar mensagem:', e.message);
        }
    }

    // ============================================
    // FLUXO DE ATENDIMENTO
    // ============================================

    async gerenciarFluxoAtendimento(sock, empresaId, remoteJid, textoRecebido, contato, nomeCliente) {
        try {
            const [empRows] = await this.db.execute(
                "SELECT nome, mensagens_padrao, msg_ausencia, welcome_media_url, welcome_media_type, horario_inicio, horario_fim, dias_funcionamento FROM empresas WHERE id = ?",
                [empresaId]
            );
            
            const [setores] = await this.db.execute(
                "SELECT id, nome, mensagem_saudacao, media_url, media_type FROM setores WHERE empresa_id = ? ORDER BY ordem ASC, id ASC",
                [empresaId]
            );

            const emp = empRows[0];
            if (!emp) return;

            // Verificar se usuário selecionou um setor (número)
            const numSel = parseInt((textoRecebido || '').toString().replace(/\D/g, ''), 10);
            const setorEscolhido = (numSel > 0 && numSel <= setores.length) ? setores[numSel - 1] : null;

            if (setorEscolhido) {
                await this.transferirParaSetor(sock, empresaId, remoteJid, setorEscolhido, nomeCliente);
                return;
            }

            // Verificar se precisa enviar boas-vindas
            const [contatoData] = await this.db.execute(
                'SELECT last_welcome_at FROM contatos WHERE empresa_id = ? AND telefone = ?',
                [empresaId, remoteJid]
            );

            const lastWelcome = contatoData[0]?.last_welcome_at ? new Date(contatoData[0].last_welcome_at).getTime() : 0;
            const diffHours = (Date.now() - lastWelcome) / (1000 * 60 * 60);
            const precisaWelcome = diffHours >= 24;

            // Não enviar menu se já está em um setor
            if (contato.setor_id) return;

            if (precisaWelcome) {
                await this.enviarBoasVindas(sock, empresaId, remoteJid, emp, setores, nomeCliente);
                await this.db.execute(
                    "UPDATE contatos SET last_welcome_at = NOW() WHERE empresa_id = ? AND telefone = ?",
                    [empresaId, remoteJid]
                );
            } else if (setores.length > 0) {
                // Enviar menu novamente se não entendeu
                const txtMenu = "Não entendi sua mensagem. Por favor, escolha uma opção:\n\n" + 
                    setores.map((s, i) => `${i + 1} - ${s.nome}`).join('\n');
                await sock.sendMessage(remoteJid, { text: txtMenu });
                this.emitirMensagemEnviada(empresaId, remoteJid, txtMenu, 'sistema', null, true);
            }

        } catch (e) {
            console.error('[Fluxo] Erro:', e.message);
        }
    }

    async transferirParaSetor(sock, empresaId, remoteJid, setor, nomeCliente) {
        await sock.sendPresenceUpdate('composing', remoteJid);
        await delay(500);

        const txt = this.formatarMensagem(
            setor.mensagem_saudacao || `Transferido para *${setor.nome}*.`,
            nomeCliente
        );
        
        await sock.sendMessage(remoteJid, { text: txt });
        this.emitirMensagemEnviada(empresaId, remoteJid, txt, 'sistema', null, true);

        // Enviar mídia do setor se existir
        if (setor.media_url) {
            const cleanPath = setor.media_url.replace(/^\/uploads\//, '');
            const fullPath = path.join(this.rootDir, 'public', cleanPath);
            
            if (fs.existsSync(fullPath)) {
                const mediaMsg = setor.media_type === 'imagem'
                    ? { image: { url: fullPath } }
                    : { audio: { url: fullPath }, mimetype: 'audio/mp4', ptt: true };
                await sock.sendMessage(remoteJid, mediaMsg);
            }
        }

        // Atualizar status do contato
        await this.db.execute(
            'UPDATE contatos SET setor_id = ?, status_atendimento = "FILA" WHERE empresa_id = ? AND telefone = ?',
            [setor.id, empresaId, remoteJid]
        );

        this.emitirAtualizacaoLista(empresaId, 'mover_fila');
    }

    async enviarBoasVindas(sock, empresaId, remoteJid, emp, setores, nomeCliente) {
        const inHorario = estaNoHorario(emp);

        // Preparar texto de boas-vindas
        let texto = 'Olá {{nome}}! Como podemos ajudar?';
        try {
            const padrao = JSON.parse(emp.mensagens_padrao || '[]');
            const msgBV = padrao.find(p => String(p.titulo).toLowerCase() === 'boasvindas');
            if (msgBV?.texto) texto = msgBV.texto;
        } catch (e) {}

        // Se fora do horário, usar mensagem de ausência
        if (!inHorario) {
            texto = emp.msg_ausencia || 'Estamos fora do horário de atendimento. Retornaremos em breve.';
        }

        texto = this.formatarMensagem(texto, nomeCliente);

        // Enviar mídia de boas-vindas se existir
        if (emp.welcome_media_url && inHorario) {
            const cleanPath = emp.welcome_media_url.replace(/^\/uploads\//, '');
            const fullPath = path.join(this.rootDir, 'public', cleanPath);
            
            if (fs.existsSync(fullPath)) {
                const msgMedia = (emp.welcome_media_type === 'video')
                    ? { video: { url: fullPath }, caption: texto }
                    : { image: { url: fullPath }, caption: texto };

                await sock.sendMessage(remoteJid, msgMedia);
                this.emitirMensagemEnviada(empresaId, remoteJid, '[Mídia Boas-Vindas]', emp.welcome_media_type, null, true);
                texto = ''; // Não enviar texto separado
            }
        }

        // Enviar texto se não enviou com mídia
        if (texto) {
            await sock.sendMessage(remoteJid, { text: texto });
            this.emitirMensagemEnviada(empresaId, remoteJid, texto, 'sistema', null, true);
        }

        // Enviar menu de setores se dentro do horário
        if (inHorario && setores.length > 0) {
            await delay(800);
            
            const menuTexto = 'Selecione uma opção:\n\n' + 
                setores.map((s, idx) => `${idx + 1} - ${s.nome}`).join('\n');
            
            await sock.sendMessage(remoteJid, { text: menuTexto });
            this.emitirMensagemEnviada(empresaId, remoteJid, menuTexto, 'sistema', null, true);
        }
    }

    // ============================================
    // AVALIAÇÃO
    // ============================================

    async processarAvaliacao(sock, empresaId, remoteJid, texto, contato) {
        const nota = parseInt(texto.trim());

        if (!isNaN(nota) && nota >= 1 && nota <= 5) {
            await this.db.execute(
                `INSERT INTO avaliacoes (empresa_id, contato_telefone, atendente_id, nota) VALUES (?, ?, ?, ?)`,
                [empresaId, remoteJid, contato.atendente_id, nota]
            );

            const msg = 'Obrigado pela sua avaliação! 🌟\nSeu feedback é muito importante para nós.';
            await sock.sendMessage(remoteJid, { text: msg });
            this.emitirMensagemEnviada(empresaId, remoteJid, msg, 'sistema', null, true);

            await this.db.execute(
                `UPDATE contatos SET status_atendimento = 'ABERTO', atendente_id = NULL, setor_id = NULL WHERE empresa_id = ? AND telefone = ?`,
                [empresaId, remoteJid]
            );

            this.emitirAtualizacaoLista(empresaId, 'finalizado');
        } else {
            const msg = 'Por favor, digite uma nota válida de 1 a 5.';
            await sock.sendMessage(remoteJid, { text: msg });
            this.emitirMensagemEnviada(empresaId, remoteJid, msg, 'sistema', null, true);
        }
    }

    // ============================================
    // UTILITÁRIOS
    // ============================================

    async updateDbStatus(empresaId, status, numero = null) {
        try {
            let sql = 'UPDATE empresas SET whatsapp_status = ?, whatsapp_updated_at = NOW()';
            const params = [status];

            if (numero) {
                sql += ', whatsapp_numero = ?';
                params.push(numero);
            }

            sql += ' WHERE id = ?';
            params.push(empresaId);

            await this.db.execute(sql, params);
        } catch (e) {
            console.error('[SessionManager] Erro ao atualizar status:', e.message);
        }
    }

    async salvarMidia(msg, empresaId) {
        try {
            const buffer = await downloadMediaMessage(msg, 'buffer', {}, {
                logger: pino({ level: 'silent' })
            });

            const pasta = path.join(this.rootDir, 'public/uploads', `empresa_${empresaId}`);
            if (!fs.existsSync(pasta)) {
                fs.mkdirSync(pasta, { recursive: true });
            }

            // Determinar extensão
            let ext = '.bin';
            const m = msg.message;
            
            if (m.imageMessage) ext = '.jpg';
            else if (m.audioMessage) ext = '.mp3';
            else if (m.videoMessage) ext = '.mp4';
            else if (m.documentMessage) ext = '.' + (m.documentMessage.fileName?.split('.').pop() || 'bin');
            else if (m.stickerMessage) ext = '.webp';

            const fileName = `media_${Date.now()}${ext}`;
            await fs.promises.writeFile(path.join(pasta, fileName), buffer);

            return `/uploads/empresa_${empresaId}/${fileName}`;
        } catch (error) {
            console.error('[SessionManager] Erro ao salvar mídia:', error.message);
            return null;
        }
    }

    // ============================================
    // GETTERS
    // ============================================

    /**
     * Obtém sessão WhatsApp ativa
     * @param {number} empresaId 
     * @returns {WASocket|undefined}
     */
    getSession(empresaId) {
        return this.sessions.get(empresaId);
    }

    /**
     * Obtém QR Code da empresa (se disponível)
     * @param {number} empresaId 
     * @returns {string|undefined}
     */
    getQRCode(empresaId) {
        return this.qrCodes.get(empresaId);
    }

    /**
     * Verifica se empresa está conectada
     * @param {number} empresaId 
     * @returns {boolean}
     */
    isConnected(empresaId) {
        const sock = this.sessions.get(empresaId);
        return sock?.user ? true : false;
    }

    /**
     * Obtém status da conexão
     * @param {number} empresaId 
     * @returns {Object}
     */
    getStatus(empresaId) {
        const sock = this.sessions.get(empresaId);
        const qr = this.qrCodes.get(empresaId);

        return {
            connected: sock?.user ? true : false,
            hasQR: !!qr,
            qr: qr || null,
            numero: sock?.user?.id?.split(':')[0] || null
        };
    }
}

module.exports = SessionManager;
