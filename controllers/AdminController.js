// ============================================
// Arquivo: controllers/AdminController.js
// Descrição: Controller do Super Admin
// Versão: 5.0 - Revisado e Corrigido
// ============================================

const bcrypt = require('bcryptjs');

class AdminController {
    /**
     * Construtor do AdminController
     * @param {Object} db - Pool de conexão MySQL
     * @param {Object} sessionManager - Instância do SessionManager
     */
    constructor(db, sessionManager) {
        this.db = db;
        this.sm = sessionManager;
    }

    // ============================================
    // ANALYTICS
    // ============================================

    /**
     * Obtém estatísticas gerais do sistema
     * GET /api/super-admin/analytics
     */
    async getAnalytics(req, res) {
        try {
            // KPIs
            const [kpis] = await this.db.execute(`
                SELECT
                    (SELECT COUNT(*) FROM empresas WHERE id != 1) as total_empresas,
                    (SELECT COUNT(*) FROM empresas WHERE id != 1 AND ativo = 1) as ativas,
                    (SELECT COUNT(*) FROM empresas WHERE id != 1 AND ativo = 0) as bloqueadas,
                    (SELECT COUNT(*) FROM mensagens) as total_msgs_sistema,
                    (SELECT COUNT(*) FROM usuarios_painel WHERE empresa_id != 1) as total_usuarios,
                    (SELECT COUNT(*) FROM contatos) as total_contatos
            `);

            // Lista de clientes
            const [clientes] = await this.db.execute(`
                SELECT
                    e.id,
                    e.nome,
                    e.plano,
                    e.limite_usuarios,
                    e.ativo,
                    e.created_at,
                    e.whatsapp_status,
                    u.email as admin_email,
                    u.nome as admin_nome,
                    (SELECT COUNT(*) FROM usuarios_painel WHERE empresa_id = e.id) as total_users,
                    (SELECT COUNT(*) FROM mensagens WHERE empresa_id = e.id) as total_msgs,
                    (SELECT COUNT(*) FROM contatos WHERE empresa_id = e.id) as total_contatos,
                    (SELECT COUNT(*) FROM contatos WHERE empresa_id = e.id AND status_atendimento = 'ATENDENDO') as em_atendimento
                FROM empresas e
                LEFT JOIN usuarios_painel u ON u.empresa_id = e.id AND u.is_admin = 1
                WHERE e.id != 1
                GROUP BY e.id
                ORDER BY e.id DESC
            `);

            // Formatar dados
            const clientesFormatados = clientes.map(cliente => ({
                ...cliente,
                created_at: new Date(cliente.created_at).toLocaleDateString('pt-BR'),
                uso_percentual: Math.round(((cliente.total_users || 0) / (cliente.limite_usuarios || 1)) * 100),
                status_whatsapp: cliente.whatsapp_status || 'DESCONECTADO'
            }));

            res.json({
                success: true,
                kpis: kpis[0],
                clientes: clientesFormatados,
                timestamp: new Date().toISOString()
            });

        } catch (error) {
            console.error('[ADMIN] Erro ao buscar analytics:', error);
            res.status(500).json({
                error: 'Erro ao buscar estatísticas',
                message: error.message
            });
        }
    }

    // ============================================
    // CRIAR EMPRESA
    // ============================================

