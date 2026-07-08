const env = require('./config/env');
const { createApp } = require('./app');
const logger = require('./shared/utils/logger');

const app = createApp();

app.listen(env.port, function onListen() {
  logger.info('Backend modular iniciado', {
    port: env.port,
    env: env.nodeEnv
  });
});
