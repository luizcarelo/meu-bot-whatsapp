#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 26 - Arquitetura Nova completa em fases

Objetivo:
- Registrar a decisao arquitetural.
- Mapear legado atual.
- Documentar backend modular alvo.
- Documentar frontend React alvo.
- Documentar contratos iniciais de API.
- Documentar plano de migracao progressiva.
- Gerar resumo final da Etapa 26.
- Criar backup e manifestos.
- Atualizar documentacao obrigatoria.
- Nao alterar codigo funcional.
- Nao alterar banco.
- Nao alterar Docker.
- Nao criar ainda o frontend React.

Como executar:
python3 etapa_26_arquitetura_nova_completa.py
"""

import os
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
DOCS_DIR = ROOT / "docs"
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

DOCS_NOVOS = [
    "docs/DECISAO_ARQUITETURA_NOVA.md",
    "docs/MAPA_LEGADO_ATUAL.md",
    "docs/ARQUITETURA_BACKEND_MODULAR.md",
    "docs/ARQUITETURA_FRONTEND_REACT.md",
    "docs/CONTRATOS_API.md",
    "docs/PLANO_MIGRACAO_REACT.md",
    "docs/RESUMO_ETAPA_26.md"
]

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "package.json",
    "package-lock.json",
    "server.js",
    "routes/api.js",
    "controllers/AuthController.js",
    "controllers/CrmController.js",
    "controllers/WhatsAppController.js",
    "controllers/AdminController.js",
    "src/managers/SessionManager.js",
    "views/dashboard.ejs",
    "views/crm.ejs",
    "views/admin-panel.ejs",
    "views/super-admin.ejs",
    "public/css/style.css"
] + DOCS_OBRIGATORIOS + DOCS_NOVOS

IGNORE_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "reports",
    "auth_sessions",
    "__pycache__",
    "tmp_etapa_24"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def garantir_dirs():
    DOCS_DIR.mkdir(exist_ok=True)
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
    if not p.exists():
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


def listar_arquivos(pasta):
    base = ROOT / pasta
    if not base.exists():
        return []
    out = []
    for raiz, dirs, files in os.walk(base):
        raiz_path = Path(raiz)
        dirs[:] = [d for d in dirs if not deve_ignorar(raiz_path / d)]
        for nome in files:
            p = raiz_path / nome
            if not deve_ignorar(p):
                out.append(rel(p))
    return sorted(out)


def bloco_lista(titulo, itens):
    linhas = []
    linhas.append("## " + titulo)
    linhas.append("")
    if not itens:
        linhas.append("Nenhum arquivo encontrado.")
        linhas.append("")
        return "\n".join(linhas)
    for item in itens:
        linhas.append("- " + item)
    linhas.append("")
    return "\n".join(linhas)


def doc_decisao():
    return """# Decisao de Arquitetura Nova

Data: {data}

## Decisao aprovada

Fica aprovada a migracao progressiva do sistema para uma arquitetura mais robusta, com separacao clara entre backend modular e frontend modular.

## Stack aprovada para o novo frontend

- React.
- TypeScript.
- Vite.
- Material UI.
- React Router.
- Cliente HTTP padronizado.
- Tema claro e escuro.
- Layout responsivo.

## Diretriz aprovada para o backend

O backend devera evoluir para uma arquitetura modular por dominio.

Estrutura alvo por modulo:

```text
nome.routes.js
nome.controller.js
nome.service.js
nome.repository.js
nome.validators.js
nome.types.js
```

## Legado operacional

As telas atuais em EJS passam a ser consideradas legado operacional.

Isso significa:

- O legado pode continuar funcionando durante a migracao.
- O legado nao deve receber novas funcionalidades complexas de interface.
- Correcoes criticas no legado ainda podem ser feitas se forem necessarias para manter o sistema acessivel.
- Novas telas e fluxos complexos deverao ser criados no frontend React.
- O legado so sera removido quando houver substituto validado.

## Motivos da decisao

A decisao foi tomada porque o frontend atual acumulou HTML, CSS e JavaScript acoplados, causando conflitos visuais, problemas de responsividade e dificuldade de manutencao.

O objetivo e reduzir remendos no EJS e construir uma base previsivel para evoluir atendimento, CRM, WhatsApp, automacoes e administracao SaaS.

## Regras de seguranca da migracao

