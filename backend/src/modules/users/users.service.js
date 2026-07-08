const repository = require('./users.repository');

async function getStatus() {
  const info = await repository.getModuleInfo();
  return {
    module: 'users',
    label: 'users',
    status: 'READY',
    info: info
  };
}

module.exports = {
  getStatus
};
