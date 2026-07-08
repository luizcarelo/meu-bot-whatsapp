const repository = require('./dashboard.repository');

async function getStatus() {
  const info = await repository.getModuleInfo();
  return {
    module: 'dashboard',
    label: 'dashboard',
    status: 'READY',
    info: info
  };
}

module.exports = {
  getStatus
};
