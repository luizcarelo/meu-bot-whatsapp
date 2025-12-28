/**
 * ============================================
 * Arquivo: src/managers/SessionManager.js
 * Descrição: Core de Sessões WhatsApp + Arquitetura de Filas (Redis/BullMQ)
 * Arquitetura: SAAS Enterprise (Event-Driven)
 * Versão: 7.2 - Redis Auth Fix
 * Autor: Sistemas de Gestão
 * ============================================
 */

// Garante carregamento do .env, independente da ordem de importação
require('dotenv').config();

const {
    makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    downloadMediaMessage,
    makeCacheableSignalKeyStore,
    delay,
    Browsers
} = require('@whiskeysockets/baileys');

const pino = require('pino');
const fs = require('fs');
const path = require('path');
const QRCode = require('qrcode');
const { Queue, Worker } = require('bullmq'); 
const IORedis = require('ioredis'); 

// Configurações de Ambiente
const SESSION_DIR = process.env.SESSION_DIR || 'auth_sessions';
const MEDIA_DIR = process.env.MEDIA_DIR || 'public/uploads';

// Configuração Redis Centralizada
const redisConfig = {
    host: process.env.REDIS_HOST || '127.0.0.1',
    port: Number(process.env.REDIS_PORT) || 6379,
    password: process.env.REDIS_PASSWORD || undefined, // undefined evita enviar string vazia/null
    maxRetriesPerRequest: null,
    enableReadyCheck: false
};

class SessionManager {
    constructor(io, db) {
        this.io = io;
        this.db = db;
        
        this.sessions = new Map();
        this.qrCodes = new Map();
        this.reconnectAttempts = new Map();
        
        this.MAX_RECONNECT_RETRIES = 5;
        this.RECONNECT_INTERVAL_BASE = 2000;
        
        this.rootDir = process.cwd();
        this.authDir = path.join(this.rootDir, SESSION_DIR);
        this.uploadDir = path.join(this.rootDir, MEDIA_DIR);

        this._initializeDirectories();
        
        // Logger silencioso para produção
        this.logger = pino({ level: process.env.LOG_LEVEL || 'error' });

        // Debug da Configuração Redis (Oculta senha real)
        console.log('🔌 [Redis Config] Host:', redisConfig.host, '| Auth:', redisConfig.password ? 'Sim (********)' : 'Não');

        // ============================================
        // INICIALIZAÇÃO DE FILAS (BULLMQ)
        // ============================================
        this.queueName = 'whatsapp-messages';
        
        // CORREÇÃO: Passamos o objeto de configuração, não a instância.
        // O BullMQ gerencia suas próprias conexões autenticadas.
        this.messageQueue = new Queue(this.queueName, { 
            connection: redisConfig,
            defaultJobOptions: {
                attempts: 3,
                backoff: { type: 'exponential', delay: 1000 },
                removeOnComplete: true,
                removeOnFail: 500
            }
        });

        this.messageWorker = null;
    }

    _initializeDirectories() {
        if (!fs.existsSync(this.authDir)) fs.mkdirSync(this.authDir, { recursive: true });
        if (!fs.existsSync(this.uploadDir)) fs.mkdirSync(this.uploadDir, { recursive: true });
    }

    initBackgroundJobs() {
        console.log('⚙️ [SessionManager] Iniciando Workers e Jobs...');
        
        // Job de Inatividade
        setInterval(() => this.verificarInatividade(), 60000);

        // Inicializa Worker
        this._initMessageWorker();
    }

    _initMessageWorker() {
        console.log(`🚀 [Worker] Iniciando processador da fila: ${this.queueName}`);
        
        // CORREÇÃO: Passamos redisConfig aqui também
        this.messageWorker = new Worker(this.queueName, async (job) => {
            const { empresaId, messageData } = job.data;
            
            const sock = this.sessions.get(empresaId);
            if (!sock) {
                // Silenciosamente falha se desconectado, ou lança erro para retry
                // throw new Error(`Sessão ${empresaId} offline`);
                return; 
            }

            await this.processarMensagemIndividual(empresaId, messageData, sock);

        }, { 
            connection: redisConfig,
            concurrency: 10,
            limiter: { max: 50, duration: 1000 }
        });

        this.messageWorker.on('failed', (job, err) => {
            console.error(`❌ Job ${job.id} falhou: ${err.message}`);
        });
        
        // Listener para erros de conexão do Redis no Worker
        this.messageWorker.on('error', (err) => {
            console.error('❌ [Worker Redis Error]', err.message);
        });
    }

