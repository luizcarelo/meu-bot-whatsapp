function getEnv(name, fallbackValue) {
  const value = process.env[name];
  if (value === undefined || value === null || value === '') {
    return fallbackValue;
  }
  return value;
}

const env = {
  nodeEnv: getEnv('NODE_ENV', 'development'),
  port: Number(getEnv('MODULAR_BACKEND_PORT', '50110')),
  appName: getEnv('APP_NAME', 'Engeradios CRM Modular')
};

module.exports = env;
