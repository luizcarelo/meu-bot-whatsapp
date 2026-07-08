const repository = require('./auth.repository');

async function getStatus() {
  const info = await repository.getModuleInfo();
  return {
    module: 'auth',
    label: 'auth',
    status: 'READY',
    info: info
  };
}

module.exports = {
  getStatus
};
