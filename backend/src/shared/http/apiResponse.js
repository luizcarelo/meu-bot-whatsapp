function success(data) {
  return {
    success: true,
    data: data,
    error: null
  };
}

function failure(code, message, data) {
  return {
    success: false,
    data: data === undefined ? null : data,
    error: {
      code: code,
      message: message
    }
  };
}

function sendSuccess(res, data, statusCode) {
  return res.status(statusCode || 200).json(success(data));
}

function sendFailure(res, code, message, statusCode, data) {
  return res.status(statusCode || 400).json(failure(code, message, data));
}

module.exports = {
  success,
  failure,
  sendSuccess,
  sendFailure
};
