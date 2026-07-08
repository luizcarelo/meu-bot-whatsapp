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

Data: 2026-07-06T21:44:35

Validar fluxos reais da interface web com usuario logado.
Validar endpoints autenticados com dados reais em modo controlado.
Reduzir verbosidade de logs de sessao e cookies em producao.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
Planejar rotacao de credenciais reais expostas anteriormente.
<!-- ETAPA_12_FIM -->

<!-- ETAPA_12_1_INICIO -->
## Pendencias apos Etapa 12.1

Data: 2026-07-06T21:36:04

Revisar resultado do diagnostico de login.
Se a senha informada nao autenticar, aprovar etapa separada para reset controlado de senha.
Validar rotas reais do sistema apos login confirmado.
Reduzir verbosidade de logs de sessao e cookies em producao.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
<!-- ETAPA_12_1_FIM -->

<!-- ETAPA_12_2_INICIO -->
## Pendencias apos Etapa 12.2

Data: 2026-07-06T21:44:23

Reexecutar a Etapa 12 com credenciais via variaveis de ambiente.
Confirmar Login OK e cookie recebido no relatorio da Etapa 12.
Validar fluxos reais da interface web em etapa posterior.
<!-- ETAPA_12_2_FIM -->

<!-- ETAPA_13_INICIO -->
## Pendencias apos Etapa 13

Data: 2026-07-06T21:46:57

Revisar eventuais 404 de links reais encontrados no dashboard.
Reduzir verbosidade de logs de sessao e cookies em producao.
Validar fluxos reais de cadastro/edicao em ambiente controlado e com dados de teste.
Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes.
Planejar rotacao de credenciais reais expostas anteriormente.
<!-- ETAPA_13_FIM -->

<!-- ETAPA_14_INICIO -->
## Pendencias apos Etapa 14

Data: 2026-07-06T21:50:01

Se o app nao foi reiniciado, reiniciar em janela controlada para aplicar server.js.
Reexecutar Etapa 13 apos restart para confirmar reducao dos logs em runtime.
Revisar CORS permissivo em etapa dedicada.
Revisar configuracao completa de cookie de sessao para HTTPS producao.
Planejar rate limit e politica de seguranca de conteudo.
<!-- ETAPA_14_FIM -->

<!-- ETAPA_14_1_INICIO -->
## Pendencias apos Etapa 14.1

Data: 2026-07-06T21:55:04

Revisar CORS permissivo em etapa dedicada.
Revisar configuracao completa de cookie de sessao para HTTPS producao.
Planejar rate limit e politica de seguranca de conteudo.
Validar ambiente externo com HTTPS antes de producao.
<!-- ETAPA_14_1_FIM -->

<!-- ETAPA_14_2_INICIO -->
## Pendencias apos Etapa 14.2

Data: 2026-07-06T22:04:35

Revisar CORS permissivo em etapa dedicada.
Revisar cookie SameSite e secure para HTTPS producao.
Planejar rate limit e politica de seguranca de conteudo.
Validar ambiente externo com HTTPS antes de producao.
<!-- ETAPA_14_2_FIM -->

<!-- ETAPA_15_INICIO -->
## Pendencias apos Etapa 15

Data: 2026-07-06T22:11:48

Se o app nao foi reiniciado, reiniciar em janela controlada com ETAPA15_RESTART_APP=true.
Definir CORS_ORIGINS no ambiente final com dominio real HTTPS.
Definir COOKIE_SECURE=true apenas com HTTPS valido.
Validar ambiente externo com HTTPS.
Planejar rate limit e politica CSP dedicada.
<!-- ETAPA_15_FIM -->

<!-- ETAPA_15_1_INICIO -->
## Pendencias apos Etapa 15.1

Data: 2026-07-06T22:17:23

Reexecutar ou revisar Etapa 15 apos hotfix se necessario.
Confirmar headers e CORS em runtime com app estavel.
Definir CORS_ORIGINS no ambiente final com dominio real HTTPS.
Definir COOKIE_SECURE=true apenas com HTTPS valido.
Planejar rate limit e politica CSP dedicada.
<!-- ETAPA_15_1_FIM -->

