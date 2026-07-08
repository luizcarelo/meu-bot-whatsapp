const { failure } = require('../shared/http/apiResponse');

function errorHandler(err, req, res, next) {
  const statusCode = err.statusCode || 500;
  const code = err.code || 'INTERNAL_ERROR';
  const message = statusCode >= 500 ? 'Erro interno.' : err.message;

  if (statusCode >= 500) {
    console.error('[Backend Modular Error]', err.message);
  }

  return res.status(statusCode).json(failure(code, message));
}

module.exports = errorHandler;
