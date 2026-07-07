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

<!-- ETAPA_11_INICIO -->
## Etapa 11 - Validacao de endpoints e interface

Data: 2026-07-06T21:27:13

Verificados containers Docker Compose.
Coletados logs recentes do servico app.
Testados endpoints HTTP basicos em porta local.
Detectados status HTTP e padroes de erro comuns.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_11_FIM -->

<!-- ETAPA_12_INICIO -->
## Etapa 12 - Validacao de login e autenticacao

Data: 2026-07-06T21:44:35

Validado login real via endpoint de autenticacao.
Validadas paginas autenticadas com cookie mantido em memoria.
Validados endpoints somente leitura quando existentes.
Coletados logs recentes para detectar erros criticos.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_12_FIM -->

<!-- ETAPA_12_1_INICIO -->
## Etapa 12.1 - Diagnostico de autenticacao

Data: 2026-07-06T21:36:04

Verificado usuario admin no banco em modo somente leitura.
Inspecionados arquivos locais de autenticacao.
Testados payloads de login sem imprimir senha.
Coletados logs recentes para apoio ao diagnostico.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_12_1_FIM -->

<!-- ETAPA_12_2_INICIO -->
## Etapa 12.2 - Correcao do script de login

Data: 2026-07-06T21:44:23

Corrigido payload principal do script etapa_12_validar_login_endpoints_autenticados.py.
Campo principal alterado para senha.
Fallback com password mantido.
Validada sintaxe com py_compile.
Criado backup do script antes da alteracao.
<!-- ETAPA_12_2_FIM -->

<!-- ETAPA_13_INICIO -->
## Etapa 13 - Validacao de interface logada

Data: 2026-07-06T21:46:57

Realizado login com cookie em memoria.
Extraidos links e assets reais do HTML do dashboard.
Testados fluxos GET encontrados no dashboard.
Testados assets locais encontrados no dashboard.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_13_FIM -->

<!-- ETAPA_14_INICIO -->
## Etapa 14 - Hardening de seguranca operacional

Data: 2026-07-06T21:50:01

Removida impressao de Session ID e cookie em logs do middleware geral quando localizada.
Reduzido log de usuario autenticado para empresa_id sem email.
Adicionado app.disable para x-powered-by quando possivel.
Adicionados headers HTTP basicos quando possivel.
Executado node --check em server.js.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_14_FIM -->

<!-- ETAPA_14_1_INICIO -->
## Etapa 14.1 - Validacao runtime do hardening

Data: 2026-07-06T21:55:04

Comparado server.js local com server.js dentro do container app.
Executado rebuild do app somente quando solicitado por variavel de ambiente.
Validado login e dashboard apos disponibilidade do app.
Analisados logs novos para confirmar ausencia de Session ID e cookies.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_14_1_FIM -->

<!-- ETAPA_14_2_INICIO -->
## Etapa 14.2 - Sanitizacao de logs de usuario

Data: 2026-07-06T22:04:35

Sanitizados logs de AuthController, rotas e servidor.
Removida exposicao de email em logs de sucesso de login e dashboard.
Removida exposicao de senha temporaria em log de recuperacao.
Mantidos logs com usuario_id e empresa_id.
Executado node --check nos arquivos relevantes.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_14_2_FIM -->

<!-- ETAPA_15_INICIO -->
## Etapa 15 - Hardening de CORS e cookies

Data: 2026-07-06T22:11:48

Removida configuracao CORS permissiva quando localizada.
Adicionado middleware CORS controlado por CORS_ORIGINS ou APP_URL.
Ajustado cookie de sessao com httpOnly, sameSite e secure condicionado.
Validados headers HTTP basicos.
Executado node --check em server.js.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_15_FIM -->

<!-- ETAPA_15_1_INICIO -->
## Etapa 15.1 - Correcao emergencial de sintaxe

Data: 2026-07-06T22:17:23

Corrigidas virgulas ausentes no bloco cookie do server.js.
Executado node --check em server.js.
Reiniciado app somente apos validacao de sintaxe.
Validado app, login e dashboard apos restart.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_15_1_FIM -->

<!-- ETAPA_15_2_INICIO -->
## Etapa 15.2 - Auditoria de seguranca HTTP sem alteracao

Data: 2026-07-06T22:21:48

Auditados CORS, cookies e headers em runtime.
Executado node --check em server.js.
Validado login e dashboard.
Coletados logs novos para verificar sanitizacao.
Nenhum arquivo de codigo foi alterado pela auditoria.
<!-- ETAPA_15_2_FIM -->

<!-- ETAPA_16_INICIO -->
## Etapa 16 - Auditoria frontend

