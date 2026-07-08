const repository = require('./tenants.repository');

async function getStatus() {
  const info = await repository.getModuleInfo();
  return {
    module: 'tenants',
    label: 'tenants',
    status: 'READY',
    info: info
  };
}

module.exports = {
  getStatus
};
