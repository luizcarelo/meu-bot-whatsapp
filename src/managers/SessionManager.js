// ============================================
// Arquivo: src/managers/SessionManager.js
// Descrição: Núcleo de conexão WhatsApp (Baileys) - Versão Final (Fluxo Corrigido & Mídia & Transcrição & Envio de Áudio)
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
const { estaNoHorario } = require('../utils/atendimento');
const QRCode = require('qrcode');
const OpenAIManager = require('./OpenAIManager');

// ==============================================================================
// CONFIGURAÇÃO DE TIPO DE MENU
// 'texto'  -> Lista numerada simples (Recomendado: 100% compatível e sem bugs)
// 'native' -> Botão azul moderno (Pode ter instabilidade no Web/iOS antigo)
// 'botoes' -> Botões visíveis (Apenas se tiver até 3 opções)
// ==============================================================================
const TIPO_MENU = 'texto'; 

class SessionManager {
    constructor(io, db) {
        this.io = io;
        this.db = db;
        this.sessions = new Map();
        this.rootDir = process.cwd();
        this.msgRetryCounterCache = new Map();
        this.reconnectAttempts = new Map();
        this.aiManager = new OpenAIManager(db);

        // Verificação de inatividade a cada minuto
        setInterval(() => this.verificarInatividade(), 60000);
    }

    // ============================================
    // HELPERS
    // ============================================

    emitirMensagemEnviada(empresaId, remoteJid, conteudo, tipo = 'texto', urlMidia = null, fromMe = true) {
        if (!this.io) {
            console.warn('[SessionManager] IO não inicializado.');
            return;
        }
        try {
            this.io.to(`empresa_${empresaId}`).emit('nova_mensagem', {
                remoteJid,
                fromMe: fromMe,
                conteudo,
                tipo,
                urlMidia,
                timestamp: Date.now() / 1000,
                status: 'sended'
            });
        } catch (e) { console.error('Erro emitirMensagemEnviada:', e); }
    }

    formatarMensagem(texto, nomeCliente) {
        if (!texto) return "";
        return texto.replace(/{{nome}}/g, nomeCliente || 'Cliente');
    }

    // ============================================
    // INATIVIDADE
    // ============================================

    async verificarInatividade() {
        try {
            const TEMPO_LIMITE_MINUTOS = 30;
            const sql = `
                SELECT c.id, c.empresa_id, c.telefone, c.nome, c.status_atendimento,
                       (SELECT MAX(data_hora) FROM mensagens m WHERE m.remote_jid = c.telefone AND m.empresa_id = c.empresa_id) as ultima_interacao
                FROM contatos c
                WHERE c.status_atendimento IN ('ATENDENDO', 'FILA', 'ABERTO')
                HAVING ultima_interacao < DATE_SUB(NOW(), INTERVAL ? MINUTE)
            `;
            const [contatosInativos] = await this.db.execute(sql, [TEMPO_LIMITE_MINUTOS]);

            if (contatosInativos.length > 0) {
                console.log(`[Inatividade] Encerrando ${contatosInativos.length} contatos.`);
                for (const contato of contatosInativos) {
                    await this.encerrarPorInatividade(contato, TEMPO_LIMITE_MINUTOS);
                }
            }
        } catch (e) {
            console.error("[Inatividade] Erro ao verificar:", e.message);
        }
    }

