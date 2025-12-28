/**
 * controllers/AdminController.js
 * Descrição: Controlador do Super Admin (Gestão de Tenants, Analytics e Segurança)
 * Versão: 5.4 - Funcionalidades Legadas Restauradas + Arquitetura Nova
 */

const db = require('../src/config/db');  // Singleton DB
const bcrypt = require('bcryptjs');
const sessionManager = require('../src/managers/SessionManager');

class AdminController {
    
    constructor(injectedDb) {
        this.db = injectedDb || db;
        this.sm = sessionManager;
    }

    // ============================================
    // 1. ANALYTICS (KPIs e Lista de Clientes)
    // ============================================

    /**
     * Obtém estatísticas gerais e lista detalhada de clientes
     * GET /api/super-admin/analytics
     */
    async getAnalytics(req, res) {
        try {
            // 1. KPIs Gerais
            // db.query retorna array de linhas. [0] pega a primeira linha.
            const kpisRows = await this.db.query(`
                SELECT
                    (SELECT COUNT(*) FROM empresas WHERE id != 1) as total_empresas,
                    (SELECT COUNT(*) FROM empresas WHERE id != 1 AND ativo = 1) as ativas,
                    (SELECT COUNT(*) FROM empresas WHERE id != 1 AND ativo = 0) as bloqueadas,
                    (SELECT COUNT(*) FROM mensagens) as total_msgs_sistema,
                    (SELECT COUNT(*) FROM usuarios_painel WHERE empresa_id != 1) as total_usuarios,
                    (SELECT COUNT(*) FROM contatos) as total_contatos
            `);
            const kpis = kpisRows[0];

            // 2. Lista Detalhada de Clientes
            const clientes = await this.db.query(`
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
                    (SELECT COUNT(*) FROM contatos WHERE empresa_id = e.id) as total_contatos
                FROM empresas e
                LEFT JOIN usuarios_painel u ON u.empresa_id = e.id AND u.is_admin = 1
                WHERE e.id != 1
                GROUP BY e.id
                ORDER BY e.id DESC
            `);

            // 3. Formatação e Status Real-time do WhatsApp
            const clientesFormatados = clientes.map(cliente => {
                // Tenta pegar status em tempo real da memória
                const realtime = this.sm.getStatus(cliente.id);
                const statusFinal = realtime.status === 'CONNECTED' ? 'CONECTADO' : (cliente.whatsapp_status || 'DESCONECTADO');

                return {
                    ...cliente,
                    created_at: new Date(cliente.created_at).toLocaleDateString('pt-BR'),
                    uso_percentual: Math.round(((cliente.total_users || 0) / (cliente.limite_usuarios || 1)) * 100),
                    status_whatsapp: statusFinal
                };
            });

            res.json({
                success: true,
                kpis: kpis,
                clientes: clientesFormatados,
                timestamp: new Date().toISOString()
            });

        } catch (error) {
            console.error('[SuperAdmin] Erro no Analytics:', error);
            res.status(500).json({ error: 'Erro ao buscar estatísticas', message: error.message });
        }
    }

    // ============================================
    // 2. GESTÃO DE EMPRESAS (Criação Transacional)
    // ============================================

