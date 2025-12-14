// ============================================
// Arquivo: src/managers/SessionManager.js
// Descrição: Núcleo de conexão WhatsApp (Baileys)
// ============================================

const {
    makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    downloadMediaMessage,
    makeCacheableSignalKeyStore,
    delay,
    proto
} = require('@whiskeysockets/baileys');
const pino = require('pino');
const fs = require('fs');
const path = require('path');
const { estaNoHorario } = require('../utils/atendimento');
const QRCode = require('qrcode');
const OpenAIManager = require('./OpenAIManager');

class SessionManager {
    constructor(io, db) {
        this.io = io;
        this.db = db;
        this.sessions = new Map();
        this.rootDir = process.cwd();
        this.msgRetryCounterCache = new Map();

        // Cache de tentativas de reconexão para evitar loops
        this.reconnectAttempts = new Map();

        // Inicializa IA Manager
        this.aiManager = new OpenAIManager(db);

        // Verificação de inatividade (Cron Job interno)
        setInterval(() => this.verificarInatividade(), 60000);
    }

    // ============================================
    // HELPERS E UTILITÁRIOS
    // ============================================

    emitirMensagemEnviada(empresaId, remoteJid, conteudo, tipo = 'texto', urlMidia = null) {
        this.io.to(`empresa_${empresaId}`).emit('nova_mensagem', {
            remoteJid,
            fromMe: true,
            conteudo,
            tipo,
            urlMidia,
            timestamp: Date.now() / 1000,
            status: 'sended'
        });
    }

    formatarMensagem(texto, nomeCliente) {
        if(!texto) return "";
        return texto.replace(/{{nome}}/g, nomeCliente || 'Cliente');
    }