<!-- ETAPA_15_2_INICIO -->
## Pendencias apos Etapa 15.2

Data: 2026-07-06T22:21:48

Se algum header ou CORS ainda estiver inadequado, propor correcao pequena e especifica.
Definir CORS_ORIGINS no ambiente final com dominio real HTTPS.
Definir COOKIE_SECURE=true apenas com HTTPS valido.
Validar ambiente externo com HTTPS.
Planejar rate limit e politica CSP dedicada.
<!-- ETAPA_15_2_FIM -->

<!-- ETAPA_16_INICIO -->
## Pendencias apos Etapa 16

Data: 2026-07-06T22:36:17

Corrigir referencias locais ausentes identificadas na auditoria.
Definir primeira melhoria visual controlada para a tela de login.
Planejar internalizacao gradual de dependencias externas.
Avaliar substituicao de FontAwesome CDN por assets locais.
Avaliar Alpine local em public/vendor.
Planejar build local do Tailwind sem quebrar classes existentes.
Mapear scripts inline antes de aplicar CSP forte.
<!-- ETAPA_16_FIM -->

<!-- ETAPA_17_INICIO -->
## Pendencias apos Etapa 17

Data: 2026-07-06T22:40:03

Validar visual da tela de login manualmente no navegador.
Planejar melhoria controlada do dashboard.
Planejar internalizacao de Alpine, FontAwesome e Tailwind em etapas separadas.
Mapear scripts inline antes de CSP forte.
Revisar assets locais ausentes apontados na Etapa 16.
<!-- ETAPA_17_FIM -->

<!-- ETAPA_17_1_INICIO -->
## Pendencias apos Etapa 17.1

Data: 2026-07-06T22:46:40

Validar visual manualmente no navegador.
Planejar melhoria controlada do dashboard.
Planejar internalizacao de dependencias externas em etapas separadas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_17_1_FIM -->

<!-- ETAPA_18_INICIO -->
## Pendencias apos Etapa 18

Data: 2026-07-06T22:51:14

Validar visual do dashboard manualmente no navegador.
Planejar internalizacao de dependencias externas.
Corrigir ou criar CSS local compartilhado para /css/style.css.
Planejar melhoria de views/crm.ejs e views/admin-panel.ejs em etapas separadas.
Mapear scripts inline antes de aplicar CSP forte.
<!-- ETAPA_18_FIM -->

<!-- ETAPA_19_INICIO -->
## Pendencias apos Etapa 19

Data: 2026-07-06T23:01:50

Validar visual de admin-panel, crm e super-admin no navegador.
Planejar etapa para aplicar classes er de forma controlada nas views antigas.
Planejar internalizacao de FontAwesome, Alpine, Tailwind e imagens externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_19_FIM -->

<!-- ETAPA_20_INICIO -->
## Pendencias apos Etapa 20

Data: 2026-07-06T23:13:14

Validar visual do CRM manualmente no navegador.
Planejar aplicacao visual em views/admin-panel.ejs.
Planejar aplicacao visual em views/super-admin.ejs.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_20_FIM -->

<!-- ETAPA_20_1_INICIO -->
## Pendencias apos Etapa 20.1

Data: 2026-07-06T23:19:41

Validar visual do CRM manualmente no navegador.
Planejar aplicacao visual em views/admin-panel.ejs.
Planejar aplicacao visual em views/super-admin.ejs.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_20_1_FIM -->

<!-- ETAPA_20_2_INICIO -->
## Pendencias apos Etapa 20.2

Data: 2026-07-06T23:30:31

Validar visual do CRM manualmente no navegador.
Planejar aplicacao visual em views/admin-panel.ejs.
Planejar aplicacao visual em views/super-admin.ejs.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_20_2_FIM -->

<!-- ETAPA_21_INICIO -->
## Pendencias apos Etapa 21

Data: 2026-07-06T23:35:11

Validar visual do painel administrativo manualmente no navegador.
Planejar aplicacao visual em views/super-admin.ejs.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_21_FIM -->

<!-- ETAPA_21_1_INICIO -->
## Pendencias apos Etapa 21.1

