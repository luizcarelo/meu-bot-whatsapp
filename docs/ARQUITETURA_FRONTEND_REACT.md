# Arquitetura Frontend React

Data: 2026-07-07T01:29:02

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
