// ============================================
// Arquivo: controllers/WhatsAppController.js
// Descrição: Controlador de envio de mensagens do WhatsApp
// ============================================

const fs = require('fs');
const path = require('path');

class WhatsAppController {
    constructor(db, sessionManager) { 
        this.db = db; 
        this.sm = sessionManager; 
    }

    async startSession(req, res) {
        try { 
            await this.sm.startSession(req.empresaId); 
            res.json({success:true}); 
        } catch(e) { 
            res.status(500).json({ error: e.message }); 
        }
    }

    // --- FUNÇÃO DE LOGOUT ---
    async logoutSession(req, res) {
        try {
            await this.sm.deleteSession(req.empresaId);
            res.json({ success: true });
        } catch (e) {
            res.status(500).json({ error: e.message });
        }
    }

    async getNomeAtendente(userId) {
        if (!userId) return null;
        try {
            const [rows] = await this.db.execute('SELECT nome FROM usuarios_painel WHERE id = ?', [userId]);
            return rows.length > 0 ? rows[0].nome : null;
        } catch (e) { return null; }
    }

    // ENVIO DE TEXTO COM SINCRONIZAÇÃO SOCKET
    async sendText(req, res) {
        const { telefone, texto } = req.body;
        const userId = req.headers['x-user-id'];

        const sock = this.sm.getSession(req.empresaId);
        if(!sock) return res.status(400).json({error:'WhatsApp Offline'});

        try {
            const jid = telefone.includes('@') ? telefone : `${telefone}@s.whatsapp.net`;
            const nomeAtendente = await this.getNomeAtendente(userId);
            let textoFinal = texto;

            // Assinatura do atendente (Opcional, pode ser removida se desejar)
            // if (nomeAtendente) {
            //     textoFinal = `${texto}\n\n~ *${nomeAtendente}*`;
            // }

            await sock.sendMessage(jid, { text: textoFinal });

            // Salvar BD
            await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`, [req.empresaId, jid, textoFinal]);
            
            // Garantir que o contato existe
            await this.db.execute(`INSERT IGNORE INTO contatos (empresa_id, telefone, nome) VALUES (?, ?, ?)`, [req.empresaId, jid, jid.split('@')[0]]);

            // Sincronizar Frontend usando o helper do SessionManager para consistência
            this.sm.emitirMensagemEnviada(req.empresaId, jid, textoFinal, 'texto', null, true);

            res.json({success:true});
        } catch(e) {
            console.error('Erro no envio de texto:', e);
            res.status(500).json({ error: 'Falha no envio da mensagem' });
        }
    }

    // ENVIO DE MÍDIA (ÁUDIO/IMAGEM/ETC) COM SINCRONIZAÇÃO SOCKET
    async sendMedia(req, res) {
        const { telefone, caption } = req.body;
        const userId = req.headers['x-user-id'];

        const sock = this.sm.getSession(req.empresaId);
        if (!sock) return res.status(400).json({ error: 'WhatsApp Offline' });
        if (!req.file) return res.status(400).json({ error: 'Nenhum arquivo enviado' });

        try {
            const jid = telefone.includes('@') ? telefone : `${telefone}@s.whatsapp.net`;
            
            // Caminho relativo para o frontend/banco
            const urlRelativa = `/uploads/empresa_${req.empresaId}/${req.file.filename}`;
            
            // Caminho absoluto para leitura do arquivo
            const filePath = req.file.path;
            const mime = req.file.mimetype;

            const nomeAtendente = await this.getNomeAtendente(userId);
            let captionFinal = caption || '';

            // Assinatura (apenas para não-áudios)
            // if (nomeAtendente && !mime.startsWith('audio')) {
            //     captionFinal = captionFinal ? `${captionFinal}\n\n~ *${nomeAtendente}*` : `~ *${nomeAtendente}*`;
            // }

            let msgSend = {};
            let tipo = 'documento';

            // Lê o arquivo para buffer (mais seguro para o Baileys)
            const fileBuffer = fs.readFileSync(filePath);

            if(mime.startsWith('image')) {
                msgSend = { image: fileBuffer, caption: captionFinal };
                tipo = 'imagem';
            } else if(mime.startsWith('video')) {
                msgSend = { video: fileBuffer, caption: captionFinal };
                tipo = 'video';
            } else if(mime.startsWith('audio')) {
                // Para áudio (PTT - Push To Talk), precisamos enviar como audio/mp4 e ptt: true
                // O Multer pode salvar como .webm ou .mp3, o Baileys converte se possível, 
                // mas é ideal que o frontend envie blob compatível ou o backend converta (ffmpeg).
                // Assumindo que o frontend envia algo "tocável".
                
                msgSend = { 
                    audio: fileBuffer, 
                    mimetype: 'audio/mp4', // Padrão WhatsApp
                    ptt: true // Envia como nota de voz
                };
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

            // Envia para o WhatsApp
            await sock.sendMessage(jid, msgSend);

            // Conteúdo para salvar no banco
            const conteudoSalvo = tipo === 'audio' ? (caption || 'Áudio enviado') : captionFinal;

            // Salva no Banco de Dados
            await this.db.execute(
                `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo, url_midia) VALUES (?, ?, 1, ?, ?, ?)`, 
                [req.empresaId, jid, tipo, conteudoSalvo, urlRelativa]
            );

            // Sincroniza Frontend
            this.sm.emitirMensagemEnviada(req.empresaId, jid, conteudoSalvo, tipo, urlRelativa, true);

            res.json({ success: true, url: urlRelativa });
        } catch (e) {
            console.error('Erro no envio de mídia:', e);
            res.status(500).json({ error: e.message });
        }
    }
}

module.exports = WhatsAppController;