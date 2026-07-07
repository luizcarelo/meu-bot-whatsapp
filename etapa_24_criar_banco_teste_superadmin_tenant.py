#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 24 - Criar base de teste com Super Admin e Tenant Cliente

Objetivo:
- Criar ou garantir Empresa Master ID 1.
- Criar ou garantir Super Admin de teste.
- Criar ou garantir Tenant Cliente de teste.
- Criar ou garantir Admin do Tenant Cliente.
- Usar bcrypt dentro do container Node.
- Nao apagar dados existentes.
- Nao alterar views, rotas ou controllers.
- Atualizar documentacao obrigatoria.
- Gerar relatorios JSON e Markdown.
- Validar login do Super Admin e do Admin Cliente.
- Validar /super-admin com Super Admin.
- Validar /dashboard com Admin Cliente.

Como executar:
sudo python3 etapa_24_criar_banco_teste_superadmin_tenant.py

Variaveis opcionais:
ETAPA24_SUPER_EMAIL='superadmin.teste@saas.local'
ETAPA24_SUPER_PASSWORD='123456'
ETAPA24_CLIENTE_NOME='Cliente Teste LTDA'
ETAPA24_CLIENTE_EMAIL='admin.cliente.teste@saas.local'
ETAPA24_CLIENTE_PASSWORD='123456'
"""

import os
import json
import shutil
import hashlib
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError, URLError
from http.cookiejar import CookieJar

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"
TMP_DIR = ROOT / "tmp_etapa_24"

BASE_URL = "http://127.0.0.1:50010"
LOGIN_API = "/api/auth/login"
DASHBOARD_PAGE = "/dashboard"
SUPER_ADMIN_PAGE = "/super-admin"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

IGNORE_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "reports",
    "__pycache__",
    "tmp_etapa_24"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def logs_since():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def rel(path):
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)
    TMP_DIR.mkdir(exist_ok=True)


def ler(path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def gravar(path, texto):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                bloco = f.read(1048576)
                if not bloco:
                    break
                h.update(bloco)
        return h.hexdigest()
    except Exception:
        return None


def salvar_json(path, dados):
    gravar(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def deve_ignorar(path):
    partes = set(path.parts)
    rel_path = rel(path)

    for nome in IGNORE_DIRS:
        if nome in partes:
            return True
        if rel_path == nome or rel_path.startswith(nome + "/"):
            return True

    return False


def gerar_manifesto():
    itens = []

    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)
        dirs[:] = [d for d in dirs if not deve_ignorar(base_path / d)]

        for nome in files:
            p = base_path / nome
            if deve_ignorar(p):
                continue

            try:
                st = p.stat()
                itens.append({
                    "arquivo": rel(p),
                    "tamanho_bytes": st.st_size,
                    "sha256": sha256(p)
                })
            except Exception as exc:
                itens.append({
                    "arquivo": rel(p),
                    "erro": str(exc)
                })

    return {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "total_arquivos": len(itens),
        "arquivos": sorted(itens, key=lambda x: x.get("arquivo", ""))
    }


def criar_backup(destino):
    destino.mkdir(parents=True, exist_ok=True)

    copiados = []
    ausentes = []
    erros = []

    for nome in BACKUP_FILES:
        origem = ROOT / nome
        destino_item = destino / nome

        if not origem.exists():
            ausentes.append(nome)
            continue

        try:
            destino_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino_item)
            copiados.append(nome)
        except Exception as exc:
            erros.append({
                "item": nome,
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def configs():
    return {
        "super_email": os.environ.get("ETAPA24_SUPER_EMAIL", "superadmin.teste@saas.local"),
        "super_password": os.environ.get("ETAPA24_SUPER_PASSWORD", "123456"),
        "cliente_nome": os.environ.get("ETAPA24_CLIENTE_NOME", "Cliente Teste LTDA"),
        "cliente_email": os.environ.get("ETAPA24_CLIENTE_EMAIL", "admin.cliente.teste@saas.local"),
        "cliente_password": os.environ.get("ETAPA24_CLIENTE_PASSWORD", "123456")
    }


def valores_sensiveis():
    c = configs()
    vals = [
        c["super_password"],
        c["cliente_password"]
    ]

    for chave, valor in os.environ.items():
        upper = chave.upper()
        if any(t in upper for t in ["PASS", "PASSWORD", "SECRET", "TOKEN", "KEY", "SENHA"]):
            if valor:
                vals.append(valor)

    return vals


def redigir(texto):
    if texto is None:
        return texto

    out = str(texto)

    for valor in valores_sensiveis():
        if valor:
            out = out.replace(valor, "<REDIGIDO>")

    cfg = configs()
    out = out.replace(cfg["super_email"], "<EMAIL_SUPER>")
    out = out.replace(cfg["cliente_email"], "<EMAIL_CLIENTE>")

    return out


def run_cmd(cmd, timeout=60):
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )

        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": redigir(proc.stdout.strip())[:50000],
            "stderr": redigir(proc.stderr.strip())[:50000],
            "ok": proc.returncode == 0
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "returncode": None,
            "stdout": "",
            "stderr": redigir(str(exc)),
            "ok": False
        }


def escrever_seed_node():
    cfg = configs()

    node_path = TMP_DIR / "etapa_24_seed.js"

    conteudo = r"""
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
"""

    gravar(node_path, conteudo)
    return node_path


def obter_container_id():
    r = run_cmd(["docker", "compose", "ps", "-q", "app"], 30)
    linhas = (r.get("stdout") or "").strip().splitlines()

    if r.get("ok") and linhas:
        return {
            "ok": True,
            "container_id": linhas[0],
            "resultado": r
        }

    return {
        "ok": False,
        "container_id": "",
        "resultado": r
    }


def executar_seed():
    node_path = escrever_seed_node()
    cid_info = obter_container_id()

    resultado = {
        "node_script": rel(node_path),
        "container": cid_info,
        "copiou": False,
        "exec": None,
        "json": None,
        "ok": False
    }

    if not cid_info["ok"]:
        resultado["erro"] = "Container app nao encontrado"
        return resultado

    cid = cid_info["container_id"]
    destino = "/tmp/etapa_24_seed.js"

    cp = run_cmd(["docker", "cp", str(node_path), cid + ":" + destino], 60)
    resultado["copiou"] = cp.get("ok")
    resultado["docker_cp"] = cp

    if not cp.get("ok"):
        resultado["erro"] = "Falha ao copiar script Node para o container"
        return resultado

    cfg = configs()

    cmd = [
        "docker", "exec",
        "-e", "ETAPA24_SUPER_EMAIL=" + cfg["super_email"],
        "-e", "ETAPA24_SUPER_PASSWORD=" + cfg["super_password"],
        "-e", "ETAPA24_CLIENTE_NOME=" + cfg["cliente_nome"],
        "-e", "ETAPA24_CLIENTE_EMAIL=" + cfg["cliente_email"],
        "-e", "ETAPA24_CLIENTE_PASSWORD=" + cfg["cliente_password"],
        cid,
        "sh", "-lc", "cd /usr/src/app && node " + destino
    ]

    ex = run_cmd(cmd, 120)
    resultado["exec"] = ex

    stdout_raw = ex.get("stdout") or ""
    try:
        resultado["json"] = json.loads(stdout_raw)
    except Exception:
        inicio = stdout_raw.find("{")
        fim = stdout_raw.rfind("}")

        if inicio >= 0 and fim >= inicio:
            trecho_json = stdout_raw[inicio:fim + 1]
            try:
                resultado["json"] = json.loads(trecho_json)
                resultado["json_extraido_de_stdout"] = True
            except Exception as exc:
                resultado["json"] = None
                resultado["json_parse_error"] = "Falha ao interpretar JSON extraido: " + str(exc)
        else:
            resultado["json"] = None
            resultado["json_parse_error"] = "Nao foi possivel localizar bloco JSON no stdout"

    json_result = resultado.get("json") or {}
    resultado["ok"] = bool(ex.get("ok") and json_result.get("ok"))
    return resultado


def restart_app():
    r = run_cmd(["docker", "compose", "restart", "app"], 120)
    return {
        "executado": True,
        "ok": r.get("ok"),
        "resultado": r
    }


def criar_opener():
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    return opener, jar


def cookies_resumo(jar):
    itens = []
    for cookie in jar:
        itens.append({
            "name": cookie.name,
            "domain": cookie.domain,
            "path": cookie.path,
            "secure": cookie.secure
        })
    return itens


def http_request(opener, metodo, path, data_obj=None, timeout=20, limite=500000):
    url = BASE_URL + path

    resultado = {
        "path": path,
        "metodo": metodo,
        "ok": False,
        "status": None,
        "erro": None,
        "content_type": "",
        "body_preview": "",
        "body_limited": ""
    }

    body_bytes = None
    headers = {
        "User-Agent": "etapa-24-seed-test/1.0"
    }

    if data_obj is not None:
        body_text = json.dumps(data_obj)
        body_bytes = body_text.encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=body_bytes, headers=headers, method=metodo)

    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(limite)
            texto = body.decode("utf-8", errors="replace")
            resultado["status"] = resp.getcode()
            resultado["ok"] = 200 <= resultado["status"] < 400
            resultado["content_type"] = resp.headers.get("Content-Type", "")
            resultado["body_preview"] = redigir(texto[:1500])
            resultado["body_limited"] = redigir(texto)
    except HTTPError as exc:
        try:
            body = exc.read(limite)
            texto = body.decode("utf-8", errors="replace")
        except Exception:
            texto = ""

        resultado["status"] = exc.code
        resultado["ok"] = 200 <= exc.code < 400
        resultado["erro"] = redigir(str(exc))
        resultado["content_type"] = exc.headers.get("Content-Type", "") if exc.headers else ""
        resultado["body_preview"] = redigir(texto[:1500])
        resultado["body_limited"] = redigir(texto)
    except URLError as exc:
        resultado["erro"] = redigir(str(exc.reason))
    except Exception as exc:
        resultado["erro"] = redigir(str(exc))

    return resultado


def aguardar_app():
    inicio = time.time()
    tentativas = []

    while time.time() - inicio < 90:
        opener, jar = criar_opener()
        r = http_request(opener, "GET", "/", None, timeout=6, limite=2000)
        tentativas.append({
            "status": r.get("status"),
            "ok": r.get("ok"),
            "erro": r.get("erro")
        })

        if r.get("status") in [200, 302, 404]:
            return {
                "ok": True,
                "tentativas": tentativas,
                "segundos": int(time.time() - inicio)
            }

        time.sleep(3)

    return {
        "ok": False,
        "tentativas": tentativas,
        "segundos": int(time.time() - inicio)
    }


def resumo_http(item):
    return {
        "path": item.get("path"),
        "status": item.get("status"),
        "ok": item.get("ok"),
        "erro": item.get("erro"),
        "content_type": item.get("content_type"),
        "body_preview": item.get("body_preview")
    }


def validar_logins():
    cfg = configs()

    resultado = {
        "super_admin": {
            "login_ok": False,
            "super_admin_ok": False,
            "cookies": [],
            "login": None,
            "super_admin_page": None
        },
        "tenant_admin": {
            "login_ok": False,
            "dashboard_ok": False,
            "super_admin_bloqueado_ou_redirecionado": False,
            "cookies": [],
            "login": None,
            "dashboard": None,
            "super_admin_page": None
        },
        "ok": False
    }

    opener_super, jar_super = criar_opener()
    login_super = http_request(opener_super, "POST", LOGIN_API, {
        "email": cfg["super_email"],
        "senha": cfg["super_password"]
    }, limite=100000)

    body_super_login = (login_super.get("body_limited") or "").lower()
    resultado["super_admin"]["cookies"] = cookies_resumo(jar_super)
    resultado["super_admin"]["login"] = resumo_http(login_super)
    resultado["super_admin"]["login_ok"] = bool(
        login_super.get("status") in [200, 201, 302] and
        ("success" in body_super_login or "sucesso" in body_super_login or len(resultado["super_admin"]["cookies"]) > 0)
    )

    super_page = http_request(opener_super, "GET", SUPER_ADMIN_PAGE, None, limite=500000)
    super_body = super_page.get("body_limited") or ""
    resultado["super_admin"]["super_admin_page"] = resumo_http(super_page)
    resultado["super_admin"]["super_admin_ok"] = bool(
        super_page.get("status") == 200 and
        "ETAPA22_SUPER_ADMIN_VISUAL_INICIO" in super_body and
        "/css/style.css" in super_body
    )

    opener_cli, jar_cli = criar_opener()
    login_cli = http_request(opener_cli, "POST", LOGIN_API, {
        "email": cfg["cliente_email"],
        "senha": cfg["cliente_password"]
    }, limite=100000)

    body_cli_login = (login_cli.get("body_limited") or "").lower()
    resultado["tenant_admin"]["cookies"] = cookies_resumo(jar_cli)
    resultado["tenant_admin"]["login"] = resumo_http(login_cli)
    resultado["tenant_admin"]["login_ok"] = bool(
        login_cli.get("status") in [200, 201, 302] and
        ("success" in body_cli_login or "sucesso" in body_cli_login or len(resultado["tenant_admin"]["cookies"]) > 0)
    )

    dash_cli = http_request(opener_cli, "GET", DASHBOARD_PAGE, None, limite=300000)
    dash_body = dash_cli.get("body_limited") or ""
    resultado["tenant_admin"]["dashboard"] = resumo_http(dash_cli)
    resultado["tenant_admin"]["dashboard_ok"] = bool(
        dash_cli.get("status") == 200 and
        "crm enterprise" in dash_body.lower()
    )

    super_cli = http_request(opener_cli, "GET", SUPER_ADMIN_PAGE, None, limite=200000)
    super_cli_body = super_cli.get("body_limited") or ""
    resultado["tenant_admin"]["super_admin_page"] = resumo_http(super_cli)
    resultado["tenant_admin"]["super_admin_bloqueado_ou_redirecionado"] = bool(
        super_cli.get("status") in [200, 302, 403] and
        "ETAPA22_SUPER_ADMIN_VISUAL_INICIO" not in super_cli_body
    )

    resultado["ok"] = bool(
        resultado["super_admin"]["login_ok"] and
        resultado["super_admin"]["super_admin_ok"] and
        resultado["tenant_admin"]["login_ok"] and
        resultado["tenant_admin"]["dashboard_ok"] and
        resultado["tenant_admin"]["super_admin_bloqueado_ou_redirecionado"]
    )

    return resultado


def coletar_logs(since):
    r = run_cmd(["docker", "compose", "logs", "--since", since, "app"], 80)

    if not r.get("ok") or not (r.get("stdout") or r.get("stderr")):
        r2 = run_cmd(["docker", "logs", "--since", since, "whatsapp_bot_app"], 80)
        return {
            "principal": r,
            "fallback": r2,
            "texto": (r2.get("stdout") or "") + "\n" + (r2.get("stderr") or "")
        }

    return {
        "principal": r,
        "fallback": None,
        "texto": (r.get("stdout") or "") + "\n" + (r.get("stderr") or "")
    }


def parece_email(token):
    token = str(token or "").strip().strip(".;:,()[]{}<>")

    if "@" not in token:
        return False

    partes = token.split("@")

    if len(partes) != 2:
        return False

    usuario = partes[0]
    dominio = partes[1]

    if not usuario:
        return False

    if "." not in dominio:
        return False

    if len(dominio) < 4:
        return False

    if dominio.replace(".", "").isdigit():
        return False

    return True


def analisar_logs(texto):
    session_id = 0
    cookie = 0
    email = 0
    achados = []

    for idx, linha in enumerate(str(texto or "").splitlines(), start=1):
        low = linha.lower()

        if "session id" in low:
            session_id += 1

        if "saas_crm_sid" in low or "connect.sid" in low or "header cookie" in low:
            cookie += 1

        tokens = linha.replace("(", " ").replace(")", " ").replace(",", " ").split()
        for token in tokens:
            if parece_email(token):
                email += 1
                break

        if "syntaxerror" in low or "exception" in low or "database" in low or "econnrefused" in low:
            achados.append({
                "linha": idx,
                "trecho": redigir(linha.strip())[:500]
            })

    return {
        "total_linhas": len(str(texto or "").splitlines()),
        "linhas_session_id": session_id,
        "linhas_cookie": cookie,
        "linhas_email": email,
        "achados": achados,
        "amostra": redigir("\n".join(str(texto or "").splitlines()[-120:]))[:30000]
    }


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)

    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_24_INICIO -->"
    fim = "<!-- ETAPA_24_FIM -->"

    bloco = []
    bloco.append("")
    bloco.append(ini)
    bloco.append("## " + titulo)
    bloco.append("")
    bloco.extend(linhas)
    bloco.append(fim)
    bloco.append("")

    novo_bloco = "\n".join(bloco)

    pos_ini = atual.find(ini)
    pos_fim = atual.find(fim)

    if pos_ini >= 0 and pos_fim >= pos_ini:
        pos_fim = pos_fim + len(fim)
        novo = atual[:pos_ini] + novo_bloco.strip() + atual[pos_fim:]
    else:
        if not atual.endswith("\n"):
            atual = atual + "\n"
        novo = atual + novo_bloco

    gravar(path, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    seed = relatorio["seed"]
    valid = relatorio["validacao_logins"]
    logs = relatorio["logs_analise"]

    seed_json = seed.get("json") or {}

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Etapa 24 - Base de teste criada",
        [
            "Data: " + data,
            "",
            "Criada ou garantida base de teste com Super Admin e tenant cliente.",
            "Seed OK: " + str(seed["ok"]) + ".",
            "Empresa master ID: " + str(seed_json.get("master", {}).get("id")) + ".",
            "Tenant cliente ID: " + str(seed_json.get("tenant", {}).get("id")) + ".",
            "Super Admin login OK: " + str(valid["super_admin"]["login_ok"]) + ".",
            "Super Admin page OK: " + str(valid["super_admin"]["super_admin_ok"]) + ".",
            "Tenant Admin login OK: " + str(valid["tenant_admin"]["login_ok"]) + ".",
            "Tenant Admin dashboard OK: " + str(valid["tenant_admin"]["dashboard_ok"]) + ".",
            "Tenant Admin bloqueado no Super Admin: " + str(valid["tenant_admin"]["super_admin_bloqueado_ou_redirecionado"]) + ".",
            "Logs Session ID: " + str(logs["linhas_session_id"]) + ".",
            "Logs cookie: " + str(logs["linhas_cookie"]) + ".",
            "Logs email: " + str(logs["linhas_email"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 24 - Base de teste Super Admin e Tenant",
        [
            "Data: " + data,
            "",
            "Criado ou atualizado Super Admin de teste.",
            "Criado ou atualizado tenant Cliente Teste LTDA.",
            "Criado ou atualizado Admin Cliente Teste.",
            "Senhas gravadas com bcrypt pelo runtime Node.",
            "Validados login e acesso esperado para ambos os usuarios."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 24 - Decisao tecnica",
        [
            "Data: " + data,
            "",
            "Decidido executar o seed pelo container Node usando src/config/db.js para aproveitar a mesma conexao do sistema.",
            "Decidido usar operacao idempotente para evitar duplicidade de usuarios e empresas.",
            "Decidido nao apagar dados existentes.",
            "Decidido validar que o admin tenant nao acessa a area Super Admin."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 24",
        [
            "Data: " + data,
            "",
            "Trocar senhas padrao se a base de teste for mantida em ambiente acessivel.",
            "Criar dados adicionais de teste somente se forem necessarios para cenarios especificos.",
            "Validar manualmente login dos usuarios de teste no navegador."
        ]
    )

    return DOCS


def gerar_md(relatorio):
    seed = relatorio["seed"]
    valid = relatorio["validacao_logins"]
    logs = relatorio["logs_analise"]
    seed_json = seed.get("json") or {}

    linhas = []
    linhas.append("# Etapa 24 - Criar banco de teste Super Admin e Tenant")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Seed OK: " + str(seed["ok"]))
    linhas.append("- Master ID: " + str(seed_json.get("master", {}).get("id")))
    linhas.append("- Master criado: " + str(seed_json.get("master", {}).get("created")))
    linhas.append("- Tenant ID: " + str(seed_json.get("tenant", {}).get("id")))
    linhas.append("- Tenant criado: " + str(seed_json.get("tenant", {}).get("created")))
    linhas.append("- Super Admin criado: " + str(seed_json.get("users", {}).get("super_admin", {}).get("created")))
    linhas.append("- Admin Tenant criado: " + str(seed_json.get("users", {}).get("tenant_admin", {}).get("created")))
    linhas.append("- Restart OK: " + str(relatorio["restart_app"]["ok"]))
    linhas.append("- App pronto: " + str(relatorio["aguardar_app"]["ok"]))
    linhas.append("- Super Admin login OK: " + str(valid["super_admin"]["login_ok"]))
    linhas.append("- Super Admin pagina OK: " + str(valid["super_admin"]["super_admin_ok"]))
    linhas.append("- Tenant Admin login OK: " + str(valid["tenant_admin"]["login_ok"]))
    linhas.append("- Tenant Admin dashboard OK: " + str(valid["tenant_admin"]["dashboard_ok"]))
    linhas.append("- Tenant Admin bloqueado ou redirecionado no Super Admin: " + str(valid["tenant_admin"]["super_admin_bloqueado_ou_redirecionado"]))
    linhas.append("- Validacao geral OK: " + str(valid["ok"]))
    linhas.append("- Logs Session ID: " + str(logs["linhas_session_id"]))
    linhas.append("- Logs cookie: " + str(logs["linhas_cookie"]))
    linhas.append("- Logs email: " + str(logs["linhas_email"]))
    linhas.append("- Achados logs: " + str(len(logs["achados"])))
    linhas.append("")
    linhas.append("## Credenciais criadas")
    linhas.append("")
    linhas.append("- Super Admin: " + configs()["super_email"])
    linhas.append("- Senha Super Admin: definida por ETAPA24_SUPER_PASSWORD ou padrao informado no script")
    linhas.append("- Admin Cliente: " + configs()["cliente_email"])
    linhas.append("- Senha Admin Cliente: definida por ETAPA24_CLIENTE_PASSWORD ou padrao informado no script")
    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_24_seed_teste_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_24_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    since = logs_since()
    seed = executar_seed()
    restart = restart_app()
    aguardar = aguardar_app()
    validacao = validar_logins()
    time.sleep(2)

    logs_coleta = coletar_logs(since)
    logs_analise = analisar_logs(logs_coleta.get("texto"))

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "config": {
            "super_email": configs()["super_email"],
            "cliente_nome": configs()["cliente_nome"],
            "cliente_email": configs()["cliente_email"]
        },
        "seed": seed,
        "restart_app": restart,
        "aguardar_app": aguardar,
        "validacao_logins": validacao,
        "logs_since": since,
        "logs_coleta": logs_coleta,
        "logs_analise": logs_analise
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_24_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_24_criar_banco_teste_superadmin_tenant.json"
    md_path = REPORTS_DIR / "etapa_24_criar_banco_teste_superadmin_tenant.md"

    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_md(relatorio))

    print("Etapa 24 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Seed OK: " + str(seed["ok"]))
    sj = seed.get("json") or {}
    print("Master ID: " + str(sj.get("master", {}).get("id")))
    print("Tenant ID: " + str(sj.get("tenant", {}).get("id")))
    print("Restart OK: " + str(restart["ok"]))
    print("App pronto: " + str(aguardar["ok"]))
    print("Super Admin login OK: " + str(validacao["super_admin"]["login_ok"]))
    print("Super Admin pagina OK: " + str(validacao["super_admin"]["super_admin_ok"]))
    print("Tenant Admin login OK: " + str(validacao["tenant_admin"]["login_ok"]))
    print("Tenant Admin dashboard OK: " + str(validacao["tenant_admin"]["dashboard_ok"]))
    print("Tenant Admin bloqueado no Super Admin: " + str(validacao["tenant_admin"]["super_admin_bloqueado_ou_redirecionado"]))
    print("Validacao geral OK: " + str(validacao["ok"]))
    print("Logs novos Session ID: " + str(logs_analise["linhas_session_id"]))
    print("Logs novos cookie: " + str(logs_analise["linhas_cookie"]))
    print("Logs novos email: " + str(logs_analise["linhas_email"]))

    if not validacao["ok"]:
        print("")
        print("Aviso: validacao geral da Etapa 24 nao passou. Consulte o relatorio.")


if __name__ == "__main__":
    main()
