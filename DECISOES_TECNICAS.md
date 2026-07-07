# DECISOES_TECNICAS

<!-- ETAPA_02_INICIO -->
## Etapa 02 - Decisoes tecnicas

Data: 2026-07-06T11:01:56

Decidido nao apagar o .env automaticamente para evitar indisponibilidade do ambiente.
Decidido criar .env.example como referencia segura para configuracao.
Decidido tratar Docker, banco, controllers e dependencias em etapas separadas.
Decidido manter manifestos com hash para auditoria antes e depois das alteracoes.
<!-- ETAPA_02_FIM -->





<!-- ETAPA_04_INICIO -->
## Etapa 04 - Decisoes tecnicas

Data: 2026-07-06T20:09:04

Decidido manter PostgreSQL como banco oficial do projeto.
Decidido converter scripts auxiliares para pg sem alterar regras de negocio.
Decidido ignorar reports, backups e scripts de etapas anteriores no scan de rastros.
Decidido manter validacao de sintaxe separada de testes funcionais de banco.
<!-- ETAPA_04_FIM -->

<!-- ETAPA_04_1_INICIO -->
## Etapa 04.1 - Decisao consolidada

Data: 2026-07-06T20:11:45

PostgreSQL fica consolidado como banco oficial do projeto.
Referencias antigas de banco foram removidas dos documentos de controle.
Historico operacional fica preservado por backups e relatorios gerados em reports.
Proximas validacoes devem focar setup_db.js, queries, rotas e fluxo funcional.
<!-- ETAPA_04_1_FIM -->

<!-- ETAPA_05_INICIO -->
## Etapa 05 - Decisoes tecnicas

Data: 2026-07-06T20:13:42

Decidido auditar antes de corrigir queries para reduzir risco.
Decidido tratar setup_db.js e queries suspeitas em etapa posterior.
Decidido manter esta etapa sem execucao de banco ou Docker.
Decidido usar severidade para priorizar correcoes futuras.
<!-- ETAPA_05_FIM -->

<!-- ETAPA_06_INICIO -->
## Etapa 06 - Decisoes tecnicas

Data: 2026-07-06T20:17:02

Decidido corrigir primeiro apenas achados de alta severidade.
Decidido usar ON CONFLICT com chave logica empresa_id e telefone.
Decidido nao alterar schema nesta etapa para reduzir risco operacional.
Decidido validar constraints e migrations em etapa posterior.
<!-- ETAPA_06_FIM -->

<!-- ETAPA_06_1_INICIO -->
## Etapa 06.1 - Decisoes tecnicas

Data: 2026-07-06T20:19:13

Decidido finalizar a correcao de sintaxe no codigo antes de alterar schema.
Decidido manter a chave logica empresa_id e telefone para conflito de contatos.
Decidido deixar constraint e migrations para etapa dedicada de schema.
<!-- ETAPA_06_1_FIM -->

<!-- ETAPA_06_2_INICIO -->
## Etapa 06.2 - Decisoes tecnicas

Data: 2026-07-06T20:21:11

Decidido substituir funcao legada por funcao nativa compativel com PostgreSQL.
Decidido manter a referencia da tabela contatos para preservar a foto existente quando a nova vier vazia.
Decidido manter schema e migrations para uma etapa dedicada.
<!-- ETAPA_06_2_FIM -->

<!-- ETAPA_07_INICIO -->
## Etapa 07 - Decisoes tecnicas

Data: 2026-07-06T20:23:50

Decidido suportar ON CONFLICT por indice unico em empresa_id e telefone.
Decidido nao executar migration automaticamente.
Decidido criar migration idempotente quando nao houver indice ou constraint detectado localmente.
Decidido validar duplicidades existentes antes de aplicar a migration em producao.
<!-- ETAPA_07_FIM -->

<!-- ETAPA_07_1_INICIO -->
## Etapa 07.1 - Decisoes tecnicas

Data: 2026-07-06T20:26:42

Decidido validar o banco real antes de prosseguir para revisao de queries de media severidade.
Decidido nao executar migration automaticamente nesta etapa.
Decidido nao imprimir credenciais nos relatorios.
Decidido tratar duplicidades ou ausencia de constraint em etapa separada, se necessario.
<!-- ETAPA_07_1_FIM -->

<!-- ETAPA_07_2_INICIO -->
## Etapa 07.2 - Decisoes tecnicas

Data: 2026-07-06T20:29:56