    async encerrarPorInatividade(contato, tempo) {
        const empresaId = contato.empresa_id;
        const remoteJid = contato.telefone;
        const sock = this.sessions.get(empresaId);

        try {
            const msgEncerramento = `⚠️ *Atendimento encerrado por inatividade.*\n\nOlá ${contato.nome || 'Cliente'}, como não houve interação nos últimos ${tempo} minutos, estamos encerrando este atendimento.\n\nResponda esta mensagem para iniciar novamente.`;

            if (sock) {
                await sock.sendMessage(remoteJid, { text: msgEncerramento });
                // Mensagem do sistema (fromMe = true)
                this.emitirMensagemEnviada(empresaId, remoteJid, msgEncerramento, 'sistema', null, true);
            }

            await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'sistema', ?)`, [empresaId, remoteJid, msgEncerramento]);
            await this.db.execute(`UPDATE contatos SET status_atendimento = 'ABERTO', setor_id = NULL, atendente_id = NULL WHERE id = ?`, [contato.id]);

            if (this.io) this.io.to(`empresa_${empresaId}`).emit('atualizar_lista', { action: 'inatividade', telefone: remoteJid });

        } catch (e) { console.error(`[Inatividade] Erro ID ${contato.id}:`, e.message); }
    }

    // ============================================
    // CONEXÃO BAILEYS
    // ============================================

    async reconnectAllSessions() {
        try {
            const [empresas] = await this.db.execute("SELECT id, nome FROM empresas WHERE ativo = 1 AND whatsapp_status != 'DESCONECTADO'");
            if (empresas.length === 0) return console.log('✅ Nenhuma sessão para restaurar.');
            console.log(`🔄 Restaurando ${empresas.length} sessões...`);
            for (const emp of empresas) {
                const authPath = path.join(this.rootDir, 'auth_sessions', `empresa_${emp.id}`);
                if (fs.existsSync(authPath) && fs.readdirSync(authPath).length > 0) {
                    await this.startSession(emp.id);
                    await delay(2000); 
                } else {
                    await this.updateDbStatus(emp.id, 'DESCONECTADO');
                }
            }
        } catch (e) { console.error('❌ Erro global ao restaurar sessões:', e); }
    }

    async deleteSession(empresaId) {
        console.log(`[Session] Removendo sessão da Empresa ${empresaId}`);
        if (this.sessions.has(empresaId)) {
            try {
                const sock = this.sessions.get(empresaId);
                sock.end(undefined);
                if (sock.ws) sock.ws.terminate();
            } catch (e) { console.error('Erro ao fechar socket:', e.message); }
            this.sessions.delete(empresaId);
        }
        const authPath = path.join(this.rootDir, 'auth_sessions', `empresa_${empresaId}`);
        if (fs.existsSync(authPath)) {
            try { fs.rmSync(authPath, { recursive: true, force: true }); } 
            catch (e) { try { fs.renameSync(authPath, `${authPath}_deleted_${Date.now()}`); } catch (ex) { } }
        }
        if (this.io) this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'offline' });
        await this.updateDbStatus(empresaId, 'DESCONECTADO');
        this.reconnectAttempts.delete(empresaId);
        return true;
    }

    async startSession(empresaId) {
        if (this.sessions.has(empresaId)) return this.sessions.get(empresaId);

        const authPath = path.join(this.rootDir, 'auth_sessions', `empresa_${empresaId}`);
        if (!fs.existsSync(authPath)) fs.mkdirSync(authPath, { recursive: true });

        const { state, saveCreds } = await useMultiFileAuthState(authPath);
        const { version } = await fetchLatestBaileysVersion();

        const sock = makeWASocket({
            version,
            logger: pino({ level: 'silent' }),
            printQRInTerminal: false,
            auth: { creds: state.creds, keys: makeCacheableSignalKeyStore(state.keys, pino({ level: "fatal" })) },
            browser: ["Sistemas de Gestão", "Chrome", "120.0"], 
            connectTimeoutMs: 60000,
            keepAliveIntervalMs: 30000,
            syncFullHistory: false,
            generateHighQualityLinkPreview: true,
            msgRetryCounterCache: this.msgRetryCounterCache,
            getMessage: async (key) => ({ conversation: 'hello' })
        });

        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            if (qr && this.io) {
                QRCode.toDataURL(qr).then(url => { this.io.to(`empresa_${empresaId}`).emit('qrcode', { qrBase64: url }); });
                await this.updateDbStatus(empresaId, 'AGUARDANDO_QR');
            }
            if (connection === 'close') {
                const reason = lastDisconnect?.error?.output?.statusCode;
                this.sessions.delete(empresaId);
                if (this.io) this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'offline' });
                const shouldReconnect = reason !== DisconnectReason.loggedOut && reason !== 401 && reason !== 403;
                if (shouldReconnect) {
                    const attempts = (this.reconnectAttempts.get(empresaId) || 0) + 1;
                    this.reconnectAttempts.set(empresaId, attempts);
                    const delayMs = Math.min(attempts * 2000, 30000);
                    setTimeout(() => this.startSession(empresaId), delayMs);
                } else {
                    await this.updateDbStatus(empresaId, 'DESCONECTADO');
                    await this.deleteSession(empresaId);
                }
            } else if (connection === 'open') {
                this.reconnectAttempts.set(empresaId, 0);
                this.sessions.set(empresaId, sock);
                if (this.io) this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'online' });
                const userJid = sock.user?.id ? sock.user.id.split(':')[0] : '';
                await this.updateDbStatus(empresaId, 'CONECTADO', userJid);
            }
        });

        sock.ev.on('creds.update', saveCreds);

        // ============================================
        // PROCESSAMENTO DE MENSAGENS (UPSERT)
        // ============================================
        sock.ev.on('messages.upsert', async ({ messages }) => {
            try {
                const msg = messages[0];
                if (!msg.message || msg.key.fromMe || msg.key.remoteJid === 'status@broadcast') return;

                const remoteJid = msg.key.remoteJid;
                const pushName = msg.pushName || remoteJid.split('@')[0];
                let conteudo = '', tipo = 'texto', urlMidia = null;
                const m = msg.message;

                // --- HELPER: Extração de Citação (Reply) ---
                const getQuote = (msgObj) => {
                    try {
                        if (msgObj.contextInfo && msgObj.contextInfo.quotedMessage) {
                            const q = msgObj.contextInfo.quotedMessage;
                            const text = q.conversation || q.extendedTextMessage?.text || (q.imageMessage ? '[Imagem]' : (q.audioMessage ? '[Áudio]' : (q.videoMessage ? '[Vídeo]' : '[Mídia]')));
                            if (text) {
                                return `> ↳ _Respondendo: ${text.substring(0, 45).replace(/\n/g, ' ')}${text.length>45?'...':''}_\n\n`;
                            }
                        }
                    } catch(e) {}
                    return '';
                };

                // Extração de Conteúdo
                if (m.conversation) {
                    conteudo = m.conversation;
                } 
                else if (m.extendedTextMessage) {
                    conteudo = getQuote(m.extendedTextMessage) + m.extendedTextMessage.text;
                } 
                else if (m.imageMessage) { 
                    tipo = 'imagem'; 
                    conteudo = getQuote(m.imageMessage) + (m.imageMessage.caption || '[Imagem]'); 
                    urlMidia = await this.salvarMidia(msg, empresaId); 
                }
                else if (m.videoMessage) { 
                    tipo = 'video'; 
                    conteudo = getQuote(m.videoMessage) + (m.videoMessage.caption || '[Vídeo]'); 
                    urlMidia = await this.salvarMidia(msg, empresaId); 
                }
                else if (m.audioMessage) { 
                    tipo = 'audio'; 
                    urlMidia = await this.salvarMidia(msg, empresaId); 
                    
                    // --- INTEGRAÇÃO COM TRANSCRIÇÃO (WHISPER) ---
                    try {
                        // Converte caminho relativo para absoluto para o fs
                        if (urlMidia) {
                            const cleanPath = urlMidia.replace(/^\/uploads\//, ''); // Remove '/uploads/' inicial se existir duplicado
                            const fullPath = path.join(this.rootDir, 'public', urlMidia.startsWith('/') ? urlMidia.substring(1) : urlMidia);
                            
                            // Aguarda um pouco para garantir que o arquivo foi escrito
                            await delay(1000); 
                            
                            const textoTranscrito = await this.aiManager.transcreverAudio(empresaId, fullPath);
                            
                            if (textoTranscrito && typeof textoTranscrito === 'string') {
                                conteudo = `🎤 *Transcrição:* ${textoTranscrito}`;
                            } else if (textoTranscrito && textoTranscrito.text) {
                                conteudo = `🎤 *Transcrição:* ${textoTranscrito.text}`;
                            } else {
                                conteudo = '[Áudio]';
                            }
                        }
                    } catch (e) {
                        console.error('[SessionManager] Erro ao transcrever áudio:', e);
                        conteudo = '[Áudio]';
                    }
                }
                else if (m.documentMessage) { 
                    tipo = 'documento'; 
                    conteudo = getQuote(m.documentMessage) + (m.documentMessage.fileName || '[Arquivo]'); 
                    urlMidia = await this.salvarMidia(msg, empresaId); 
                }
                else if (m.stickerMessage) { 
                    tipo = 'sticker'; 
                    conteudo = '[Figurinha]'; 
                    urlMidia = await this.salvarMidia(msg, empresaId); 
                }
                else if (m.interactiveResponseMessage) {
                    try {
                        const nativeFlow = m.interactiveResponseMessage.nativeFlowResponseMessage;
                        if (nativeFlow?.paramsJson) conteudo = JSON.parse(nativeFlow.paramsJson).id;
                        else if (m.interactiveResponseMessage.body) conteudo = m.interactiveResponseMessage.body.text;
                    } catch (e) { conteudo = ''; }
                } 
                else if (m.listResponseMessage) conteudo = m.listResponseMessage.singleSelectReply?.selectedRowId;
                else if (m.buttonsResponseMessage) conteudo = m.buttonsResponseMessage.selectedButtonId;
                else if (m.templateButtonReplyMessage) conteudo = m.templateButtonReplyMessage.selectedId;

                if (!conteudo && !urlMidia) return;

                // Gestão de Contato
                const [contatoExistente] = await this.db.execute(
                    'SELECT id, setor_id, status_atendimento, foto_perfil, atendente_id, last_welcome_at FROM contatos WHERE empresa_id = ? AND telefone = ?',
                    [empresaId, remoteJid]
                );

                let welcomeEnviado = false; 

                // --- FLUXO PRINCIPAL ---
                try {
                    const [empRows] = await this.db.execute(
                        "SELECT nome, mensagens_padrao, msg_ausencia, welcome_media_url, welcome_media_type, horario_inicio, horario_fim, dias_funcionamento FROM empresas WHERE id = ?",
                        [empresaId]
                    );
                    const emp = empRows[0];
                    let contatoId = contatoExistente[0]?.id;
                    let lastWelcomeAt = contatoExistente[0]?.last_welcome_at;

                    if (!contatoId) {
                        const [ins] = await this.db.execute(
                            "INSERT INTO contatos (empresa_id, telefone, nome, status_atendimento, created_at) VALUES (?, ?, ?, 'ABERTO', NOW())",
                            [empresaId, remoteJid, pushName]
                        );
                        contatoId = ins.insertId;
                    }

                    const precisaWelcome = !lastWelcomeAt || ((Date.now() - new Date(lastWelcomeAt).getTime()) / 3600000 >= 24);
                    const [setores] = await this.db.execute(
                        "SELECT id, nome, mensagem_saudacao, cor, media_url, media_type FROM setores WHERE empresa_id = ? ORDER BY ordem ASC, id ASC",
                        [empresaId]
                    );

                    // 1. VERIFICA SE É UMA SELEÇÃO DE MENU (NÚMERO)
                    const numSel = parseInt((conteudo || "").trim(), 10);
                    
                    if (!isNaN(numSel) && numSel >= 1 && numSel <= setores.length) {
                        const setorEscolhido = setores[numSel - 1];
                        
                        await this.db.execute(
                            "UPDATE contatos SET status_atendimento = 'FILA', setor_id = ?, atendente_id = NULL WHERE empresa_id = ? AND telefone = ?",
                            [setorEscolhido.id, empresaId, remoteJid]
                        );

                        const aviso = `🔄 Transferido para setor: *${setorEscolhido.nome}*`;
                        await sock.sendMessage(remoteJid, { text: aviso });
                        
                        if(setorEscolhido.mensagem_saudacao) {
                            const msgSetor = this.formatarMensagem(setorEscolhido.mensagem_saudacao, pushName);
                            await sock.sendMessage(remoteJid, { text: msgSetor });
                            this.emitirMensagemEnviada(empresaId, remoteJid, msgSetor, 'sistema', null, true);
                        }

                        if (setorEscolhido.media_url) {
                            const safePath = path.join(this.rootDir, 'public', setorEscolhido.media_url.replace(/^\//, ''));
                            if (fs.existsSync(safePath)) {
                                try {
                                    const fileBuffer = fs.readFileSync(safePath);
                                    const mediaMsg = setorEscolhido.media_type === 'imagem' ? { image: fileBuffer } : 
                                                     (setorEscolhido.media_type === 'audio' ? { audio: fileBuffer, mimetype: 'audio/mp4', ptt: true } : { document: fileBuffer, fileName: 'Arquivo' });
                                    await sock.sendMessage(remoteJid, mediaMsg);
                                } catch(e) {}
                            }
                        }

                        await this.db.execute("INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'sistema', ?)", [empresaId, remoteJid, aviso]);
                        // Correção: fromMe = true para mensagens do sistema
                        this.emitirMensagemEnviada(empresaId, remoteJid, aviso, 'sistema', null, true);
                        if(this.io) this.io.to(`empresa_${empresaId}`).emit('atualizar_lista', { action: 'mover_fila' });
                        
                        welcomeEnviado = true; // Impede que o fallback processe isso

                    } else if (precisaWelcome && emp) {
                        // 2. ENVIA BOAS VINDAS + MENU
                        const inHorario = estaNoHorario(emp);
                        let boasVindasText = "Olá! Seja bem-vindo(a).";
                        try {
                            const padrao = JSON.parse(emp.mensagens_padrao || "[]");
                            const msgBV = padrao.find(p => String(p.titulo || "").toLowerCase() === "boasvindas");
                            if (msgBV?.texto) boasVindasText = this.formatarMensagem(msgBV.texto, pushName);
                        } catch { }
                        
                        const ausenciaText = emp.msg_ausencia || "Estamos fora do horário. Retornaremos assim que possível.";

                        if (!inHorario) {
                            await sock.sendMessage(remoteJid, { text: ausenciaText });
                            await this.db.execute("INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'sistema', ?)", [empresaId, remoteJid, ausenciaText]);
                            this.emitirMensagemEnviada(empresaId, remoteJid, ausenciaText, 'sistema', null, true);
                        } else {
                            if (emp.welcome_media_url) {
                                const safePath = path.join(this.rootDir, "public", emp.welcome_media_url.replace(/^\/+/, ""));
                                if(fs.existsSync(safePath)) {
                                    try {
                                        const fileBuffer = fs.readFileSync(safePath);
                                        const type = String(emp.welcome_media_type).toLowerCase();
                                        const msgSend = (type === "imagem") ? { image: fileBuffer, caption: boasVindasText } :
                                                        (type === "video") ? { video: fileBuffer, caption: boasVindasText } :
                                                        (type === "audio") ? { audio: fileBuffer, mimetype: 'audio/mp4', ptt: true } :
                                                                            { document: fileBuffer, caption: boasVindasText, fileName: 'Arquivo' };
                                        await sock.sendMessage(remoteJid, msgSend);
                                        this.emitirMensagemEnviada(empresaId, remoteJid, boasVindasText || '[Mídia]', type, emp.welcome_media_url, true);
                                        boasVindasText = ""; 
                                    } catch (err) { console.error("Erro mídia welcome", err.message); }
                                }
                            }

                            if (boasVindasText) {
                                await sock.sendMessage(remoteJid, { text: boasVindasText });
                                this.emitirMensagemEnviada(empresaId, remoteJid, boasVindasText, 'sistema', null, true);
                            }

                            if(setores.length > 0) {
                                await this.enviarMenu(sock, remoteJid, setores, TIPO_MENU);
                                this.emitirMensagemEnviada(empresaId, remoteJid, "[Menu de Opções]", 'sistema', null, true);
                            }
                        }
                        await this.db.execute("UPDATE contatos SET last_welcome_at = NOW() WHERE id = ?", [contatoId]);
                        welcomeEnviado = true; // Marca que o fluxo de boas vindas ocorreu
                    }

                } catch (e) { console.error("[WelcomeFlow] Erro:", e); }

                // Salva contato e mensagem
                let fotoPerfil = contatoExistente[0]?.foto_perfil;
                if (!fotoPerfil) try { fotoPerfil = await sock.profilePictureUrl(remoteJid, 'image'); } catch (e) { }
                if (contatoExistente.length > 0) await this.db.execute(`UPDATE contatos SET foto_perfil=?, nome=? WHERE empresa_id=? AND telefone=?`, [fotoPerfil, pushName, empresaId, remoteJid]);
                await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo, url_midia) VALUES (?, ?, ?, ?, ?, ?)`, [empresaId, remoteJid, 0, tipo, conteudo, urlMidia]);
                
