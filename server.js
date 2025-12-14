// ============================================
// Arquivo: server.js
// Descrição: Ponto de entrada da aplicação SaaS CRM (Otimizado)
// ============================================

require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const session = require('express-session'); // Adicionado para gestão de sessão

// Configuração de Logs e Tratamento de Exceções Globais
process.on('uncaughtException', (err) => {
    if (err.code === 'EADDRINUSE') return;
    console.error('❌ ERRO CRÍTICO NÃO TRATADO:', err);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('❌ PROMISE REJEITADA NÃO TRATADA:', reason);
});

// Configuração de Pastas Essenciais
const uploadDir = path.join(__dirname, 'public/uploads');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
    console.log(`📁 Pasta de uploads verificada: ${uploadDir}`);
}

const app = express();
const server = http.createServer(app);

// Configuração de Sessão (CRUCIAL PARA O LOGIN FUNCIONAR)
app.use(session({
    secret: process.env.SESSION_SECRET || 'segredo_padrao_dev_123',
    resave: false,
    saveUninitialized: false,
    cookie: { 
        secure: process.env.NODE_ENV === 'production', // true apenas se tiver HTTPS
        maxAge: 1000 * 60 * 60 * 24 // 1 dia
    }
}));

// Configuração do Socket.IO
const io = new Server(server, {
    cors: {
        origin: "*", // Em produção, restrinja para seu domínio
        methods: ["GET", "POST"]
    },
    maxHttpBufferSize: 1e8 // 100 MB
});

// Middlewares Globais
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Configuração de View Engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));

// Middleware Global de Variáveis (Torna user acessível em todas as views)
app.use((req, res, next) => {
    res.locals.user = req.session.user || null;
    res.locals.isMobile = /mobile|android|iphone/i.test(req.headers['user-agent'] || '');
    next();
});

// --- CORREÇÃO DE ERRO DE CONSOLE (Favicon) ---
app.get('/favicon.ico', (req, res) => res.status(204).end());

// Importação de Rotas
const routes = require('./routes/index'); // Certifique-se que o arquivo esteja em routes/index.js
app.use('/', routes);

// Tratamento de Erro 404
app.use((req, res) => {
    if (req.accepts('html')) {
        res.status(404).render('login', { erro: 'Página não encontrada', titulo: '404' });
        return;
    }
    res.status(404).json({ error: 'Endpoint não encontrado' });
});

// --- SISTEMA DE GRACEFUL SHUTDOWN (Mantido do seu código original) ---
async function gracefulShutdown(signal) {
    console.log(`\n🛑 Recebido sinal ${signal}. Encerrando graciosamente...`);
    try {
        await new Promise((resolve) => server.close(resolve));
        console.log('✅ Servidor HTTP fechado.');
        process.exit(0);
    } catch (err) {
        console.error('❌ Erro ao encerrar:', err);
        process.exit(1);
    }
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Inicialização do Servidor
const PORT = process.env.PORT || 50010;

server.on('error', (e) => {
    if (e.code === 'EADDRINUSE') {
        console.error(`\n❌ ERRO FATAL: A porta ${PORT} já está em uso!`);
        console.error(`🛠️  Execute: node script/force_stop.js`);
        process.exit(1);
    } else {
        console.error('❌ Erro desconhecido no servidor HTTP:', e);
    }
});

server.listen(PORT, () => {
    console.log(`\n🚀 SISTEMA DE GESTÃO SAAS INICIADO`);
    console.log(`🌐 URL: http://localhost:${PORT}`);
    console.log(`============================================`);
});