Data: 2026-07-06T23:45:03

Validar visual do painel administrativo manualmente no navegador.
Planejar aplicacao visual em views/super-admin.ejs.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_21_1_FIM -->

<!-- ETAPA_21_2_INICIO -->
## Pendencias apos Etapa 21.2

Data: 2026-07-06T23:50:22

Validar visual do painel administrativo manualmente no navegador.
Planejar aplicacao visual em views/super-admin.ejs.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_21_2_FIM -->

<!-- ETAPA_21_3_INICIO -->
## Pendencias apos Etapa 21.3

Data: 2026-07-06T23:53:24

Validar visual do painel administrativo manualmente no navegador.
Planejar aplicacao visual em views/super-admin.ejs.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_21_3_FIM -->

<!-- ETAPA_22_INICIO -->
## Pendencias apos Etapa 22

Data: 2026-07-06T23:57:44

Validar visual do Super Admin manualmente no navegador.
Se /super-admin nao validar em runtime, planejar Etapa 22.1 para rota ou controller.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_22_FIM -->

<!-- ETAPA_22_1_INICIO -->
## Pendencias apos Etapa 22.1

Data: 2026-07-07T00:03:38

Validar visual do Super Admin manualmente no navegador.
Se houver erro de permissao, revisar regra isSuperAdmin em etapa separada.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_22_1_FIM -->

<!-- ETAPA_23_INICIO -->
## Pendencias apos Etapa 23

Data: 2026-07-07T00:20:25

Validar manualmente as telas no navegador.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
Avaliar padronizacao visual adicional apenas apos validacao manual.
<!-- ETAPA_23_FIM -->

<!-- ETAPA_23_1_INICIO -->
## Pendencias apos Etapa 23.1

Data: 2026-07-07T00:10:18

Executar novamente a Etapa 23 se desejar consolidar status geral final.
Validar manualmente as telas no navegador.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_23_1_FIM -->

<!-- ETAPA_23_2_INICIO -->
## Pendencias apos Etapa 23.2

Data: 2026-07-07T00:14:15

Reexecutar a Etapa 23 para consolidar o status geral final.
Validar manualmente /super-admin no navegador.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_23_2_FIM -->

<!-- ETAPA_23_3_INICIO -->
## Pendencias apos Etapa 23.3

Data: 2026-07-07T00:20:13

Reexecutar a Etapa 23 para consolidar o status geral final.
Validar manualmente /super-admin no navegador.
Planejar internalizacao de dependencias externas.
Mapear scripts inline antes de CSP forte.
<!-- ETAPA_23_3_FIM -->

<!-- ETAPA_24_INICIO -->
## Pendencias apos Etapa 24

Data: 2026-07-07T00:33:13

Trocar senhas padrao se a base de teste for mantida em ambiente acessivel.
Criar dados adicionais de teste somente se forem necessarios para cenarios especificos.
Validar manualmente login dos usuarios de teste no navegador.
<!-- ETAPA_24_FIM -->

<!-- ETAPA_25_INICIO -->
## Pendencias apos Etapa 25

Data: 2026-07-07T00:46:46

Validar manualmente o layout no navegador em desktop e mobile.
Executar Etapa 26 para auditoria funcional completa.
Planejar Etapa 27 para Baileys e camada WhatsApp.
Planejar refinamento visual fino apos avaliacao manual.
<!-- ETAPA_25_FIM -->

<!-- ETAPA_25_1_INICIO -->
## Pendencias apos Etapa 25.1

Data: 2026-07-07T00:52:30

Validar manualmente a navegacao entre dashboard, CRM, admin panel e super admin.
Se aprovado visualmente, seguir para Etapa 26 de auditoria funcional.
Refinar responsividade mobile se necessario.
<!-- ETAPA_25_1_FIM -->

<!-- ETAPA_25_2_INICIO -->
## Pendencias apos Etapa 25.2

Data: 2026-07-07T00:57:10

Validar manualmente o dashboard no navegador e confirmar ausencia de erros appData/initApp.
Planejar etapa futura para remover Tailwind CDN e Alpine CDN em producao.
Seguir para Etapa 26 de auditoria funcional apos validacao manual.
<!-- ETAPA_25_2_FIM -->