Decidido validar PostgreSQL pela rede Docker Compose.
Decidido nao executar migration automaticamente.
Decidido nao imprimir credenciais nos relatorios.
Decidido seguir para revisao de queries de media severidade somente apos runtime estar validado.
<!-- ETAPA_07_2_FIM -->

<!-- ETAPA_08_INICIO -->
## Etapa 08 - Decisoes tecnicas

Data: 2026-07-06T20:32:39

Decidido corrigir apenas padroes reais e evitar mexer em template strings.
Decidido usar STRING_AGG para agregacao textual.
Decidido usar json_agg e json_build_object para agregacao JSON.
Decidido usar RETURNING id para capturar id de insert no PostgreSQL.
<!-- ETAPA_08_FIM -->

<!-- ETAPA_08_1_INICIO -->
## Etapa 08.1 - Decisoes tecnicas

Data: 2026-07-06T21:08:22

Decidido usar RETURNING id para capturar identificadores em PostgreSQL.
Decidido remover LIMIT de comandos UPDATE por incompatibilidade com PostgreSQL.
Decidido considerar SELECT com LIMIT como valido e fora do escopo desta correcao.
<!-- ETAPA_08_1_FIM -->

<!-- ETAPA_09_INICIO -->
## Etapa 09 - Decisoes tecnicas

Data: 2026-07-06T21:11:11

Decidido executar apenas consultas somente leitura nesta etapa.
Decidido validar tabelas e colunas antes de testes funcionais com escrita.
Decidido nao executar migrations, inserts, updates ou deletes.
Decidido tratar falhas encontradas em etapa posterior, se houver.
<!-- ETAPA_09_FIM -->

<!-- ETAPA_09_1_INICIO -->
## Etapa 09.1 - Decisoes tecnicas

Data: 2026-07-06T21:13:14

Decidido preparar migration sem execucao automatica.
Decidido usar ADD COLUMN IF NOT EXISTS e CREATE TABLE IF NOT EXISTS.
Decidido incluir campos de almoco por compatibilidade com utilitario de atendimento.
Decidido validar novamente em etapa posterior apos execucao controlada.
<!-- ETAPA_09_1_FIM -->

<!-- ETAPA_09_2_INICIO -->
## Etapa 09.2 - Decisoes tecnicas

Data: 2026-07-06T21:15:43

Decidido executar a migration idempotente aprovada na Etapa 09.1.
Decidido usar psql com ON_ERROR_STOP para interromper em erro.
Decidido gerar backup logico antes da execucao quando pg_dump estiver disponivel.
Decidido repetir validacao somente leitura apos aplicar o schema.
<!-- ETAPA_09_2_FIM -->

<!-- ETAPA_10_HOTFIX_INICIO -->
## Hotfix Etapa 10 - Decisao tecnica

Data: 2026-07-06T21:19:12

Decidido aplicar hotfix minimo e localizado.
Decidido nao executar banco ou Docker durante o hotfix.
Decidido validar sintaxe antes de liberar nova execucao da Etapa 10.
<!-- ETAPA_10_HOTFIX_FIM -->

<!-- ETAPA_10_INICIO -->
## Etapa 10 - Decisoes tecnicas

Data: 2026-07-06T21:21:55

Decidido executar testes de escrita somente dentro de transacao com rollback.
Decidido usar dados de teste marcados com identificador da etapa.
Decidido validar limpeza apos rollback com consultas separadas.
Decidido manter testes sem chamadas externas ao WhatsApp ou SMTP.
<!-- ETAPA_10_FIM -->

<!-- ETAPA_10_1_INICIO -->
## Etapa 10.1 - Decisoes tecnicas

Data: 2026-07-06T21:21:38

Decidido corrigir sequences antes de repetir testes funcionais de escrita.
Decidido usar setval com GREATEST entre MAX(id) e 1.
Decidido nao inserir dados de teste nesta etapa.
Decidido gerar backup logico antes de alterar sequences.
<!-- ETAPA_10_1_FIM -->

<!-- ETAPA_11_INICIO -->
## Etapa 11 - Decisoes tecnicas

Data: 2026-07-06T21:27:13

Decidido validar disponibilidade antes de testar login real.
Decidido nao fazer escrita nem chamadas externas nesta etapa.
Decidido separar login e fluxos reais para etapa posterior.
Decidido registrar achados de logs para triagem posterior.
<!-- ETAPA_11_FIM -->

<!-- ETAPA_12_INICIO -->
## Etapa 12 - Decisoes tecnicas

