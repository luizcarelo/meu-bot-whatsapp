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
