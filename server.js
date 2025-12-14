// ============================================
// Arquivo: server.js
// Descrição: Ponto de entrada da aplicação SaaS CRM
// ============================================

require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

// Configuração de Logs e Tratamento de Exceções Globais
process.on('uncaughtException', (err) => {
    console.error('❌ ERRO CRÍTICO NÃO TRATADO:', err);
    // Em produção, considerar reiniciar o processo via PM2
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

// Dependências Internas
const db = require('./config/db');
const SessionManager = require('./src/managers/SessionManager');

const app = express();
const server = http.createServer(app);

// Configuração do Socket.IO com CORS e Buffer otimizado
const io = new Server(server, {
    cors: {
        origin: "*", // Em produção, restrinja para o domínio do seu frontend
        methods: ["GET", "POST"]
    },
    maxHttpBufferSize: 1e8, // 100MB para uploads via socket se necessário
    pingTimeout: 60000 // Aumenta tolerância para conexões lentas
});

// Configuração do Express
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Middlewares Globais
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Inicialização do Gerenciador de Sessões (WhatsApp Core)
const sessionManager = new SessionManager(io, db);

// Importação de Rotas
const indexRoutes = require('./routes/index');
app.use('/', indexRoutes);

try {
    // Injeção de Dependências nas Rotas da API
    const apiRoutes = require('./routes/api')(sessionManager, db);
    app.use('/api', apiRoutes);
} catch (error) {
    console.error("❌ Erro crítico ao carregar rotas da API:", error);
}

// Socket.IO Connection Handler Global
io.on('connection', (socket) => {
    // Lógica para salas privadas por empresa (Multi-tenancy via Socket)
    socket.on('join_empresa', (empresaId) => {
        if(empresaId) {
            const room = `empresa_${empresaId}`;
            socket.join(room);
            // console.log(`🔌 Socket ${socket.id} entrou na sala: ${room}`);
        }
    });

    socket.on('disconnect', () => {
        // console.log(`🔌 Socket ${socket.id} desconectado`);
    });
});

// Handler 404
app.use((req, res) => {
    if (req.accepts('html')) {
        res.status(404).render('login', { titulo: 'Página não encontrada - 404' });
        return;
    }
    res.status(404).json({ error: 'Recurso não encontrado' });
});

// Inicialização do Servidor
const PORT = process.env.PORT || 50010;
server.listen(PORT, async () => {
    console.log(`\n🚀 SISTEMA DE GESTÃO SAAS INICIADO`);
    console.log(`🌐 URL: https://chatbot.lcsolucoesdigital.com.br:${PORT}`);
    console.log(`📅 Data: ${new Date().toLocaleString('pt-BR')}`);
    console.log(`============================================`);

    // Auto-Reconexão das Sessões WhatsApp
    console.log('⏳ Iniciando restauração de sessões do WhatsApp...');
    try {
        await sessionManager.reconnectAllSessions();
    } catch (error) {
        console.error('❌ Falha na reconexão automática:', error);
    }
});