    // ============================================
    // GESTÃO DE INATIVIDADE
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
                this.emitirMensagemEnviada(empresaId, remoteJid, msgEncerramento);
            }

            await this.db.execute(
                `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'sistema', ?)`,
                [empresaId, remoteJid, msgEncerramento]
            );

            await this.db.execute(
                `UPDATE contatos SET status_atendimento = 'ABERTO', setor_id = NULL, atendente_id = NULL WHERE id = ?`,
                [contato.id]
            );

            this.io.to(`empresa_${empresaId}`).emit('atualizar_lista', { action: 'inatividade', telefone: remoteJid });

        } catch (e) {
            console.error(`[Inatividade] Erro ID ${contato.id}:`, e.message);
        }
    }

    // ============================================
    // NÚCLEO DA SESSÃO WHATSAPP
    // ============================================

    async reconnectAllSessions() {
        try {
            const [empresas] = await this.db.execute("SELECT id, nome FROM empresas WHERE ativo = 1 AND whatsapp_status != 'DESCONECTADO'");
            if (empresas.length === 0) return console.log('✅ Nenhuma sessão para restaurar.');

            console.log(`🔄 Restaurando ${empresas.length} sessões...`);

            for (const emp of empresas) {
                const authPath = path.join(this.rootDir, 'auth_sessions', `empresa_${emp.id}`);
                // Verifica se a pasta existe e não está vazia
                if (fs.existsSync(authPath) && fs.readdirSync(authPath).length > 0) {
                    await this.startSession(emp.id);
                    await delay(2000); // Delay escalar para não saturar CPU
                } else {
                    await this.updateDbStatus(emp.id, 'DESCONECTADO');
                }
            }
        } catch (e) { console.error('❌ Erro global ao restaurar sessões:', e); }
    }

    async deleteSession(empresaId) {
        console.log(`[Session] Removendo sessão da Empresa ${empresaId}`);

        // 1. Fecha Socket
        if (this.sessions.has(empresaId)) {
            try {
                const sock = this.sessions.get(empresaId);
                sock.end(undefined);
                // Força destruição do WS se existir
                if(sock.ws) sock.ws.terminate();
            } catch(e) { console.error('Erro ao fechar socket:', e.message); }
            this.sessions.delete(empresaId);
        }

        // 2. Remove Arquivos
        const authPath = path.join(this.rootDir, 'auth_sessions', `empresa_${empresaId}`);
        if (fs.existsSync(authPath)) {
            try {
                fs.rmSync(authPath, { recursive: true, force: true });
            } catch (e) {
                console.error(`Erro ao deletar pasta ${authPath}:`, e.message);
                // Tenta fallback para renomear se estiver travado (Windows/Linux locks)
                try { fs.renameSync(authPath, `${authPath}_deleted_${Date.now()}`); } catch(ex) {}
            }
        }

        // 3. Atualiza DB e Frontend
        this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'offline' });
        await this.updateDbStatus(empresaId, 'DESCONECTADO');
        this.reconnectAttempts.delete(empresaId);
        return true;
    }

    async startSession(empresaId) {
        // Se já existe sessão ativa, retorna ela
        if (this.sessions.has(empresaId)) return this.sessions.get(empresaId);

        const authPath = path.join(this.rootDir, 'auth_sessions', `empresa_${empresaId}`);
        if (!fs.existsSync(authPath)) fs.mkdirSync(authPath, { recursive: true });

        const { state, saveCreds } = await useMultiFileAuthState(authPath);
        const { version } = await fetchLatestBaileysVersion();

        const sock = makeWASocket({
            version,
            logger: pino({ level: 'silent' }), // 'debug' em dev se precisar
            printQRInTerminal: false,
            auth: {
                creds: state.creds,
                keys: makeCacheableSignalKeyStore(state.keys, pino({ level: "fatal" }))
            },
            browser: ["SaaS CRM", "Chrome", "10.0"],
            connectTimeoutMs: 60000,
            keepAliveIntervalMs: 30000,
            syncFullHistory: false,
            generateHighQualityLinkPreview: true,
            msgRetryCounterCache: this.msgRetryCounterCache,
            getMessage: async (key) => {
                // Necessário para re-envio de mensagens e estabilidade
                return { conversation: 'system_placeholder' };
            }
        });

        // Evento de Atualização de Conexão
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                // Envia QR Code para o frontend
                QRCode.toDataURL(qr).then(url => {
                    this.io.to(`empresa_${empresaId}`).emit('qrcode', { qrBase64: url });
                });
                await this.updateDbStatus(empresaId, 'AGUARDANDO_QR');
            }

            if (connection === 'close') {
                const reason = lastDisconnect?.error?.output?.statusCode;
                this.sessions.delete(empresaId);
                this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'offline' });

                const shouldReconnect = reason !== DisconnectReason.loggedOut && reason !== 401 && reason !== 403;

                if (shouldReconnect) {
                    // Lógica de Backoff Exponencial Simples
                    const attempts = (this.reconnectAttempts.get(empresaId) || 0) + 1;
                    this.reconnectAttempts.set(empresaId, attempts);

                    const delayMs = Math.min(attempts * 2000, 30000); // Max 30s
                    console.log(`[Empresa ${empresaId}] Desconectado (${reason}). Reconectando em ${delayMs/1000}s... (Tentativa ${attempts})`);

                    setTimeout(() => this.startSession(empresaId), delayMs);
                } else {
                    console.log(`[Empresa ${empresaId}] Sessão encerrada permanentemente (${reason}).`);
                    await this.updateDbStatus(empresaId, 'DESCONECTADO');
                    await this.deleteSession(empresaId); // Limpa arquivos
                }

            } else if (connection === 'open') {
                console.log(`[Empresa ${empresaId}] Conexão Estabelecida 🟢`);
                this.reconnectAttempts.set(empresaId, 0); // Reseta tentativas
                this.sessions.set(empresaId, sock);
                this.io.to(`empresa_${empresaId}`).emit('status_conn', { status: 'online' });

                const userJid = sock.user?.id ? sock.user.id.split(':')[0] : '';
                await this.updateDbStatus(empresaId, 'CONECTADO', userJid);
            }
        });

        sock.ev.on('creds.update', saveCreds);

        // Processamento de Mensagens
        sock.ev.on('messages.upsert', async ({ messages }) => {
            try {
                const msg = messages[0];
                if (!msg.message || msg.key.fromMe || msg.key.remoteJid === 'status@broadcast') return;

                const remoteJid = msg.key.remoteJid;
                const pushName = msg.pushName || remoteJid.split('@')[0];

                let conteudo = '';
                let tipo = 'texto';
                let urlMidia = null;

                const m = msg.message;

                // Tratamento de Tipos de Mensagem (Compatibilidade Baileys v6+)
                if (m.conversation) conteudo = m.conversation;
                else if (m.extendedTextMessage) conteudo = m.extendedTextMessage.text;
                else if (m.imageMessage) {
                    tipo = 'imagem';
                    conteudo = m.imageMessage.caption || '[Imagem]';
                    urlMidia = await this.salvarMidia(msg, empresaId);
                }
                else if (m.videoMessage) {
                    tipo = 'video';
                    conteudo = m.videoMessage.caption || '[Vídeo]';
                    urlMidia = await this.salvarMidia(msg, empresaId);
                }
                else if (m.audioMessage) {
                    tipo = 'audio';
                    conteudo = '[Áudio]';
                    urlMidia = await this.salvarMidia(msg, empresaId);
                }
                else if (m.documentMessage) {
                    tipo = 'documento';
                    conteudo = m.documentMessage.fileName || '[Arquivo]';
                    urlMidia = await this.salvarMidia(msg, empresaId);
                }
                else if (m.stickerMessage) {
                    tipo = 'sticker';
                    conteudo = '[Figurinha]';
                    urlMidia = await this.salvarMidia(msg, empresaId);
                }
                // Tratamento de Respostas Interativas (Listas/Botões)
                else if (m.interactiveResponseMessage) {
                    try {
                        const params = JSON.parse(m.interactiveResponseMessage.nativeFlowResponseMessage.paramsJson);
                        conteudo = params.id;
                    } catch (e) {
                        conteudo = m.interactiveResponseMessage.body?.text || '';
                    }
                }
                else if (m.listResponseMessage) conteudo = m.listResponseMessage.singleSelectReply.selectedRowId;
                else if (m.buttonsResponseMessage) conteudo = m.buttonsResponseMessage.selectedButtonId;

                // Ignora mensagens vazias ou de protocolo desconhecido
                if (!conteudo && !urlMidia) return;

                // Persistência e Lógica de CRM
                const [contatoExistente] = await this.db.execute(
                    'SELECT id, setor_id, status_atendimento, foto_perfil, atendente_id FROM contatos WHERE empresa_id = ? AND telefone = ?',
                    [empresaId, remoteJid]
                );

                // Atualiza Foto de Perfil (Opcional, pode ser pesado)
                let fotoPerfil = contatoExistente[0]?.foto_perfil;
                if (!fotoPerfil) {
                    try { fotoPerfil = await sock.profilePictureUrl(remoteJid, 'image'); } catch (e) {}
                }

                if (contatoExistente.length === 0) {
                    await this.db.execute(
                        `INSERT INTO contatos (empresa_id, telefone, nome, status_atendimento, foto_perfil) VALUES (?, ?, ?, 'ABERTO', ?)`,
                        [empresaId, remoteJid, pushName, fotoPerfil]
                    );
                } else {
                    await this.db.execute(
                        `UPDATE contatos SET foto_perfil=?, nome=? WHERE empresa_id=? AND telefone=?`,
                        [fotoPerfil, pushName, empresaId, remoteJid]
                    );
                }

                await this.db.execute(
                    `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo, url_midia) VALUES (?, ?, ?, ?, ?, ?)`,
                    [empresaId, remoteJid, 0, tipo, conteudo, urlMidia]
                );

                this.io.to(`empresa_${empresaId}`).emit('nova_mensagem', {
                    remoteJid,
                    fromMe: false,
                    conteudo,
                    tipo,
                    urlMidia,
                    pushName,
                    foto: fotoPerfil,
                    timestamp: msg.messageTimestamp
                });

                // Roteamento de Chatbot
                const contatoAtual = contatoExistente[0] || { setor_id: null, status_atendimento: 'ABERTO', atendente_id: null };

                if (contatoAtual.status_atendimento === 'AGUARDANDO_AVALIACAO') {
                    await this.processarAvaliacao(sock, empresaId, remoteJid, conteudo, contatoAtual);
                } else if (contatoAtual.status_atendimento === 'ABERTO' || contatoAtual.status_atendimento === 'FILA') {
                    // Processa apenas se não estiver sendo atendido por humano
                    await this.processarAutoResposta(sock, empresaId, remoteJid, conteudo, contatoAtual, tipo, pushName);
                }

            } catch (e) {
                console.error(`[Erro Msg Upsert Empresa ${empresaId}]:`, e.message);
            }
        });

        this.sessions.set(empresaId, sock);
        return sock;
    }

    // ============================================
    // LÓGICA DE CHATBOT (MENU & IA)
    // ============================================

    async processarAutoResposta(sock, empresaId, remoteJid, textoRecebido, contato, tipoMensagem, nomeCliente) {
        try {
            // Se já tem setor, não manda menu, a menos que seja para sair da fila (opcional)
            if (contato.setor_id) return;

            const [setores] = await this.db.execute('SELECT id, nome, mensagem_saudacao, media_url, media_type FROM setores WHERE empresa_id = ? ORDER BY ordem ASC, id ASC', [empresaId]);

            let opcao = -1;
            const numeroMatch = textoRecebido ? textoRecebido.toString().match(/^\d+$/) : null;
            if(numeroMatch) opcao = parseInt(numeroMatch[0]);

            const setorEscolhido = (opcao > 0 && opcao <= setores.length) ? setores[opcao - 1] : null;

            if (setorEscolhido) {
                // --> Cliente escolheu uma opção válida
                await sock.sendPresenceUpdate('composing', remoteJid);
                await delay(500);

                const txtSetor = this.formatarMensagem(setorEscolhido.mensagem_saudacao || `Transferido para ${setorEscolhido.nome}.`, nomeCliente);
                await sock.sendMessage(remoteJid, { text: txtSetor });
                this.emitirMensagemEnviada(empresaId, remoteJid, txtSetor);

                if(setorEscolhido.media_url) {
                    const safePath = path.join(this.rootDir, 'public', setorEscolhido.media_url.replace(/^\//, ''));
                    if(fs.existsSync(safePath)) {
                        const mediaMsg = setorEscolhido.media_type === 'imagem'
                            ? { image: { url: safePath } }
                            : { audio: { url: safePath }, mimetype: 'audio/mp4', ptt: true };
                        await sock.sendMessage(remoteJid, mediaMsg);
                        this.emitirMensagemEnviada(empresaId, remoteJid, '[Mídia do Setor]', setorEscolhido.media_type, setorEscolhido.media_url);
                    }
                }

                await this.db.execute('UPDATE contatos SET setor_id = ?, status_atendimento = "FILA" WHERE empresa_id = ? AND telefone = ?', [setorEscolhido.id, empresaId, remoteJid]);
                this.io.to(`empresa_${empresaId}`).emit('atualizar_lista', { action: 'mover_fila' });

            } else {
                // --> Cliente mandou mensagem genérica: Tenta IA ou Manda Menu

                // 1. Tenta IA primeiro (se ativado)
                const iaResponse = await this.aiManager.getResponse(empresaId, textoRecebido, remoteJid);

                if (iaResponse) {
                    await sock.sendPresenceUpdate('composing', remoteJid);
                    await delay(1000);
                    await sock.sendMessage(remoteJid, { text: iaResponse });
                    await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`, [empresaId, remoteJid, iaResponse]);
                    this.emitirMensagemEnviada(empresaId, remoteJid, iaResponse);
                    return; // Se a IA respondeu, não manda menu
                }

                // 2. Se IA não configurada ou falhou, manda Menu
                if (setores.length === 0) return; // Sem setores, sem menu

                const [empresa] = await this.db.execute('SELECT welcome_media_url, welcome_media_type, mensagens_padrao FROM empresas WHERE id = ?', [empresaId]);

                let textoBoasVindas = "Olá {{nome}}! 👋\nComo podemos ajudar?";
                try {
                    const msgs = JSON.parse(empresa[0].mensagens_padrao || '[]');
                    const bemVindo = msgs.find(m => m.titulo === 'boasvindas');
                    if(bemVindo) textoBoasVindas = bemVindo.texto;
                } catch(e) {}

                textoBoasVindas = this.formatarMensagem(textoBoasVindas, nomeCliente);

                // Envia Mídia de Boas Vindas se houver
                if(empresa[0].welcome_media_url) {
                    const safePath = path.join(this.rootDir, 'public', empresa[0].welcome_media_url.replace(/^\//, ''));
                    if(fs.existsSync(safePath)) {
                        const msgMedia = empresa[0].welcome_media_type === 'video'
                            ? { video: { url: safePath }, caption: textoBoasVindas }
                            : { image: { url: safePath }, caption: textoBoasVindas };

                        await sock.sendMessage(remoteJid, msgMedia);
                        this.emitirMensagemEnviada(empresaId, remoteJid, '[Mídia Boas-Vindas]', empresa[0].welcome_media_type);

                        // Se enviou mídia com legenda, o texto já foi. Se não, precisaríamos enviar o menu abaixo.
                        // Para simplificar, vamos enviar o menu interativo com texto breve.
                        textoBoasVindas = "Selecione uma opção abaixo:";
                    }
                }

                // Montagem do Menu Interativo (Native Flow)
                const rows = setores.map((s, idx) => ({
                    header: "",
                    title: `${idx + 1}. ${s.nome}`,
                    description: s.mensagem_saudacao ? s.mensagem_saudacao.substring(0, 30) + "..." : "",
                    id: `${idx + 1}`
                }));

                const interactiveMessage = {
                    viewOnceMessage: {
                        message: {
                            messageContextInfo: {
                                deviceListMetadata: {},
                                deviceListMetadataVersion: 2
                            },
                            interactiveMessage: {
                                body: { text: textoBoasVindas },
                                footer: { text: "Atendimento Automático" },
                                header: { title: "", subtitle: "", hasMediaAttachment: false },
                                nativeFlowMessage: {
                                    buttons: [
                                        {
                                            name: "single_select",
                                            buttonParamsJson: JSON.stringify({
                                                title: "MENU DE OPÇÕES",
                                                sections: [
                                                    {
                                                        title: "Escolha um departamento",
                                                        rows: rows
                                                    }
                                                ]
                                            })
                                        }
                                    ]
                                }
                            }
                        }
                    }
                };

                await sock.relayMessage(remoteJid, interactiveMessage, {});
                this.emitirMensagemEnviada(empresaId, remoteJid, "[Menu Interativo Enviado]");
            }
        } catch (e) { console.error(`[Chatbot Erro Empresa ${empresaId}]`, e.message); }
    }

    async processarAvaliacao(sock, empresaId, remoteJid, texto, contato) {
        const nota = parseInt(texto.trim());
        if (!isNaN(nota) && nota >= 1 && nota <= 5) {
            try {
                await this.db.execute(`INSERT INTO avaliacoes (empresa_id, contato_telefone, atendente_id, nota) VALUES (?, ?, ?, ?)`, [empresaId, remoteJid, contato.atendente_id, nota]);
                const msg = "Obrigado pela sua avaliação! 🌟";
                await sock.sendMessage(remoteJid, { text: msg });
                this.emitirMensagemEnviada(empresaId, remoteJid, msg);
                await this.db.execute(`UPDATE contatos SET status_atendimento = 'ABERTO', atendente_id = NULL, setor_id = NULL WHERE empresa_id = ? AND telefone = ?`, [empresaId, remoteJid]);
                this.io.to(`empresa_${empresaId}`).emit('atualizar_lista', { action: 'finalizado' });
            } catch (e) { console.error("Erro avaliação", e); }
        } else {
            const msg = "Por favor, digite uma nota válida de 1 a 5.";
            await sock.sendMessage(remoteJid, { text: msg });
            this.emitirMensagemEnviada(empresaId, remoteJid, msg);
        }
    }

    async updateDbStatus(empresaId, status, numero = null) {
        try {
            let sql = 'UPDATE empresas SET whatsapp_status = ?, whatsapp_updated_at = NOW()';
            let params = [status];
            if (numero) { sql += ', whatsapp_numero = ?'; params.push(numero); }
            sql += ' WHERE id = ?'; params.push(empresaId);
            await this.db.execute(sql, params);
        } catch (e) { console.error("Erro updateDbStatus:", e.message); }
    }

    async salvarMidia(msg, empresaId) {
        try {
            const buffer = await downloadMediaMessage(msg, 'buffer', { }, { logger: pino({ level: 'silent' }) });
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
        } catch (error) {
            console.error("Erro ao salvar mídia:", error.message);
            return null;
        }
    }

    getSession(empresaId) { return this.sessions.get(empresaId); }
}

module.exports = SessionManager;