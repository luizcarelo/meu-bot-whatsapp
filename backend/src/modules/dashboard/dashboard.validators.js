function validatePlaceholder(input) {
  return {
    valid: true,
    data: input || null,
    errors: []
  };
}

module.exports = {
  validatePlaceholder
};
