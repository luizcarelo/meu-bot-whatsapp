// ============================================
// Arquivo: src/middleware/auth.js
// Descrição: Middleware de autenticação
// ============================================

/**
 * Middleware de autenticação para proteger rotas
 * Verifica se a empresa está identificada no header
 *
 * @param {Object} req - Request object
 * @param {Object} res - Response object
 * @param {Function} next - Next middleware
 */
module.exports = (req, res, next) => {

    // ============================================
    // ROTAS PÚBLICAS (SEM AUTENTICAÇÃO)
    // ============================================
    const publicRoutes = [
        '/auth/login',
        '/auth/esqueci-senha',
        '/auth/trocar-senha'
    ];

    // Verifica se é rota pública
    if (publicRoutes.some(route => req.path.startsWith(route))) {
        return next();
    }

    // Rotas do super admin também passam
    if (req.path.startsWith('/super-admin')) {
        return next();
    }

    // ============================================
    // VALIDAÇÃO DA EMPRESA
    // ============================================
    const empresaId = req.headers['x-empresa-id'];
    const userId = req.headers['x-user-id'];

    // Valida se o ID da empresa foi fornecido
    if (!empresaId || isNaN(empresaId)) {
        return res.status(401).json({
            error: 'Acesso não autorizado',
            message: 'ID da empresa não fornecido ou inválido',
            code: 'EMPRESA_ID_MISSING'
        });
    }

    // Adiciona IDs ao request para uso nos controllers
    req.empresaId = parseInt(empresaId);
    req.userId = userId ? parseInt(userId) : null;

    // ============================================
    // LOG DE ACESSO (OPCIONAL - APENAS EM DEV)
    // ============================================
    if (process.env.NODE_ENV === 'development') {
        console.log(`[AUTH] Empresa: ${req.empresaId} | User: ${req.userId || 'N/A'} | ${req.method} ${req.path}`);
    }

    next();
};

/**
 * Middleware adicional para verificar se é administrador
 * Use depois do middleware auth principal
 */
module.exports.isAdmin = async (req, res, next) => {
    if (!req.userId) {
        return res.status(403).json({
            error: 'Acesso negado',
            message: 'Esta ação requer autenticação de usuário'
        });
    }

    try {
        // Aqui você pode fazer uma query para verificar se é admin
        // Por enquanto, apenas passa adiante
        // TODO: Implementar verificação de admin no banco
        next();
    } catch (err) {
        return res.status(500).json({
            error: 'Erro ao verificar permissões',
            message: err.message
        });
    }
};

/**
 * Middleware para validar empresa ativa
 * Use depois do middleware auth principal
 */
module.exports.empresaAtiva = (db) => {
    return async (req, res, next) => {
        try {
            const [empresa] = await db.execute(
                'SELECT ativo FROM empresas WHERE id = ?',
                [req.empresaId]
            );

            if (!empresa.length || !empresa[0].ativo) {
                return res.status(403).json({
                    error: 'Empresa inativa',
                    message: 'Esta empresa está bloqueada. Entre em contato com o suporte.',
                    code: 'EMPRESA_INATIVA'
                });
            }

            next();
        } catch (err) {
            return res.status(500).json({
                error: 'Erro ao verificar status da empresa',
                message: err.message
            });
        }
    };
};