require('dotenv').config({ path: require('path').join(__dirname, '../.env') });
const { Client } = require('pg');

async function fixAccess() {
    const client = new Client({
        host: process.env.DB_HOST,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        database: process.env.DB_NAME
    });

    try {
        await client.connect();
        
        // 1. Ativa a Empresa (vamos ativar todas para garantir)
        await client.query("UPDATE empresas SET ativo = true");
        
        // 2. Ativa o Usuário
        const res = await client.query("UPDATE usuarios_painel SET ativo = true WHERE email = $1 RETURNING empresa_id", ['admin@saas.com']);
        
        if (res.rowCount > 0) {
            console.log("✅ [Sucesso] Usuário e Empresa ativados!");
        } else {
            console.log("⚠️ Usuário admin@saas.com não encontrado no banco.");
        }

    } catch (err) {
        console.error("❌ ERRO:", err.message);
    } finally {
        await client.end();
    }
}

fixAccess();