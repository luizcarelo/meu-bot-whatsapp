const repository = require('./crm.repository');

async function getStatus() {
  const info = await repository.getModuleInfo();
  return {
    module: 'crm',
    label: 'crm',
    status: 'READY',
    info: info
  };
}

module.exports = {
  getStatus
};
