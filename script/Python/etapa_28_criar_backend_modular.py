#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 28 - Criar backend modular em paralelo

Objetivo:
- Criar estrutura backend modular em backend/.
- Criar modulos auth, dashboard, whatsapp, crm, tenants e users.
- Criar middlewares e shared HTTP helpers.
- Criar app.js e server.js modulares independentes.
- Nao alterar backend legado.
- Nao alterar server.js atual.
- Nao alterar routes/api.js atual.
- Nao alterar controllers antigos.
- Nao alterar banco.
- Nao alterar Docker.
- Nao alterar frontend React.
- Criar backup, manifesto, validacao e relatorios.
- Atualizar documentacao obrigatoria.

Como executar:
python3 etapa_28_criar_backend_modular.py
"""

import os
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
BACKEND_DIR = ROOT / "backend"
SRC_DIR = BACKEND_DIR / "src"
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"
DOCS_DIR = ROOT / "docs"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "backend",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md",
    "docs/ARQUITETURA_BACKEND_MODULAR.md",
    "docs/CONTRATOS_API.md",
    "docs/PLANO_MIGRACAO_REACT.md"
]

IGNORE_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "reports",
    "auth_sessions",
    "__pycache__",
    "tmp_etapa_24",
    "frontend/node_modules",
    "frontend/dist",
    "backend/node_modules",
    "backend/dist"
]

MODULES = [
    "auth",
    "dashboard",
    "whatsapp",
    "crm",
    "tenants",
    "users"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)
    BACKEND_DIR.mkdir(exist_ok=True)
    SRC_DIR.mkdir(parents=True, exist_ok=True)


def rel(path):
    try:
        return str(Path(path).relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def ler(path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")


def gravar(path, texto):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")


def sha256(path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            bloco = f.read(1048576)
            if not bloco:
                break
            h.update(bloco)
    return h.hexdigest()


def salvar_json(path, dados):
    gravar(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def deve_ignorar(path):
    partes = set(path.parts)
    caminho = rel(path)
    for nome in IGNORE_DIRS:
        if nome in partes:
            return True
        if caminho == nome or caminho.startswith(nome + "/"):
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


def copiar_item(origem, destino):
    if origem.is_dir():
        if destino.exists():
            shutil.rmtree(destino)
        shutil.copytree(origem, destino, ignore=shutil.ignore_patterns("node_modules", "dist"))
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)


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
            copiar_item(origem, destino_item)
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


def run_cmd(cmd, cwd=None, timeout=300):
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        return {
            "cmd": cmd,
            "cwd": str(cwd or ROOT),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip()[:60000],
            "stderr": proc.stderr.strip()[:60000],
            "ok": proc.returncode == 0
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "cwd": str(cwd or ROOT),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "ok": False
        }


def json_dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def package_json():
    return json_dump({
        "name": "engeradios-crm-backend-modular",
        "private": True,
        "version": "0.1.0",
        "description": "Backend modular em paralelo criado na Etapa 28",
        "main": "src/server.js",
        "scripts": {
            "start": "node src/server.js",
            "check": "node --check src/app.js && node --check src/server.js",
            "check:all": "node scripts/check-syntax.js"
        },
        "dependencies": {
            "express": "latest"
        },
        "devDependencies": {}
    })


def readme_backend():
    return """# Backend Modular

Base criada na Etapa 28.

## Objetivo

Esta pasta contem a nova estrutura modular do backend.

## Estado

Esta base ainda nao substitui o backend legado.

## Comandos

```bash
npm install
npm run check
npm start
```

## Rotas previstas

```text
/health
/api/v2/auth
/api/v2/dashboard
/api/v2/whatsapp
/api/v2/crm
/api/v2/tenants
/api/v2/users
```

## Regra

O backend legado continua funcionando ate que cada modulo novo tenha substituto validado.
"""


def env_js():
    return """function getEnv(name, fallbackValue) {
  const value = process.env[name];
  if (value === undefined || value === null || value === '') {
    return fallbackValue;
  }
  return value;
}