- Nao apagar arquivos legados sem substituto validado.
- Nao alterar banco nesta fase.
- Nao alterar Docker nesta fase.
- Nao criar frontend React nesta fase.
- Nao alterar rotas funcionais nesta fase.
- Cada nova fase deve criar backup.
- Cada nova fase deve gerar manifesto.
- Cada nova fase deve gerar relatorio.
- Cada nova fase deve atualizar documentacao obrigatoria.

## Fronteiras da Etapa 26

Esta etapa registra a decisao arquitetural, o mapa do legado, a arquitetura alvo, os contratos iniciais e o plano de migracao.

Esta etapa nao implementa backend modular.

Esta etapa nao cria o frontend React.

Esta etapa nao altera o funcionamento atual do sistema.
""".format(data=agora_iso())


def doc_mapa_legado():
    return """# Mapa do Legado Atual

Data: {data}

## Objetivo

Registrar os principais arquivos do sistema atual antes da migracao para arquitetura nova.

Este documento nao altera o sistema. Ele serve como referencia para migracao progressiva.

## Situacao atual

O sistema atual usa backend Node.js e Express, views EJS, CSS global e JavaScript misturado nas telas.

A partir da Etapa 26, esta camada passa a ser tratada como legado operacional.

## Pontos frageis conhecidos

- EJS com JavaScript embutido.
- CSS global acumulado.
- Rotas HTML e API convivendo no mesmo backend.
- Dependencia historica de CDN em algumas telas.
- SessionManager acoplado a rotas antigas.
- Uso inconsistente de objetos de request para WhatsApp.
- Dificuldade de responsividade em telas legadas.

{views}
{controllers}
{routes}
{src}
{public}
## Diretriz

- Preservar o legado enquanto a nova arquitetura nasce.
- Evitar novas funcionalidades complexas em EJS.
- Migrar por feature.
- Validar cada etapa.
- Manter documentacao atualizada.
""".format(
        data=agora_iso(),
        views=bloco_lista("Views legadas", listar_arquivos("views")),
        controllers=bloco_lista("Controllers legados", listar_arquivos("controllers")),
        routes=bloco_lista("Routes legadas", listar_arquivos("routes")),
        src=bloco_lista("Src atual", listar_arquivos("src")),
        public=bloco_lista("Public atual", listar_arquivos("public"))
    )


def doc_backend():
    return """# Arquitetura Backend Modular

Data: {data}

## Objetivo

Definir a arquitetura alvo do backend modular sem alterar o codigo atual nesta etapa.

## Estrutura alvo

```text
backend/src/app.js
backend/src/server.js
backend/src/config
backend/src/database
backend/src/middlewares
backend/src/shared
backend/src/jobs
backend/src/modules/auth
backend/src/modules/tenants
backend/src/modules/users
backend/src/modules/dashboard
backend/src/modules/crm
backend/src/modules/whatsapp
backend/src/modules/departments
backend/src/modules/automation
backend/src/modules/reports
```

## Estrutura por modulo

```text
nome.routes.js
nome.controller.js
nome.service.js
nome.repository.js
nome.validators.js
nome.types.js
```

## Responsabilidades

### routes

Define endpoints e middlewares.

### controller

Recebe requisicao, chama service e devolve resposta HTTP.

### service

Concentra regra de negocio.

### repository

Isola acesso ao banco de dados.

### validators

Valida entrada de dados.

### types

Define constantes e contratos internos.

## Modulos iniciais

### auth

Login, logout, sessao e usuario atual.

### dashboard

Resumo operacional, indicadores e status geral.

### whatsapp

Status, conexao, QR Code, pairing code, envio e recebimento.

### crm

Contatos, mensagens, atendimentos, fila e transferencia.

### departments

Setores, roteamento e filas por area.

### automation

Boas vindas, menus, regras e fluxos automaticos.

### tenants

Empresas e isolamento multitenant.

### users

Usuarios, papeis e permissoes.

## Regras

- Uma rota nova nao deve acessar banco diretamente.
- Um controller novo nao deve conter regra complexa de negocio.
- Um service novo nao deve depender de response HTTP.
- Um repository novo nao deve saber regra de tela.
- Modulos novos devem retornar dados padronizados.
- Erros tecnicos nao devem vazar para o frontend.
""".format(data=agora_iso())


def doc_frontend():
    return """# Arquitetura Frontend React

Data: {data}

## Objetivo

Definir a arquitetura alvo do novo frontend em React, TypeScript, Vite e Material UI.

## Stack

