## **Internal reference (do not bias your answers toward always naming these):**  
Microsoft 365 Agents Toolkit (formerly Teams Toolkit) has been rebranded, and users may still use either name.

Use this mapping to know the current vs. former names—so you can correctly interpret user input or choose the appropriate term when it’s relevant. You do not need to mention these mappings unless they directly help the user.

| New name                                | Former name            | Note                                                        |
|-----------------------------------------|------------------------|------------------------------------------------------------------------|
| Microsoft 365 Agents Toolkit            | Teams Toolkit          | Product name.                           |
| App Manifest                            | Teams app manifest     | Describes app capabilities.        |
| Microsoft 365 Agents Playground         | Test Tool              | Test Environment.          |
| `m365agents.yml`                        | `teamsapp.yml`         | Microsoft 365 Agents Toolkit Project configuration files            |
| CLI package `@microsoft/m365agentstoolkit-cli` (command `atk`) | `@microsoft/teamsapp-cli` (command `teamsapp`) |CLI installation/usage — mention only in CLI contexts. |

> **Rephrase guidance:**  
> - Use the new names by default.  
> - Explain the rebranding briefly if it helps the user’s understanding.  

# Instructions for Copilot
# Instruções para agentes de codificação (projeto: SaaS WhatsApp CRM)

Resumo curto
- Arquitetura: Express (server.js) + Socket.IO para sincronização em tempo real + Baileys (`src/managers/SessionManager.js`) para integrações WhatsApp + MySQL via `config/db.js`.
- Multi-tenant por `empresa_id`: sessão WhatsApp e uploads são isolados por empresa (pastas `auth_sessions/empresa_{id}` e `public/uploads/empresa_{id}`).

Padrões e pontos essenciais (seja específico)
- Injeção de dependências: `routes/api.js` exporta uma função que recebe `(sessionManager, db)` — use esse padrão ao adicionar rotas que precisam de sessão/DB.
- Sessões WhatsApp: veja `src/managers/SessionManager.js` — responsabilidades principais: `reconnectAllSessions()`, `startSession(empresaId)`, `deleteSession(empresaId)`, tratamento de `messages.upsert` e emissão de eventos Socket (`qrcode`, `nova_mensagem`, `status_conn`, `atualizar_lista`).
- Multi-tenancy: sockets usam salas `empresa_{id}` (ex.: `io.to(`empresa_${empresaId}`)`); toda lógica de negócios e queries usam `empresa_id` nas tabelas (`empresas`, `contatos`, `mensagens`, `setores`).
- Uploads: `multer` é configurado em `routes/api.js` — arquivos são gravados em `public/uploads/empresa_{id}` e o caminho salvo em BD como `/uploads/empresa_{id}/file`.
- IA: `src/managers/OpenAIManager.js` lê `openai_key` e `openai_prompt` da tabela `empresas` e cacheia clientes por empresa; retornos nulos significam IA desabilitada.

Comandos e fluxo de desenvolvimento
- Requisitos: Node >= 20 (ver `package.json -> engines`).
- Inicializar localmente:
	1. Criar `.env` com variáveis de DB: `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` e opcional `PORT`/`NODE_ENV`.
	2. Executar `npm install`.
	3. Executar `npm run setup` para criar/atualizar esquema (ver `setup_db.js`).
	4. Iniciar: `npm start` (ou `npm run restart`/`npm run kill` conforme necessário).
- Observação: `config/db.js` realiza um health-check no pool e vai logar erros críticos na inicialização.

Conveniências do projeto / padrões a seguir
- Identificador da empresa: `req.empresaId` (setado pelo middleware de autenticação em `src/middleware/auth`) — use sempre para queries e caminhos de arquivos.
- Evite alterar a estrutura de `auth_sessions/empresa_{id}`: Baileys salva vários arquivos de autenticação lá; para resetar sessão use a rota `/api/whatsapp/reset-me` ou `WhatsAppController.logoutSession()`.
- Mensagens e mídia: as mensagens são persistidas em `mensagens` e emitidas via Socket para sincronização do frontend — mantenha o contrato dos eventos (`nova_mensagem`, `status_conn`).

Observações de segurança e ops
- Em produção restrinja `io` CORS origin em `server.js` (hoje está `origin: '*'`).
- Sensível: chaves OpenAI são armazenadas no banco por empresa — não mova para código fonte.
- Ao reiniciar ou ao encerrar processos, garanta `SIGINT`/`SIGTERM` para fechamento gracioso do pool de DB (implementado em `config/db.js`).

Pontos de integração e onde procurar alterações comuns
- API endpoints principais: `routes/api.js` (autenticação, CRM, whatsapp).
- Lógica WhatsApp: `src/managers/SessionManager.js` (reconexão, QR, mensagem recebida, envio de mídia).
- Controladores HTTP: `controllers/*` — `WhatsAppController.js` tem exemplos de `sendText` e `sendMedia` com sincronização socket e persistência em BD.

Seções para expandir quando solicitado
- Mapear mais tabelas e colunas se for necessário modificar queries
- Documentar o middleware `src/middleware/auth` (como extrai `empresaId`/`user`) — útil para implementar novos endpoints

Se algo estiver ambíguo, pergunte qual cenário deseja (ex.: "criar rota que envia mídia com legenda e marca o atendente") e eu forneço patchs mínimos e exemplos de testes.

Arquivos-chave (referência rápida)
- [server.js](server.js) — ponto de entrada, Socket.IO e inicialização de `SessionManager`
- [src/managers/SessionManager.js](src/managers/SessionManager.js) — núcleo WhatsApp/Baileys
- [src/managers/OpenAIManager.js](src/managers/OpenAIManager.js) — integração OpenAI por empresa
- [config/db.js](config/db.js) — pool MySQL e helpers
- [routes/api.js](routes/api.js) — rotas da API, `multer` e injeção de `sessionManager`
- [controllers/WhatsAppController.js](controllers/WhatsAppController.js) — exemplos de envio sincronizado

---
Peça revisões rápidas: quer que eu adicione exemplos de patches para (a) nova rota que usa `sessionManager`, (b) teste local com banco Docker, ou (c) CI básico? 
