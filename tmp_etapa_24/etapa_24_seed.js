
const db = require('/usr/src/app/src/config/db');
const bcrypt = require('/usr/src/app/node_modules/bcryptjs');


function value(name, def) {
    return process.env[name] || def;
}

const cfg = {
    superEmail: value('ETAPA24_SUPER_EMAIL', 'superadmin.teste@saas.local'),
    superPassword: value('ETAPA24_SUPER_PASSWORD', '123456'),
    clienteNome: value('ETAPA24_CLIENTE_NOME', 'Cliente Teste LTDA'),
    clienteEmail: value('ETAPA24_CLIENTE_EMAIL', 'admin.cliente.teste@saas.local'),
    clientePassword: value('ETAPA24_CLIENTE_PASSWORD', '123456')
};

async function q(sql, params) {
    return await db.query(sql, params || []);
}

async function tableExists(name) {
    const rows = await q(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = ?",
        [name]
    );
    return rows.length > 0;
}

async function columns(table) {
    const rows = await q(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = ?",
        [table]
    );
    const out = {};
    for (const r of rows) {
        out[r.column_name] = true;
    }
    return out;
}

function pick(cols, data) {
    const out = {};
    for (const k of Object.keys(data)) {
        if (cols[k]) {
            out[k] = data[k];
        }
    }
    return out;
}

async function selectOne(sql, params) {
    const rows = await q(sql, params || []);
    if (!rows || rows.length === 0) return null;
    return rows[0];
}

async function insertReturning(table, data) {
    const keys = Object.keys(data);
    const placeholders = keys.map(function () { return '?'; }).join(', ');
    const cols = keys.join(', ');
    const vals = keys.map(k => data[k]);
    const sql = "INSERT INTO " + table + " (" + cols + ") VALUES (" + placeholders + ") RETURNING id";
    const rows = await q(sql, vals);
    return rows[0].id;
}

async function updateById(table, id, data) {
    const keys = Object.keys(data);
    if (keys.length === 0) return false;

    const sets = keys.map(k => k + " = ?").join(', ');
    const vals = keys.map(k => data[k]);
    vals.push(id);

    await q("UPDATE " + table + " SET " + sets + " WHERE id = ?", vals);
    return true;
}

async function ensureEmpresaMaster(empCols) {
    let master = null;

    if (empCols.id) {
        master = await selectOne("SELECT id FROM empresas WHERE id = ?", [1]);
    }

    if (master && master.id) {
        const upd = pick(empCols, {
            nome: 'Super Admin',
            ativo: 1,
            plano: 'master',
            limite_usuarios: 9999
        });
        await updateById('empresas', master.id, upd);
        return { id: master.id, created: false };
    }

    const data = pick(empCols, {
        id: 1,
        nome: 'Super Admin',
        ativo: 1,
        plano: 'master',
        limite_usuarios: 9999,
        created_at: new Date()
    });

    if (!data.nome && empCols.nome_empresa) {
        data.nome_empresa = 'Super Admin';
    }

    const id = await insertReturning('empresas', data);
    return { id: id, created: true };
}

async function ensureEmpresaCliente(empCols) {
    let emp = null;

    if (empCols.nome) {
        emp = await selectOne("SELECT id FROM empresas WHERE nome = ? LIMIT 1", [cfg.clienteNome]);
    }

    if (emp && emp.id) {
        const upd = pick(empCols, {
            nome: cfg.clienteNome,
            ativo: 1,
            plano: 'teste',
            limite_usuarios: 10
        });
        await updateById('empresas', emp.id, upd);
        return { id: emp.id, created: false };
    }

    const data = pick(empCols, {
        nome: cfg.clienteNome,
        ativo: 1,
        plano: 'teste',
        limite_usuarios: 10,
        created_at: new Date()
    });

    if (!data.nome && empCols.nome_empresa) {
        data.nome_empresa = cfg.clienteNome;
    }

    const id = await insertReturning('empresas', data);
    return { id: id, created: true };
}

async function ensureUsuario(userCols, dataBase) {
    const email = dataBase.email;
    let user = null;

    if (userCols.email) {
        user = await selectOne("SELECT id FROM usuarios_painel WHERE email = ? LIMIT 1", [email]);
    }

    const data = pick(userCols, dataBase);

    if (user && user.id) {
        await updateById('usuarios_painel', user.id, data);
        return { id: user.id, created: false };
    }

    const id = await insertReturning('usuarios_painel', data);
    return { id: id, created: true };
}

async function ensureSetor(setorCols, empresaId) {
    if (!setorCols || !setorCols.empresa_id || !setorCols.nome) {
        return { skipped: true, reason: 'colunas insuficientes' };
    }

    const existing = await selectOne(
        "SELECT id FROM setores WHERE empresa_id = ? AND nome = ? LIMIT 1",
        [empresaId, 'Geral']
    );

    if (existing && existing.id) {
        return { id: existing.id, created: false };
    }

    const data = pick(setorCols, {
        empresa_id: empresaId,
        nome: 'Geral',
        ordem: 1,
        padrao: 1,
        cor: '#ef4444',
        mensagem_saudacao: 'Olá, seja bem-vindo ao atendimento.'
    });

    const id = await insertReturning('setores', data);
    return { id: id, created: true };
}

async function main() {
    const result = {
        ok: false,
        tables: {},
        master: {},
        tenant: {},
        users: {},
        auxiliares: {}
    };

    result.tables.empresas = await tableExists('empresas');
    result.tables.usuarios_painel = await tableExists('usuarios_painel');
    result.tables.setores = await tableExists('setores');

    if (!result.tables.empresas || !result.tables.usuarios_painel) {
        throw new Error('Tabelas obrigatorias empresas ou usuarios_painel nao encontradas.');
    }

    const empCols = await columns('empresas');
    const userCols = await columns('usuarios_painel');
    const setorCols = result.tables.setores ? await columns('setores') : null;

    const master = await ensureEmpresaMaster(empCols);
    const tenant = await ensureEmpresaCliente(empCols);

    const superHash = await bcrypt.hash(cfg.superPassword, 10);
    const clienteHash = await bcrypt.hash(cfg.clientePassword, 10);

    const superUser = await ensureUsuario(userCols, {
        empresa_id: master.id,
        nome: 'Super Admin Teste',
        email: cfg.superEmail,
        senha: superHash,
        is_admin: 1,
        cargo: 'Super Admin',
        ativo: 1,
        created_at: new Date()
    });

    const tenantUser = await ensureUsuario(userCols, {
        empresa_id: tenant.id,
        nome: 'Admin Cliente Teste',
        email: cfg.clienteEmail,
        senha: clienteHash,
        is_admin: 1,
        cargo: 'Gerente',
        ativo: 1,
        created_at: new Date()
    });

    let setorTenant = { skipped: true, reason: 'tabela setores ausente' };
    if (result.tables.setores) {
        setorTenant = await ensureSetor(setorCols, tenant.id);
    }

    result.master = master;
    result.tenant = tenant;
    result.users.super_admin = superUser;
    result.users.tenant_admin = tenantUser;
    result.auxiliares.setor_tenant = setorTenant;
    result.ok = true;

    console.log(JSON.stringify(result, null, 2));

    if (db.close) {
        try { await db.close(); } catch (e) {}
    }

    process.exit(0);
}

main().catch(async function (err) {
    console.error(JSON.stringify({
        ok: false,
        error: err.message,
        stack: err.stack
    }, null, 2));

    if (db.close) {
        try { await db.close(); } catch (e) {}
    }

    process.exit(1);
});