    /**
     * Cria uma nova empresa com toda estrutura inicial
     * POST /api/super-admin/empresas
     */
    async createEmpresa(req, res) {
        const { nome, admin_email, admin_senha, limite_usuarios, plano, senha_mestra, telefone } = req.body;

        try {
            // 1. Validação de Segurança
            if (senha_mestra !== process.env.SUPER_ADMIN_PASS) {
                return res.status(403).json({ error: 'Senha Mestra inválida.' });
            }

            if (!nome || !admin_email || !admin_senha) {
                return res.status(400).json({ error: 'Campos obrigatórios: Nome, Email e Senha.' });
            }

            // 2. Validação de Duplicidade (Email e Nome)
            const check = await this.db.query(
                `SELECT id FROM usuarios_painel WHERE email = ? UNION SELECT id FROM empresas WHERE nome = ?`,
                [admin_email, nome]
            );
            
            if (check.length > 0) {
                return res.status(409).json({ error: 'Empresa ou E-mail já cadastrados.' });
            }

            // 3. Início da Transação
            // Precisamos de uma conexão dedicada para transaction
            const conn = await this.db.pool.getConnection();
            await conn.beginTransaction();

            try {
                // A. Criar Empresa
                const msgsPadrao = [{ titulo: "boasvindas", texto: `Olá {{nome}}! 👋\nBem-vindo à *${nome}*!` }];
                
                const [resEmp] = await conn.execute(
                    `INSERT INTO empresas (
                        nome, nome_sistema, plano, limite_usuarios, ativo, mensagens_padrao,
                        cor_primaria, msg_ausencia, msg_avaliacao,
                        horario_inicio, horario_fim, dias_funcionamento, created_at, whatsapp_status
                    ) VALUES (?, ?, ?, ?, 1, ?, '#4f46e5',
                        'Olá! Nosso horário de atendimento é de segunda a sexta, das 8h às 18h.',
                        'Por favor, avalie nosso atendimento de 1 a 5.',
                        '08:00', '18:00', ?, NOW(), 'DESCONECTADO')`,
                    [
                        nome, nome, plano || 'pro', limite_usuarios || 5,
                        JSON.stringify(msgsPadrao),
                        JSON.stringify(['seg', 'ter', 'qua', 'qui', 'sex'])
                    ]
                );
                
                const empId = resEmp.insertId;

                // B. Criar Setores Padrão
                const setores = [
                    { nome: "Comercial 💰", msg: "Olá {{nome}}, um consultor logo vai te atender.", cor: "#10b981" },
                    { nome: "Suporte 🛠️", msg: "Entendido {{nome}}. Um técnico analisará seu caso.", cor: "#3b82f6" },
                    { nome: "Financeiro 📄", msg: "Olá {{nome}}. Assuntos financeiros aqui.", cor: "#f59e0b" }
                ];

                for (let i = 0; i < setores.length; i++) {
                    await conn.execute(
                        `INSERT INTO setores (empresa_id, nome, mensagem_saudacao, padrao, cor, ordem) VALUES (?, ?, ?, 0, ?, ?)`,
                        [empId, setores[i].nome, setores[i].msg, setores[i].cor, i]
                    );
                }

                // C. Criar Mensagens Rápidas Padrão
                const rapidas = [
                    { titulo: "Pix", conteudo: "Chave Pix: CNPJ 00.000.000/0001-00", atalho: "/pix" },
                    { titulo: "Endereço", conteudo: "Estamos na Rua Exemplo, 100.", atalho: "/end" },
                    { titulo: "Agradecimento", conteudo: "Obrigado, {{nome}}! 🚀", atalho: "/obg" }
                ];

                for (const r of rapidas) {
                    await conn.execute(
                        `INSERT INTO mensagens_rapidas (empresa_id, titulo, conteudo, atalho) VALUES (?, ?, ?, ?)`,
                        [empId, r.titulo, r.conteudo, r.atalho]
                    );
                }

                // D. Criar Grade de Horários (Vital para o Bot)
                const diasSemana = [0, 1, 2, 3, 4, 5, 6]; 
                for (const dia of diasSemana) {
                    const ativo = (dia >= 1 && dia <= 5) ? 1 : 0; // Seg a Sex ativo
                    await conn.execute(
                        `INSERT INTO horarios_atendimento (empresa_id, dia_semana, horario_abertura, horario_fechamento, ativo) 
                         VALUES (?, ?, '08:00:00', '18:00:00', ?)`,
                        [empId, dia, ativo]
                    );
                }

                // E. Criar Usuário Admin
                const senhaHash = await bcrypt.hash(admin_senha, 10);
                await conn.execute(
                    `INSERT INTO usuarios_painel (empresa_id, nome, email, senha, is_admin, cargo, ativo, telefone, created_at)
                     VALUES (?, 'Administrador', ?, ?, 1, 'Gerente', 1, ?, NOW())`,
                    [empId, admin_email, senhaHash, telefone || null]
                );

                await conn.commit();
                console.log(`✅ [SuperAdmin] Empresa criada: ${nome} (ID: ${empId})`);

                res.json({ success: true, message: 'Empresa criada com sucesso!', empresaId: empId });

            } catch (error) {
                await conn.rollback();
                throw error; // Repassa para o catch externo
            } finally {
                conn.release(); // Libera conexão
            }

        } catch (error) {
            console.error('[SuperAdmin] Erro crítico ao criar empresa:', error);
            res.status(500).json({ error: 'Erro ao criar empresa', message: error.message });
        }
    }

