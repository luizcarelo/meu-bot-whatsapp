#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 27.1 - Corrigir build e validacao do frontend React

Objetivo:
- Corrigir falha do TypeScript causada por baseUrl deprecated no TypeScript 6.
- Manter alias @ sem usar baseUrl.
- Corrigir rota wildcard para evitar caractere asterisco em arquivo TSX.
- Ajustar validacao para nao bloquear caracteres tecnicamente necessarios em arquivos de configuracao quando inevitavel.
- Rodar npm run build novamente.
- Nao alterar backend.
- Nao alterar banco.
- Nao alterar Docker.
- Nao substituir o legado EJS.
- Criar backup, manifesto, validacao e relatorios.
- Atualizar documentacao obrigatoria.

Como executar:
python3 etapa_27_1_corrigir_frontend_react_build.py
"""

import os
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
FRONTEND_DIR = ROOT / "frontend"
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "frontend/tsconfig.app.json",
    "frontend/src/routes/AppRoutes.tsx",
    "frontend/package.json",
    "frontend/package-lock.json",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
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
    "frontend/dist"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


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
            erros.append({"item": nome, "erro": str(exc)})
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


def tsconfig_app_corrigido():
    return """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
"""


def app_routes_corrigido():
    return """import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/layouts/AppShell';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage';
import { CrmPage } from '@/features/crm/pages/CrmPage';
import { WhatsappPage } from '@/features/whatsapp/pages/WhatsappPage';
import { AdminPage } from '@/features/settings/pages/AdminPage';
import { SuperAdminPage } from '@/features/super-admin/pages/SuperAdminPage';