                // CORREÇÃO CRÍTICA: fromMe = false para mensagens que CHEGAM do cliente
                this.emitirMensagemEnviada(empresaId, remoteJid, conteudo, tipo, urlMidia, false);

                // 3. FALLBACK: CHATBOT E AVALIAÇÃO
                const contatoAtual = contatoExistente[0] || { setor_id: null, status_atendimento: 'ABERTO', atendente_id: null };

                if (contatoAtual.status_atendimento === 'AGUARDANDO_AVALIACAO') {
                    await this.processarAvaliacao(sock, empresaId, remoteJid, conteudo, contatoAtual);
                } 
                // CORREÇÃO: Só chama o auto-resposta se NÃO acabou de enviar o Welcome e NÃO é uma seleção de menu
                else if (!welcomeEnviado && (contatoAtual.status_atendimento === 'ABERTO' || contatoAtual.status_atendimento === 'FILA') && conteudo) {
                    const num = parseInt(conteudo);
                    if (isNaN(num)) {
                        await this.processarAutoResposta(sock, empresaId, remoteJid, conteudo, contatoAtual, pushName);
                    }
                }

            } catch (e) { console.error(`[Erro Msg Upsert]:`, e); }
        });

        this.sessions.set(empresaId, sock);
        return sock;
    }

    // ============================================
    // MENU UNIFICADO
    // ============================================
    async enviarMenu(sock, remoteJid, setores, tipo = 'texto') {
        try {
            if (tipo === 'texto') {
                let txt = "MENU DE OPÇÕES:\n\n";
                setores.forEach((s, i) => { txt += `*${i + 1}*. ${s.nome}\n`; });
                txt += "\nDigite o número da opção desejada.";
                await sock.sendMessage(remoteJid, { text: txt });
            } else if (tipo === 'lista' || tipo === 'native') {
                // Implementação de lista (compatível com Native Flow)
                const sections = [{
                    title: "Departamentos",
                    rows: setores.map((s, idx) => ({
                        header: "", title: s.nome, description: s.mensagem_saudacao ? s.mensagem_saudacao.substring(0, 50) + "..." : "", id: `${idx + 1}`
                    }))
                }];
                const msgContent = generateWAMessageFromContent(remoteJid, {
                    viewOnceMessage: {
                        message: {
                            interactiveMessage: {
                                body: { text: "Por favor, escolha o departamento:" },
                                footer: { text: "Atendimento Automático" },
                                header: { title: "MENU", subtitle: "", hasMediaAttachment: false },
                                nativeFlowMessage: {
                                    buttons: [{ name: "single_select", buttonParamsJson: JSON.stringify({ title: "Ver Opções", sections }) }]
                                }
                            }
                        }
                    }
                }, {});
                await sock.relayMessage(remoteJid, msgContent.message, { messageId: msgContent.key.id });
            }
        } catch (e) {
            console.error("Erro ao enviar menu:", e);
            // Fallback robusto para texto
            let txt = "MENU DE OPÇÕES:\n\n";
            setores.forEach((s, i) => { txt += `*${i + 1}*. ${s.nome}\n`; });
            txt += "\nResponda com o número.";
            await sock.sendMessage(remoteJid, { text: txt });
        }
    }

    // ============================================
    // CHATBOT E FALLBACK
    // ============================================
    async processarAutoResposta(sock, empresaId, remoteJid, textoRecebido, contato, nomeCliente) {
        try {
            if (contato.setor_id) return;

            // 1. Tenta IA
            const iaResponse = await this.aiManager.getResponse(empresaId, textoRecebido, remoteJid);
            if (iaResponse) {
                await sock.sendPresenceUpdate('composing', remoteJid);
                await delay(1500);
                await sock.sendMessage(remoteJid, { text: iaResponse });
                await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`, [empresaId, remoteJid, iaResponse]);
                // Correção: fromMe = true para IA
                this.emitirMensagemEnviada(empresaId, remoteJid, iaResponse, 'texto', null, true);
                return;
            }

            // 2. Se IA não respondeu, re-envia o menu (Recuperação)
            const [setores] = await this.db.execute("SELECT id, nome, mensagem_saudacao FROM setores WHERE empresa_id = ? ORDER BY ordem ASC, id ASC", [empresaId]);
            if(setores.length > 0) {
                await this.enviarMenu(sock, remoteJid, setores, TIPO_MENU);
                // Correção: fromMe = true para Menu
                this.emitirMensagemEnviada(empresaId, remoteJid, "[Menu Re-enviado]", 'sistema', null, true);
            }
            
        } catch (e) { console.error(`[Chatbot Erro]:`, e.message); }
    }

    async processarAvaliacao(sock, empresaId, remoteJid, texto, contato) {
        const nota = parseInt(texto.trim());
        if (!isNaN(nota) && nota >= 1 && nota <= 5) {
            try {
                await this.db.execute(`INSERT INTO avaliacoes (empresa_id, contato_telefone, atendente_id, nota) VALUES (?, ?, ?, ?)`, [empresaId, remoteJid, contato.atendente_id, nota]);
                const msg = "Obrigado pela sua avaliação! 🌟";
                await sock.sendMessage(remoteJid, { text: msg });
                // Correção: fromMe = true
                this.emitirMensagemEnviada(empresaId, remoteJid, msg, 'texto', null, true);
                await this.db.execute(`UPDATE contatos SET status_atendimento = 'ABERTO', atendente_id = NULL, setor_id = NULL WHERE empresa_id = ? AND telefone = ?`, [empresaId, remoteJid]);
                if (this.io) this.io.to(`empresa_${empresaId}`).emit('atualizar_lista', { action: 'finalizado' });
            } catch (e) {}
        } else {
            const msg = "Por favor, digite uma nota válida de 1 a 5.";
            await sock.sendMessage(remoteJid, { text: msg });
            this.emitirMensagemEnviada(empresaId, remoteJid, msg, 'texto', null, true);
        }
    }

    async updateDbStatus(empresaId, status, numero = null) {
        try {
            let sql = 'UPDATE empresas SET whatsapp_status = ?, whatsapp_updated_at = NOW()';
            let params = [status];
            if (numero) { sql += ', whatsapp_numero = ?'; params.push(numero); }
            sql += ' WHERE id = ?'; params.push(empresaId);
            await this.db.execute(sql, params);
        } catch (e) { }
    }

    async salvarMidia(msg, empresaId) {
        try {
            const buffer = await downloadMediaMessage(msg, 'buffer', {}, { logger: pino({ level: 'silent' }) });
            const pasta = path.join(this.rootDir, 'public/uploads', `empresa_${empresaId}`);
            if (!fs.existsSync(pasta)) fs.mkdirSync(pasta, { recursive: true });
            let ext = '.bin';
            if (msg.message.imageMessage) ext = '.jpg';
            else if (msg.message.audioMessage) ext = '.mp3';
            else if (msg.message.videoMessage) ext = '.mp4';
            else if (msg.message.documentMessage) ext = '.' + (msg.message.documentMessage.fileName?.split('.').pop() || 'bin');
            const fileName = `media_${Date.now()}${ext}`;
            await fs.promises.writeFile(path.join(pasta, fileName), buffer);
            return `/uploads/empresa_${empresaId}/${fileName}`;
        } catch (error) { return null; }
    }

    getSession(empresaId) { return this.sessions.get(empresaId); }
}

module.exports = SessionManager;