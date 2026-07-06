# Etapa 01 - Auditoria estatica

Data: 2026-07-06T10:58:32

## Resumo executivo

- Projeto analisado: /home/luizcarelo/meu-bot-whatsapp
- Arquivos analisados: 49
- Achados criticos: 2
- Achados altos: 2
- Achados medios: 1

## Achados de seguranca

- Arquivos sensiveis encontrados:
  - .env

- Possiveis segredos encontrados, com valores redigidos:
  - .env:13 - Possivel senha - DB_PASS=<REDIGIDO>
  - .env:29 - Possivel senha - SMTP_PASS=<REDIGIDO>
  - .env:29 - Possivel chave JWT/API - SMTP_PASS=<REDIGIDO>
  - .env:35 - Possivel senha - SUPER_ADMIN_PASS=<REDIGIDO>
  - .env:40 - Possivel senha - # JWT_SECRET=<REDIGIDO>
  - .env:40 - Possivel chave JWT/API - # JWT_SECRET=<REDIGIDO>
  - .env:41 - Possivel senha - SESSION_SECRET=<REDIGIDO>
  - .env:54 - Possivel senha - REDIS_PASSWORD=<REDIGIDO>
  - .env:54 - Possivel chave JWT/API - REDIS_PASSWORD=<REDIGIDO>
  - MELHORIAS.md:180 - Possivel senha - DB_PASS=<REDIGIDO>
  - MELHORIAS.md:193 - Possivel senha - SMTP_PASS=<REDIGIDO>
  - MELHORIAS.md:193 - Possivel chave JWT/API - SMTP_PASS=<REDIGIDO>
  - README.md:74 - Possivel senha - DB_PASS=<REDIGIDO>
  - README.md:82 - Possivel senha - SUPER_ADMIN_PASS=<REDIGIDO>
  - README.md:89 - Possivel senha - SMTP_PASS=<REDIGIDO>
  - README.md:89 - Possivel chave JWT/API - SMTP_PASS=<REDIGIDO>
  - controllers/AdminController.js:239 - Possivel senha - `UPDATE usuarios_painel SET senha=<REDIGIDO>
  - controllers/AuthController.js:75 - Possivel senha - } else if (user.senha=<REDIGIDO>
  - controllers/AuthController.js:88 - Possivel senha - await db.run('UPDATE usuarios_painel SET senha=<REDIGIDO>
  - controllers/AuthController.js:170 - Possivel senha - const novaSenha=<REDIGIDO>
  - controllers/AuthController.js:173 - Possivel senha - await db.run("UPDATE usuarios_painel SET senha=<REDIGIDO>
  - controllers/AuthController.js:196 - Possivel senha - await db.run("UPDATE usuarios_painel SET senha=<REDIGIDO>
  - controllers/CrmController.js:441 - Possivel senha - 'UPDATE empresas SET openai_key=<REDIGIDO>
  - docker-compose.yml:25 - Possivel senha - - POSTGRES_PASSWORD=<REDIGIDO>
  - docker-compose.yml:40 - Possivel senha - - REDIS_PASSWORD=<REDIGIDO>
  - docker-compose.yml:40 - Possivel chave JWT/API - - REDIS_PASSWORD=<REDIGIDO>
  - script/export_full.js:70 - Possivel senha - const tableKey=<REDIGIDO>
  - server.js:44 - Possivel URI com credencial - <REDIGIDO>
  - src/managers/OpenAIManager.js:1 - Possivel chave JWT/API - const OpenAI=<REDIGIDO>
  - src/managers/OpenAIManager.js:14 - Possivel chave JWT/API - let openai=<REDIGIDO>
  - src/managers/OpenAIManager.js:29 - Possivel chave JWT/API - openai=<REDIGIDO>
  - src/managers/OpenAIManager.js:36 - Possivel chave JWT/API - const openai=<REDIGIDO>
  - src/managers/OpenAIManager.js:74 - Possivel chave JWT/API - const openai=<REDIGIDO>
  - views/admin-panel.ejs:698 - Possivel senha - const senha=<REDIGIDO>
  - views/crm.ejs:249 - Possivel senha - input.addEventListener('keydown', (e)=<REDIGIDO>
  - views/crm.ejs:389 - Possivel senha - async function fazerLogin() { const empresa=<REDIGIDO>
  - views/dashboard.ejs:156 - Possivel senha - <template x-for=<REDIGIDO>
  - views/dashboard.ejs:244 - Possivel senha - <template x-for=<REDIGIDO>

## Banco de dados e Docker

- .env existe: True
- docker-compose.yml existe: True
- Inconsistencia detectada: True
  - .env indica configuracao compativel com MySQL
  - docker-compose.yml usa imagem ou variaveis de PostgreSQL

## Controllers suspeitos

- Nenhum controller suspeito encontrado pelos criterios simples.

## Dependencias com alerta

- package.json: encontrado
- Total de dependencias: 34
- fluent-ffmpeg ^2.1.2: Pacote sem suporte ativo segundo avisos comuns do npm.
- multer ^1.4.5-lts.1: Multer 1.x possui historico de vulnerabilidades corrigidas na linha 2.x.

## JavaScript com sinais suspeitos

- controllers/AuthController.js: Exporta instancia unica. Verificar consistencia com injecao de dependencias.

## Recomendacao da proxima etapa

- Etapa 02 deve criar backup, manifesto e sanitizacao do pacote.
- Etapa 03 deve corrigir estrutura de ambiente, Docker e banco.
- Etapa 04 deve validar sintaxe e reconstruir controllers quebrados.
- Etapa 05 deve endurecer seguranca, CORS, rate limit e logs.

