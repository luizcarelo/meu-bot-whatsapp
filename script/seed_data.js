require('dotenv').config({ path: require('path').join(__dirname, '../.env') });
const { Client } = require('pg');
const bcrypt = require('bcrypt');

async function seed() {
    const client = new Client({
        host: process.env.DB_HOST,
        user: process.env.DB_USER,
        password: process.env.DB_PASS,
        database: process.env.DB_NAME
    });

    try {
        await client.connect();
        console.log("🌱 [Seed] Iniciando inserção de dados...");

        // 1. Criar Empresa
        const empRes = await client.query(`
            INSERT INTO empresas (nome, ativo, cor_primaria) 
            VALUES ('Empresa Master', true, '#4f46e5') 
            RETURNING id;
        `);
        const empresaId = empRes.rows[0].id;

        // 2. Criar Super Admin
        const senhaHash = await bcrypt.hash('123456', 10);
        await client.query(`
            INSERT INTO usuarios_painel (empresa_id, nome, email, senha, is_super_admin, is_admin, cargo, ativo)
            VALUES ($1, 'Administrador', 'admin@saas.com', $2, true, true, 'Gerente Geral', true);
        `, [empresaId, senhaHash]);

        console.log("✅ [Seed] Usuário 'admin@saas.com' criado com sucesso!");
        console.log("🚀 [Seed] Empresa 'Empresa Master' criada.");
        console.log("✨ Pronto! Agora você pode logar com admin@saas.com / 123456");

    } catch (err) {
        console.error("❌ ERRO NO SEED:", err.message);
    } finally {
        await client.end();
    }
}

seed();