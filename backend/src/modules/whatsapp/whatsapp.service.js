const repository = require('./whatsapp.repository');

async function getStatus() {
  const info = await repository.getModuleInfo();
  return {
    module: 'whatsapp',
    label: 'whatsapp',
    status: 'READY',
    info: info
  };
}

module.exports = {
  getStatus
};
