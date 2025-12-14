// ============================================
// Arquivo: src/managers/SessionManager.js
// Descrição: Núcleo de conexão WhatsApp (Baileys) - Versão Definitiva (ViewOnce Corrigido)
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

        setInterval(() => this.verificarInatividade(), 60000);
    }

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
        } catch (e) { console.error('Erro emitirMensagemEnviada:', e.message); }
    }

    formatarMensagem(texto, nomeCliente) {
        if (!texto) return "";
        return texto.replace(/{{nome}}/g, nomeCliente || 'Cliente');
    }

    async verificarInatividade() {
        try {
            const [rows] = await this.db.execute(`
                SELECT c.id, c.empresa_id, c.telefone, c.nome 
                FROM contatos c 
                WHERE c.status_atendimento IN ('ATENDENDO','FILA','ABERTO') 
                AND (SELECT MAX(data_hora) FROM mensagens m WHERE m.remote_jid = c.telefone AND m.empresa_id = c.empresa_id) < DATE_SUB(NOW(), INTERVAL 30 MINUTE)
            `);
            for (const c of rows) await this.encerrarPorInatividade(c);
        } catch (e) { console.error("Erro inatividade:", e.message); }
    }

    async encerrarPorInatividade(contato) {
        const msg = `⚠️ *Atendimento encerrado por inatividade.*`;
        const sock = this.sessions.get(contato.empresa_id);
        try {
            if (sock) {
                await sock.sendMessage(contato.telefone, { text: msg });
                this.emitirMensagemEnviada(contato.empresa_id, contato.telefone, msg, 'sistema', null, true);
            }
            await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'sistema', ?)`, [contato.empresa_id, contato.telefone, msg]);
            await this.db.execute(`UPDATE contatos SET status_atendimento = 'ABERTO', setor_id = NULL, atendente_id = NULL WHERE id = ?`, [contato.id]);
            if(this.io) this.io.to(`empresa_${contato.empresa_id}`).emit('atualizar_lista', { action: 'inatividade' });
        } catch(e) { console.error("Erro ao encerrar:", e.message); }
    }

    async reconnectAllSessions() {
        try {
            const [empresas] = await this.db.execute("SELECT id FROM empresas WHERE ativo = 1 AND whatsapp_status != 'DESCONECTADO'");
            for (const e of empresas) {
                const p = path.join(this.rootDir, 'auth_sessions', `empresa_${e.id}`);
                if (fs.existsSync(p)) { 
                    await this.startSession(e.id); 
                    await delay(2000); 
                } else {
                    await this.updateDbStatus(e.id, 'DESCONECTADO');
                }
            }
        } catch (e) { console.error('Erro reconnect:', e.message); }
    }

    async deleteSession(empresaId) {
        if (this.sessions.has(empresaId)) {
            try { 
                const s = this.sessions.get(empresaId);
                s.end(undefined);
                if(s.ws) s.ws.terminate();
            } catch(e){}
            this.sessions.delete(empresaId);
        }
        const p = path.join(this.rootDir, 'auth_sessions', `empresa_${empresaId}`);
        if (fs.existsSync(p)) {
            try { fs.rmSync(p, { recursive: true, force: true }); } 
            catch(e) { try { fs.renameSync(p, `${p}_del_${Date.now()}`); } catch(ex){} }
        }
        if(this.io) this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'offline' });
        await this.updateDbStatus(empresaId, 'DESCONECTADO');
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
            browser: ["Sistemas de Gestão", "Chrome", "10.0"], 
            connectTimeoutMs: 60000, 
            syncFullHistory: false,
            msgRetryCounterCache: this.msgRetryCounterCache,
            getMessage: async (key) => ({ conversation: 'hello' })
        });

        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            if (qr && this.io) {
                QRCode.toDataURL(qr).then(url => this.io.to(`empresa_${empresaId}`).emit('qrcode', { qrBase64: url }));
                await this.updateDbStatus(empresaId, 'AGUARDANDO_QR');
            }
            if (connection === 'close') {
                this.sessions.delete(empresaId);
                if(this.io) this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'offline' });
                const code = lastDisconnect?.error?.output?.statusCode;
                if (code !== DisconnectReason.loggedOut && code !== 401 && code !== 403) {
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
                if(this.io) this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'online' });
                await this.updateDbStatus(empresaId, 'CONECTADO', sock.user?.id?.split(':')[0]);
            }
        });

        sock.ev.on('creds.update', saveCreds);

        sock.ev.on('messages.upsert', async ({ messages }) => {
            try {
                const msg = messages[0];
                if (!msg.message || msg.key.fromMe || msg.key.remoteJid === 'status@broadcast') return;

                const remoteJid = msg.key.remoteJid;
                const pushName = msg.pushName || remoteJid.split('@')[0];
                let conteudo = '', tipo = 'texto', urlMidia = null;
                
                // --- TRATAMENTO PARA VIEW ONCE (Mídia de visualização única) ---
                // O Baileys coloca a mensagem real dentro de 'viewOnceMessage' ou 'viewOnceMessageV2'
                let m = msg.message;
                if (m.viewOnceMessageV2) {
                    m = m.viewOnceMessageV2.message;
                    conteudo = '[Mídia de Visualização Única]'; // Marcador para saber que é ViewOnce
                } else if (m.viewOnceMessage) {
                    m = m.viewOnceMessage.message;
                    conteudo = '[Mídia de Visualização Única]';
                }

                const getQuote = (obj) => {
                    try {
                        const q = obj.contextInfo?.quotedMessage;
                        if(q) {
                            const txt = q.conversation || q.extendedTextMessage?.text || (q.imageMessage?'[Imagem]':'[Mídia]');
                            return `> ↳ _Respondendo: ${txt.substring(0,45).replace(/\n/g, ' ')}..._\n\n`;
                        }
                    } catch(e){} return '';
                };

                if (m.conversation) conteudo = m.conversation;
                else if (m.extendedTextMessage) conteudo = getQuote(m.extendedTextMessage) + m.extendedTextMessage.text;
                else if (m.imageMessage) { 
                    tipo = 'imagem'; 
                    // Se for viewOnce, adicionamos o aviso na legenda
                    const aviso = conteudo === '[Mídia de Visualização Única]' ? ' (Visualização Única)' : '';
                    conteudo = getQuote(m.imageMessage) + (m.imageMessage.caption || '') + aviso; 
                    urlMidia = await this.salvarMidia({ message: m }, empresaId); // Passa o objeto 'm' desembrulhado
                }
                else if (m.videoMessage) { 
                    tipo = 'video'; 
                    const aviso = conteudo === '[Mídia de Visualização Única]' ? ' (Visualização Única)' : '';
                    conteudo = getQuote(m.videoMessage) + (m.videoMessage.caption || '') + aviso; 
                    urlMidia = await this.salvarMidia({ message: m }, empresaId); 
                }
                else if (m.audioMessage) {
                    tipo = 'audio';
                    urlMidia = await this.salvarMidia({ message: m }, empresaId);
                    try {
                        if (urlMidia) {
                            const cleanPath = urlMidia.replace(/^\/uploads\//, '');
                            const fullPath = path.join(this.rootDir, 'public', cleanPath);
                            await delay(1000); 
                            const textoTranscrito = await this.aiManager.transcreverAudio(empresaId, fullPath);
                            if (textoTranscrito) {
                                const txt = typeof textoTranscrito === 'string' ? textoTranscrito : textoTranscrito.text;
                                conteudo = `🎤 *Transcrição:* ${txt}`;
                            } else { conteudo = '[Áudio]'; }
                        }
                    } catch(e) { conteudo = '[Áudio]'; }
                }
                else if (m.documentMessage) { tipo = 'documento'; conteudo = getQuote(m.documentMessage) + (m.documentMessage.fileName || 'Arquivo'); urlMidia = await this.salvarMidia({ message: m }, empresaId); }
                else if (m.stickerMessage) { tipo = 'sticker'; urlMidia = await this.salvarMidia({ message: m }, empresaId); }
                else if (m.locationMessage) {
                    tipo = 'localizacao';
                    conteudo = JSON.stringify({ lat: m.locationMessage.degreesLatitude, lng: m.locationMessage.degreesLongitude, name: m.locationMessage.name, address: m.locationMessage.address });
                }
                else if (m.contactMessage) {
                    tipo = 'contato';
                    conteudo = JSON.stringify({ displayName: m.contactMessage.displayName, vcard: m.contactMessage.vcard });
                }
                else if (m.pollCreationMessage || m.pollCreationMessageV2 || m.pollCreationMessageV3) {
                    tipo = 'enquete';
                    const poll = m.pollCreationMessage || m.pollCreationMessageV2 || m.pollCreationMessageV3;
                    conteudo = JSON.stringify({ name: poll.name, options: (poll.options || []).map(o => o.optionName) });
                }
                else if (m.eventMessage) {
                    tipo = 'evento';
                    conteudo = JSON.stringify({ name: m.eventMessage.name, description: m.eventMessage.description, startTime: m.eventMessage.startTime });
                }
                else if (m.interactiveResponseMessage) {
                    try { const json = JSON.parse(m.interactiveResponseMessage.nativeFlowResponseMessage.paramsJson); conteudo = json.id; } catch(e) { conteudo = m.interactiveResponseMessage.body?.text || ''; }
                }
                else if (m.listResponseMessage) conteudo = m.listResponseMessage.singleSelectReply.selectedRowId;
                else if (m.buttonsResponseMessage) conteudo = m.buttonsResponseMessage.selectedButtonId;

                if (!conteudo && !urlMidia) return;

                const [contatoEx] = await this.db.execute('SELECT id, setor_id, status_atendimento, foto_perfil, last_welcome_at FROM contatos WHERE empresa_id = ? AND telefone = ?', [empresaId, remoteJid]);
                
                let fotoPerfil = contatoEx[0]?.foto_perfil;
                try {
                    const picUrl = await sock.profilePictureUrl(remoteJid, 'image');
                    if (picUrl && picUrl !== fotoPerfil) fotoPerfil = picUrl;
                } catch (e) { }

                if (contatoEx.length === 0) {
                    await this.db.execute('INSERT INTO contatos (empresa_id, telefone, nome, status_atendimento, foto_perfil, created_at) VALUES (?, ?, ?, "ABERTO", ?, NOW())', [empresaId, remoteJid, pushName, fotoPerfil]);
                } else {
                    await this.db.execute('UPDATE contatos SET foto_perfil=?, nome=? WHERE empresa_id=? AND telefone=?', [fotoPerfil, pushName, empresaId, remoteJid]);
                }

                await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo, url_midia) VALUES (?, ?, 0, ?, ?, ?)`, [empresaId, remoteJid, tipo, conteudo, urlMidia]);

                if(this.io) {
                    this.io.to(`empresa_${empresaId}`).emit('nova_mensagem', {
                        remoteJid, fromMe: false, conteudo, tipo, urlMidia, timestamp: Date.now() / 1000, status: 'received', pushName, foto: fotoPerfil 
                    });
                }

                const contato = contatoEx[0] || { setor_id: null, status_atendimento: 'ABERTO' };
                const tiposSistema = ['localizacao', 'contato', 'enquete', 'evento', 'sticker'];

                if (contato.status_atendimento === 'AGUARDANDO_AVALIACAO') {
                    await this.processarAvaliacao(sock, empresaId, remoteJid, conteudo, contato);
                } 
                else if (!tiposSistema.includes(tipo) && (contato.status_atendimento === 'ABERTO' || contato.status_atendimento === 'FILA')) {
                    await this.gerenciarFluxoAtendimento(sock, empresaId, remoteJid, conteudo, contato, pushName);
                }

            } catch (e) { console.error(`[Erro Msg Upsert]:`, e.message); }
        });

        this.sessions.set(empresaId, sock);
        return sock;
    }

    async gerenciarFluxoAtendimento(sock, empresaId, remoteJid, textoRecebido, contato, nomeCliente) {
        try {
            const [empRows] = await this.db.execute("SELECT nome, mensagens_padrao, msg_ausencia, welcome_media_url, welcome_media_type, horario_inicio, horario_fim, dias_funcionamento FROM empresas WHERE id = ?", [empresaId]);
            const [setores] = await this.db.execute("SELECT id, nome, mensagem_saudacao, media_url, media_type FROM setores WHERE empresa_id = ? ORDER BY ordem ASC, id ASC", [empresaId]);
            
            const emp = empRows[0];
            if (!emp) return;

            const numSel = parseInt((textoRecebido || "").toString().replace(/\D/g, ''), 10);
            const setorEscolhido = (numSel > 0 && numSel <= setores.length) ? setores[numSel - 1] : null;

            if (setorEscolhido) {
                await this.transferirParaSetor(sock, empresaId, remoteJid, setorEscolhido, nomeCliente);
                return;
            }

            const lastWelcome = contato.last_welcome_at ? new Date(contato.last_welcome_at).getTime() : 0;
            const diffHours = (Date.now() - lastWelcome) / (1000 * 60 * 60);
            const precisaWelcome = diffHours >= 24;

            if (contato.setor_id) return;

            if (precisaWelcome) {
                await this.enviarBoasVindas(sock, empresaId, remoteJid, emp, setores, nomeCliente);
                await this.db.execute("UPDATE contatos SET last_welcome_at = NOW() WHERE empresa_id = ? AND telefone = ?", [empresaId, remoteJid]);
            } else {
                const iaResponse = await this.aiManager.getResponse(empresaId, textoRecebido, remoteJid);
                if (iaResponse) {
                    await sock.sendPresenceUpdate('composing', remoteJid);
                    await delay(1000);
                    await sock.sendMessage(remoteJid, { text: iaResponse });
                    await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`, [empresaId, remoteJid, iaResponse]);
                    this.emitirMensagemEnviada(empresaId, remoteJid, iaResponse, 'texto', null, true);
                } else if (setores.length > 0) {
                    const txtMenu = "Não entendi. Por favor, escolha uma opção:\n\n" + setores.map((s, i) => `${i+1} - ${s.nome}`).join('\n');
                    await sock.sendMessage(remoteJid, { text: txtMenu });
                    this.emitirMensagemEnviada(empresaId, remoteJid, txtMenu, 'sistema', null, true);
                }
            }

        } catch (e) { console.error("[Fluxo] Erro:", e.message); }
    }

    async transferirParaSetor(sock, empresaId, remoteJid, setor, nomeCliente) {
        await sock.sendPresenceUpdate('composing', remoteJid);
        await delay(500);

        const txt = this.formatarMensagem(setor.mensagem_saudacao || `Transferido para *${setor.nome}*.`, nomeCliente);
        await sock.sendMessage(remoteJid, { text: txt });
        this.emitirMensagemEnviada(empresaId, remoteJid, txt, 'sistema', null, true);

        if (setor.media_url) {
            const cleanPath = setor.media_url.replace(/^\/uploads\//, '');
            const fullPath = path.join(this.rootDir, 'public', cleanPath);
            if (fs.existsSync(fullPath)) {
                const mediaMsg = setor.media_type === 'imagem' ? { image: { url: fullPath } } : { audio: { url: fullPath }, mimetype: 'audio/mp4', ptt: true };
                await sock.sendMessage(remoteJid, mediaMsg);
            }
        }

        await this.db.execute('UPDATE contatos SET setor_id = ?, status_atendimento = "FILA" WHERE empresa_id = ? AND telefone = ?', [setor.id, empresaId, remoteJid]);
        if(this.io) this.io.to(`empresa_${empresaId}`).emit('atualizar_lista', { action: 'mover_fila' });
    }

    async enviarBoasVindas(sock, empresaId, remoteJid, emp, setores, nomeCliente) {
        const inHorario = estaNoHorario(emp);
        let texto = "Olá {{nome}}! Como podemos ajudar?";
        try {
            const padrao = JSON.parse(emp.mensagens_padrao || "[]");
            const msgBV = padrao.find(p => String(p.titulo).toLowerCase() === "boasvindas");
            if (msgBV?.texto) texto = msgBV.texto;
        } catch {}

        if (!inHorario) texto = emp.msg_ausencia || "Estamos fora do horário de atendimento.";
        texto = this.formatarMensagem(texto, nomeCliente);

        if (emp.welcome_media_url) {
            const cleanPath = emp.welcome_media_url.replace(/^\/uploads\//, '');
            const fullPath = path.join(this.rootDir, 'public', cleanPath);
            if (fs.existsSync(fullPath)) {
                const msgMedia = (emp.welcome_media_type === 'video') 
                    ? { video: { url: fullPath }, caption: texto }
                    : { image: { url: fullPath }, caption: texto };
                
                await sock.sendMessage(remoteJid, msgMedia);
                this.emitirMensagemEnviada(empresaId, remoteJid, '[Mídia Boas-Vindas]', emp.welcome_media_type, null, true);
                texto = ""; 
            }
        }

        if (texto) {
            await sock.sendMessage(remoteJid, { text: texto });
            this.emitirMensagemEnviada(empresaId, remoteJid, texto, 'sistema', null, true);
        }

        if (inHorario && setores.length > 0) {
            await delay(800);
            const sections = [{
                title: "Departamentos",
                rows: setores.map((s, idx) => ({
                    header: "",
                    title: `${idx + 1}. ${s.nome}`,
                    description: s.mensagem_saudacao ? s.mensagem_saudacao.substring(0, 40) + "..." : "Falar com este setor",
                    id: `${idx + 1}`
                }))
            }];

            const msgMenu = generateWAMessageFromContent(remoteJid, {
                viewOnceMessage: {
                    message: {
                        interactiveMessage: {
                            body: { text: "Selecione uma opção abaixo:" },
                            footer: { text: "Atendimento Automático" },
                            header: { title: "", subtitle: "", hasMediaAttachment: false },
                            nativeFlowMessage: {
                                buttons: [{
                                    name: "single_select",
                                    buttonParamsJson: JSON.stringify({ title: "ABRIR MENU", sections })
                                }]
                            }
                        }
                    }
                }
            }, {});

            await sock.relayMessage(remoteJid, msgMenu.message, {});
            this.emitirMensagemEnviada(empresaId, remoteJid, "🔢 [Menu de Opções Enviado]", 'sistema', null, true);
        }
    }

    async processarAvaliacao(sock, empresaId, remoteJid, texto, contato) {
        const nota = parseInt(texto.trim());
        if (!isNaN(nota) && nota >= 1 && nota <= 5) {
            await this.db.execute(`INSERT INTO avaliacoes (empresa_id, contato_telefone, atendente_id, nota) VALUES (?, ?, ?, ?)`, [empresaId, remoteJid, contato.atendente_id, nota]);
            const msg = "Obrigado pela sua avaliação! 🌟";
            await sock.sendMessage(remoteJid, { text: msg });
            this.emitirMensagemEnviada(empresaId, remoteJid, msg, 'sistema', null, true);
            await this.db.execute(`UPDATE contatos SET status_atendimento = 'ABERTO', atendente_id = NULL, setor_id = NULL WHERE empresa_id = ? AND telefone = ?`, [empresaId, remoteJid]);
            if(this.io) this.io.to(`empresa_${empresaId}`).emit('atualizar_lista', { action: 'finalizado' });
        } else {
            const msg = "Por favor, digite uma nota válida de 1 a 5.";
            await sock.sendMessage(remoteJid, { text: msg });
            this.emitirMensagemEnviada(empresaId, remoteJid, msg, 'sistema', null, true);
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
            // Nota: Se 'msg' for viewOnce, usamos 'msg.message' que já foi desembrulhado no 'upsert'
            const buffer = await downloadMediaMessage(msg, 'buffer', {}, { logger: pino({ level: 'silent' }) });
            const pasta = path.join(this.rootDir, 'public/uploads', `empresa_${empresaId}`);
            if (!fs.existsSync(pasta)) fs.mkdirSync(pasta, { recursive: true });

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
        } catch (error) { return null; }
    }

    getSession(empresaId) { return this.sessions.get(empresaId); }
}

module.exports = SessionManager;