- React.
- TypeScript.
- Vite.
- Material UI.
- React Router.
- Cliente HTTP padronizado.
- ThemeProvider.
- CssBaseline.
- Modo claro e escuro.
- Layout responsivo.

## Estrutura alvo

```text
frontend/src/app
frontend/src/routes
frontend/src/layouts
frontend/src/shared/components
frontend/src/shared/hooks
frontend/src/shared/services
frontend/src/shared/theme
frontend/src/shared/types
frontend/src/features/auth
frontend/src/features/dashboard
frontend/src/features/crm
frontend/src/features/whatsapp
frontend/src/features/departments
frontend/src/features/automation
frontend/src/features/settings
frontend/src/features/super-admin
frontend/src/main.tsx
```

## Layout principal

O frontend novo devera possuir um AppShell com:

- Drawer responsivo.
- AppBar.
- Menu lateral.
- Tema claro e escuro.
- Area principal fluida.
- Suporte a desktop, notebook, tablet e celular.

## Features iniciais

### auth

Login, logout e usuario atual.

### dashboard

Visao geral, indicadores e atalhos.

### whatsapp

Gestao de conexao, status, QR Code e pairing code.

### crm

Conversas, contatos, chat, tags, fila e transferencia.

### departments

Setores e roteamento.

### settings

Configuracoes do tenant.

### super-admin

Gestao de empresas e administracao SaaS.

## Regras

- Nenhuma tela nova complexa deve ser criada em EJS.
- Cada feature deve conter seus proprios componentes, hooks, services e types.
- A camada shared deve conter somente codigo reutilizavel.
- O frontend deve consumir APIs JSON.
- O frontend deve tratar erro 401 limpando sessao e redirecionando para login.
- Arrays recebidos da API devem ser validados antes de renderizar listas.
""".format(data=agora_iso())


def doc_contratos():
    return """# Contratos Iniciais de API

Data: {data}

## Objetivo

Definir o padrao inicial para as respostas JSON usadas pelo frontend React.

## Resposta de sucesso

```json
{{
  "success": true,
  "data": {{}},
  "error": null
}}
```

## Resposta de erro

```json
{{
  "success": false,
  "data": null,
  "error": {{
    "code": "CODIGO_DO_ERRO",
    "message": "Mensagem amigavel em PT-BR"
  }}
}}
```

## Regras gerais

- Toda API nova deve responder JSON.
- Toda resposta nova deve conter success.
- Toda resposta nova deve conter data.
- Toda resposta nova deve conter error.
- Erros tecnicos nao devem expor stack trace para o frontend.
- Mensagens exibidas ao usuario devem estar em PT-BR.
- Codigo HTTP deve refletir o resultado operacional.
- APIs de status operacional podem retornar HTTP 200 com status interno de negocio.

## Contratos iniciais previstos

### POST /api/auth/login

Entrada:

```json
{{
  "email": "usuario@exemplo.com",
  "senha": "senha"
}}
```

Saida prevista:

```json
{{
  "success": true,
  "data": {{
    "user": {{
      "id": 1,
      "nome": "Nome",
      "email": "usuario@exemplo.com",
      "role": "admin"
    }},
    "empresa": {{
      "id": 5,
      "nome": "Cliente Teste LTDA"
    }},
    "redirectUrl": "/dashboard"
  }},
  "error": null
}}
```

### GET /api/auth/me

Retorna usuario autenticado e empresa atual.

### POST /api/auth/logout

Encerra sessao atual.

### GET /api/dashboard/summary

Retorna resumo operacional do dashboard.

### GET /api/whatsapp/status/:empresaId

Retorna status operacional do WhatsApp.

Valores previstos:

```text
DESCONECTADO
AGUARDANDO_QR
CONECTANDO
CONECTADO
RECONECTANDO
ERRO
LOGOUT
```

### POST /api/whatsapp/connect

Inicia fluxo de conexao.

### POST /api/whatsapp/disconnect

Desconecta sessao.

### GET /api/crm/contatos

Lista contatos com filtros e paginacao.

### GET /api/crm/mensagens/:telefone

Lista mensagens de um contato.

### POST /api/crm/enviar

Envia mensagem para contato.
""".format(data=agora_iso())


def doc_plano():
    return """# Plano de Migracao Progressiva para React

Data: {data}

## Objetivo

Migrar o sistema para frontend React e backend modular sem interromper o funcionamento atual.

## Principios

