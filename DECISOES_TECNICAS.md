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
