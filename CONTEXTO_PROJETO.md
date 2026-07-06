# CONTEXTO_PROJETO

<!-- ETAPA_02_INICIO -->
## Etapa 02 - Saneamento seguro

Data: 2026-07-06T11:01:56

Foi executada uma etapa de saneamento seguro antes de alteracoes funcionais.
A etapa criou backup, manifestos, .env.example seguro e relatorios em reports/.
O arquivo .env real foi preservado localmente e nao foi removido automaticamente.
A etapa nao alterou regras de negocio, banco, Docker, controllers ou dependencias.
<!-- ETAPA_02_FIM -->





<!-- ETAPA_04_INICIO -->
## Etapa 04 - Limpeza PostgreSQL

Data: 2026-07-06T20:09:04

Os scripts auxiliares de exportacao e backup foram convertidos para PostgreSQL usando pg.
O package.json foi validado quanto ao uso de pg.
Foi executada validacao de sintaxe com node --check quando Node estava disponivel.
Rastros filtrados restantes: 15.
<!-- ETAPA_04_FIM -->

<!-- ETAPA_04_1_INICIO -->
## Etapa 04.1 - Historico tecnico limpo

Data: 2026-07-06T20:11:45

Foram removidos rastros textuais antigos sobre banco anterior nos documentos de controle.
A decisao consolidada do projeto e PostgreSQL como banco oficial.
A etapa preservou os documentos de governanca e registrou a revisao de decisao.
Rastros restantes nos documentos de controle: 0.
<!-- ETAPA_04_1_FIM -->

<!-- ETAPA_05_INICIO -->
## Etapa 05 - Auditoria backend PostgreSQL

Data: 2026-07-06T20:13:42

Foi executada auditoria estatica do backend com foco em PostgreSQL.
Foram analisados setup_db.js, src/config/db.js, controllers, routes e src.
Queries mapeadas: 133.
Achados de alta severidade: 3.
Achados de media severidade: 102.
Achados de baixa severidade: 20.
Nenhuma correcao de query foi aplicada nesta etapa.
<!-- ETAPA_05_FIM -->

<!-- ETAPA_06_INICIO -->
## Etapa 06 - Upserts PostgreSQL

Data: 2026-07-06T20:17:02

Foram corrigidos os upserts de alta severidade para sintaxe PostgreSQL.
controllers/WhatsAppController.js foi ajustado para usar ON CONFLICT DO NOTHING.
src/managers/SessionManager.js foi ajustado para usar ON CONFLICT DO UPDATE.
Ocorrencias proibidas restantes em controllers e src: 1.
Falhas em node --check nos alvos alterados: 0.
A constraint unica de contatos por empresa e telefone deve ser validada em etapa de schema.
<!-- ETAPA_06_FIM -->

<!-- ETAPA_06_1_INICIO -->
## Etapa 06.1 - Upsert restante corrigido

Data: 2026-07-06T20:19:13

Foi corrigido o upsert restante em src/managers/SessionManager.js.
A query passou a usar sintaxe PostgreSQL com conflito por empresa_id e telefone.
Padroes antigos restantes em controllers e src: 0.
Node check do arquivo alterado OK: True.
A validacao de constraint unica continua planejada para a etapa de schema.
<!-- ETAPA_06_1_FIM -->

<!-- ETAPA_06_2_INICIO -->
## Etapa 06.2 - Funcao legada removida do upsert

Data: 2026-07-06T20:21:11

Foi corrigida a expressao de foto de perfil no upsert de contatos.
O codigo agora usa funcao compativel com PostgreSQL e referencia EXCLUDED.
Padroes antigos restantes em controllers e src: 0.
Node check do arquivo alterado OK: True.
A validacao de constraint unica continua planejada para etapa de schema.
<!-- ETAPA_06_2_FIM -->

<!-- ETAPA_07_INICIO -->
## Etapa 07 - Schema PostgreSQL validado

Data: 2026-07-06T20:23:50

Foi executada auditoria local de schema e migrations PostgreSQL.
Arquivos de schema encontrados: 11.
Tabela contatos encontrada em arquivos locais: True.
Indice ou constraint unica por empresa e telefone encontrada: True.
Migration criada: False.
Arquivo de migration: None.
A migration nao foi executada automaticamente.
<!-- ETAPA_07_FIM -->

<!-- ETAPA_07_1_INICIO -->
## Etapa 07.1 - Constraint runtime validada

Data: 2026-07-06T20:26:42

Foi executada validacao runtime no PostgreSQL usando configuracao local.
Conexao realizada: False.
Indice ou constraint unica por empresa e telefone no banco real: False.
Grupos duplicados encontrados: nao_validado.
Banco pronto para ON CONFLICT por empresa e telefone: False.
Nenhuma alteracao foi aplicada ao banco.
<!-- ETAPA_07_1_FIM -->

<!-- ETAPA_07_2_INICIO -->
## Etapa 07.2 - PostgreSQL Docker runtime validado

Data: 2026-07-06T20:29:56

Foi executada validacao runtime do PostgreSQL via Docker Compose.
Docker disponivel: True.
Indice ou constraint unica por empresa e telefone no banco: True.
Grupos duplicados encontrados: 0.
Banco pronto para ON CONFLICT por empresa e telefone: True.
Nenhuma alteracao foi aplicada ao banco.
<!-- ETAPA_07_2_FIM -->
