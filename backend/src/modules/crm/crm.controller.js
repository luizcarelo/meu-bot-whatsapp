const service = require('./crm.service');
const { sendSuccess } = require('../../shared/http/apiResponse');

async function health(req, res) {
  const data = await service.getStatus();
  return sendSuccess(res, data);
}

module.exports = {
  health
};