    // ============================================
    // LÓGICA DE SESSÃO
    // ============================================

    async startSession(empresaId) {
        // console.log(`Iniciando sessão ${empresaId}...`);
        
        if (this.sessions.has(empresaId)) {
            const sock = this.sessions.get(empresaId);
            if (sock.user) return sock;
            this.sessions.delete(empresaId);
        }

        const authPath = path.join(this.authDir, `empresa_${empresaId}`);
        if (!fs.existsSync(authPath)) fs.mkdirSync(authPath, { recursive: true });

        try {
            const { state, saveCreds } = await useMultiFileAuthState(authPath);
            const { version } = await fetchLatestBaileysVersion();
            
            const sock = makeWASocket({
                version,
                logger: this.logger,
                printQRInTerminal: false,
                auth: {
                    creds: state.creds,
                    keys: makeCacheableSignalKeyStore(state.keys, this.logger),
                },
                browser: Browsers.ubuntu('Chrome'), 
                generateHighQualityLinkPreview: true,
                syncFullHistory: false,
                markOnlineOnConnect: true,
                connectTimeoutMs: 60000,
                keepAliveIntervalMs: 30000,
            });

            this.sessions.set(empresaId, sock);

            sock.ev.on('creds.update', saveCreds);
            sock.ev.on('connection.update', (update) => this._handleConnectionUpdate(empresaId, update));
            sock.ev.on('messages.upsert', (update) => this._handleMessagesUpsert(empresaId, update));

            return sock;

        } catch (error) {
            console.error(`❌ [Empresa ${empresaId}] Falha crítica:`, error.message);
            await this._updateDbStatus(empresaId, 'ERRO');
            throw error;
        }
    }

    async _handleConnectionUpdate(empresaId, update) {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            try {
                const qrBase64 = await QRCode.toDataURL(qr, { margin: 2, scale: 10 });
                this.qrCodes.set(empresaId, qrBase64);
                this._emitToRoom(empresaId, 'qr_code', { qr: qrBase64, empresaId });
                await this._updateDbStatus(empresaId, 'AGUARDANDO_QR');
            } catch (err) { console.error(err); }
        }