<!-- ETAPA_25_3_INICIO -->
## Pendencias apos Etapa 25.3

Data: 2026-07-07T01:02:26

Validar no navegador se o erro 500 de /api/whatsapp/status/5 sumiu.
Planejar Etapa 26 para auditoria funcional completa.
Planejar etapa futura para internalizar Tailwind e Alpine.
<!-- ETAPA_25_3_FIM -->

<!-- ETAPA_25_4_INICIO -->
## Pendencias apos Etapa 25.4

Data: 2026-07-07T01:08:08

Validar manualmente /dashboard em desktop, notebook, tablet e celular.
Executar auditoria funcional completa na Etapa 26.
Planejar etapa futura para remover CDN de Tailwind/Alpine das demais telas.
Planejar refinamento visual do /crm sem misturar com dashboard.
<!-- ETAPA_25_4_FIM -->

<!-- ETAPA_25_4_1_INICIO -->
## Pendencias apos Etapa 25.4.1

Data: 2026-07-07T01:14:19

Validar manualmente o dashboard com Ctrl+F5.
Se aprovado, seguir para auditoria funcional completa.
Refinar futuramente o shell em todas as telas se necessario.
<!-- ETAPA_25_4_1_FIM -->

<!-- ETAPA_26_INICIO -->
## Pendencias apos Etapa 26

Data: 2026-07-07T01:29:02

Etapa 27: criar base do frontend React.
Etapa 28: criar backend modular em paralelo.
Etapa 29: padronizar respostas reais de API.
Etapa 30: migrar login e sessao.
Etapa 31: migrar dashboard.
Etapa 32: criar gestao WhatsApp web.
<!-- ETAPA_26_FIM -->

<!-- ETAPA_27_INICIO -->
## Pendencias apos Etapa 27

Data: 2026-07-07T01:34:21

Validar npm install e npm run build no frontend.
Etapa 28: criar backend modular em paralelo.
Etapa 29: padronizar respostas de API.
Etapa 30: migrar login e sessao para o frontend React.
Etapa 31: migrar dashboard definitivo.
<!-- ETAPA_27_FIM -->

<!-- ETAPA_27_1_INICIO -->
## Pendencias apos Etapa 27.1

Data: 2026-07-07T08:02:24

Validar visualmente o frontend React com npm run dev.
Etapa 28: criar backend modular em paralelo.
Etapa 29: padronizar respostas de API.
<!-- ETAPA_27_1_FIM -->

<!-- ETAPA_27_2_INICIO -->
## Pendencias apos Etapa 27.2

Data: 2026-07-07T08:10:08

Validar visualmente o frontend com npm run dev.
Etapa 28: criar backend modular em paralelo.
Etapa 29: padronizar respostas reais de API.
Etapa 30: migrar login real para React.
<!-- ETAPA_27_2_FIM -->

<!-- ETAPA_28_INICIO -->
## Pendencias apos Etapa 28

Data: 2026-07-08T19:08:13

Etapa 28.1: validar backend modular isolado com npm install opcional.
Etapa 29: padronizar respostas reais de API.
Etapa 30: migrar autenticacao para contrato novo.
Etapa futura: conectar repositories modulares ao banco.
<!-- ETAPA_28_FIM -->

<!-- ETAPA_28_1_INICIO -->
## Pendencias apos Etapa 28.1

Data: 2026-07-08T20:00:47

Etapa 29: padronizar respostas reais de API.
Etapa 30: migrar autenticacao para contrato novo.
Etapa futura: conectar repositories modulares ao banco.
Etapa futura: integrar backend modular ao proxy ou Docker.
<!-- ETAPA_28_1_FIM -->

<!-- ETAPA_29_1_INICIO -->
## Pendencias apos Etapa 29.1

Data: 2026-07-08T20:15:43

Etapa 29.2: reforcar apiResponse.js e errors.js.
Etapa 29.3: padronizar errorHandler e notFoundHandler.
Etapa 29.4: validar endpoints health com contrato padronizado.
<!-- ETAPA_29_1_FIM -->