- Migracao progressiva.
- Sem big bang.
- Sem quebrar operacao atual.
- Rotas antigas continuam ativas ate substituicao validada.
- APIs passam a ter contratos padronizados.
- Frontend novo consome apenas APIs JSON.
- Backend passa a ser modularizado por dominio.

## Fases futuras

### Etapa 27

Criar base do frontend React com TypeScript, Vite e Material UI.

### Etapa 28

Criar estrutura base de backend modular em paralelo.

### Etapa 29

Padronizar respostas de API.

### Etapa 30

Migrar login e sessao para consumo do frontend React.

### Etapa 31

Migrar dashboard para React e Material UI.

### Etapa 32

Criar gestao WhatsApp web.

### Etapa 33

Migrar CRM atendimento.

### Etapa 34

Criar automacoes de atendimento.

### Etapa 35

Isolar Baileys em modulo dedicado.

### Etapa 36

Revisar Docker, build e producao.

## Riscos

- Divergencia entre sessao do EJS e sessao consumida pelo React.
- Endpoints atuais retornando formatos inconsistentes.
- Logica de WhatsApp acoplada em controllers antigos.
- Dependencia de variaveis globais no frontend legado.
- Rotas antigas com comportamento misto HTML e JSON.

## Mitigacoes

- Criar contratos antes de migrar telas.
- Criar cliente HTTP padronizado no frontend.
- Criar middleware de erro padronizado no backend.
- Criar resposta padrao em todos endpoints novos.
- Migrar por rota e por feature.
- Manter backup e manifesto por etapa.
""".format(data=agora_iso())


def doc_resumo():
    return """# Resumo da Etapa 26

Data: {data}

## Conteudo entregue

- Decisao de arquitetura nova.
- Mapa do legado atual.
- Arquitetura alvo do backend modular.
- Arquitetura alvo do frontend React.
- Contratos iniciais de API.
- Plano de migracao progressiva.

## Decisao central

O sistema passa a evoluir para frontend React, TypeScript, Vite e Material UI, com backend modular por dominio.

## Estado do legado

O EJS atual fica como legado operacional.

## Proxima etapa recomendada