        if (connection === 'open') {
            console.log(`✅ [Empresa ${empresaId}] Conectado`);
            this.qrCodes.delete(empresaId);
            this.reconnectAttempts.delete(empresaId);
            
            const phoneNumber = this.sessions.get(empresaId)?.user?.id.split(':')[0];
            this._emitToRoom(empresaId, 'status_conn', { status: 'online' });
            this._emitToRoom(empresaId, 'whatsapp_ready', { numero: phoneNumber, status: 'CONECTADO' });
            await this._updateDbStatus(empresaId, 'CONECTADO', phoneNumber);
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut && statusCode !== 403;
            
            this.sessions.delete(empresaId);
            this.qrCodes.delete(empresaId);
            this._emitToRoom(empresaId, 'status_conn', { status: 'offline' });

            if (shouldReconnect) {
                this._handleReconnection(empresaId);
            } else {
                await this.deleteSession(empresaId);
                await this._updateDbStatus(empresaId, 'DESCONECTADO');
            }
        }
    }

    _handleReconnection(empresaId) {
        const attempts = (this.reconnectAttempts.get(empresaId) || 0) + 1;
        if (attempts > this.MAX_RECONNECT_RETRIES) {
            this._updateDbStatus(empresaId, 'ERRO');
            return;
        }
        this.reconnectAttempts.set(empresaId, attempts);
        const delayMs = Math.min(this.RECONNECT_INTERVAL_BASE * Math.pow(2, attempts - 1), 60000);
        setTimeout(() => this.startSession(empresaId), delayMs);
    }

    // ============================================
    // PRODUCER (ADD TO QUEUE)
    // ============================================

    async _handleMessagesUpsert(empresaId, { messages, type }) {
        if (type !== 'notify') return;

        for (const msg of messages) {
            if (!msg.message || msg.key.fromMe || msg.key.remoteJid === 'status@broadcast') continue;

            // Envia para a fila Redis ao invés de processar direto
            this.messageQueue.add('process-message', {
                empresaId,
                messageData: msg,
                timestamp: Date.now()
            }, {
                jobId: `${empresaId}_${msg.key.id}`,
                removeOnComplete: true
            });
        }
    }

    // ============================================
    // CONSUMER (WORKER PROCESS)
    // ============================================

    async processarMensagemIndividual(empresaId, msg, sock) {
        const remoteJid = msg.key.remoteJid;
        const pushName = msg.pushName || remoteJid.split('@')[0];
        
        const { tipo, conteudo, urlMidia } = await this._extractMessageContent(msg, empresaId);

        if (!conteudo && !urlMidia) return;

        await this._upsertContato(empresaId, remoteJid, pushName, sock);

        await this.db.execute(
            `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo, url_midia, created_at) VALUES (?, ?, 0, ?, ?, ?, NOW())`,
            [empresaId, remoteJid, tipo, conteudo, urlMidia]
        );

        this._emitToRoom(empresaId, 'nova_mensagem', {
            remoteJid,
            fromMe: false,
            conteudo,
            tipo,
            urlMidia,
            timestamp: Date.now() / 1000,
            pushName
        });

        await this._executarLogicaNegocio(empresaId, remoteJid, conteudo, tipo, pushName, sock);
    }

    async _extractMessageContent(msg, empresaId) {
        let m = msg.message;
        if (m.viewOnceMessageV2?.message) m = m.viewOnceMessageV2.message;
        if (m.viewOnceMessage?.message) m = m.viewOnceMessage.message;

        let tipo = 'texto';
        let conteudo = '';
        let urlMidia = null;

        if (m.conversation) {
            conteudo = m.conversation;
        } else if (m.extendedTextMessage) {
            conteudo = m.extendedTextMessage.text;
        } else if (m.imageMessage || m.videoMessage || m.audioMessage || m.documentMessage || m.stickerMessage) {
            tipo = Object.keys(m)[0].replace('Message', '');
            if (tipo === 'document') tipo = 'documento';
            
            conteudo = m[Object.keys(m)[0]].caption || (tipo === 'audio' ? '[Áudio]' : `[${tipo}]`);
            urlMidia = await this.salvarMidia({ message: m }, empresaId);
        }

        return { tipo, conteudo, urlMidia };
    }

    async _executarLogicaNegocio(empresaId, remoteJid, conteudo, tipo, nomeCliente, sock) {
        const [rows] = await this.db.execute(
            'SELECT setor_id, status_atendimento, atendente_id FROM contatos WHERE empresa_id = ? AND telefone = ? LIMIT 1',
            [empresaId, remoteJid]
        );
        const contato = rows[0];

        if (!contato) return;

        // Se estiver em atendimento, ignora
        if (['ATENDENDO', 'FILA'].includes(contato.status_atendimento)) return;

        if (contato.status_atendimento === 'AGUARDANDO_AVALIACAO') {
            // Lógica de avaliação
            return; 
        }

        // Recupera dados da empresa
        const [empRows] = await this.db.execute(
            "SELECT mensagens_padrao, msg_ausencia FROM empresas WHERE id = ?", 
            [empresaId]
        );
        
        if (contato.status_atendimento === 'ABERTO') {
            // Chama lógica de Menu/Boas vindas (Placeholder)
        }
    }

    async verificarInatividade() {
        const sql = `
            SELECT c.id, c.empresa_id, c.telefone 
            FROM contatos c
            INNER JOIN (
                SELECT empresa_id, remote_jid, MAX(created_at) as last_msg_time
                FROM mensagens
                GROUP BY empresa_id, remote_jid
            ) m ON c.empresa_id = m.empresa_id AND c.telefone = m.remote_jid
            WHERE c.status_atendimento IN ('ATENDENDO', 'FILA')
            AND m.last_msg_time < DATE_SUB(NOW(), INTERVAL 30 MINUTE)
        `;

        try {
            const [rows] = await this.db.execute(sql);
            if (rows.length > 0) {
                for (const contato of rows) {
                    await this.encerrarPorInatividade(contato);
                }
            }
        } catch (e) {
            console.error('[Job Inatividade] Erro SQL:', e.message);
        }
    }

    async encerrarPorInatividade(contato) {
        const sock = this.sessions.get(contato.empresa_id);
        const msg = '⚠️ *Atendimento encerrado por inatividade.*';
        if (sock) await sock.sendMessage(contato.telefone, { text: msg });
        
        await this.db.execute(
            "UPDATE contatos SET status_atendimento = 'ABERTO', setor_id = NULL, atendente_id = NULL WHERE id = ?",
            [contato.id]
        );
        this._emitToRoom(contato.empresa_id, 'atualizar_lista', { action: 'inatividade' });
    }

    async _upsertContato(empresaId, remoteJid, pushName, sock) {
        let fotoPerfil = null;
        try {
            fotoPerfil = await sock.profilePictureUrl(remoteJid, 'image');
        } catch {}

        const sql = `
            INSERT INTO contatos (empresa_id, telefone, nome, foto_perfil, status_atendimento, created_at, ultima_msg)
            VALUES (?, ?, ?, ?, 'ABERTO', NOW(), NOW())
            ON DUPLICATE KEY UPDATE 
                nome = VALUES(nome),
                foto_perfil = IFNULL(VALUES(foto_perfil), foto_perfil),
                ultima_msg = NOW()
        `;
        await this.db.execute(sql, [empresaId, remoteJid, pushName, fotoPerfil]);
    }

    async salvarMidia(msg, empresaId) {
        try {
            const buffer = await downloadMediaMessage(msg, 'buffer', {}, { logger: this.logger });
            
            const m = msg.message;
            const type = Object.keys(m)[0];
            const extMap = { 'imageMessage': 'jpg', 'videoMessage': 'mp4', 'audioMessage': 'mp3', 'documentMessage': 'bin', 'stickerMessage': 'webp' };
            const ext = extMap[type] || 'bin';
            
            const dateDir = new Date().toISOString().split('T')[0]; 
            const empresaDir = path.join(this.uploadDir, `empresa_${empresaId}`, dateDir);
            
            if (!fs.existsSync(empresaDir)) fs.mkdirSync(empresaDir, { recursive: true });

            const fileName = `${Date.now()}_${Math.random().toString(36).substring(7)}.${ext}`;
            const filePath = path.join(empresaDir, fileName);
            
            await fs.promises.writeFile(filePath, buffer);
            return `/uploads/empresa_${empresaId}/${dateDir}/${fileName}`;
        } catch (error) {
            console.error('[Media] Erro ao salvar:', error.message);
            return null;
        }
    }

    async deleteSession(empresaId) {
        if (this.sessions.has(empresaId)) {
            const sock = this.sessions.get(empresaId);
            sock.end(undefined);
            this.sessions.delete(empresaId);
        }
        const pathAuth = path.join(this.authDir, `empresa_${empresaId}`);
        if (fs.existsSync(pathAuth)) fs.rmSync(pathAuth, { recursive: true, force: true });
        return true;
    }

    async reconnectAllSessions() {
        // Implementar se necessário auto-start
    }

    _updateDbStatus(empresaId, status, numero = null) {
        const params = [status, empresaId];
        let sql = 'UPDATE empresas SET whatsapp_status = ?, whatsapp_updated_at = NOW()';
        if (numero) {
            sql = 'UPDATE empresas SET whatsapp_status = ?, whatsapp_numero = ?, whatsapp_updated_at = NOW()';
            params.splice(1, 0, numero);
        }
        sql += ' WHERE id = ?';
        return this.db.execute(sql, params).catch(e => console.error('DB Error:', e));
    }

    _emitToRoom(empresaId, event, data) {
        if (this.io) this.io.to(`empresa_${empresaId}`).emit(event, data);
    }
}

module.exports = SessionManager;