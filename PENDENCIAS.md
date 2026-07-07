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

<!-- ETAPA_08_INICIO -->
## Pendencias apos Etapa 08

Data: 2026-07-06T20:32:39

Investigar padroes focados restantes listados no relatorio da Etapa 08.
Executar testes funcionais das telas de CRM, usuarios e contatos.
Validar retorno das consultas alteradas em ambiente com dados reais.
Revisar achados de baixa severidade, especialmente booleanos numericos.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
Planejar rotacao de credenciais reais expostas anteriormente.
<!-- ETAPA_08_FIM -->

<!-- ETAPA_08_1_INICIO -->
## Pendencias apos Etapa 08.1

Data: 2026-07-06T21:08:22

Executar testes funcionais de criacao e edicao de empresas.
Executar testes funcionais de alteracao de senha do admin da empresa.
Validar telas do CRM que usam consultas com SELECT LIMIT.
Revisar achados de baixa severidade, especialmente booleanos numericos.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
<!-- ETAPA_08_1_FIM -->

<!-- ETAPA_09_INICIO -->
## Pendencias apos Etapa 09

Data: 2026-07-06T21:11:11

Corrigir pendencias de validacao somente leitura listadas no relatorio da Etapa 09.
Executar testes funcionais com escrita em ambiente controlado.
Validar criacao de empresa e usuario admin.
Validar fluxo de recebimento de mensagem e upsert de contato.
Validar fluxo de envio de mensagem e registro no historico.
Revisar achados de baixa severidade, especialmente booleanos numericos.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
<!-- ETAPA_09_FIM -->

<!-- ETAPA_09_1_INICIO -->
## Pendencias apos Etapa 09.1

Data: 2026-07-06T21:13:14

Revisar a migration criada antes de executar.
Executar a migration em ambiente controlado.
Repetir validacao somente leitura da Etapa 09 apos aplicar migration.
Executar testes funcionais com escrita em ambiente controlado.
Validar telas de setores e horarios de atendimento.
<!-- ETAPA_09_1_FIM -->

<!-- ETAPA_09_2_INICIO -->
## Pendencias apos Etapa 09.2

Data: 2026-07-06T21:15:43

Executar testes funcionais com escrita em ambiente controlado.
Validar criacao de empresa e usuario admin.
Validar fluxo de recebimento de mensagem e upsert de contato.
Validar fluxo de envio de mensagem e registro no historico.
Validar telas de setores e horarios de atendimento.
Revisar achados de baixa severidade, especialmente booleanos numericos.
<!-- ETAPA_09_2_FIM -->

<!-- ETAPA_10_HOTFIX_INICIO -->
## Pendencias apos Hotfix Etapa 10

Data: 2026-07-06T21:19:12

Executar novamente a Etapa 10.
Enviar o relatorio Markdown da Etapa 10 apos a nova execucao.
<!-- ETAPA_10_HOTFIX_FIM -->

<!-- ETAPA_10_INICIO -->
## Pendencias apos Etapa 10

Data: 2026-07-06T21:21:55

Executar testes funcionais pela interface web.
Validar fluxo real de login e painel administrativo.
Validar envio e recebimento real de mensagens com ambiente controlado.
Revisar achados de baixa severidade, especialmente booleanos numericos.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
Planejar rotacao de credenciais reais expostas anteriormente.
<!-- ETAPA_10_FIM -->

<!-- ETAPA_10_1_INICIO -->
## Pendencias apos Etapa 10.1

Data: 2026-07-06T21:21:38

Reexecutar a Etapa 10 de testes funcionais com escrita.
Validar se o insert em usuarios_painel avanca sem violar chave primaria.
Executar testes funcionais pela interface web apos Etapa 10 passar.
Revisar achados de baixa severidade, especialmente booleanos numericos.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
<!-- ETAPA_10_1_FIM -->

<!-- ETAPA_11_INICIO -->
## Pendencias apos Etapa 11

Data: 2026-07-06T21:27:13

Validar login real em etapa separada.
Validar endpoints autenticados em ambiente controlado.
Validar fluxo real de WhatsApp somente apos login e sessoes estarem estaveis.
Revisar achados de logs, se houver.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
<!-- ETAPA_11_FIM -->

<!-- ETAPA_12_INICIO -->
## Pendencias apos Etapa 12

Data: 2026-07-06T21:31:11

Corrigir achados da Etapa 12 antes de avancar para fluxos reais.
Validar fluxos reais da interface web com usuario logado.
Validar endpoints autenticados com dados reais em modo controlado.
Reduzir verbosidade de logs de sessao e cookies em producao.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
Planejar rotacao de credenciais reais expostas anteriormente.
<!-- ETAPA_12_FIM -->
