const express = require('express');
const asyncHandler = require('../../middlewares/asyncHandler');
const controller = require('./auth.controller');

const router = express.Router();

router.get('/health', asyncHandler(controller.health));

module.exports = router;
