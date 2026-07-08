const express = require('express');
const env = require('./config/env');
const errorHandler = require('./middlewares/errorHandler');
const { sendSuccess } = require('./shared/http/apiResponse');

const authRoutes = require('./modules/auth/auth.routes');
const dashboardRoutes = require('./modules/dashboard/dashboard.routes');
const whatsappRoutes = require('./modules/whatsapp/whatsapp.routes');
const crmRoutes = require('./modules/crm/crm.routes');
const tenantsRoutes = require('./modules/tenants/tenants.routes');
const usersRoutes = require('./modules/users/users.routes');

function createApp() {
  const app = express();

  app.disable('x-powered-by');
  app.use(express.json({ limit: '2mb' }));
  app.use(express.urlencoded({ extended: true }));

  app.get('/health', function health(req, res) {
    return sendSuccess(res, {
      service: env.appName,
      status: 'OK',
      layer: 'backend-modular',
      version: '0.1.0'
    });
  });

  app.use('/api/v2/auth', authRoutes);
  app.use('/api/v2/dashboard', dashboardRoutes);
  app.use('/api/v2/whatsapp', whatsappRoutes);
  app.use('/api/v2/crm', crmRoutes);
  app.use('/api/v2/tenants', tenantsRoutes);
  app.use('/api/v2/users', usersRoutes);

  app.use(errorHandler);

  return app;
}

module.exports = {
  createApp
};
