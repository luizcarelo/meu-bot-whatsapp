require('dotenv').config({ path: require('path').join(__dirname, '../.env') });
const { Client } = require('pg');

async function forceActivate() {
    const client = new Client({
        host: process.env.DB_HOST,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        database: process.env.DB_NAME
    });

    try {
        await client.connect();
        
        // 1. Ativa a primeira empresa encontrada (ID 1)
        await client.query("UPDATE empresas SET ativo = true WHERE id = 1");
        
        // 2. Garante que o admin esteja vinculado à empresa ativa
        await client.query("UPDATE usuarios_painel SET empresa_id = 1 WHERE email = 'admin@saas.com'");
        
        console.log("✅ [Sucesso] Empresa 1 ativada e usuário admin vinculado!");
    } catch (err) {
        console.error("❌ ERRO:", err.message);
    } finally {
        await client.end();
    }
}

forceActivate();