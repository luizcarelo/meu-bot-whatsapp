# PENDENCIAS

<!-- ETAPA_02_INICIO -->
## Pendencias apos Etapa 02

Data: 2026-07-06T11:01:56

Rotacionar credenciais reais expostas anteriormente em arquivos locais ou historico.
Revisar CORS, Helmet, rate limit e politicas de sessao.
Revisar dependencias com alerta, incluindo multer e fluent-ffmpeg.
Validar sintaxe e testes dos controllers e rotas principais.
Criar rotina de pacote limpo sem .env, .git, node_modules, auth_sessions, uploads e backups.
<!-- ETAPA_02_FIM -->





<!-- ETAPA_04_INICIO -->
## Pendencias apos Etapa 04

Data: 2026-07-06T20:09:04

Revisar eventuais rastros PostgreSQL pendentes listados no relatorio da Etapa 04.
Executar testes funcionais com banco PostgreSQL em ambiente controlado.
Validar setup_db.js e migrations em detalhes.
Revisar queries complexas em controllers e managers.
Planejar rotacao de credenciais reais expostas anteriormente.
Planejar etapa de hardening de seguranca HTTP, CORS e rate limit.
<!-- ETAPA_04_FIM -->

<!-- ETAPA_04_1_INICIO -->
## Pendencias apos Etapa 04.1

Data: 2026-07-06T20:11:45

Validar setup_db.js com PostgreSQL.
Validar queries complexas em controllers, managers e rotas.
Executar testes funcionais em ambiente controlado.
Planejar rotacao de credenciais reais expostas anteriormente.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
<!-- ETAPA_04_1_FIM -->

<!-- ETAPA_05_INICIO -->
## Pendencias apos Etapa 05

Data: 2026-07-06T20:13:42

Corrigir achados de alta severidade apontados no relatorio.
Revisar achados de media severidade apontados no relatorio.
Validar setup_db.js com PostgreSQL em ambiente controlado.
Executar testes funcionais de rotas e controllers.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
Planejar rotacao de credenciais reais expostas anteriormente.
<!-- ETAPA_05_FIM -->

<!-- ETAPA_06_INICIO -->
## Pendencias apos Etapa 06

Data: 2026-07-06T20:17:02

Validar se contatos possui constraint unica em empresa_id e telefone.
Criar ou ajustar migration caso a constraint unica nao exista.
Revisar queries restantes com funcoes agregadas e retorno de inserts.
Validar fluxo funcional de recebimento e envio de mensagens.
Executar testes em ambiente controlado com PostgreSQL.
<!-- ETAPA_06_FIM -->

<!-- ETAPA_06_1_INICIO -->
## Pendencias apos Etapa 06.1

Data: 2026-07-06T20:19:13

Validar constraint unica em contatos por empresa_id e telefone.
Criar migration PostgreSQL caso a constraint nao exista.
Revisar queries com funcoes agregadas especificas e retorno de inserts.
Executar teste funcional de recebimento de mensagem e criacao de contato.
Executar teste funcional de envio de mensagem e registro no historico.
<!-- ETAPA_06_1_FIM -->

<!-- ETAPA_06_2_INICIO -->
## Pendencias apos Etapa 06.2

Data: 2026-07-06T20:21:11

Validar constraint unica em contatos por empresa_id e telefone.
Criar migration PostgreSQL caso a constraint nao exista.
Executar teste funcional de recebimento de mensagem e criacao de contato.
Executar teste funcional de atualizacao de contato existente.
Revisar proximas queries suspeitas de media severidade.
<!-- ETAPA_06_2_FIM -->

<!-- ETAPA_07_INICIO -->
## Pendencias apos Etapa 07

Data: 2026-07-06T20:23:50

Antes de aplicar a migration, verificar se existem contatos duplicados por empresa_id e telefone.
Executar a migration em ambiente controlado.
Validar recebimento de mensagem criando contato novo.
Validar recebimento de mensagem atualizando contato existente.
Revisar queries de media severidade apontadas na Etapa 05.
<!-- ETAPA_07_FIM -->

<!-- ETAPA_07_1_INICIO -->
## Pendencias apos Etapa 07.1

Data: 2026-07-06T20:26:42

Resolver pendencia runtime de constraint ou duplicidade em contatos antes de usar o fluxo em producao.
Revisar queries de media severidade apontadas na Etapa 05.
Executar testes funcionais de recebimento e envio de mensagens.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
Planejar rotacao de credenciais reais expostas anteriormente.
<!-- ETAPA_07_1_FIM -->

<!-- ETAPA_07_2_INICIO -->
## Pendencias apos Etapa 07.2

Data: 2026-07-06T20:29:56

Revisar queries de media severidade apontadas na Etapa 05.
Executar testes funcionais de recebimento e envio de mensagens.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
Planejar rotacao de credenciais reais expostas anteriormente.
<!-- ETAPA_07_2_FIM -->
