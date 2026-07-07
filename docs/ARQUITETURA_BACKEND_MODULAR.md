# Arquitetura Backend Modular

Data: 2026-07-07T01:29:02

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
