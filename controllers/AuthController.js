/**
 * controllers/AuthController.js
 * Descrição: Controlador de Autenticação Híbrido (Global Lookup + Segurança)
 * Versão: 7.3 - Fusion (Facilidade do Legado + Segurança do Enterprise)
 * Autor: Sistemas de Gestão
 */

const db = require('../src/config/db');
const bcrypt = require('bcryptjs');
const nodemailer = require('nodemailer');
const crypto = require('crypto');

// Configuração SMTP (Opcional)
let transporter = null;
if (process.env.SMTP_HOST) {
    transporter = nodemailer.createTransport({
        host: process.env.SMTP_HOST,
        port: Number(process.env.SMTP_PORT) || 587,
        secure: process.env.SMTP_SECURE === 'true',
        auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
        tls: { rejectUnauthorized: false }
    });
}

class AuthController {

    /**
     * Login Inteligente: Busca usuário pelo e-mail e descobre a empresa automaticamente
     */
    async login(req, res) {
        // Aceita empresaId opcionalmente, mas foca no email
        const { email, senha } = req.body;

        try {
            if (!email || !senha) {
                return res.status(400).json({ success: false, message: 'E-mail e senha são obrigatórios.' });
            }

            // 1. Busca Global Inteligente (JOIN com Empresas)
            // Traz dados do usuário E da empresa em uma única query
            const sql = `
                SELECT 
                    u.id, u.nome, u.email, u.senha, u.is_admin, u.cargo, u.ativo as user_ativo, u.empresa_id,
                    e.nome as empresa_nome, e.ativo as empresa_ativa, e.logo_url, e.cor_primaria, e.mensagens_padrao
                FROM usuarios_painel u
                INNER JOIN empresas e ON u.empresa_id = e.id
                WHERE u.email = ?
                LIMIT 1
            `;
            
            const users = await db.query(sql, [email]);

            if (users.length === 0) {
                return res.status(401).json({ success: false, message: 'E-mail não encontrado.' });
            }

            const user = users[0];

            // 2. Validações de Status
            if (user.empresa_ativa !== 1) {
                return res.status(403).json({ success: false, message: 'Empresa bloqueada. Contate o suporte.' });
            }
            if (user.user_ativo !== 1) {
                return res.status(403).json({ success: false, message: 'Usuário desativado.' });
            }

            // 3. Validação de Senha (Suporta Texto Puro para Migração E Hash)
            let senhaValida = false;
            let precisaMigrar = false;

            if (user.senha.startsWith('$2')) {
                // Já é Hash Bcrypt (Seu caso atual no banco)
                senhaValida = await bcrypt.compare(senha, user.senha);
            } else if (user.senha === senha) {
                // É Texto Puro (Legado)
                senhaValida = true;
                precisaMigrar = true;
            }

            if (!senhaValida) {
                return res.status(401).json({ success: false, message: 'Senha incorreta.' });
            }

            // Auto-migração de senha insegura
            if (precisaMigrar) {
                const hash = await bcrypt.hash(senha, 10);
                await db.run('UPDATE usuarios_painel SET senha = ? WHERE id = ?', [hash, user.id]);
                console.log(`[AUTH] Senha migrada para Bcrypt: ${user.email}`);
            }

            // 4. Definição de Role/Cargo
            let role = 'user';
            if (user.is_admin === 1) {
                // Se for empresa 1 e admin, é Super Admin
                role = (user.empresa_id === 1) ? 'superadmin' : 'admin';
            } else if (user.cargo === 'Gerente') {
                role = 'admin';
            }

            // 5. Criação da Sessão (CRÍTICO)
            req.session.user = {
                id: user.id,
                nome: user.nome,
                email: user.email,
                is_admin: user.is_admin,
                cargo: user.cargo,
                role: role
            };
            req.session.empresaId = user.empresa_id;

            // Carrega configs (Mensagens padrão) na sessão para uso rápido
            try {
                req.session.msgs = JSON.parse(user.mensagens_padrao || '[]');
            } catch (e) { req.session.msgs = []; }

            req.session.save(err => {
                if (err) {
                    console.error('[Session Error]', err);
                    return res.status(500).json({ success: false, message: 'Erro de sessão.' });
                }

                console.log(`✅ [AUTH] Sucesso: ${user.email} @ ${user.empresa_nome}`);

                return res.json({
                    success: true,
                    message: 'Login realizado com sucesso',
                    redirectUrl: role === 'superadmin' ? '/super-admin' : '/dashboard',
                    user: req.session.user,
                    empresa: {
                        id: user.empresa_id,
                        nome: user.empresa_nome,
                        logo: user.logo_url,
                        cor: user.cor_primaria || '#4f46e5'
                    }
                });
            });

        } catch (error) {
            console.error('[AUTH ERROR]', error);
            res.status(500).json({ success: false, message: 'Erro interno.' });
        }
    }

    // --- Métodos Auxiliares Mantidos ---

    async logout(req, res) {
        req.session.destroy(() => {
            res.clearCookie('saas_session_cookie');
            res.json({ success: true });
        });
    }

    async checkSession(req, res) {
        if (req.session && req.session.user) {
            res.json({ isAuthenticated: true, user: req.session.user, empresaId: req.session.empresaId });
        } else {
            res.json({ isAuthenticated: false });
        }
    }

    async recuperarSenha(req, res) {
        // Implementação de recuperação via e-mail mantida...
        const { email } = req.body;
        try {
            const users = await db.query("SELECT id, nome FROM usuarios_painel WHERE email = ?", [email]);
            if (users.length === 0) return res.json({ success: true, message: 'Se o e-mail existir, enviamos instruções.' });
            
            const user = users[0];
            const novaSenha = crypto.randomBytes(4).toString('hex');
            const hash = await bcrypt.hash(novaSenha, 10);
            
            await db.run("UPDATE usuarios_painel SET senha = ? WHERE id = ?", [hash, user.id]);
            
            if (transporter) {
                await transporter.sendMail({
                    from: process.env.SMTP_USER,
                    to: email,
                    subject: 'Recuperação de Senha',
                    html: `<p>Sua nova senha temporária: <b>${novaSenha}</b></p>`
                });
            } else {
                console.log(`[DEBUG] Senha para ${email}: ${novaSenha}`);
            }
            res.json({ success: true, message: 'Instruções enviadas.' });
        } catch (e) {
            res.status(500).json({ success: false });
        }
    }

    async trocarSenha(req, res) {
        // Implementação de troca mantida...
        const { userId, novaSenha } = req.body;
        try {
            const hash = await bcrypt.hash(novaSenha, 10);
            await db.run("UPDATE usuarios_painel SET senha = ? WHERE id = ?", [hash, userId]);
            res.json({ success: true });
        } catch (e) {
            res.status(500).json({ success: false });
        }
    }
}

module.exports = new AuthController();