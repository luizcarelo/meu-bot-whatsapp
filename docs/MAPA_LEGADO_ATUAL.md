# Mapa do Legado Atual

Data: 2026-07-07T01:29:02

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

## Views legadas

- views/admin-panel.ejs
- views/crm.ejs
- views/dashboard.ejs
- views/login.ejs
- views/super-admin.ejs

## Controllers legados

- controllers/AdminController.js
- controllers/AdminPanelController.js
- controllers/AuthController.js
- controllers/CrmController.js
- controllers/ScheduleController.js
- controllers/WhatsAppController.js

## Routes legadas

- routes/api.js
- routes/index.js

## Src atual

- src/config/db.js
- src/managers/OpenAIManager.js
- src/managers/SessionManager.js
- src/middleware/auth.js
- src/styles.css
- src/utils/atendimento.js

## Public atual

- public/css/style.css
- public/images/chatbot_logo.png
- public/images/lh_chatbot_favicon.png
- public/images/lhsolucao_logo.png
- public/uploads/empresa_2/1765714023337_logo.png
- public/uploads/empresa_2/css/style.css

## Diretriz

- Preservar o legado enquanto a nova arquitetura nasce.
- Evitar novas funcionalidades complexas em EJS.
- Migrar por feature.
- Validar cada etapa.
- Manter documentacao atualizada.
