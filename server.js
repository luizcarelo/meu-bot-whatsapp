/**
 * server.js
 * Entry Point do SAAS WhatsApp & CRM
 * Versão: 8.1 - Fix RedisStore Constructor & Deep Debug
 * Autor: Sistemas de Gestão
 */

require('dotenv').config({ path: require('path').join(__dirname, 'script', '.env') });
const express = require('express');
const session = require('express-session');
const path = require('path');
const http = require('http');
const cors = require('cors');
const { Server } = require('socket.io');
const { createClient } = require('redis');

// ==============================================================================
// BLINDAGEM DO REDIS STORE (Correção do erro "not a constructor")
// ==============================================================================
let RedisStore;
try {
    const connectRedis = require('connect-redis');
    
    // Detecta se é versão nova (com .default) ou antiga (função factory)
    if (connectRedis.default) {
        RedisStore = connectRedis.default;
    } else {
        try {
            // Tenta inicializar como Factory (padrão v6 ou inferior)
            RedisStore = connectRedis(session);
        } catch (err) {
            // Se der erro ao chamar como função, assume que é a classe direta
            RedisStore = connectRedis;
        }
    }
} catch (e) {
    console.error('❌ Erro crítico: module connect-redis não encontrado. Execute: npm install connect-redis');
    process.exit(1);
}

// Importações internas
const db = require('./src/config/db');
const indexRoutes = require('./routes/index');
const apiRoutes = require('./routes/api');
const SessionManager = require('./src/managers/SessionManager');

const app = express();
const server = http.createServer(app);
const PORT = process.env.PORT || 3000;

// ==============================================================================
// 1. Redis Client (Infraestrutura)
// ==============================================================================
const redisClient = createClient({
    url: `redis://${process.env.REDIS_HOST || '127.0.0.1'}:${process.env.REDIS_PORT || 6379}`,
    password: process.env.REDIS_PASSWORD || undefined,
    legacyMode: false
});

redisClient.on('error', (err) => console.error('❌ [Redis Error]', err));
redisClient.on('connect', () => console.log('🔌 [Redis] Conectado com sucesso.'));

(async () => {
    await redisClient.connect();

    // ==============================================================================
    // 2. Socket.IO (Real-time)
    // ==============================================================================
    const io = new Server(server, {
        cors: { origin: "*", methods: ["GET", "POST"] },
        pingTimeout: 60000
    });

    // ==============================================================================
    // 3. Middlewares Globais
    // ==============================================================================
    app.use(cors());
    app.use(express.json({ limit: '50mb' }));
    app.use(express.urlencoded({ extended: true, limit: '50mb' }));
    app.use(express.static(path.join(__dirname, 'public')));
    app.set('view engine', 'ejs');
    app.set('views', path.join(__dirname, 'views'));
    app.set('trust proxy', 1); // Essencial para cookies através de proxies

    // ==============================================================================
    // 4. Configuração de Sessão (O Coração do Login)
    // ==============================================================================
    const isHttps = process.env.USE_HTTPS === 'true';

    app.use(session({
        store: new RedisStore({ client: redisClient }),
        name: 'saas_crm_sid', // Nome personalizado do cookie
        secret: process.env.SESSION_SECRET || 'chave_ultra_secreta_debug',
        resave: false,
        saveUninitialized: false,
        rolling: true,
        cookie: {
            secure: isHttps, // Mantenha false se não tiver certeza do SSL
            httpOnly: true,
            maxAge: 1000 * 60 * 60 * 24 // 1 dia
        }
    }));

    // ==============================================================================
    // 5. DEBUGGER DE SESSÃO (O Farejador)
    // ==============================================================================
    app.use((req, res, next) => {
        // Ignora arquivos estáticos para não poluir o log
        if (req.path.match(/\.(css|js|png|jpg|ico|woff|woff2)$/)) return next();

        console.log('\n--- 🔍 DEBUG REQUEST ---');
        console.log(`📡 URL: ${req.method} ${req.url}`);
        console.log(`🔑 Session ID: ${req.sessionID}`);
        
        // Verifica se o cookie chegou
        const cookieHeader = req.headers.cookie;
        console.log(`🍪 Header Cookie: ${cookieHeader ? 'RECEBIDO' : 'AUSENTE ❌'}`);
        if (cookieHeader) console.log(`   Conteúdo: ${cookieHeader.substring(0, 50)}...`);

        // Verifica se o Redis devolveu dados
        if (req.session && req.session.user) {
            console.log(`👤 Usuário Logado: ${req.session.user.email} (Empresa: ${req.session.empresaId})`);
        } else {
            console.log(`👻 Sessão Vazia (Anônimo)`);
        }
        console.log('------------------------');
        
        next();
    });

    // ==============================================================================
    // 6. Inicialização dos Gerentes (Bot WhatsApp)
    // ==============================================================================
    const sessionManager = new SessionManager(io);
    await sessionManager.init();
    app.set('io', io);
    app.set('sessionManager', sessionManager);

    // ==============================================================================
    // 7. Rotas
    // ==============================================================================
    app.use('/', indexRoutes);
    app.use('/api', apiRoutes);

    // Tratamento de 404
    app.use((req, res) => {
        if (req.xhr || req.path.startsWith('/api')) {
            return res.status(404).json({ success: false, message: 'Endpoint não encontrado' });
        }
        res.status(404).render('login', { error: 'Página não encontrada' });
    });

    // Start
    server.listen(PORT, () => {
        console.log(`\n🚀 [System] SAAS Server rodando na porta ${PORT}`);
        console.log(`📡 [Env] ${process.env.NODE_ENV}`);
        console.log(`🔒 [Security] Cookie Secure: ${isHttps ? 'ATIVADO' : 'DESATIVADO'}`);
    });

})();