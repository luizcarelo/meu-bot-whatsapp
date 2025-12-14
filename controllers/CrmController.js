class CrmController {
    constructor(db, sessionManager) {
        this.db = db;
        this.sm = sessionManager;
    }

    emitirAtualizacao(empresaId, dados) {
        if (this.sm && this.sm.io) {
            this.sm.io.to(`empresa_${empresaId}`).emit('atualizar_lista', dados);
        }
    }

    // --- MENSAGENS E CONTATOS ---

    async getMensagens(req, res) {
        const { telefone } = req.params;
        const remoteJid = telefone.includes('@') ? telefone : `${telefone}@s.whatsapp.net`;
        try {
            const [rows] = await this.db.execute(
                'SELECT * FROM mensagens WHERE empresa_id = ? AND remote_jid = ? ORDER BY data_hora ASC',
                [req.empresaId, remoteJid]
            );
            res.json(rows);
        } catch(e) {
            res.status(500).json({error: 'Erro ao buscar mensagens'});
        }
    }

    async createContato(req, res) {
        let { nome, telefone } = req.body;
        const atendenteId = req.headers['x-user-id'];

        telefone = telefone.replace(/\D/g, '');
        if (telefone.length <= 11 && !telefone.startsWith('55')) {
            telefone = '55' + telefone;
        }
        const remoteJid = `${telefone}@s.whatsapp.net`;

        try {
            const [existe] = await this.db.execute('SELECT id FROM contatos WHERE empresa_id = ? AND telefone = ?', [req.empresaId, remoteJid]);

            if (existe.length > 0) {
                await this.db.execute(
                    `UPDATE contatos SET nome = ?, status_atendimento = 'ATENDENDO', atendente_id = ? WHERE id = ?`,
                    [nome, atendenteId, existe[0].id]
                );
            } else {
                await this.db.execute(
                    `INSERT INTO contatos (empresa_id, telefone, nome, status_atendimento, atendente_id) VALUES (?, ?, ?, 'ATENDENDO', ?)`,
                    [req.empresaId, remoteJid, nome, atendenteId]
                );
            }

            await this.db.execute(
                `INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'sistema', 'Iniciou uma nova conversa.')`,
                [req.empresaId, remoteJid]
            );

            this.emitirAtualizacao(req.empresaId, { action: 'create_contato', telefone: remoteJid });
            res.json({ success: true, telefone: remoteJid });

        } catch (e) {
            res.status(500).json({ error: 'Erro ao criar contato.' });
        }
    }


    async getContatos(req, res) {
        const userId = req.headers['x-user-id'];
        const statusFiltro = req.query.status;

        try {
            const [users] = await this.db.execute(
                'SELECT is_admin FROM usuarios_painel WHERE id = ?',
                [userId]
            );
            const isAdmin = users[0] && (users[0].is_admin == 1 || users[0].is_admin === true);

            // Query otimizada para buscar contatos e suas tags agregadas
            // O uso de COALESCE garante que retorne '[]' em vez de null se não houver tags
            let sql = `
                SELECT c.*,
                    (SELECT conteudo FROM mensagens m WHERE m.remote_jid = c.telefone AND m.empresa_id = c.empresa_id ORDER BY id DESC LIMIT 1) as ultima_msg,
                    (SELECT data_hora FROM mensagens m WHERE m.remote_jid = c.telefone AND m.empresa_id = c.empresa_id ORDER BY id DESC LIMIT 1) as ordenacao,
                    s.nome as nome_setor,
                    s.cor as cor_setor,
                    u.nome as nome_atendente,
                    COALESCE(
                        (
                            SELECT JSON_ARRAYAGG(JSON_OBJECT('id', e.id, 'nome', e.nome, 'cor', e.cor))
                            FROM contatos_etiquetas ce
                            JOIN etiquetas e ON ce.etiqueta_id = e.id
                            WHERE ce.contato_id = c.id
                        ), 
                    '[]') as tags
                FROM contatos c
                LEFT JOIN setores s ON c.setor_id = s.id
                LEFT JOIN usuarios_painel u ON c.atendente_id = u.id
                WHERE c.empresa_id = ?
            `;
            
            const params = [req.empresaId];

            if (statusFiltro === 'meus') {
                sql += ` AND c.status_atendimento = 'ATENDENDO' AND c.atendente_id = ?`;
                params.push(userId);
            } else if (statusFiltro === 'fila') {
                sql += ` AND c.status_atendimento = 'FILA'`;
                if (!isAdmin) {
                    sql += ` AND c.setor_id IN (SELECT setor_id FROM usuarios_setores WHERE usuario_id = ?)`;
                    params.push(userId);
                }
            } else if (statusFiltro === 'todos') {
                if (isAdmin) {
                    sql += ` AND c.status_atendimento IN ('ATENDENDO','FILA','ABERTO')`;
                } else {
                    sql += ` AND (
                        (c.status_atendimento = 'FILA' AND c.setor_id IN (SELECT setor_id FROM usuarios_setores WHERE usuario_id = ?))
                        OR
                        (c.status_atendimento = 'ATENDENDO' AND c.atendente_id = ?)
                    )`;
                    params.push(userId, userId);
                }
            }

            // Ordenação: Conversas com mensagens primeiro, depois pela data da última mensagem
            sql += ` ORDER BY CASE WHEN ordenacao IS NULL THEN 0 ELSE 1 END, ordenacao DESC`;

            const [rows] = await this.db.execute(sql, params);
            res.json(rows);
        } catch (e) {
            console.error('Erro ao buscar contatos:', e);
            res.status(500).json({ error: 'Erro ao buscar contatos' });
        }
    }

    // --- FLUXO DE ATENDIMENTO ---

    async assumirAtendimento(req, res) {
        const { telefone } = req.body;
        const atendenteId = req.headers['x-user-id'];
        try {
            await this.db.execute(
                `UPDATE contatos SET status_atendimento = 'ATENDENDO', atendente_id = ? WHERE empresa_id = ? AND telefone = ?`,
                [atendenteId, req.empresaId, telefone]
            );

            // Notifica no chat
            const sock = this.sm.getSession(req.empresaId);
            if(sock) {
                const [u] = await this.db.execute('SELECT nome FROM usuarios_painel WHERE id = ?', [atendenteId]);
                const nome = u[0]?.nome || 'Um atendente';
                await sock.sendMessage(telefone, { text: `✅ *${nome}* iniciou o atendimento.` });
            }

            this.emitirAtualizacao(req.empresaId, { action: 'assumir', telefone });
            res.json({ success: true });
        } catch(e) { res.status(500).json({error: e.message}); }
    }

    async transferirAtendimento(req, res) {
        const { telefone, setorId } = req.body;
        try {
            const [setor] = await this.db.execute('SELECT mensagem_saudacao, nome FROM setores WHERE id = ?', [setorId]);
            const msg = setor[0]?.mensagem_saudacao || `Transferindo para ${setor[0]?.nome || 'o setor'}.`;

            const sock = this.sm.getSession(req.empresaId);
            if (sock) {
                await sock.sendMessage(telefone, { text: `🔄 *Transferido:* ${msg}` });
            }

            await this.db.execute(
                `UPDATE contatos SET status_atendimento = 'FILA', setor_id = ?, atendente_id = NULL WHERE empresa_id = ? AND telefone = ?`,
                [setorId, req.empresaId, telefone]
            );

            await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`, [req.empresaId, telefone, `🔄 *Transferido para setor:* ${setor[0]?.nome}`]);

            this.emitirAtualizacao(req.empresaId, { action: 'transferir', telefone });
            res.json({ success: true });
        } catch(e) { res.status(500).json({error: e.message}); }
    }

    async transferirParaUsuario(req, res) {
        const { telefone, usuarioId } = req.body;
        try {
            const [user] = await this.db.execute('SELECT nome FROM usuarios_painel WHERE id = ?', [usuarioId]);
            const nomeUser = user[0]?.nome || 'Outro atendente';

            const sock = this.sm.getSession(req.empresaId);
            if (sock) {
                await sock.sendMessage(telefone, { text: `🔄 Seu atendimento foi transferido para *${nomeUser}*.` });
            }

            await this.db.execute(
                `UPDATE contatos SET status_atendimento = 'ATENDENDO', atendente_id = ? WHERE empresa_id = ? AND telefone = ?`,
                [usuarioId, req.empresaId, telefone]
            );

            await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`, [req.empresaId, telefone, `🔄 *Transferido para usuário:* ${nomeUser}`]);

            this.emitirAtualizacao(req.empresaId, { action: 'transferir_user', telefone });
            res.json({ success: true });
        } catch(e) { res.status(500).json({error: e.message}); }
    }

    async encerrarAtendimento(req, res) {
        const { telefone } = req.body;
        try {
            const [empresa] = await this.db.execute('SELECT msg_avaliacao FROM empresas WHERE id = ?', [req.empresaId]);
            const padrao = `✅ *Atendimento finalizado pelo operador.*\n\nPor favor, avalie o nosso atendimento de 1 a 5:\n\n1️⃣ - Muito Insatisfeito\n2️⃣ - Insatisfeito\n3️⃣ - Normal\n4️⃣ - Satisfeito\n5️⃣ - Muito Satisfeito`;
            const msgEncerramento = empresa[0].msg_avaliacao || padrao;

            await this.db.execute(
                `UPDATE contatos SET status_atendimento = 'AGUARDANDO_AVALIACAO' WHERE empresa_id = ? AND telefone = ?`,
                [req.empresaId, telefone]
            );

            const sock = this.sm.getSession(req.empresaId);
            if (sock) {
                await sock.sendMessage(telefone, { text: msgEncerramento });
            }

            await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`, [req.empresaId, telefone, msgEncerramento]);
            this.emitirAtualizacao(req.empresaId, { action: 'encerrar', telefone });
            res.json({ success: true, mensagem: msgEncerramento });
        } catch(e) { res.status(500).json({error: e.message}); }
    }

    // --- CONFIGURAÇÃO ---

    async getConfig(req, res) {
        try {
            const [rows] = await this.db.execute(
                'SELECT nome, nome_sistema, logo_url, cor_primaria, mensagens_padrao, msg_ausencia, msg_avaliacao, horario_inicio, horario_fim, dias_funcionamento, welcome_media_url, welcome_media_type, whatsapp_numero, whatsapp_status, whatsapp_updated_at, openai_key, openai_prompt, openai_ativo FROM empresas WHERE id = ?',
                [req.empresaId]
            );
            const dados = rows[0];
            dados.nome_exibicao = dados.nome_sistema || dados.nome;
            res.json(dados);
        } catch(e) { res.status(500).json({error: e.message}); }
    }

    async updateConfig(req, res) {
        const { nome, cor, mensagens, msg_ausencia, msg_avaliacao, horario_inicio, horario_fim, dias } = req.body;
        let updateFields = [];
        let updateValues = [];

        if(nome) { updateFields.push('nome_sistema = ?'); updateValues.push(nome); }
        if(cor) { updateFields.push('cor_primaria = ?'); updateValues.push(cor); }
        if(mensagens) { updateFields.push('mensagens_padrao = ?'); updateValues.push(mensagens); }
        if(msg_ausencia !== undefined) { updateFields.push('msg_ausencia = ?'); updateValues.push(msg_ausencia); }
        if(msg_avaliacao !== undefined) { updateFields.push('msg_avaliacao = ?'); updateValues.push(msg_avaliacao); }

        if(horario_inicio) { updateFields.push('horario_inicio = ?'); updateValues.push(horario_inicio); }
        if(horario_fim) { updateFields.push('horario_fim = ?'); updateValues.push(horario_fim); }
        if(dias) { updateFields.push('dias_funcionamento = ?'); updateValues.push(dias); }

        if(req.files) {
            if(req.files['logo']) {
                updateFields.push('logo_url = ?');
                updateValues.push(`/uploads/empresa_${req.empresaId}/${req.files['logo'][0].filename}`);
            }
            if(req.files['welcome_media']) {
                const file = req.files['welcome_media'][0];
                updateFields.push('welcome_media_url = ?');
                updateValues.push(`/uploads/empresa_${req.empresaId}/${file.filename}`);
                let type = 'documento';
                if(file.mimetype.startsWith('image')) type = 'imagem';
                else if(file.mimetype.startsWith('video')) type = 'video';
                else if(file.mimetype.startsWith('audio')) type = 'audio';
                updateFields.push('welcome_media_type = ?');
                updateValues.push(type);
            }
        }

        if(updateFields.length === 0) return res.json({success:true});

        const sql = `UPDATE empresas SET ${updateFields.join(', ')} WHERE id = ?`;
        updateValues.push(req.empresaId);

        try {
            await this.db.execute(sql, updateValues);
            res.json({ success: true });
        } catch(e) { res.status(500).json({error: e.message}); }
    }

    async updateConfigIA(req, res) {
        const { openai_key, openai_prompt, openai_ativo } = req.body;
        try {
            await this.db.execute(
                'UPDATE empresas SET openai_key = ?, openai_prompt = ?, openai_ativo = ? WHERE id = ?',
                [openai_key, openai_prompt, openai_ativo ? 1 : 0, req.empresaId]
            );
            res.json({ success: true });
        } catch(e) { res.status(500).json({error: e.message}); }
    }

    async sendBroadcast(req, res) {
        const { mensagem } = req.body;
        if (!mensagem) return res.status(400).json({ error: 'Mensagem vazia' });

        try {
            const [contatos] = await this.db.execute(
                'SELECT telefone FROM contatos WHERE empresa_id = ?',
                [req.empresaId]
            );

            const sock = this.sm.getSession(req.empresaId);
            if (!sock) return res.status(400).json({ error: 'WhatsApp desconectado' });

            let enviados = 0;
            for (const c of contatos) {
                const delay = Math.floor(Math.random() * 2000) + 1000;
                await new Promise(r => setTimeout(r, delay));

                await sock.sendMessage(c.telefone, { text: mensagem });
                await this.db.execute(`INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'texto', ?)`, [req.empresaId, c.telefone, mensagem]);
                enviados++;
            }

            res.json({ success: true, enviados, total: contatos.length });
        } catch(e) { res.status(500).json({ error: e.message }); }
    }

    // --- SETORES ---

    async getSetores(req, res) {
        const [rows] = await this.db.execute('SELECT * FROM setores WHERE empresa_id = ? ORDER BY ordem ASC, id ASC', [req.empresaId]);
        res.json(rows);
    }

    async createSetor(req, res) {
        const { nome, mensagem, cor } = req.body;
        let mediaUrl = null;
        let mediaType = null;

        if(req.file) {
            mediaUrl = `/uploads/empresa_${req.empresaId}/${req.file.filename}`;
            if(req.file.mimetype.startsWith('image')) mediaType = 'imagem';
            else if(req.file.mimetype.startsWith('video')) mediaType = 'video';
            else if(req.file.mimetype.startsWith('audio')) mediaType = 'audio';
            else mediaType = 'documento';
        }

        await this.db.execute(
            'INSERT INTO setores (empresa_id, nome, mensagem_saudacao, padrao, media_url, media_type, cor) VALUES (?, ?, ?, 0, ?, ?, ?)',
            [req.empresaId, nome, mensagem, mediaUrl, mediaType, cor || '#cbd5e1']
        );
        res.json({success:true});
    }

    async updateSetor(req, res) {
        const { id } = req.params;
        const { nome, mensagem, cor } = req.body;
        let sql = 'UPDATE setores SET nome = ?, mensagem_saudacao = ?, cor = ?';
        let params = [nome, mensagem, cor];

        if(req.file) {
            let mediaType = 'documento';
            if(req.file.mimetype.startsWith('image')) mediaType = 'imagem';
            else if(req.file.mimetype.startsWith('video')) mediaType = 'video';
            else if(req.file.mimetype.startsWith('audio')) mediaType = 'audio';

            sql += ', media_url = ?, media_type = ?';
            params.push(`/uploads/empresa_${req.empresaId}/${req.file.filename}`, mediaType);
        }

        sql += ' WHERE id = ? AND empresa_id = ?';
        params.push(id, req.empresaId);

        await this.db.execute(sql, params);
        res.json({success:true});
    }

    async reordenarSetores(req, res) {
        const { ordem } = req.body;
        if (!ordem || !Array.isArray(ordem)) return res.status(400).json({error:'Dados inválidos'});
        for (let i = 0; i < ordem.length; i++) {
            await this.db.execute('UPDATE setores SET ordem = ? WHERE id = ? AND empresa_id = ?', [i, ordem[i], req.empresaId]);
        }
        res.json({success:true});
    }

    async deleteSetor(req, res) {
        const { id } = req.params;
        await this.db.execute('DELETE FROM setores WHERE id = ? AND empresa_id = ?', [id, req.empresaId]);
        res.json({success:true});
    }

    // --- MENSAGENS RÁPIDAS ---

    async getQuickMessages(req, res) {
        const [rows] = await this.db.execute('SELECT * FROM mensagens_rapidas WHERE empresa_id = ? ORDER BY titulo ASC', [req.empresaId]);
        res.json(rows);
    }

    async createQuickMessage(req, res) {
        const { titulo, conteudo, atalho } = req.body;
        if(!titulo || !conteudo) return res.status(400).json({error: 'Preencha título e conteúdo'});
        await this.db.execute(
            'INSERT INTO mensagens_rapidas (empresa_id, titulo, conteudo, atalho) VALUES (?, ?, ?, ?)',
            [req.empresaId, titulo, conteudo, atalho]
        );
        res.json({success: true});
    }

    async deleteQuickMessage(req, res) {
        await this.db.execute('DELETE FROM mensagens_rapidas WHERE id = ? AND empresa_id = ?', [req.params.id, req.empresaId]);
        res.json({success: true});
    }

    // --- USUÁRIOS E EQUIPE ---

    async getAtendentes(req, res) {
        const [rows] = await this.db.execute(`
            SELECT u.id, u.nome, u.email, u.is_admin, u.telefone, u.cargo, u.ativo,
            (SELECT GROUP_CONCAT(s.nome SEPARATOR ', ')
             FROM usuarios_setores us
             JOIN setores s ON us.setor_id = s.id
             WHERE us.usuario_id = u.id) as setores,
             (SELECT GROUP_CONCAT(s.id SEPARATOR ',')
             FROM usuarios_setores us
             JOIN setores s ON us.setor_id = s.id
             WHERE us.usuario_id = u.id) as setores_ids
            FROM usuarios_painel u
            WHERE u.empresa_id = ?`, [req.empresaId]);
        res.json(rows);
    }

    async createAtendente(req, res) {
        const bcrypt = require('bcryptjs');
        const { nome, email, senha, is_admin, setores, telefone, cargo, ativo } = req.body;
        const senhaHash = await bcrypt.hash(senha, 10);
        
        const [emp] = await this.db.execute('SELECT limite_usuarios FROM empresas WHERE id = ?', [req.empresaId]);
        const [qtd] = await this.db.execute('SELECT COUNT(*) as total FROM usuarios_painel WHERE empresa_id = ?', [req.empresaId]);
        if (qtd[0].total >= emp[0].limite_usuarios) return res.status(400).json({ error: 'Limite atingido.' });

        const conn = await this.db.getConnection();
        try {
            await conn.beginTransaction();
            const [resUser] = await conn.execute(
                'INSERT INTO usuarios_painel (empresa_id, nome, email, senha, is_admin, telefone, cargo, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                [req.empresaId, nome, email, senhaHash, is_admin ? 1 : 0, telefone, cargo, ativo ? 1 : 0]
            );
            if (setores && Array.isArray(setores)) {
                for (const sId of setores) {
                    await conn.execute('INSERT INTO usuarios_setores (usuario_id, setor_id) VALUES (?, ?)', [resUser.insertId, sId]);
                }
            }
            await conn.commit();
            res.json({ success: true });
        } catch (e) {
            await conn.rollback();
            res.status(500).json({ error: e.message });
        } finally {
            conn.release();
        }
    }

    async deleteAtendente(req, res) {
        await this.db.execute('DELETE FROM usuarios_painel WHERE id=? AND empresa_id=?', [req.params.id, req.empresaId]);
        res.json({ success: true });
    }

    // --- OUTROS ---

    async getClientDashboard(req, res) {
        try {
            const [msgs] = await this.db.execute("SELECT COUNT(*) as t FROM mensagens WHERE empresa_id = ?", [req.empresaId]);
            const [contatos] = await this.db.execute("SELECT COUNT(*) as t FROM contatos WHERE empresa_id = ?", [req.empresaId]);
            const [users] = await this.db.execute("SELECT COUNT(*) as t FROM usuarios_painel WHERE empresa_id = ?", [req.empresaId]);
            res.json({ mensagens: msgs[0].t, contatos: contatos[0].t, equipe: users[0].t });
        } catch(e) { res.status(500).json({error: e.message}); }
    }

    async updateContato(req, res) {
        const { telefone, nome, cnpj, email, endereco, anotacoes } = req.body;
        await this.db.execute(`UPDATE contatos SET nome=?, cnpj_cpf=?, email=?, endereco=?, anotacoes=? WHERE empresa_id=? AND telefone=?`, [nome, cnpj, email, endereco, anotacoes, req.empresaId, telefone]);
        this.emitirAtualizacao(req.empresaId, { action: 'update_contato', telefone });
        res.json({ success: true });
    }

    async getAvaliacoes(req, res) {
        try {
            const [media] = await this.db.execute(
                `SELECT AVG(nota) as media, COUNT(*) as total FROM avaliacoes WHERE empresa_id = ?`,
                [req.empresaId]
            );
            const [lista] = await this.db.execute(
                `SELECT a.*, u.nome as nome_atendente, c.nome as nome_cliente
                 FROM avaliacoes a
                 LEFT JOIN usuarios_painel u ON a.atendente_id = u.id
                 LEFT JOIN contatos c ON a.contato_telefone = c.telefone AND c.empresa_id = a.empresa_id
                 WHERE a.empresa_id = ?
                 ORDER BY a.data_avaliacao DESC LIMIT 50`,
                [req.empresaId]
            );
            res.json({
                media: parseFloat(media[0].media || 0).toFixed(1),
                total: media[0].total,
                lista: lista
            });
        } catch(e) {
            console.error(e);
            res.status(500).json({ error: e.message });
        }
    }
    
    async getAgenda(req, res) {
        try {
            const [rows] = await this.db.execute(`
                SELECT c.*, s.nome as nome_setor
                FROM contatos c
                LEFT JOIN setores s ON c.setor_id = s.id
                WHERE c.empresa_id = ?
                ORDER BY c.nome ASC
            `, [req.empresaId]);
            res.json(rows);
        } catch (e) {
            res.status(500).json({ error: 'Erro ao carregar agenda' });
        }
    }

    // --- ETIQUETAS (TAGS) ---

    async getEtiquetas(req, res) {
        try {
            const [rows] = await this.db.execute(
                'SELECT * FROM etiquetas WHERE empresa_id = ? ORDER BY nome ASC',
                [req.empresaId]
            );
            res.json(rows);
        } catch (e) { res.status(500).json({ error: e.message }); }
    }

    async createEtiqueta(req, res) {
        const { nome, cor } = req.body;
        if (!nome) return res.status(400).json({ error: 'Nome obrigatório' });
        try {
            await this.db.execute(
                'INSERT INTO etiquetas (empresa_id, nome, cor) VALUES (?, ?, ?)',
                [req.empresaId, nome, cor || '#64748b']
            );
            res.json({ success: true });
        } catch (e) { res.status(500).json({ error: e.message }); }
    }

    async deleteEtiqueta(req, res) {
        const { id } = req.params;
        try {
            await this.db.execute('DELETE FROM etiquetas WHERE id = ? AND empresa_id = ?', [id, req.empresaId]);
            res.json({ success: true });
        } catch (e) { res.status(500).json({ error: e.message }); }
    }

    async toggleEtiquetaContato(req, res) {
        const { contatoId, etiquetaId } = req.body;
        try {
            const [exists] = await this.db.execute(
                'SELECT * FROM contatos_etiquetas WHERE contato_id = ? AND etiqueta_id = ?',
                [contatoId, etiquetaId]
            );

            if (exists.length > 0) {
                await this.db.execute(
                    'DELETE FROM contatos_etiquetas WHERE contato_id = ? AND etiqueta_id = ?',
                    [contatoId, etiquetaId]
                );
                res.json({ success: true, action: 'removed' });
            } else {
                await this.db.execute(
                    'INSERT INTO contatos_etiquetas (contato_id, etiqueta_id, empresa_id) VALUES (?, ?, ?)',
                    [contatoId, etiquetaId, req.empresaId]
                );
                res.json({ success: true, action: 'added' });
            }
        } catch (e) { res.status(500).json({ error: e.message }); }
    }
}

module.exports = CrmController;