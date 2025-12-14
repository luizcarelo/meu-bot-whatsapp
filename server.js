/**
 * server.js
 * Arquivo principal de entrada do Sistema SAAS WhatsApp CRM.
 * Otimizado por Sistemas de Gestão para alta performance e escalabilidade.
 */

require('dotenv').config();
const express = require('express');
const http = require('http');
const path = require('path');
const session = require('express-session');
const cors = require('cors');
const compression = require('compression'); 
const { Server } = require("socket.io");
const flash = require('connect-flash');

// Inicialização do App e Servidor HTTP
const app = express();
const server = http.createServer(app);

/**
 * Configuração de Socket.IO com CORS permitindo acesso flexível
 */
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"],
        credentials: true
    }
});

// --- Middlewares Globais ---

// 1. Compressão Gzip
app.use(compression({
    level: 6,
    threshold: 10 * 1000,
    filter: (req, res) => {
        if (req.headers['x-no-compression']) return false;
        return compression.filter(req, res);
    }
}));

// 2. Parsers
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// 3. Segurança e CORS
app.use(cors());

// 4. Sessão
app.use(session({
    secret: process.env.SESSION_SECRET || 'gerenciamento_sistema_secure_key',
    resave: false,
    saveUninitialized: false,
    cookie: { 
        secure: false, // Setar true em produção com HTTPS
        maxAge: 24 * 60 * 60 * 1000 
    }
}));

app.use(flash());

// 5. Arquivos Estáticos
app.use(express.static(path.join(__dirname, 'public'), {
    maxAge: '1d', 
    etag: false
}));

// --- View Engine ---
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// --- Rotas e Middleware de Variáveis ---
const indexRoutes = require('./routes/index');
const apiRoutes = require('./routes/api');

// Middleware para passar variáveis globais para as views
app.use((req, res, next) => {
    res.locals.user = req.session.user || null;
    res.locals.success_msg = req.flash('success_msg');
    res.locals.error_msg = req.flash('error_msg');
    res.locals.error = req.flash('error');
    // Variável global de título para evitar ReferenceError em views genéricas
    res.locals.titulo = 'Sistemas de Gestão - SAAS'; 
    next();
});

app.use('/', indexRoutes);
app.use('/api', apiRoutes);

// --- Tratamento de Erros 404 e 500 ---
app.use((req, res, next) => {
    // CORREÇÃO: Passando 'titulo' explicitamente para garantir que o login.ejs renderize
    res.status(404).render('login', { 
        titulo: 'Login | Página não encontrada',
        error_msg: 'Página não encontrada ou sessão expirada.' 
    });
});

app.use((err, req, res, next) => {
    console.error(`[CRITICAL ERROR]: ${err.stack}`);
    res.status(500).send('Erro Interno do Servidor - Contate o Administrador do Sistema.');
});

// --- Inicialização do Servidor ---
const PORT = process.env.PORT || 50010;

server.listen(PORT, () => {
    console.log(`===========================================================`);
    console.log(` SISTEMAS DE GESTÃO - SAAS CRM RUNNING`);
    console.log(` Ambiente: ${process.env.NODE_ENV || 'Development'}`);
    console.log(` Porta: ${PORT}`);
    console.log(` Compressão: ATIVADA (Gzip level 6)`);
    console.log(`===========================================================`);
});