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

<!-- ETAPA_03_INICIO -->
## Etapa 03 - Correcao do Docker para MySQL

Data: 2026-07-06T11:10:03

Substituido servico db baseado em PostgreSQL por MySQL 8.
Substituido volume pgdata por mysqldata.
Ajustado healthcheck do banco para mysqladmin ping.
Preservado servico Redis.
Atualizado .env.example com MYSQL_ROOT_PASSWORD quando necessario.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_03_FIM -->

<!-- ETAPA_03_1_INICIO -->
## Etapa 03.1 - Padronizacao PostgreSQL

Data: 2026-07-06T20:02:04

Corrigido docker-compose.yml para usar postgres:15-alpine.
Removidas configuracoes MySQL do docker-compose.yml.
Substituido volume mysqldata por pgdata.
Ajustado healthcheck do banco para pg_isready.
Atualizado .env.example para PostgreSQL.
Gerado relatorio de rastros MySQL ainda presentes no projeto.
<!-- ETAPA_03_1_FIM -->
