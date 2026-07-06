require('dotenv').config({ path: require('path').join(__dirname, '../.env') });
const { Client } = require('pg');

async function check() {
    const client = new Client({
        host: process.env.DB_HOST,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        database: process.env.DB_NAME
    });

    await client.connect();
    const res = await client.query(`
        SELECT u.email, u.empresa_id, e.nome as empresa_nome, e.ativo 
        FROM usuarios_painel u 
        JOIN empresas e ON u.empresa_id = e.id 
        WHERE u.email = 'admin@saas.com'
    `);
    
    if (res.rows.length > 0) {
        console.log("🔍 Dados encontrados:", res.rows[0]);
    } else {
        console.log("❌ Usuário não vinculado a nenhuma empresa no banco!");
    }
    await client.end();
}
check();