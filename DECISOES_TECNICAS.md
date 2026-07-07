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