    /**
     * Atualiza dados da empresa
     * POST /api/super-admin/empresas/update
     */
    async updateEmpresa(req, res) {
        const { id, nome, plano, limite_usuarios, admin_email, admin_senha_nova } = req.body;

        try {
            // Atualiza dados básicos
            await this.db.run(
                `UPDATE empresas SET nome = ?, plano = ?, limite_usuarios = ? WHERE id = ?`,
                [nome, plano, limite_usuarios, id]
            );

            // Atualiza Email do Admin (Busca o primeiro admin da empresa)
            if (admin_email) {
                await this.db.run(
                    `UPDATE usuarios_painel SET email = ? WHERE empresa_id = ? AND is_admin = 1 LIMIT 1`,
                    [admin_email, id]
                );
            }

            // Atualiza Senha do Admin
            if (admin_senha_nova) {
                const hash = await bcrypt.hash(admin_senha_nova, 10);
                await this.db.run(
                    `UPDATE usuarios_painel SET senha = ? WHERE empresa_id = ? AND is_admin = 1 LIMIT 1`,
                    [hash, id]
                );
            }

            res.json({ success: true, message: 'Dados atualizados.' });
        } catch (e) {
            console.error('[SuperAdmin] Erro update:', e);
            res.status(500).json({ error: e.message });
        }
    }

    // ============================================
    // 3. CONTROLE DE ACESSO E STATUS
    // ============================================

    async toggleStatus(req, res) {
        const { id } = req.params;
        const { ativo } = req.body; // espera true/false ou 1/0

        try {
            await this.db.run('UPDATE empresas SET ativo = ? WHERE id = ?', [ativo ? 1 : 0, id]);
            
            // Se bloqueou, derruba a sessão
            if (!ativo || ativo == 0) {
                await this.sm.deleteSession(parseInt(id));
                console.log(`[SuperAdmin] Empresa ${id} bloqueada e desconectada.`);
            }

            res.json({ success: true, message: ativo ? 'Empresa ativada' : 'Empresa bloqueada' });
        } catch (e) {
            res.status(500).json({ error: e.message });
        }
    }

    async deleteEmpresa(req, res) {
        const { id } = req.params;
        const { senha_mestra } = req.body;

        try {
            if (senha_mestra !== process.env.SUPER_ADMIN_PASS) {
                return res.status(403).json({ error: 'Senha Mestra incorreta' });
            }

            if (id == 1) return res.status(403).json({ error: 'Proibido excluir a conta Master.' });

            // 1. Derruba WhatsApp
            await this.sm.deleteSession(parseInt(id));

            // 2. Deleta do Banco (Cascade cuida do resto)
            await this.db.run('DELETE FROM empresas WHERE id = ?', [id]);

            console.log(`[SuperAdmin] Empresa ${id} excluída permanentemente.`);
            res.json({ success: true, message: 'Empresa excluída.' });

        } catch (e) {
            console.error('[SuperAdmin] Erro delete:', e);
            res.status(500).json({ error: e.message });
        }
    }

    async resetSession(req, res) {
        const { id } = req.params;
        const { senha_mestra } = req.body;

        try {
            if (senha_mestra !== process.env.SUPER_ADMIN_PASS) {
                return res.status(403).json({ error: 'Senha Mestra incorreta' });
            }

            await this.sm.deleteSession(parseInt(id));
            await this.db.run("UPDATE empresas SET whatsapp_status = 'DESCONECTADO' WHERE id = ?", [id]);
            
            console.log(`[SuperAdmin] Sessão da empresa ${id} resetada via painel.`);
            res.json({ success: true, message: 'Sessão resetada com sucesso.' });

        } catch (e) {
            res.status(500).json({ error: e.message });
        }
    }
}

module.exports = AdminController;