Data: 2026-07-06T22:36:17

Mapeados arquivos de frontend em views, public, routes e arquivos principais.
Identificadas dependencias externas e CDNs.
Identificados estilos e scripts inline.
Identificados assets locais referenciados.
Gerados relatorios JSON e Markdown da auditoria.
<!-- ETAPA_16_FIM -->

<!-- ETAPA_17_INICIO -->
## Etapa 17 - Login visual melhorado

Data: 2026-07-06T22:40:03

Melhorado layout da tela de login.
Mantido payload email e senha para /api/auth/login.
Adicionado estado visual de carregamento.
Adicionado botao para mostrar ou ocultar senha.
Validado login real e dashboard quando credenciais foram fornecidas.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_17_FIM -->

<!-- ETAPA_17_1_INICIO -->
## Etapa 17.1 - Validacao runtime do login visual

Data: 2026-07-06T22:46:40

Comparado views/login.ejs local com arquivo dentro do container app.
Restart executado somente quando solicitado por variavel de ambiente.
Validada tela /login com textos e classes da nova interface.
Validado login real e dashboard.
Gerados backup documental, manifestos e relatorios da etapa.
<!-- ETAPA_17_1_FIM -->

<!-- ETAPA_18_INICIO -->
## Etapa 18 - Dashboard visual melhorado

Data: 2026-07-06T22:51:14

Adicionada camada visual controlada ao dashboard.
Preservada estrutura existente da view.
Preservados Tailwind, FontAwesome, Alpine e Socket.IO.
Validado login real e dashboard.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_18_FIM -->

<!-- ETAPA_19_INICIO -->
## Etapa 19 - CSS compartilhado criado

Data: 2026-07-06T23:01:50

Criado arquivo public/css/style.css.
Adicionada base visual compartilhada para telas antigas.
Nenhuma view foi modificada.
Nenhum backend ou banco foi modificado.
<!-- ETAPA_19_FIM -->

<!-- ETAPA_20_INICIO -->
## Etapa 20 - Visual aplicado em views/crm.ejs

Data: 2026-07-06T23:13:14

Incluido link para /css/style.css em views/crm.ejs quando ausente.
Adicionada camada visual controlada com marcadores ETAPA20.
Preservados fetch, Socket.IO, endpoints e logica existente.
Validado login, dashboard e rota /crm.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_20_FIM -->

<!-- ETAPA_20_1_INICIO -->
## Etapa 20.1 - Registro da rota /crm

Data: 2026-07-06T23:19:41

Adicionada rota GET /crm protegida por isAuthenticated.
A rota renderiza views/crm.ejs com titulo, usuario, empresa, isMobile e socketUrl.
Executado node --check em routes/index.js.
Validado login, dashboard e CRM.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_20_1_FIM -->

<!-- ETAPA_20_2_INICIO -->
## Etapa 20.2 - Correcao da rota CRM

Data: 2026-07-06T23:30:31

Substituida consulta da rota /crm para SELECT  FROM empresas.
Removida dependencia das colunas logo, cor, plano e limite_usuarios na rota /crm.
Executado node --check em routes/index.js.
Validado login, dashboard e CRM.
Gerados backup, manifestos e relatorios da etapa.
<!-- ETAPA_20_2_FIM -->

<!-- ETAPA_21_INICIO -->
## Etapa 21 - Visual aplicado em admin-panel

Data: 2026-07-06T23:35:11

Incluido link para /css/style.css em views/admin-panel.ejs quando ausente.
Adicionada camada visual controlada com marcadores ETAPA21.
Preservados fetch, Socket.IO, Sortable, endpoints e logica existente.
Validado login, dashboard e painel administrativo.
<!-- ETAPA_21_FIM -->

<!-- ETAPA_21_1_INICIO -->
## Etapa 21.1 - Registro da rota admin panel

Data: 2026-07-06T23:45:03

Adicionada rota GET /admin/painel protegida por isAuthenticated.
A rota chama AdminPanelController.renderPanel.
Executado node --check em routes/index.js.
Validado login, dashboard e painel administrativo.
<!-- ETAPA_21_1_FIM -->

<!-- ETAPA_21_2_INICIO -->
## Etapa 21.2 - Correcao do admin panel

Data: 2026-07-06T23:50:22

Substituida consulta de empresa do AdminPanelController para SELECT id, nome FROM empresas.
Removida dependencia de colunas inexistentes como nome_sistema, logo_url e cor_primaria.
Executado node --check em controllers/AdminPanelController.js.
Validado login, dashboard e painel administrativo.
<!-- ETAPA_21_2_FIM -->