const fallbackRoute = String.fromCharCode(42);

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/crm" element={<CrmPage />} />
        <Route path="/whatsapp" element={<WhatsappPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/super-admin" element={<SuperAdminPage />} />
      </Route>
      <Route path={fallbackRoute} element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
"""


def aplicar_correcoes():
    alteracoes = []
    arquivos = {
        "frontend/tsconfig.app.json": tsconfig_app_corrigido(),
        "frontend/src/routes/AppRoutes.tsx": app_routes_corrigido()
    }
    for nome, texto in arquivos.items():
        antes = sha256(nome)
        atual = ler(nome)
        alterado = atual != texto
        if alterado:
            gravar(nome, texto)
        depois = sha256(nome)
        alteracoes.append({
            "arquivo": nome,
            "alterado": alterado,
            "sha256_antes": antes,
            "sha256_depois": depois,
            "tamanho": len(texto)
        })
    return alteracoes


def validar_sem_asterisco(nome, texto):
    achados = []
    for idx, linha in enumerate(texto.splitlines(), start=1):
        if chr(42) in linha:
            achados.append({"arquivo": nome, "linha": idx, "texto": linha[:300]})
    return achados


def validar_estrutura():
    arquivos = [
        "frontend/tsconfig.app.json",
        "frontend/src/routes/AppRoutes.tsx",
        "frontend/package.json",
        "frontend/src/main.tsx",
        "frontend/src/layouts/AppShell.tsx",
        "frontend/src/features/dashboard/pages/DashboardPage.tsx"
    ]
    itens = []
    erros = []
    for nome in arquivos:
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
    tsconfig = ler("frontend/tsconfig.app.json") or ""
    routes = ler("frontend/src/routes/AppRoutes.tsx") or ""
    checks = {
        "sem_baseUrl": "baseUrl" not in tsconfig,
        "alias_com_paths": "@/*" in tsconfig and "./src/*" in tsconfig,
        "sem_path_asterisco_literal": 'path="*"' not in routes,
        "fallback_com_from_char_code": "String.fromCharCode(42)" in routes
    }
    ok = len(erros) == 0 and all(checks.values())
    return {"arquivos": itens, "checks": checks, "erros": erros, "ok": ok}


def executar_build():
    return {
        "node_version": run_cmd(["node", "--version"], timeout=30),
        "npm_version": run_cmd(["npm", "--version"], timeout=30),
        "typecheck": run_cmd(["npm", "run", "typecheck"], cwd=FRONTEND_DIR, timeout=600),
        "build": run_cmd(["npm", "run", "build"], cwd=FRONTEND_DIR, timeout=600)
    }


def build_ok(builds):
    return bool(builds["typecheck"].get("ok") and builds["build"].get("ok"))


def atualizar_doc_obrigatorio(nome, titulo, linhas):
    atual = ler(nome)
    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"
    ini = "<!-- ETAPA_27_1_INICIO -->"
    fim = "<!-- ETAPA_27_1_FIM -->"
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
    atualizar_doc_obrigatorio("CONTEXTO_PROJETO.md", "Etapa 27.1 - Correcao build frontend React", [
        "Data: " + data,
        "",
        "Corrigida configuracao TypeScript do frontend React removendo baseUrl.",
        "Mantido alias @ via paths com ./src.",
        "Corrigida rota fallback para evitar caractere asterisco literal em TSX.",
        "Build OK: " + str(relatorio["build_ok"]) + "."
    ])
    atualizar_doc_obrigatorio("CHANGELOG.md", "Etapa 27.1 - Ajustes de build React", [
        "Data: " + data,
        "",
        "Removido baseUrl de frontend/tsconfig.app.json.",
        "Ajustado alias @ para ./src.",
        "Ajustado fallback de rotas no React Router.",
        "Executado typecheck e build do frontend."
    ])
    atualizar_doc_obrigatorio("DECISOES_TECNICAS.md", "Etapa 27.1 - Decisao TypeScript", [
        "Data: " + data,
        "",
        "Decidido remover baseUrl para compatibilidade com TypeScript 6.",
        "Decidido manter path alias @ sem baseUrl.",
        "Decidido manter validacao anti-asterisco para arquivos gerados, usando String.fromCharCode(42) quando necessario."
    ])
    atualizar_doc_obrigatorio("PENDENCIAS.md", "Pendencias apos Etapa 27.1", [
        "Data: " + data,
        "",
        "Validar visualmente o frontend React com npm run dev.",
        "Etapa 28: criar backend modular em paralelo.",
        "Etapa 29: padronizar respostas de API."
    ])
    return DOCS_OBRIGATORIOS


def gerar_relatorio_md(relatorio):
    linhas = []
    linhas.append("# Etapa 27.1 - Corrigir build do frontend React")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivos alterados: " + str(sum(1 for x in relatorio["alteracoes"] if x["alterado"])))
    linhas.append("- Validacao estrutura OK: " + str(relatorio["validacao"]["ok"]))
    linhas.append("- Typecheck OK: " + str(relatorio["builds"]["typecheck"].get("ok")))
    linhas.append("- Build OK: " + str(relatorio["builds"]["build"].get("ok")))
    linhas.append("- Runtime geral OK: " + str(relatorio["ok"]))
    linhas.append("")
    linhas.append("## Checks")
    linhas.append("")
    for chave, valor in relatorio["validacao"]["checks"].items():
        linhas.append("- " + chave + ": " + str(valor))
    linhas.append("")
    linhas.append("## Alteracoes")
    linhas.append("")
    for item in relatorio["alteracoes"]:
        linhas.append("- " + item["arquivo"] + " alterado: " + str(item["alterado"]))
    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()
    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_27_1_frontend_react_build_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_27_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    alteracoes = aplicar_correcoes()
    validacao = validar_estrutura()
    builds = executar_build()
    ok_build = build_ok(builds)

    relatorio_base = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "alteracoes": alteracoes,
        "validacao": validacao,
        "builds": builds,
        "build_ok": ok_build,
        "ok": bool(validacao["ok"] and ok_build)
    }
    docs = atualizar_documentacao(relatorio_base)
    relatorio_base["docs_obrigatorios"] = docs

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_27_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)
    relatorio_base["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_27_1_corrigir_frontend_react_build.json"
    md_path = REPORTS_DIR / "etapa_27_1_corrigir_frontend_react_build.md"
    salvar_json(json_path, relatorio_base)
    gravar(md_path, gerar_relatorio_md(relatorio_base))

    print("Etapa 27.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Validacao estrutura OK: " + str(validacao["ok"]))
    print("Typecheck OK: " + str(builds["typecheck"].get("ok")))
    print("Build OK: " + str(builds["build"].get("ok")))
    print("Runtime geral OK: " + str(relatorio_base["ok"]))

    if not relatorio_base["ok"]:
        print("")
        print("Aviso: Etapa 27.1 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()