const env = {
  nodeEnv: getEnv('NODE_ENV', 'development'),
  port: Number(getEnv('MODULAR_BACKEND_PORT', '50110')),
  appName: getEnv('APP_NAME', 'Engeradios CRM Modular')
};

module.exports = env;
"""


def db_js():
    return """function getDatabaseStatus() {
  return {
    connected: false,
    mode: 'placeholder',
    message: 'Database adapter ainda nao conectado nesta etapa.'
  };
}

module.exports = {
  getDatabaseStatus
};
"""


def logger_js():
    return """function info(message, meta) {
  if (meta) {
    console.log('[INFO]', message, meta);
    return;
  }
  console.log('[INFO]', message);
}

function warn(message, meta) {
  if (meta) {
    console.warn('[WARN]', message, meta);
    return;
  }
  console.warn('[WARN]', message);
}

function error(message, meta) {
  if (meta) {
    console.error('[ERROR]', message, meta);
    return;
  }
  console.error('[ERROR]', message);
}

module.exports = {
  info,
  warn,
  error
};
"""


def api_response_js():
    return """function success(data) {
  return {
    success: true,
    data: data,
    error: null
  };
}

function failure(code, message, data) {
  return {
    success: false,
    data: data === undefined ? null : data,
    error: {
      code: code,
      message: message
    }
  };
}

function sendSuccess(res, data, statusCode) {
  return res.status(statusCode || 200).json(success(data));
}

function sendFailure(res, code, message, statusCode, data) {
  return res.status(statusCode || 400).json(failure(code, message, data));
}

module.exports = {
  success,
  failure,
  sendSuccess,
  sendFailure
};
"""


def errors_js():
    return """class AppError extends Error {
  constructor(code, message, statusCode) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.statusCode = statusCode || 400;
  }
}

function createError(code, message, statusCode) {
  return new AppError(code, message, statusCode);
}

module.exports = {
  AppError,
  createError
};
"""


def async_handler_js():
    return """function asyncHandler(handler) {
  return function wrappedHandler(req, res, next) {
    Promise.resolve(handler(req, res, next)).catch(next);
  };
}

module.exports = asyncHandler;
"""


def error_handler_js():
    return """const { failure } = require('../shared/http/apiResponse');

function errorHandler(err, req, res, next) {
  const statusCode = err.statusCode || 500;
  const code = err.code || 'INTERNAL_ERROR';
  const message = statusCode >= 500 ? 'Erro interno.' : err.message;

  if (statusCode >= 500) {
    console.error('[Backend Modular Error]', err.message);
  }

  return res.status(statusCode).json(failure(code, message));
}

module.exports = errorHandler;
"""


def require_auth_js():
    return """function requireAuth(req, res, next) {
  const sessionUser = req.session && req.session.usuario ? req.session.usuario : null;

  if (!sessionUser) {
    return res.status(401).json({
      success: false,
      data: null,
      error: {
        code: 'AUTH_REQUIRED',
        message: 'Autenticacao obrigatoria.'
      }
    });
  }

  req.user = sessionUser;
  return next();
}

module.exports = requireAuth;
"""


def app_js():
    return """const express = require('express');
const env = require('./config/env');
const errorHandler = require('./middlewares/errorHandler');
const { sendSuccess } = require('./shared/http/apiResponse');

const authRoutes = require('./modules/auth/auth.routes');
const dashboardRoutes = require('./modules/dashboard/dashboard.routes');
const whatsappRoutes = require('./modules/whatsapp/whatsapp.routes');
const crmRoutes = require('./modules/crm/crm.routes');
const tenantsRoutes = require('./modules/tenants/tenants.routes');
const usersRoutes = require('./modules/users/users.routes');

