/**
 * src/middleware/auth.js
 * Descrição: Middleware de Segurança e Controle de Acesso (RBAC)
 * Versão: 7.0 - Hybrid (UX + Security)
 */

/**
 * Verifica se o usuário está logado (Autenticação)
 */
const isAuthenticated = (req, res, next) => {
    // 1. Verifica se a sessão existe e tem usuário
    if (req.session && req.session.user) {
        return next();
    }

    // 2. Se não estiver logado:
    
    // Detecção robusta de API: XHR, rota /api/ ou cabeçalho JSON
    const isApiCall = req.xhr || req.path.startsWith('/api/') || (req.headers.accept && req.headers.accept.indexOf('json') > -1);

    if (isApiCall) {
        return res.status(401).json({
            success: false,
            message: 'Sessão expirada ou inválida. Faça login novamente.',
            code: 'SESSION_EXPIRED'
        });
    }

    // Acesso via Navegador: Redireciona para login
    return res.redirect('/');
};

/**
 * Verifica privilégios administrativos (Autorização)
 * Permite: Admins (is_admin=1) OU Gerentes
 */
const isAdmin = (req, res, next) => {
    const user = req.session?.user;
    
    // Lógica RBAC v7: Admin ou Gerente
    const hasPermission = user && (user.is_admin === 1 || user.cargo === 'Gerente');

    if (hasPermission) {
        return next();
    }
    
    // Tratamento de Erro
    const isApiCall = req.xhr || req.path.startsWith('/api/');
    
    if (isApiCall) {
        return res.status(403).json({ success: false, message: 'Acesso negado. Requer privilégios administrativos.' });
    }
    
    return res.redirect('/dashboard?error=access_denied');
};

/**
 * Verifica privilégios de Super Admin (Multi-tenant)
 * Permite: Apenas usuários da Empresa 1 com flag admin ou cargo Super Admin
 */
const isSuperAdmin = (req, res, next) => {
    const user = req.session?.user;
    const empresaId = req.session?.empresaId;

    // Regra Estrita: Deve pertencer à Empresa 1 (Master) E ter permissão elevada
    const isMasterCompany = empresaId === 1;
    const hasSuperPrivilege = user && (user.is_admin === 1 || user.cargo === 'Super Admin');

    if (isMasterCompany && hasSuperPrivilege) {
        return next();
    }

    // Tratamento de Erro
    const isApiCall = req.xhr || req.path.startsWith('/api/');

    if (isApiCall) {
        return res.status(403).json({ success: false, message: 'Acesso restrito a Super Administradores.' });
    }

    return res.redirect('/dashboard');
};

module.exports = {
    isAuthenticated,
    isAdmin,
    isSuperAdmin
};