Data: 2026-07-06T21:44:35

Decidido manter cookie apenas em memoria durante a validacao.
Decidido nao imprimir senha nem persistir credenciais.
Decidido nao executar criacao, edicao ou exclusao de dados nesta etapa.
Decidido separar fluxos reais de WhatsApp para etapa posterior.
<!-- ETAPA_12_FIM -->

<!-- ETAPA_12_1_INICIO -->
## Etapa 12.1 - Decisoes tecnicas

Data: 2026-07-06T21:36:04

Decidido diagnosticar antes de resetar senha.
Decidido nao persistir cookies nem credenciais.
Decidido testar payloads JSON e form com campos password e senha.
Decidido nao alterar banco nem codigo nesta etapa.
<!-- ETAPA_12_1_FIM -->

<!-- ETAPA_12_2_INICIO -->
## Etapa 12.2 - Decisoes tecnicas

Data: 2026-07-06T21:44:23

Decidido alinhar o script ao AuthController, que espera email e senha.
Decidido manter fallback com password para compatibilidade futura.
Decidido nao executar login automaticamente nesta correcao.
Decidido nao alterar codigo da aplicacao.
<!-- ETAPA_12_2_FIM -->

<!-- ETAPA_13_INICIO -->
## Etapa 13 - Decisoes tecnicas

Data: 2026-07-06T21:46:57

Decidido testar links reais do dashboard em vez de rotas presumidas.
Decidido limitar a etapa a requisicoes GET/HEAD seguras.
Decidido nao executar operacoes de escrita.
Decidido registrar exposicao de Session ID e cookies nos logs para hardening posterior.
<!-- ETAPA_13_FIM -->

<!-- ETAPA_14_INICIO -->
## Etapa 14 - Decisoes tecnicas

Data: 2026-07-06T21:50:01

Decidido remover dados de sessao e cookie dos logs.
Decidido manter logs uteis sem identificadores sensiveis.
Decidido nao reiniciar app por padrao.
Decidido permitir restart somente com ETAPA14_RESTART_APP=true.
Decidido adicionar headers basicos sem alterar regras de negocio.
<!-- ETAPA_14_FIM -->

<!-- ETAPA_14_1_INICIO -->
## Etapa 14.1 - Decisoes tecnicas

Data: 2026-07-06T21:55:04

Decidido comparar hashes para confirmar se o container usa o codigo atualizado.
Decidido nao fazer rebuild automaticamente sem ETAPA14_1_REBUILD_APP=true.
Decidido analisar logs novos usando marco temporal da propria etapa.
Decidido manter a validacao sem alterar banco.
<!-- ETAPA_14_1_FIM -->

<!-- ETAPA_14_2_INICIO -->
## Etapa 14.2 - Decisoes tecnicas

Data: 2026-07-06T22:04:35

Decidido substituir logs identificaveis por logs com IDs internos.
Decidido nao alterar regras de autenticacao.
Decidido nao alterar banco.
Decidido reiniciar app somente com ETAPA14_2_RESTART_APP=true.
<!-- ETAPA_14_2_FIM -->

<!-- ETAPA_15_INICIO -->
## Etapa 15 - Decisoes tecnicas

Data: 2026-07-06T22:11:48

Decidido bloquear origem aberta em CORS quando houver sessao e cookie.
Decidido usar CORS_ORIGINS ou APP_URL como origem permitida em ambiente configurado.
Decidido usar origens locais somente como fallback de desenvolvimento.
Decidido condicionar secure do cookie a NODE_ENV production e COOKIE_SECURE true.
Decidido manter restart dependente de ETAPA15_RESTART_APP=true.
<!-- ETAPA_15_FIM -->

<!-- ETAPA_15_1_INICIO -->
## Etapa 15.1 - Decisao tecnica

Data: 2026-07-06T22:17:23

Decidido corrigir apenas sintaxe do bloco cookie.
Decidido nao alterar banco nem regra de autenticacao.
Decidido reiniciar app somente apos node --check OK.
Decidido manter a Etapa 15 para revisao posterior de CORS e headers.
<!-- ETAPA_15_1_FIM -->

<!-- ETAPA_15_2_INICIO -->
## Etapa 15.2 - Decisoes tecnicas

Data: 2026-07-06T22:21:48

Decidido auditar antes de nova alteracao em CORS e headers.
Decidido nao reiniciar app nesta etapa.
Decidido usar teste com Origin local e Origin externo nao permitido.
Decidido manter esta etapa como baseline de seguranca HTTP.
<!-- ETAPA_15_2_FIM -->