<!-- ETAPA_21_3_INICIO -->
## Etapa 21.3 - Correcao da consulta de equipe

Data: 2026-07-06T23:53:24

Removida coluna telefone da consulta de usuarios_painel no AdminPanelController.
Executado node --check em controllers/AdminPanelController.js.
Validado login, dashboard e painel administrativo.
<!-- ETAPA_21_3_FIM -->

<!-- ETAPA_22_INICIO -->
## Etapa 22 - Visual aplicado em Super Admin

Data: 2026-07-06T23:57:44

Incluido link para /css/style.css em views/super-admin.ejs quando ausente.
Adicionada camada visual controlada com marcadores ETAPA22.
Preservados fetch, formularios, botoes e logica existente.
Validado login, dashboard e rota /super-admin quando disponivel.
<!-- ETAPA_22_FIM -->

<!-- ETAPA_22_1_INICIO -->
## Etapa 22.1 - Registro da rota Super Admin

Data: 2026-07-07T00:03:38

Adicionada rota GET /super-admin protegida por isAuthenticated e isSuperAdmin.
A rota renderiza views/super-admin.ejs.
Executado node --check em routes/index.js.
Validado login, dashboard e Super Admin.
<!-- ETAPA_22_1_FIM -->

<!-- ETAPA_23_INICIO -->
## Etapa 23 - Auditoria final executada

Data: 2026-07-07T00:20:25

Executada auditoria final das telas login, dashboard, CRM, admin panel e super admin.
Validadas rotas principais e marcadores visuais.
Validados logs novos sem Session ID, cookie e email.
Gerados relatorios finais JSON e Markdown.
<!-- ETAPA_23_FIM -->

<!-- ETAPA_23_1_INICIO -->
## Etapa 23.1 - Super Admin sincronizado no runtime

Data: 2026-07-07T00:10:18

Comparado hash local e hash do container para views/super-admin.ejs.
Copiada a view para o container quando necessario.
Validado /super-admin com marcadores visuais da Etapa 22.
Gerados relatorios JSON e Markdown.
<!-- ETAPA_23_1_FIM -->

<!-- ETAPA_23_2_INICIO -->
## Etapa 23.2 - Super Admin via sendFile

Data: 2026-07-07T00:14:15

Alterada a rota /super-admin para usar res.type('html').sendFile.
Mantidas as protecoes isAuthenticated e isSuperAdmin.
Validado node --check, login, dashboard e Super Admin.
<!-- ETAPA_23_2_FIM -->

<!-- ETAPA_23_3_INICIO -->
## Etapa 23.3 - Correcao isSuperAdmin

Data: 2026-07-07T00:20:13

Ajustado middleware isSuperAdmin para aceitar is_admin igual a 1 ou true.
Adicionado suporte a role superadmin.
Mantida exigencia de empresa master igual a 1.
Validado node --check, login, dashboard e Super Admin.
<!-- ETAPA_23_3_FIM -->

<!-- ETAPA_24_INICIO -->
## Etapa 24 - Base de teste Super Admin e Tenant

Data: 2026-07-07T00:33:13

Criado ou atualizado Super Admin de teste.
Criado ou atualizado tenant Cliente Teste LTDA.
Criado ou atualizado Admin Cliente Teste.
Senhas gravadas com bcrypt pelo runtime Node.
Validados login e acesso esperado para ambos os usuarios.
<!-- ETAPA_24_FIM -->

<!-- ETAPA_25_INICIO -->
## Etapa 25 - Layout profissional aplicado

Data: 2026-07-07T00:46:46

Adicionado shell visual profissional nas telas principais.
Adicionado menu lateral comum.
Adicionado botao de tema claro/escuro com localStorage.
Padronizada estrutura visual via public/css/style.css.
Preservadas as funcoes existentes das telas.
<!-- ETAPA_25_FIM -->

<!-- ETAPA_25_1_INICIO -->
## Etapa 25.1 - Correcao do frontend

Data: 2026-07-07T00:52:30

Removido script antigo que reconstruia o body.
Adicionado shell seguro com menu lateral e tema claro/escuro.
Preservados scripts originais das paginas.
Validadas rotas principais em runtime.
<!-- ETAPA_25_1_FIM -->

<!-- ETAPA_25_2_INICIO -->
## Etapa 25.2 - Correcao Alpine no Dashboard

Data: 2026-07-07T00:57:10

Adicionado defer ao carregamento do Alpine no dashboard.
Garantida exposicao de appData em window para inicializacao do Alpine.
Mantido shell seguro da Etapa 25.1.
Validadas rotas principais em runtime.
<!-- ETAPA_25_2_FIM -->
