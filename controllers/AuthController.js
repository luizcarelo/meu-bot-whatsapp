// Arquivo: controllers/AuthController.js
// Controlador de Autenticação - Login, Recuperação de Senha e Troca de Senha

const bcrypt = require('bcryptjs');
const nodemailer = require('nodemailer');
const crypto = require('crypto');

// Configuração do Transporter de E-mail

const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST || 'smtp.gmail.com',
  port: Number(process.env.SMTP_PORT) || 587,
  secure: false, // true para 465, false para outras portas
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS
   }});

class AuthController {
    constructor(db) {
        this.db = db;
    }

    async login(req, res) {
        const { nomeEmpresa, email, senha } = req.body;

        try {
            // 1. Login Super Admin (Credenciais Fixas)
            if (email === 'admin@saas.com' && senha === '123456') {
                return res.json({
                    success: true,
                    role: 'super_admin',
                    redirectUrl: '/super-admin',
                    empresaId: 1,
                    empresaNome: 'Sistema',
                    usuario: {
                        id: 0,
                        nome: 'Super Admin',
                        email: 'admin@saas.com',
                        is_admin: 1
                    },
                    config: {
                        logo: null,
                        cor: '#4f46e5',
                        msgs: []
                    }
                });
            }

            // 2. Validação de Campos
            if (!email || !senha) {
                return res.status(400).json({ error: 'Email e senha são obrigatórios' });
            }

            // 3. Busca o Usuário pelo Email (SEM depender do nome da empresa)
            const [usuarios] = await this.db.execute(
                `SELECT u.id, u.nome, u.email, u.senha, u.is_admin, u.empresa_id, u.ativo,
                        e.nome as empresa_nome, e.ativo as empresa_ativa, e.logo_url, e.cor_primaria, e.mensagens_padrao
                 FROM usuarios_painel u
                 INNER JOIN empresas e ON u.empresa_id = e.id
                 WHERE u.email = ?`,
                [email]
            );

            if (usuarios.length === 0) {
                return res.status(401).json({ error: 'Email não encontrado' });
            }

            const user = usuarios[0];

            // 4. Verifica se a Empresa está Ativa
            if (!user.empresa_ativa) {
                return res.status(403).json({ error: 'Empresa bloqueada. Entre em contato com o suporte.' });
            }

            // 5. Verifica se o Usuário está Ativo
            if (!user.ativo) {
                return res.status(403).json({ error: 'Usuário desativado. Entre em contato com o administrador.' });
            }

            // 6. Valida a Senha (Suporta texto puro legado E bcrypt hash)
            let senhaValida = false;

            if (user.senha === senha) {
                // Senha em texto puro (LEGADO - migração automática)
                senhaValida = true;

                // Atualiza para hash bcrypt (melhora de segurança)
                const hash = await bcrypt.hash(senha, 10);
                await this.db.execute('UPDATE usuarios_painel SET senha = ? WHERE id = ?', [hash, user.id]);
                console.log(`[Auth] Senha do usuário ${user.email} migrada para bcrypt`);

            } else if (user.senha.startsWith('$2')) {
                // Senha já em bcrypt
                senhaValida = await bcrypt.compare(senha, user.senha);
            }

            if (!senhaValida) {
                return res.status(401).json({ error: 'Senha incorreta' });
            }

            // 7. Prepara Mensagens Padrão
            let mensagensPadrao = [];
            try {
                mensagensPadrao = JSON.parse(user.mensagens_padrao || '[]');
            } catch (e) {
                console.error('[Auth] Erro ao parsear mensagens_padrao:', e);
            }

            // 8. Retorna Sessão Completa
            res.json({
                success: true,
                role: 'cliente',
                redirectUrl: '/crm',
                empresaId: user.empresa_id,
                empresaNome: user.empresa_nome,
                config: {
                    logo: user.logo_url,
                    cor: user.cor_primaria || '#4f46e5',
                    msgs: mensagensPadrao
                },
                usuario: {
                    id: user.id,
                    nome: user.nome,
                    email: user.email,
                    is_admin: user.is_admin
                }
            });

        } catch (e) {
            console.error('[Auth] Erro no login:', e);
            res.status(500).json({ error: 'Erro interno do servidor. Tente novamente.' });
        }
    }

    // Recuperação de Senha
    async esqueciSenha(req, res) {
        const { email } = req.body;

        try {
            // 1. Verifica se o usuário existe
            const [users] = await this.db.execute(
                'SELECT id, nome, email FROM usuarios_painel WHERE email = ?',
                [email]
            );

            if (users.length === 0) {
                // Por segurança, não revelamos se o email existe
                return res.json({
                    success: true,
                    message: 'Se o email existir, você receberá instruções de recuperação.'
                });
            }

            const user = users[0];

            // 2. Gera uma nova senha aleatória (8 caracteres hexadecimais)
            const novaSenhaTemp = crypto.randomBytes(4).toString('hex');

            // 3. Criptografa a nova senha
            const hash = await bcrypt.hash(novaSenhaTemp, 10);

            // 4. Salva no banco
            await this.db.execute(
                "UPDATE usuarios_painel SET senha = ? WHERE id = ?",
                [hash, user.id]
            );

            // 5. Envia o email
            if (process.env.SMTP_USER) {
                await transporter.sendMail({
                    from: `"Suporte SaaS CRM" <${process.env.SMTP_USER}>`,
                    to: email,
                    subject: 'Redefinição de Senha - CRM WhatsApp',
                    html: `
                        <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 10px; max-width: 600px;">
                            <h2 style="color: #4f46e5;">Olá, ${user.nome}!</h2>
                            <p>Recebemos uma solicitação para redefinir sua senha.</p>
                            <p>Sua nova senha temporária é:</p>
                            <h3 style="background: #f3f4f6; padding: 15px; display: inline-block; border-radius: 5px; font-family: monospace;">${novaSenhaTemp}</h3>
                            <p>Por favor, faça login e altere sua senha imediatamente no painel de configurações.</p>
                            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                            <p style="font-size: 12px; color: #666;">Se você não solicitou isso, entre em contato com o suporte.</p>
                        </div>
                    `
                });

                res.json({
                    success: true,
                    message: `Uma nova senha foi enviada para ${email}`
                });

            } else {
                // Fallback para desenvolvimento (mostra no console)
                console.log(`[DEBUG EMAIL] Nova senha para ${email}: ${novaSenhaTemp}`);
                res.json({
                    success: true,
                    message: 'Senha resetada com sucesso! (SMTP não configurado, verifique o console do servidor)'
                });
            }

        } catch(e) {
            console.error('[Auth] Erro ao recuperar senha:', e);
            res.status(500).json({ error: 'Erro ao processar solicitação.' });
        }
    }

    // Troca de Senha (Para usuário logado)
    async trocarSenha(req, res) {
        const { userId, novaSenha } = req.body;

        try {
            if (!userId || !novaSenha) {
                return res.status(400).json({ error: 'Dados incompletos' });
            }

            const hash = await bcrypt.hash(novaSenha, 10);
            await this.db.execute(
                "UPDATE usuarios_painel SET senha = ? WHERE id = ?",
                [hash, userId]
            );

            res.json({ success: true, message: 'Senha alterada com sucesso!' });

        } catch(e) {
            console.error('[Auth] Erro ao trocar senha:', e);
            res.status(500).json({ error: e.message });
        }
    }
}

module.exports = AuthController;