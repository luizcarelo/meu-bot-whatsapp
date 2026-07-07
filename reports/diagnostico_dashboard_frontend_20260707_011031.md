# Diagnostico Dashboard Frontend

Data: 2026-07-07T01:10:31

## Resumo

- Login OK: True
- Dashboard status: 200
- API status WhatsApp status: 200
- Dashboard local SHA256: bb6af0a6a888397e26214cf349136ae01a5a12a16ee16fa9cc7c5fa6bfeb5e11
- CSS local SHA256: afdeb4f2b8d33f960e6b9a699cdd4bd2eec43ecffbd30b6a762c40922d96f163

## Problemas provaveis

- Dashboard renderizado contem texto de links quebrados, como /crmAbrir ou /admin/painelPainel.
- Dashboard nao contem href="/crm" valido.
- Dashboard nao contem href="/admin/painel" valido.
- Dashboard nao contem href="/super-admin" valido.
- views/dashboard.ejs pode conter /css/style.css sem tag <link href=...> valida.

## Recomendacoes

- Se houver links quebrados no relatorio, corrigir views/dashboard.ejs para usar tags <a href="..."> completas.
- Se /css/style.css estiver como texto solto, corrigir para <link href="/css/style.css" rel="stylesheet">.
- Se o HTML local divergir do container, sincronizar arquivos ou reiniciar/recriar container.
- Se tudo estiver correto no HTML e ainda quebrar visualmente, fazer captura do HTML renderizado e CSS computado no navegador.

## Marcadores do /dashboard renderizado

- alpine: False
- api_status: True
- dashboard_antigo: False
- er25dash: True
- er25safe: True
- etapa25_1: True
- etapa25_4: True
- href_admin_literal: False
- href_crm_literal: False
- href_super_literal: False
- tailwind_cdn: False
- texto_link_quebrado_admin: True
- texto_link_quebrado_crm: True
- texto_link_quebrado_super: True

## Inspecao HTML do /dashboard

- Title: Dashboard | Engeradios CRM
- Links total: 0
- Links sample: []
- Links suspeitos: []
- Scripts: ['', '']
- Stylesheets: []

## Padroes suspeitos em arquivos

- views/dashboard.ejs: href_sem_tag_crm, href_sem_tag_admin, href_sem_tag_super, link_literal_css_quebrado, a_tag_quebrada
- views/crm.ejs: html_escaped_links
- views/admin-panel.ejs: sem padroes suspeitos principais
- views/super-admin.ejs: sem padroes suspeitos principais
- public/css/style.css: sem padroes suspeitos principais
- routes/api.js: sem padroes suspeitos principais
- server.js: sem padroes suspeitos principais

## Logs suspeitos

- linha 39: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 57: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 60: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 63: whatsapp_bot_app  | 📡 URL: GET /api/whatsapp/status/5
- linha 68: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 71: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 74: whatsapp_bot_app  | 📡 URL: GET /api/whatsapp/status/5
- linha 79: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 82: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 85: whatsapp_bot_app  | 📡 URL: GET /api/whatsapp/status/5
- linha 90: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 93: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 96: whatsapp_bot_app  | 📡 URL: GET /api/whatsapp/status/5
- linha 116: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 119: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 122: whatsapp_bot_app  | 📡 URL: GET /api/whatsapp/status/5
- linha 137: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 140: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 143: whatsapp_bot_app  | 📡 URL: GET /api/whatsapp/status/5
- linha 148: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 151: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 154: whatsapp_bot_app  | 📡 URL: GET /api/whatsapp/status/5
- linha 174: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 177: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 180: whatsapp_bot_app  | 📡 URL: GET /api/whatsapp/status/5
- linha 191: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 194: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 212: whatsapp_bot_app  | 📡 URL: GET /dashboard
- linha 215: whatsapp_bot_app  | [DASHBOARD] Acesso permitido empresa_id=5
- linha 218: whatsapp_bot_app  | 📡 URL: GET /api/whatsapp/status/5
