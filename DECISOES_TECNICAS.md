# DECISOES_TECNICAS

<!-- ETAPA_02_INICIO -->
## Etapa 02 - Decisoes tecnicas

Data: 2026-07-06T11:01:56

Decidido nao apagar o .env automaticamente para evitar indisponibilidade do ambiente.
Decidido criar .env.example como referencia segura para configuracao.
Decidido tratar Docker, banco, controllers e dependencias em etapas separadas.
Decidido manter manifestos com hash para auditoria antes e depois das alteracoes.
<!-- ETAPA_02_FIM -->

<!-- ETAPA_03_INICIO -->
## Etapa 03 - Decisoes tecnicas

Data: 2026-07-06T11:10:03

Decidido alinhar Docker ao MySQL porque o ambiente do projeto usa variaveis DB_HOST, DB_USER, DB_PASS e DB_NAME.
Decidido nao alterar config/db.js nesta etapa para reduzir risco.
Decidido preservar Redis e apenas padronizar fallback de senha.
Decidido manter Docker e validacao de sintaxe JavaScript em etapas separadas.
<!-- ETAPA_03_FIM -->

<!-- ETAPA_03_1_INICIO -->
## Etapa 03.1 - Decisoes tecnicas

Data: 2026-07-06T20:02:04

Decidido padronizar PostgreSQL como banco oficial do projeto.
Decidido nao alterar o .env real automaticamente para evitar perda de credenciais locais.
Decidido manter a correcao de codigo e queries para a Etapa 04.
Decidido preservar Redis e apenas alinhar sua referencia no .env.example.
Decidido remover o atributo version do docker-compose.yml para evitar aviso do Docker Compose atual.
<!-- ETAPA_03_1_FIM -->