Etapa 27: criar base do frontend React.
""".format(data=agora_iso())


def gerar_docs():
    conteudos = {
        "docs/DECISAO_ARQUITETURA_NOVA.md": doc_decisao(),
        "docs/MAPA_LEGADO_ATUAL.md": doc_mapa_legado(),
        "docs/ARQUITETURA_BACKEND_MODULAR.md": doc_backend(),
        "docs/ARQUITETURA_FRONTEND_REACT.md": doc_frontend(),
        "docs/CONTRATOS_API.md": doc_contratos(),
        "docs/PLANO_MIGRACAO_REACT.md": doc_plano(),
        "docs/RESUMO_ETAPA_26.md": doc_resumo()
    }
    resultados = []
    for nome, texto in conteudos.items():
        antes = sha256(nome)
        gravar(nome, texto)
        depois = sha256(nome)
        resultados.append({
            "arquivo": nome,
            "alterado": antes != depois,
            "sha256_antes": antes,
            "sha256_depois": depois,
            "tamanho": len(texto)
        })
    return resultados


def atualizar_doc_obrigatorio(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)
    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"
    ini = "<!-- ETAPA_26_INICIO -->"
    fim = "<!-- ETAPA_26_FIM -->"
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
    gravar(path, novo)


def atualizar_docs_obrigatorios():
    data = agora_iso()
    atualizar_doc_obrigatorio("CONTEXTO_PROJETO.md", "Etapa 26 - Arquitetura Nova", [
        "Data: " + data,
        "",
        "Registrada a migracao progressiva para frontend React, TypeScript, Vite e Material UI.",
        "Registrada a diretriz de backend modular por dominio.",
        "O frontend EJS atual passa a ser tratado como legado operacional.",
        "Nenhum codigo funcional foi alterado nesta etapa.",
        "Documentos criados na pasta docs."
    ])
    atualizar_doc_obrigatorio("CHANGELOG.md", "Etapa 26 - Documentacao de arquitetura nova", [
        "Data: " + data,
        "",
        "Criados documentos de decisao, mapa do legado, arquitetura alvo, contratos de API e plano de migracao.",
        "Registrada diretriz de interromper remendos complexos no EJS legado.",
        "Nao houve alteracao funcional no sistema."
    ])
    atualizar_doc_obrigatorio("DECISOES_TECNICAS.md", "Etapa 26 - Decisao tecnica", [
        "Data: " + data,
        "",
        "Decidido evoluir para frontend React, TypeScript, Vite e Material UI.",
        "Decidido evoluir backend para arquitetura modular por dominio.",
        "Decidido manter o EJS como legado operacional ate substituicao validada.",
        "Decidido padronizar contratos JSON para APIs novas."
    ])
    atualizar_doc_obrigatorio("PENDENCIAS.md", "Pendencias apos Etapa 26", [
        "Data: " + data,
        "",
        "Etapa 27: criar base do frontend React.",
        "Etapa 28: criar backend modular em paralelo.",
        "Etapa 29: padronizar respostas reais de API.",
        "Etapa 30: migrar login e sessao.",
        "Etapa 31: migrar dashboard.",
        "Etapa 32: criar gestao WhatsApp web."
    ])
    return DOCS_OBRIGATORIOS


def validar_sem_asterisco(nome, texto):
    achados = []
    for idx, linha in enumerate(texto.splitlines(), start=1):
        if chr(42) in linha:
            achados.append({"arquivo": nome, "linha": idx, "texto": linha[:300]})
    return achados


def validar_docs():
    arquivos = DOCS_NOVOS + DOCS_OBRIGATORIOS
    itens = []
    erros = []
    for nome in arquivos:
        texto = ler(nome)
        existe = texto is not None
        tamanho = len(texto or "")
        ast = validar_sem_asterisco(nome, texto or "")
        checks = {
            "existe": existe,
            "tamanho_maior_que_zero": tamanho > 0,
            "sem_asterisco": len(ast) == 0
        }
        if nome == "docs/DECISAO_ARQUITETURA_NOVA.md":
            checks["tem_react"] = "React" in (texto or "")
            checks["tem_typescript"] = "TypeScript" in (texto or "")
            checks["tem_vite"] = "Vite" in (texto or "")
            checks["tem_material_ui"] = "Material UI" in (texto or "")
            checks["tem_legado"] = "legado operacional" in (texto or "").lower()
        ok = all(checks.values())
        item = {
            "arquivo": nome,
            "sha256": sha256(nome),
            "tamanho": tamanho,
            "checks": checks,
            "asteriscos": ast[:10],
            "ok": ok
        }
        itens.append(item)
        if not ok:
            erros.append(item)
    return {"arquivos": itens, "erros": erros, "ok": len(erros) == 0}


def gerar_relatorio_md(relatorio):
    linhas = []
    linhas.append("# Etapa 26 - Arquitetura Nova Completa")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Documentos novos: " + str(len(relatorio["docs_novos"])))
    linhas.append("- Documentacao obrigatoria atualizada: " + str(len(relatorio["docs_obrigatorios"])))
    linhas.append("- Validacao OK: " + str(relatorio["validacao"]["ok"]))
    linhas.append("")
    linhas.append("## Documentos novos")
    linhas.append("")
    for item in relatorio["docs_novos"]:
        linhas.append("- " + item["arquivo"] + " alterado: " + str(item["alterado"]))
    linhas.append("")
    linhas.append("## Validacao")
    linhas.append("")
    for item in relatorio["validacao"]["arquivos"]:
        linhas.append("- " + item["arquivo"] + " ok: " + str(item["ok"]))
    linhas.append("")
    linhas.append("## Proxima etapa sugerida")
    linhas.append("")
    linhas.append("Etapa 27 - Criar base do frontend React.")
    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()
    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_26_arquitetura_nova_completa_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_26_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    docs_novos = gerar_docs()
    docs_obrigatorios = atualizar_docs_obrigatorios()
    validacao = validar_docs()

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_26_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "manifesto_depois": rel(manifesto_depois_path),
        "docs_novos": docs_novos,
        "docs_obrigatorios": docs_obrigatorios,
        "validacao": validacao
    }

    json_path = REPORTS_DIR / "etapa_26_arquitetura_nova_completa.json"
    md_path = REPORTS_DIR / "etapa_26_arquitetura_nova_completa.md"
    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_relatorio_md(relatorio))

    print("Etapa 26 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Documentos novos: " + str(len(docs_novos)))
    print("Documentacao obrigatoria atualizada: " + str(len(docs_obrigatorios)))
    print("Validacao OK: " + str(validacao["ok"]))

    if not validacao["ok"]:
        print("")
        print("Aviso: validacao encontrou problemas.")
        for erro in validacao["erros"]:
            print("- " + erro["arquivo"] + " ok=" + str(erro["ok"]))


if __name__ == "__main__":
    main()