function createApp() {
  const app = express();

  app.disable('x-powered-by');
  app.use(express.json({ limit: '2mb' }));
  app.use(express.urlencoded({ extended: true }));

  app.get('/health', function health(req, res) {
    return sendSuccess(res, {
      service: env.appName,
      status: 'OK',
      layer: 'backend-modular',
      version: '0.1.0'
    });
  });

  app.use('/api/v2/auth', authRoutes);
  app.use('/api/v2/dashboard', dashboardRoutes);
  app.use('/api/v2/whatsapp', whatsappRoutes);
  app.use('/api/v2/crm', crmRoutes);
  app.use('/api/v2/tenants', tenantsRoutes);
  app.use('/api/v2/users', usersRoutes);

  app.use(errorHandler);

  return app;
}

module.exports = {
  createApp
};
"""


def server_js():
    return """const env = require('./config/env');
const { createApp } = require('./app');
const logger = require('./shared/utils/logger');

const app = createApp();

app.listen(env.port, function onListen() {
  logger.info('Backend modular iniciado', {
    port: env.port,
    env: env.nodeEnv
  });
});
"""


def module_types_js(module_name):
    const_name = module_name.upper().replace('-', '_')
    return """const MODULE_NAME = '{module_name}';

const {const_name}_STATUS = {{
  ACTIVE: 'ACTIVE',
  INACTIVE: 'INACTIVE'
}};

module.exports = {{
  MODULE_NAME,
  {const_name}_STATUS
}};
""".format(module_name=module_name, const_name=const_name)


def module_repository_js(module_name):
    return """async function getModuleInfo() {
  return {
    module: '""" + module_name + """',
    repository: 'placeholder',
    connected: false
  };
}

module.exports = {
  getModuleInfo
};
"""


def module_service_js(module_name):
    label = module_name.replace("-", " ")
    return """const repository = require('./""" + module_name + """.repository');

async function getStatus() {
  const info = await repository.getModuleInfo();
  return {
    module: '""" + module_name + """',
    label: '""" + label + """',
    status: 'READY',
    info: info
  };
}

module.exports = {
  getStatus
};
"""


def module_controller_js(module_name):
    return """const service = require('./{module_name}.service');
const {{ sendSuccess }} = require('../../shared/http/apiResponse');

async function health(req, res) {{
  const data = await service.getStatus();
  return sendSuccess(res, data);
}}

module.exports = {{
  health
}};
""".format(module_name=module_name)


def module_validators_js(module_name):
    return """function validatePlaceholder(input) {
  return {
    valid: true,
    data: input || null,
    errors: []
  };
}

module.exports = {
  validatePlaceholder
};
"""


def module_routes_js(module_name):
    return """const express = require('express');
const asyncHandler = require('../../middlewares/asyncHandler');
const controller = require('./{module_name}.controller');

const router = express.Router();

router.get('/health', asyncHandler(controller.health));

module.exports = router;
""".format(module_name=module_name)


def check_syntax_js():
    return """const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');

const root = path.resolve(__dirname, '..');
const files = [];

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === 'dist') {
        continue;
      }
      walk(full);
      continue;
    }
    if (entry.isFile() && entry.name.endsWith('.js')) {
      files.push(full);
    }
  }
}

walk(path.join(root, 'src'));

for (const file of files) {
  childProcess.execFileSync('node', ['--check', file], { stdio: 'inherit' });
}

