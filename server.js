/**
 * server.js
 * Entry Point do SAAS WhatsApp & CRM
 * Versão: 8.2 - Importação Moderna do Redis (v9)
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
// IMPORTAÇÃO MODERNA DO REDIS STORE (Compatível com v7, v8 e v9)
// ==============================================================================
let RedisStore;
try {
    const connectRedis = require('connect-redis');
    // Nas versões novas do pacote, a classe fica guardada dentro da propriedade RedisStore ou default
    RedisStore = connectRedis.RedisStore || connectRedis.default || connectRedis;
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
app.disable('x-powered-by');
// ETAPA14_SECURITY_HEADERS_INICIO
app.use((req, res, next) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Frame-Options', 'SAMEORIGIN');
    res.setHeader('Referrer-Policy', 'no-referrer');
    res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
    next();
});
// ETAPA14_SECURITY_HEADERS_FIM

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
        
        // Verifica se o cookie chegou

        // Verifica se o Redis devolveu dados
        if (req.session && req.session.user) {
            console.log(`[REQ] Usuario autenticado empresa_id=${req.session?.empresaId || 'N/A'}`);
        } else {
            console.log(`👻 Sessão Vazia (Anônimo)`);
        }
        console.log('------------------------');
        
        next();
    });

    // ==============================================================================
    // 6. Inicialização dos Gerentes (Bot WhatsApp)
    // ==============================================================================
    // Adicionamos o 'db' aqui para que o SessionManager consiga salvar no banco de dados
    const sessionManager = new SessionManager(io, db); 
    
    // Trocamos o .init() pelo nome correto da função que existe no arquivo
    sessionManager.initBackgroundJobs(); 
    
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