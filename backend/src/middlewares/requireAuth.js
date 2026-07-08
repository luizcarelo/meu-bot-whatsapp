function requireAuth(req, res, next) {
  const sessionUser = req.session && req.session.usuario ? req.session.usuario : null;

  if (!sessionUser) {
    return res.status(401).json({
      success: false,
      data: null,
      error: {
        code: 'AUTH_REQUIRED',
        message: 'Autenticacao obrigatoria.'
      }
    });
  }

  req.user = sessionUser;
  return next();
}

module.exports = requireAuth;