console.log('Syntax check OK:', files.length);
"""


def arquivos_backend():
    arquivos = {
        "backend/package.json": package_json(),
        "backend/README.md": readme_backend(),
        "backend/src/config/env.js": env_js(),
        "backend/src/database/db.js": db_js(),
        "backend/src/shared/utils/logger.js": logger_js(),
        "backend/src/shared/http/apiResponse.js": api_response_js(),
        "backend/src/shared/http/errors.js": errors_js(),
        "backend/src/middlewares/asyncHandler.js": async_handler_js(),
        "backend/src/middlewares/errorHandler.js": error_handler_js(),
        "backend/src/middlewares/requireAuth.js": require_auth_js(),
        "backend/src/app.js": app_js(),
        "backend/src/server.js": server_js(),
        "backend/scripts/check-syntax.js": check_syntax_js()
    }

    for module_name in MODULES:
        base = "backend/src/modules/" + module_name + "/" + module_name
        arquivos[base + ".routes.js"] = module_routes_js(module_name)
        arquivos[base + ".controller.js"] = module_controller_js(module_name)
        arquivos[base + ".service.js"] = module_service_js(module_name)
        arquivos[base + ".repository.js"] = module_repository_js(module_name)
        arquivos[base + ".validators.js"] = module_validators_js(module_name)
        arquivos[base + ".types.js"] = module_types_js(module_name)

    return arquivos


def aplicar_backend():
    resultados = []
    for nome, texto in arquivos_backend().items():
        antes = sha256(nome)
        atual = ler(nome)
        alterado = atual != texto

        if alterado:
            gravar(nome, texto)

        depois = sha256(nome)
        resultados.append({
            "arquivo": nome,
            "alterado": alterado,
            "sha256_antes": antes,
            "sha256_depois": depois,
            "tamanho": len(texto)
        })

    return resultados


def validar_sem_asterisco(nome, texto):
    achados = []
    for idx, linha in enumerate(texto.splitlines(), start=1):
        if chr(42) in linha:
            achados.append({
                "arquivo": nome,
                "linha": idx,
                "texto": linha[:300]
            })
    return achados


def arquivos_js_backend():
    out = []
    for caminho in sorted((BACKEND_DIR / "src").rglob(".js")):
        out.append(caminho)
    for caminho in sorted((BACKEND_DIR / "scripts").rglob(".js")):
        out.append(caminho)
    return out


def validar_estrutura():
    obrigatorios = list(arquivos_backend().keys())
    itens = []
    erros = []

    for nome in obrigatorios:
        texto = ler(nome)
        existe = texto is not None
        ast = validar_sem_asterisco(nome, texto or "")
        item = {
            "arquivo": nome,
            "existe": existe,
            "sha256": sha256(nome),
            "sem_asterisco": len(ast) == 0,
            "asteriscos": ast[:10],
            "ok": existe and len(ast) == 0
        }
        itens.append(item)

        if not item["ok"]:
            erros.append(item)

    checks = {
        "tem_backend_dir": BACKEND_DIR.exists(),
        "tem_src_dir": SRC_DIR.exists(),
        "tem_app": (SRC_DIR / "app.js").exists(),
        "tem_server": (SRC_DIR / "server.js").exists(),
        "tem_modules": all((SRC_DIR / "modules" / module_name).exists() for module_name in MODULES),
        "legado_server_preservado": (ROOT / "server.js").exists(),
        "legado_routes_preservado": (ROOT / "routes" / "api.js").exists()
    }

    ok = len(erros) == 0 and all(checks.values())

    return {
        "arquivos": itens,
        "checks": checks,
        "erros": erros,
        "ok": ok
    }


def node_check():
    resultados = []

    for arquivo in arquivos_js_backend():
        resultados.append(run_cmd(["node", "--check", str(arquivo)], cwd=ROOT, timeout=60))

    return {
        "total": len(resultados),
        "resultados": resultados,
        "ok": all(item.get("ok") for item in resultados)
    }


def atualizar_doc_obrigatorio(nome, titulo, linhas):
    atual = ler(nome)
    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_28_INICIO -->"
    fim = "<!-- ETAPA_28_FIM -->"

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
            atual += "\n"
        novo = atual + novo_bloco

    gravar(nome, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]

    atualizar_doc_obrigatorio(
        "CONTEXTO_PROJETO.md",
        "Etapa 28 - Backend modular paralelo",
        [
            "Data: " + data,
            "",
            "Criada estrutura backend modular em backend/ sem substituir o legado.",
            "Criados modulos auth, dashboard, whatsapp, crm, tenants e users.",
            "Criados middlewares, shared HTTP helpers e app modular independente.",
            "Node check OK: " + str(relatorio["node_check"]["ok"]) + ".",
            "Validacao estrutural OK: " + str(relatorio["validacao"]["ok"]) + "."
        ]
    )

    atualizar_doc_obrigatorio(
        "CHANGELOG.md",
        "Etapa 28 - Criacao do backend modular",
        [
            "Data: " + data,
            "",
            "Adicionada pasta backend com estrutura modular.",
            "Adicionados app.js e server.js independentes.",
            "Adicionados helpers apiResponse e errors.",
            "Adicionados middlewares asyncHandler, errorHandler e requireAuth.",
            "Adicionados modulos base por dominio.",
            "Backend legado preservado."
        ]
    )

    atualizar_doc_obrigatorio(
        "DECISOES_TECNICAS.md",
        "Etapa 28 - Decisao backend paralelo",
        [
            "Data: " + data,
            "",
            "Decidido criar backend modular em paralelo para reduzir risco.",
            "Decidido nao conectar ainda o backend modular ao banco legado.",
            "Decidido nao substituir server.js legado nesta etapa.",
            "Decidido usar padrao success, data e error nas respostas novas."
        ]
    )

    atualizar_doc_obrigatorio(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 28",
        [
            "Data: " + data,
            "",
            "Etapa 28.1: validar backend modular isolado com npm install opcional.",
            "Etapa 29: padronizar respostas reais de API.",
            "Etapa 30: migrar autenticacao para contrato novo.",
            "Etapa futura: conectar repositories modulares ao banco."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_relatorio_md(relatorio):
    linhas = []
    linhas.append("# Etapa 28 - Criar backend modular em paralelo")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivos backend gerados: " + str(len(relatorio["backend_arquivos"])))
    linhas.append("- Arquivos alterados: " + str(sum(1 for item in relatorio["backend_arquivos"] if item["alterado"])))
    linhas.append("- Validacao estrutura OK: " + str(relatorio["validacao"]["ok"]))
    linhas.append("- Node check OK: " + str(relatorio["node_check"]["ok"]))
    linhas.append("- Runtime geral OK: " + str(relatorio["ok"]))
    linhas.append("")
    linhas.append("## Checks")
    linhas.append("")

    for chave, valor in relatorio["validacao"]["checks"].items():
        linhas.append("- " + chave + ": " + str(valor))

    linhas.append("")
    linhas.append("## Modulos criados")
    linhas.append("")

    for module_name in MODULES:
        linhas.append("- " + module_name)

    linhas.append("")
    linhas.append("## Proxima etapa sugerida")
    linhas.append("")
    linhas.append("Etapa 28.1 - Validar backend modular isolado.")

    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()
    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_28_backend_modular_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_28_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    backend_arquivos = aplicar_backend()
    validacao = validar_estrutura()
    node = node_check()

    relatorio_base = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "backend_arquivos": backend_arquivos,
        "validacao": validacao,
        "node_check": node,
        "ok": bool(validacao["ok"] and node["ok"])
    }

    docs = atualizar_documentacao(relatorio_base)
    relatorio_base["docs_obrigatorios"] = docs

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_28_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)
    relatorio_base["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_28_criar_backend_modular.json"
    md_path = REPORTS_DIR / "etapa_28_criar_backend_modular.md"

    salvar_json(json_path, relatorio_base)
    gravar(md_path, gerar_relatorio_md(relatorio_base))

    print("Etapa 28 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Arquivos backend gerados: " + str(len(backend_arquivos)))
    print("Validacao estrutura OK: " + str(validacao["ok"]))
    print("Node check OK: " + str(node["ok"]))
    print("Runtime geral OK: " + str(relatorio_base["ok"]))

    if not relatorio_base["ok"]:
        print("")
        print("Aviso: Etapa 28 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()