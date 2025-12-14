class WhatsAppController {
    constructor(db, sessionManager) { this.db = db; this.sm = sessionManager; }

    async startSession(req, res) {
        try { await this.sm.startSession(req.empresaId); res.json({success:true}); }
        catch(e) { res.status(500).json({ error: e.message }); }
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
        if(!sock) return res.status(400).json({error:'Offline'});

        try {
            const jid = telefone.includes('@') ? telefone : `${telefone}@s.whatsapp.net`;
            const nomeAtendente = await this.getNomeAtendente(userId);
            let textoFinal = texto;

            if (nomeAtendente) {
                textoFinal = `${texto}\n\n~ *${nomeAtendente}*`;
            }

            await sock.sendMessage(jid, { text: textoFinal });

            // Salvar BD
            await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`, [req.empresaId, jid, textoFinal]);
            await this.db.execute(`INSERT IGNORE INTO contatos (empresa_id, telefone, nome) VALUES (?, ?, ?)`, [req.empresaId, jid, jid.split('@')[0]]);

            // Sincronizar Frontend
            this.sm.io.to(`empresa_${req.empresaId}`).emit('nova_mensagem', {
                remoteJid: jid,
                fromMe: true,
                conteudo: textoFinal,
                tipo: 'texto',
                timestamp: Date.now()/1000
            });

            res.json({success:true});
        } catch(e) {
            console.error(e);
            res.status(500).json({ error: 'Falha no envio' });
        }
    }

    // ENVIO DE MÍDIA COM SINCRONIZAÇÃO SOCKET
    async sendMedia(req, res) {
        const { telefone, caption } = req.body;
        const userId = req.headers['x-user-id'];

        const sock = this.sm.getSession(req.empresaId);
        if (!sock || !req.file) return res.status(400).json({ error: 'Erro dados' });

        try {
            const jid = telefone.includes('@') ? telefone : `${telefone}@s.whatsapp.net`;
            const url = `/uploads/empresa_${req.empresaId}/${req.file.filename}`;
            const filePath = req.file.path;
            const mime = req.file.mimetype;

            const nomeAtendente = await this.getNomeAtendente(userId);
            let captionFinal = caption || '';

            if (nomeAtendente) {
                captionFinal = captionFinal ? `${captionFinal}\n\n~ *${nomeAtendente}*` : `~ *${nomeAtendente}*`;
            }

            let msgSend = {};
            let tipo = 'documento';

            if(mime.startsWith('image')) {
                msgSend = { image: { url: filePath }, caption: captionFinal };
                tipo = 'imagem';
            } else if(mime.startsWith('video')) {
                msgSend = { video: { url: filePath }, caption: captionFinal };
                tipo = 'video';
            } else if(mime.startsWith('audio')) {
                msgSend = { audio: { url: filePath }, mimetype: mime };
                tipo = 'audio';
            } else {
                msgSend = { document: { url: filePath }, mimetype: mime, fileName: req.file.originalname, caption: captionFinal };
                tipo = 'documento';
            }

            await sock.sendMessage(jid, msgSend);

            const conteudoSalvo = tipo === 'audio' ? (caption || req.file.originalname) : captionFinal;

            await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo, url_midia) VALUES (?, ?, 1, ?, ?, ?)`, [req.empresaId, jid, tipo, conteudoSalvo, url]);

            // Sincronizar Frontend
            this.sm.io.to(`empresa_${req.empresaId}`).emit('nova_mensagem', {
                remoteJid: jid,
                fromMe: true,
                conteudo: conteudoSalvo,
                urlMidia: url,
                tipo: tipo,
                timestamp: Date.now()/1000
            });

            res.json({ success: true, url });
        } catch (e) {
            console.error(e);
            res.status(500).json({ error: e.message });
        }
    }
}
module.exports = WhatsAppController;