<!-- ETAPA_16_INICIO -->
## Etapa 16 - Decisoes tecnicas frontend

Data: 2026-07-06T22:36:17

Decidido auditar antes de alterar telas.
Decidido separar melhorias visuais de internalizacao de dependencias.
Decidido iniciar melhorias futuras por login e dashboard.
Decidido tratar Tailwind CDN com cautela para evitar quebra de layout.
<!-- ETAPA_16_FIM -->

<!-- ETAPA_17_INICIO -->
## Etapa 17 - Decisoes tecnicas frontend

Data: 2026-07-06T22:40:03

Decidido melhorar apenas views/login.ejs nesta etapa.
Decidido nao remover CDNs ainda para reduzir risco.
Decidido manter endpoint /api/auth/login.
Decidido manter campo senha no payload.
Decidido tratar dashboard em etapa posterior.
<!-- ETAPA_17_FIM -->

<!-- ETAPA_17_1_INICIO -->
## Etapa 17.1 - Decisoes tecnicas

Data: 2026-07-06T22:46:40

Decidido validar runtime antes de novas melhorias visuais.
Decidido comparar hashes local/container para confirmar aplicacao da view.
Decidido nao alterar frontend nesta etapa.
Decidido reiniciar app somente com ETAPA17_1_RESTART_APP=true.
<!-- ETAPA_17_1_FIM -->

<!-- ETAPA_18_INICIO -->
## Etapa 18 - Decisoes tecnicas frontend

Data: 2026-07-06T22:51:14

Decidido melhorar o dashboard por injecao controlada de CSS e script marcados.
Decidido nao substituir completamente views/dashboard.ejs para reduzir risco.
Decidido nao remover CDNs nesta etapa.
Decidido manter a logica e os endpoints existentes.
<!-- ETAPA_18_FIM -->

<!-- ETAPA_19_INICIO -->
## Etapa 19 - Decisoes tecnicas frontend

Data: 2026-07-06T23:01:50

Decidido criar CSS compartilhado antes de alterar views antigas.
Decidido evitar seletor universal para reduzir efeito colateral.
Decidido manter escopo visual por classes er.
Decidido manter esta etapa limitada a CSS e documentacao.
<!-- ETAPA_19_FIM -->

<!-- ETAPA_20_INICIO -->
## Etapa 20 - Decisoes tecnicas frontend

Data: 2026-07-06T23:13:14

Decidido aplicar visual no CRM por injecao controlada, sem substituir a view inteira.
Decidido usar public/css/style.css criado na Etapa 19.
Decidido preservar scripts e chamadas existentes.
Decidido nao alterar backend ou banco nesta etapa.
<!-- ETAPA_20_FIM -->

<!-- ETAPA_20_1_INICIO -->
## Etapa 20.1 - Decisoes tecnicas

Data: 2026-07-06T23:19:41

Decidido registrar /crm em routes/index.js porque a view existia mas nao havia rota frontend.
Decidido nao alterar views/crm.ejs nesta etapa.
Decidido reutilizar consulta de empresa semelhante ao dashboard.
Decidido reiniciar app somente com ETAPA20_1_RESTART_APP=true.
<!-- ETAPA_20_1_FIM -->

<!-- ETAPA_20_2_INICIO -->
## Etapa 20.2 - Decisao tecnica

Data: 2026-07-06T23:30:31

Decidido alinhar a consulta da rota /crm com a abordagem ja usada pelo dashboard.
Decidido usar SELECT  FROM empresas para evitar dependencia de colunas inexistentes.
Decidido nao alterar banco nesta etapa.
Decidido manter a rota /crm protegida por isAuthenticated.
<!-- ETAPA_20_2_FIM -->

<!-- ETAPA_21_INICIO -->
## Etapa 21 - Decisoes tecnicas frontend

Data: 2026-07-06T23:35:11

Decidido aplicar visual no painel administrativo por injecao controlada.
Decidido usar public/css/style.css criado na Etapa 19.
Decidido preservar scripts e chamadas existentes.
Decidido nao alterar backend ou banco nesta etapa.
<!-- ETAPA_21_FIM -->

<!-- ETAPA_21_1_INICIO -->
## Etapa 21.1 - Decisoes tecnicas

Data: 2026-07-06T23:45:03

