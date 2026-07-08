function getDatabaseStatus() {
  return {
    connected: false,
    mode: 'placeholder',
    message: 'Database adapter ainda nao conectado nesta etapa.'
  };
}

module.exports = {
  getDatabaseStatus
};
