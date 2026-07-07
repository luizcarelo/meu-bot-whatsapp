# CHANGELOG

<!-- ETAPA_02_INICIO -->
## Etapa 02 - Saneamento seguro

Data: 2026-07-06T11:01:56

Adicionado .env.example com valores de exemplo seguros.
Sanitizados exemplos sensiveis em arquivos de documentacao quando encontrados.
Gerados manifestos antes e depois da etapa.
Gerados relatorios JSON e Markdown da etapa.
Criado backup local antes das alteracoes.
<!-- ETAPA_02_FIM -->





<!-- ETAPA_04_INICIO -->
## Etapa 04 - Limpeza PostgreSQL

Data: 2026-07-06T20:09:04

Atualizada documentacao principal para PostgreSQL.
Atualizadas instrucoes internas em .github/copilot-instructions.md.
Corrigidos comentarios tecnicos em controllers e utilitarios.
Convertidos script/export_full.js e script/backup_database.js para pg.
Gerado relatorio filtrado de rastros restantes.
Executado node --check nos arquivos JS principais.
<!-- ETAPA_04_FIM -->

<!-- ETAPA_04_1_INICIO -->
## Etapa 04.1 - Limpeza final de documentos

Data: 2026-07-06T20:11:45

Limpos documentos de controle para remover referencias antigas de banco.
Mantida a decisao consolidada de PostgreSQL como padrao oficial.
Gerados backup, manifestos e relatorios da etapa.
Executado scan final nos documentos de controle.
<!-- ETAPA_04_1_FIM -->

<!-- ETAPA_05_INICIO -->
## Etapa 05 - Auditoria PostgreSQL

Data: 2026-07-06T20:13:42

Adicionado relatorio de auditoria de compatibilidade PostgreSQL.
Mapeadas queries SQL em arquivos JS.
Analisados setup_db.js e src/config/db.js.
Executado node --check nos principais arquivos JS.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_05_FIM -->

<!-- ETAPA_06_INICIO -->
## Etapa 06 - Correcao de upserts PostgreSQL

Data: 2026-07-06T20:17:02

Substituido uso de INSERT IGNORE por ON CONFLICT DO NOTHING.
Substituido uso de ON DUPLICATE KEY UPDATE por ON CONFLICT DO UPDATE.
Executado node --check nos arquivos alterados.
Executado scan para confirmar ausencia de padroes antigos em controllers e src.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_06_FIM -->

<!-- ETAPA_06_1_INICIO -->
## Etapa 06.1 - Finalizacao dos upserts PostgreSQL

Data: 2026-07-06T20:19:13

Finalizada a correcao do upsert restante em src/managers/SessionManager.js.
Executado node --check no arquivo alterado.
Executado scan de padroes antigos em controllers e src.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_06_1_FIM -->

<!-- ETAPA_06_2_INICIO -->
## Etapa 06.2 - Ajuste final do upsert PostgreSQL

Data: 2026-07-06T20:21:11

Substituida funcao legada de valor nulo no upsert de contatos.
Executado node --check no arquivo alterado.
Executado scan de padroes antigos em controllers e src.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_06_2_FIM -->

<!-- ETAPA_07_INICIO -->
## Etapa 07 - Validacao de schema PostgreSQL

Data: 2026-07-06T20:23:50

Auditados arquivos locais de schema e migrations.
Verificada necessidade de indice unico para contatos por empresa e telefone.
Gerada migration idempotente quando necessario.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_07_FIM -->

<!-- ETAPA_07_1_INICIO -->
## Etapa 07.1 - Validacao runtime de constraint

Data: 2026-07-06T20:26:42

Adicionada validacao runtime da tabela contatos no PostgreSQL.
Verificada existencia das colunas empresa_id e telefone.
Verificada existencia de indice ou constraint unica.
Verificada existencia de duplicidades.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_07_1_FIM -->

<!-- ETAPA_07_2_INICIO -->
## Etapa 07.2 - Validacao runtime via Docker

Data: 2026-07-06T20:29:56

Adicionada validacao runtime via docker compose exec no servico db.
Verificada existencia da tabela contatos e colunas essenciais.
Verificada existencia de indice ou constraint unica.
Verificada existencia de duplicidades.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_07_2_FIM -->

<!-- ETAPA_08_INICIO -->
## Etapa 08 - Correcao de queries medias PostgreSQL

Data: 2026-07-06T20:32:39

Substituidos agregadores antigos por funcoes PostgreSQL.
Ajustado retorno de insert de usuario para RETURNING id.
Removido LIMIT 1 de update incompatvel com PostgreSQL.
Executado node --check nos arquivos alterados.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_08_FIM -->

<!-- ETAPA_08_1_INICIO -->
## Etapa 08.1 - Correcao final do AdminController

Data: 2026-07-06T21:08:22

Adicionado RETURNING id no insert de empresas.
Substituido uso de insertId por retorno de rows.
Removido LIMIT de UPDATE de senha.
Executado node --check no AdminController.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_08_1_FIM -->

<!-- ETAPA_09_INICIO -->
## Etapa 09 - Validacao funcional controlada

Data: 2026-07-06T21:11:11

Executado node --check nos principais arquivos JS.
Verificado Docker Compose e servico de banco.
Executadas consultas somente leitura em tabelas essenciais.
Validadas colunas usadas pelas queries corrigidas.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_09_FIM -->

<!-- ETAPA_09_1_INICIO -->
## Etapa 09.1 - Migration de schema funcional

Data: 2026-07-06T21:13:14

Criada migration idempotente para coluna ordem em setores.
Criada migration idempotente para tabela horarios_atendimento.
Criado indice para horarios_atendimento por empresa e dia da semana.
Gerados backup, manifestos e relatorios da etapa.
Nenhuma alteracao foi aplicada ao banco.
<!-- ETAPA_09_1_FIM -->

<!-- ETAPA_09_2_INICIO -->
## Etapa 09.2 - Execucao de migration funcional

Data: 2026-07-06T21:15:43

Executada migration para complementar schema funcional.
Adicionada coluna ordem em setores quando ausente.
Criada tabela horarios_atendimento quando ausente.
Criado indice de horarios por empresa e dia.
Repetida validacao somente leitura apos execucao.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_09_2_FIM -->

<!-- ETAPA_10_HOTFIX_INICIO -->
## Hotfix Etapa 10 - Correcao de script

Data: 2026-07-06T21:19:12

Corrigido SyntaxError no script etapa_10_testes_funcionais_escrita_postgres.py.
Validada sintaxe do script com py_compile.
Criado backup do script antes da alteracao.
<!-- ETAPA_10_HOTFIX_FIM -->

<!-- ETAPA_10_INICIO -->
## Etapa 10 - Testes funcionais de escrita

Data: 2026-07-06T21:21:55

Executados testes de criacao de empresa, usuario, setor e horario.
Executado teste de upsert de contato com ON CONFLICT.
Executado teste de insercao de mensagem.
Executado rollback e validacao de limpeza dos dados de teste.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_10_FIM -->

<!-- ETAPA_10_1_INICIO -->
## Etapa 10.1 - Correcao de sequences

Data: 2026-07-06T21:21:38

Auditadas sequences de empresas, usuarios_painel, contatos, mensagens, setores e horarios_atendimento.
Corrigidas sequences desalinhadas usando setval quando necessario.
Revalidadas sequences apos correcao.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_10_1_FIM -->
