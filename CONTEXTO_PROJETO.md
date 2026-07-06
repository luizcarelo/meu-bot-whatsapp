# CONTEXTO_PROJETO

<!-- ETAPA_02_INICIO -->
## Etapa 02 - Saneamento seguro

Data: 2026-07-06T11:01:56

Foi executada uma etapa de saneamento seguro antes de alteracoes funcionais.
A etapa criou backup, manifestos, .env.example seguro e relatorios em reports/.
O arquivo .env real foi preservado localmente e nao foi removido automaticamente.
A etapa nao alterou regras de negocio, banco, Docker, controllers ou dependencias.
<!-- ETAPA_02_FIM -->

<!-- ETAPA_03_INICIO -->
## Etapa 03 - Docker alinhado ao MySQL

Data: 2026-07-06T11:10:03

Foi corrigida a configuracao do docker-compose.yml para usar MySQL 8.
A decisao foi manter o padrao de variaveis DB_HOST, DB_USER, DB_PASS e DB_NAME ja usado pelo projeto.
O Redis foi preservado no docker-compose.yml.
Esta etapa nao alterou controllers, rotas, banco em codigo, package.json ou regras de negocio.
<!-- ETAPA_03_FIM -->

<!-- ETAPA_03_1_INICIO -->
## Etapa 03.1 - Padronizacao PostgreSQL

Data: 2026-07-06T20:02:04

A decisao tecnica foi revisada: o banco oficial do projeto passa a ser PostgreSQL.
O docker-compose.yml foi padronizado para PostgreSQL 15 Alpine.
O .env.example foi padronizado para DB_PORT 5432 e variaveis DB compatveis com PostgreSQL.
Esta etapa nao alterou .env real, controllers, config/db.js, setup_db.js, package.json ou regras de negocio.
Foram encontrados 498 rastros de MySQL para analise na proxima etapa.
<!-- ETAPA_03_1_FIM -->