    /**
     * Cria uma nova empresa
     * POST /api/super-admin/empresas
     */
    async createEmpresa(req, res) {
        const {
            nome,
            admin_email,
            admin_senha,
            limite_usuarios,
            plano,
            senha_mestra
        } = req.body;

        try {
            // Validar senha mestra
            if (senha_mestra !== process.env.SUPER_ADMIN_PASS) {
                return res.status(403).json({
                    error: 'Senha Mestra inválida'
                });
            }

            // Validar campos
            if (!nome || !admin_email || !admin_senha) {
                return res.status(400).json({
                    error: 'Nome, email e senha são obrigatórios'
                });
            }

            // Validar email
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(admin_email)) {
                return res.status(400).json({
                    error: 'Email inválido'
                });
            }

            // Verificar se empresa existe
            const [empresaExiste] = await this.db.execute(
                'SELECT id FROM empresas WHERE nome = ?',
                [nome]
            );

            if (empresaExiste.length > 0) {
                return res.status(409).json({
                    error: 'Empresa já existe'
                });
            }

            // Verificar se email está em uso
            const [emailExiste] = await this.db.execute(
                'SELECT id FROM usuarios_painel WHERE email = ?',
                [admin_email]
            );

            if (emailExiste.length > 0) {
                return res.status(409).json({
                    error: 'Email já está em uso'
                });
            }

            // Transação
            const conn = await this.db.getConnection();

            try {
                await conn.beginTransaction();

                // Mensagens padrão
                const msgsPadrao = [
                    {
                        titulo: "boasvindas",
                        texto: `Olá {{nome}}! 👋\nSeja bem-vindo(a) à *${nome}*!\n\nComo podemos ajudar?`
                    }
                ];

                // Criar empresa
                const [resEmp] = await conn.execute(
                    `INSERT INTO empresas (
                        nome, plano, limite_usuarios, ativo, mensagens_padrao,
                        welcome_media_type, cor_primaria, msg_ausencia, msg_avaliacao,
                        horario_inicio, horario_fim, dias_funcionamento, created_at
                    ) VALUES (?, ?, ?, 1, ?, 'texto', '#4f46e5',
                        'Olá! Nosso horário de atendimento é de segunda a sexta, das 8h às 18h.',
                        'Obrigado pelo contato! Por favor, avalie nosso atendimento de 1 a 5.',
                        '08:00', '18:00', ?, NOW())`,
                    [
                        nome,
                        plano || 'pro',
                        limite_usuarios || 5,
                        JSON.stringify(msgsPadrao),
                        JSON.stringify(['seg', 'ter', 'qua', 'qui', 'sex'])
                    ]
                );

                const empId = resEmp.insertId;

                // Criar setores padrão
                const setores = [
                    { nome: "Comercial 💰", msg: "Olá {{nome}}, vou te conectar com nosso time de Vendas!", cor: "#10b981" },
                    { nome: "Suporte 🛠️", msg: "Entendido {{nome}}. Um técnico já vai te ajudar.", cor: "#3b82f6" },
                    { nome: "Financeiro 📄", msg: "Olá {{nome}}. Assuntos financeiros serão tratados agora.", cor: "#f59e0b" }
                ];

                for (let i = 0; i < setores.length; i++) {
                    const s = setores[i];
                    await conn.execute(
                        `INSERT INTO setores (empresa_id, nome, mensagem_saudacao, padrao, cor, ordem)
                         VALUES (?, ?, ?, 0, ?, ?)`,
                        [empId, s.nome, s.msg, s.cor, i]
                    );
                }

                // Criar mensagens rápidas padrão
                const rapidas = [
                    { titulo: "Pix", conteudo: "Nossa chave Pix é: 00.000.000/0001-00 (CNPJ)", atalho: "/pix" },
                    { titulo: "Endereço", conteudo: "Estamos localizados na Rua Exemplo, 123.", atalho: "/end" },
                    { titulo: "Agradecimento", conteudo: "Muito obrigado, {{nome}}! Volte sempre. 🚀", atalho: "/obg" },
                    { titulo: "Aguarde", conteudo: "Só um momento, estou verificando...", atalho: "/momento" }
                ];

                for (const r of rapidas) {
                    await conn.execute(
                        `INSERT INTO mensagens_rapidas (empresa_id, titulo, conteudo, atalho)
                         VALUES (?, ?, ?, ?)`,
                        [empId, r.titulo, r.conteudo, r.atalho]
                    );
                }

                // Criar usuário admin
                const senhaHash = await bcrypt.hash(admin_senha, 10);
                await conn.execute(
                    `INSERT INTO usuarios_painel (empresa_id, nome, email, senha, is_admin, cargo, ativo, created_at)
                     VALUES (?, 'Administrador', ?, ?, 1, 'Gerente', 1, NOW())`,
                    [empId, admin_email, senhaHash]
                );

                await conn.commit();

                console.log(`✅ [ADMIN] Nova empresa criada: ${nome} (ID: ${empId})`);

                res.json({
                    success: true,
                    message: 'Empresa criada com sucesso',
                    empresaId: empId
                });

            } catch (error) {
                await conn.rollback();
                throw error;
            } finally {
                conn.release();
            }

        } catch (error) {
            console.error('[ADMIN] Erro ao criar empresa:', error);
            res.status(500).json({
                error: 'Erro ao criar empresa',
                message: error.message
            });
        }
    }

    // ============================================
    // ATUALIZAR EMPRESA
    // ============================================

    /**
     * Atualiza dados de uma empresa
     * PUT /api/super-admin/empresas/update
     */
    async updateEmpresa(req, res) {
        const { id, nome, plano, limite, admin_email, admin_senha_nova } = req.body;

        try {
            if (!id || !nome || !plano || !limite) {
                return res.status(400).json({
                    error: 'Campos obrigatórios não preenchidos'
                });
            }

            // Verificar se empresa existe
            const [empresa] = await this.db.execute(
                'SELECT id FROM empresas WHERE id = ?',
                [id]
            );

            if (empresa.length === 0) {
                return res.status(404).json({
                    error: 'Empresa não encontrada'
                });
            }

            // Atualizar empresa
            await this.db.execute(
                `UPDATE empresas SET nome = ?, plano = ?, limite_usuarios = ?, updated_at = NOW() WHERE id = ?`,
                [nome, plano, limite, id]
            );

            // Atualizar email do admin
            if (admin_email) {
                await this.db.execute(
                    `UPDATE usuarios_painel SET email = ? WHERE empresa_id = ? AND is_admin = 1`,
                    [admin_email, id]
                );
            }

            // Atualizar senha do admin
            if (admin_senha_nova) {
                const senhaHash = await bcrypt.hash(admin_senha_nova, 10);
                await this.db.execute(
                    `UPDATE usuarios_painel SET senha = ? WHERE empresa_id = ? AND is_admin = 1`,
                    [senhaHash, id]
                );
            }

            console.log(`✅ [ADMIN] Empresa atualizada: ${nome} (ID: ${id})`);

            res.json({
                success: true,
                message: 'Empresa atualizada com sucesso'
            });

        } catch (error) {
            console.error('[ADMIN] Erro ao atualizar empresa:', error);
            res.status(500).json({
                error: 'Erro ao atualizar empresa',
                message: error.message
            });
        }
    }

    // ============================================
    // ALTERNAR STATUS
    // ============================================

    /**
     * Ativa/desativa empresa
     * POST /api/super-admin/empresas/:id/status
     */
    async toggleStatus(req, res) {
        const { id } = req.params;

        try {
            await this.db.execute(
                'UPDATE empresas SET ativo = NOT ativo, updated_at = NOW() WHERE id = ?',
                [id]
            );

            const [emp] = await this.db.execute(
                'SELECT ativo, nome FROM empresas WHERE id = ?',
                [id]
            );

            if (emp.length === 0) {
                return res.status(404).json({
                    error: 'Empresa não encontrada'
                });
            }

            const novoStatus = emp[0].ativo;

            // Desconectar WhatsApp se bloqueado
            if (!novoStatus) {
                await this.sm.deleteSession(parseInt(id));
                console.log(`⚠️ [ADMIN] Empresa bloqueada: ${emp[0].nome}`);
            } else {
                console.log(`✅ [ADMIN] Empresa desbloqueada: ${emp[0].nome}`);
            }

            res.json({
                success: true,
                novo_status: novoStatus,
                message: novoStatus ? 'Empresa ativada' : 'Empresa bloqueada'
            });

        } catch (error) {
            console.error('[ADMIN] Erro ao alterar status:', error);
            res.status(500).json({
                error: 'Erro ao alterar status',
                message: error.message
            });
        }
    }

    // ============================================
    // EXCLUIR EMPRESA
    // ============================================

    /**
     * Remove empresa permanentemente
     * POST /api/super-admin/empresas/:id/delete
     */
    async deleteEmpresa(req, res) {
        const { senha_mestra } = req.body;
        const id = parseInt(req.params.id);

        try {
            // Validar senha mestra
            if (senha_mestra !== process.env.SUPER_ADMIN_PASS) {
                return res.status(403).json({
                    error: 'Senha Mestra inválida'
                });
            }

            // Proteção: não pode excluir empresa ID 1
            if (id === 1) {
                return res.status(403).json({
                    error: 'Não é possível excluir a empresa do sistema'
                });
            }

            // Buscar nome
            const [empresa] = await this.db.execute(
                'SELECT nome FROM empresas WHERE id = ?',
                [id]
            );

            if (empresa.length === 0) {
                return res.status(404).json({
                    error: 'Empresa não encontrada'
                });
            }

            const nomeEmpresa = empresa[0].nome;

            // Desconectar WhatsApp
            await this.sm.deleteSession(id);

            // Excluir dados
            const conn = await this.db.getConnection();

            try {
                await conn.beginTransaction();

                await conn.execute('DELETE FROM avaliacoes WHERE empresa_id = ?', [id]);
                await conn.execute('DELETE FROM mensagens WHERE empresa_id = ?', [id]);
                await conn.execute('DELETE FROM mensagens_rapidas WHERE empresa_id = ?', [id]);
                await conn.execute('DELETE FROM contatos_etiquetas WHERE empresa_id = ?', [id]);
                await conn.execute('DELETE FROM etiquetas WHERE empresa_id = ?', [id]);
                await conn.execute('DELETE FROM usuarios_setores WHERE usuario_id IN (SELECT id FROM usuarios_painel WHERE empresa_id = ?)', [id]);
                await conn.execute('DELETE FROM contatos WHERE empresa_id = ?', [id]);
                await conn.execute('DELETE FROM setores WHERE empresa_id = ?', [id]);
                await conn.execute('DELETE FROM usuarios_painel WHERE empresa_id = ?', [id]);
                await conn.execute('DELETE FROM empresas WHERE id = ?', [id]);

                await conn.commit();

                console.log(`🗑️ [ADMIN] Empresa excluída: ${nomeEmpresa} (ID: ${id})`);

                res.json({
                    success: true,
                    message: 'Empresa excluída permanentemente'
                });

            } catch (error) {
                await conn.rollback();
                throw error;
            } finally {
                conn.release();
            }

        } catch (error) {
            console.error('[ADMIN] Erro ao excluir empresa:', error);
            res.status(500).json({
                error: 'Erro ao excluir empresa',
                message: error.message
            });
        }
    }

    // ============================================
    // RESETAR SESSÃO WHATSAPP
    // ============================================

    /**
     * Desconecta sessão WhatsApp da empresa
     * POST /api/super-admin/empresas/:id/reset
     */
    async resetSession(req, res) {
        const { senha_mestra } = req.body;
        const id = parseInt(req.params.id);

        try {
            // Validar senha mestra
            if (senha_mestra !== process.env.SUPER_ADMIN_PASS) {
                return res.status(403).json({
                    error: 'Senha Mestra inválida'
                });
            }

            // Buscar empresa
            const [empresa] = await this.db.execute(
                'SELECT nome FROM empresas WHERE id = ?',
                [id]
            );

            if (empresa.length === 0) {
                return res.status(404).json({
                    error: 'Empresa não encontrada'
                });
            }

            // Resetar sessão
            await this.sm.deleteSession(id);

            console.log(`🔄 [ADMIN] Sessão resetada: ${empresa[0].nome} (ID: ${id})`);

            res.json({
                success: true,
                message: 'Sessão WhatsApp resetada com sucesso'
            });

        } catch (error) {
            console.error('[ADMIN] Erro ao resetar sessão:', error);
            res.status(500).json({
                error: 'Erro ao resetar sessão',
                message: error.message
            });
        }
    }
}

module.exports = AdminController;