Decidido registrar /admin/painel em routes/index.js porque o controller ja existia.
Decidido reutilizar AdminPanelController.renderPanel.
Decidido nao alterar views/admin-panel.ejs nesta etapa.
Decidido reiniciar app somente com ETAPA21_1_RESTART_APP=true.
<!-- ETAPA_21_1_FIM -->

<!-- ETAPA_21_2_INICIO -->
## Etapa 21.2 - Decisao tecnica

Data: 2026-07-06T23:50:22

Decidido usar consulta minima e segura para a empresa no painel administrativo.
Decidido nao alterar banco nesta etapa.
Decidido nao alterar views nesta etapa.
Decidido manter a rota /admin/painel protegida por isAuthenticated.
<!-- ETAPA_21_2_FIM -->

<!-- ETAPA_21_3_INICIO -->
## Etapa 21.3 - Decisao tecnica

Data: 2026-07-06T23:53:24

Decidido remover telefone da consulta de equipe porque a coluna nao existe no banco atual.
Decidido nao alterar banco nesta etapa.
Decidido nao alterar views nesta etapa.
Decidido preservar a rota /admin/painel registrada na Etapa 21.1.
<!-- ETAPA_21_3_FIM -->

<!-- ETAPA_22_INICIO -->
## Etapa 22 - Decisoes tecnicas frontend

Data: 2026-07-06T23:57:44

Decidido aplicar visual em super-admin por injecao controlada.
Decidido usar public/css/style.css criado na Etapa 19.
Decidido nao alterar backend ou banco nesta etapa.
Decidido tratar rota ou controller em etapa separada se /super-admin nao validar.
<!-- ETAPA_22_FIM -->

<!-- ETAPA_22_1_INICIO -->
## Etapa 22.1 - Decisoes tecnicas

Data: 2026-07-07T00:03:38

Decidido registrar /super-admin em routes/index.js porque a view existia mas nao havia rota frontend.
Decidido proteger a rota com isAuthenticated e isSuperAdmin.
Decidido nao consultar banco nesta etapa porque a view nao usa variaveis EJS.
Decidido nao alterar views nesta etapa.
<!-- ETAPA_22_1_FIM -->

<!-- ETAPA_23_INICIO -->
## Etapa 23 - Decisao tecnica

Data: 2026-07-07T00:20:25

Decidido consolidar as validacoes das etapas 17 a 22 em uma auditoria final.
A auditoria nao altera backend, banco, views, rotas ou controllers.
A auditoria valida runtime com leitura ampliada para evitar falso negativo em marcadores no final das views.
<!-- ETAPA_23_FIM -->

<!-- ETAPA_23_1_INICIO -->
## Etapa 23.1 - Decisao tecnica

Data: 2026-07-07T00:10:18

Decidido sincronizar a view super-admin no container para eliminar divergencia entre arquivo local e runtime.
Decidido nao alterar rotas, controllers, banco ou outras views nesta etapa.
Decidido validar o HTML de /super-admin com limite ampliado de leitura.
<!-- ETAPA_23_1_FIM -->

<!-- ETAPA_23_2_INICIO -->
## Etapa 23.2 - Decisao tecnica

Data: 2026-07-07T00:14:15

Decidido servir views/super-admin.ejs diretamente na rota /super-admin para eliminar divergencia de runtime.
A decisao e segura porque views/super-admin.ejs nao usa variaveis EJS.
Decidido nao alterar banco, controllers ou outras views nesta etapa.
<!-- ETAPA_23_2_FIM -->

<!-- ETAPA_23_3_INICIO -->
## Etapa 23.3 - Decisao tecnica

Data: 2026-07-07T00:20:13

Decidido corrigir o middleware sem remover a protecao isSuperAdmin.
Decidido aceitar boolean true porque o login serializa is_admin como booleano no JSON.
Decidido manter empresa master obrigatoria para preservar seguranca multi-tenant.
Decidido validar o HTML de /super-admin para confirmar que nao houve redirecionamento para dashboard.
<!-- ETAPA_23_3_FIM -->

<!-- ETAPA_24_INICIO -->
## Etapa 24 - Decisao tecnica

Data: 2026-07-07T00:33:13

Decidido executar o seed pelo container Node usando src/config/db.js para aproveitar a mesma conexao do sistema.
Decidido usar operacao idempotente para evitar duplicidade de usuarios e empresas.
Decidido nao apagar dados existentes.
Decidido validar que o admin tenant nao acessa a area Super Admin.
<!-- ETAPA_24_FIM -->
