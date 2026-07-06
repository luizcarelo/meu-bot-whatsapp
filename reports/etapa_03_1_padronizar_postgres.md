# Etapa 03.1 - Padronizar PostgreSQL

Data: 2026-07-06T20:02:04

## Resumo

- Backup criado em: backups/etapa_03_1_20260706_200204
- Manifesto antes: reports/etapa_03_1_manifesto_antes.json
- Manifesto depois: reports/etapa_03_1_manifesto_depois.json
- Docker alterado: False
- .env.example alterado: False

## Validacao do docker-compose.yml

- Validacao OK: True
- Erros: nenhum
- Avisos: nenhum

## Validacao do .env.example

- Validacao OK: True
- Erros: nenhum
- Avisos: nenhum

## Rastros MySQL encontrados

- Total: 498
- README.md:36 termos=mysql, mariadb trecho=- [asterisco][asterisco]MySQL ≥ 5.7[asterisco][asterisco] (ou MariaDB ≥ 10.3)
- README.md:100 termos=mysql trecho=├── config/               # Conexão MySQL
- README.md:153 termos=mysql trecho=- Rotacione senhas do [asterisco][asterisco]MySQL/SMTP/SUPER_ADMIN_PASS[asterisco][asterisco] regularmente.
- CHANGELOG.md:16 termos=mysql trecho=## Etapa 03 - Correcao do Docker para MySQL
- CHANGELOG.md:20 termos=mysql trecho=Substituido servico db baseado em PostgreSQL por MySQL 8.
- CHANGELOG.md:21 termos=mysql, mysqldata trecho=Substituido volume pgdata por mysqldata.
- CHANGELOG.md:22 termos=mysql, mysqladmin trecho=Ajustado healthcheck do banco para mysqladmin ping.
- CHANGELOG.md:24 termos=mysql, MYSQL_ trecho=Atualizado .env.example com MYSQL_ROOT_PASSWORD quando necessario.
- CHANGELOG.md:34 termos=mysql trecho=Removidas configuracoes MySQL do docker-compose.yml.
- CHANGELOG.md:35 termos=mysql, mysqldata trecho=Substituido volume mysqldata por pgdata.
- CHANGELOG.md:38 termos=mysql trecho=Gerado relatorio de rastros MySQL ainda presentes no projeto.
- etapa_03_1_padronizar_postgres.py:12 termos=mysql, MYSQL_ trecho=- Remover MYSQL_ROOT_PASSWORD do .env.example.
- etapa_03_1_padronizar_postgres.py:13 termos=mysql trecho=- Gerar relatorio de rastros MySQL ainda presentes no projeto.
- etapa_03_1_padronizar_postgres.py:69 termos=mysql trecho=TERMOS_MYSQL = [
- etapa_03_1_padronizar_postgres.py:70 termos=mysql trecho="mysql",
- etapa_03_1_padronizar_postgres.py:71 termos=mysql, mysql2 trecho="mysql2",
- etapa_03_1_padronizar_postgres.py:72 termos=mariadb trecho="mariadb",
- etapa_03_1_padronizar_postgres.py:73 termos=mysql, MYSQL_ trecho="MYSQL_",
- etapa_03_1_padronizar_postgres.py:74 termos=mysql, mysqldata trecho="mysqldata",
- etapa_03_1_padronizar_postgres.py:75 termos=mysql, mysqladmin trecho="mysqladmin",
- etapa_03_1_padronizar_postgres.py:76 termos=DB_PORT=3306, 3306 trecho="DB_PORT=3306",
- etapa_03_1_padronizar_postgres.py:77 termos=3306 trecho="3306"
- etapa_03_1_padronizar_postgres.py:81 termos=mysql trecho="mysql:8.0",
- etapa_03_1_padronizar_postgres.py:82 termos=mysql, MYSQL_ trecho="mysql_native_password",
- etapa_03_1_padronizar_postgres.py:83 termos=mysql, MYSQL_ trecho="MYSQL_DATABASE",
- etapa_03_1_padronizar_postgres.py:84 termos=mysql, MYSQL_ trecho="MYSQL_USER",
- etapa_03_1_padronizar_postgres.py:85 termos=mysql, MYSQL_ trecho="MYSQL_PASSWORD",
- etapa_03_1_padronizar_postgres.py:86 termos=mysql, MYSQL_ trecho="MYSQL_ROOT_PASSWORD",
- etapa_03_1_padronizar_postgres.py:87 termos=mysql, mysqldata trecho="mysqldata",
- etapa_03_1_padronizar_postgres.py:88 termos=mysql, mysqladmin trecho="mysqladmin"
- etapa_03_1_padronizar_postgres.py:356 termos=mysql trecho=erros.append("Termo MySQL ainda presente no Docker: " + termo)
- etapa_03_1_padronizar_postgres.py:462 termos=mysql, MYSQL_ trecho="MYSQL_ROOT_PASSWORD",
- etapa_03_1_padronizar_postgres.py:463 termos=mysql, MYSQL_ trecho="MYSQL_DATABASE",
- etapa_03_1_padronizar_postgres.py:464 termos=mysql, MYSQL_ trecho="MYSQL_USER",
- etapa_03_1_padronizar_postgres.py:465 termos=mysql, MYSQL_ trecho="MYSQL_PASSWORD",
- etapa_03_1_padronizar_postgres.py:466 termos=DB_PORT=3306, 3306 trecho="DB_PORT=3306"
- etapa_03_1_padronizar_postgres.py:477 termos=mysql trecho=erros.append("Linha MySQL proibida em .env.example: " + termo)
- etapa_03_1_padronizar_postgres.py:528 termos=mysql trecho=def escanear_rastros_mysql():
- etapa_03_1_padronizar_postgres.py:561 termos=mysql trecho=for termo in TERMOS_MYSQL:
- etapa_03_1_padronizar_postgres.py:617 termos=mysql trecho=total_rastros = str(len(relatorio["rastros_mysql"]))
- etapa_03_1_padronizar_postgres.py:629 termos=mysql trecho="Foram encontrados " + total_rastros + " rastros de MySQL para analise na proxima etapa."
- etapa_03_1_padronizar_postgres.py:640 termos=mysql trecho="Removidas configuracoes MySQL do docker-compose.yml.",
- etapa_03_1_padronizar_postgres.py:641 termos=mysql, mysqldata trecho="Substituido volume mysqldata por pgdata.",
- etapa_03_1_padronizar_postgres.py:644 termos=mysql trecho="Gerado relatorio de rastros MySQL ainda presentes no projeto."
- etapa_03_1_padronizar_postgres.py:668 termos=mysql trecho="Revisar rastros MySQL listados no relatorio da Etapa 03.1.",
- etapa_03_1_padronizar_postgres.py:734 termos=mysql trecho=linhas.append("## Rastros MySQL encontrados")
- etapa_03_1_padronizar_postgres.py:736 termos=mysql trecho=linhas.append("- Total: " + str(len(relatorio["rastros_mysql"])))
- etapa_03_1_padronizar_postgres.py:738 termos=mysql trecho=if relatorio["rastros_mysql"]:
- etapa_03_1_padronizar_postgres.py:740 termos=mysql trecho=for item in relatorio["rastros_mysql"][:limite]:
- etapa_03_1_padronizar_postgres.py:751 termos=mysql trecho=if len(relatorio["rastros_mysql"]) > limite:
- etapa_03_1_padronizar_postgres.py:754 termos=mysql trecho=linhas.append("- Nenhum rastro MySQL encontrado.")
- etapa_03_1_padronizar_postgres.py:791 termos=mysql trecho=rastros_mysql = escanear_rastros_mysql()
- etapa_03_1_padronizar_postgres.py:802 termos=mysql trecho="rastros_mysql": rastros_mysql
- etapa_03_1_padronizar_postgres.py:828 termos=mysql trecho=print("Rastros MySQL encontrados: " + str(len(rastros_mysql)))
- etapa_01_auditoria_estatica.py:48 termos=mysql trecho=("Possivel URI com credencial", r"(?i)(mysql|postgres|mongodb|redis):\/\/[^ \n]+"),
- etapa_01_auditoria_estatica.py:241 termos=mysql trecho=sinais_mysql = []
- etapa_01_auditoria_estatica.py:245 termos=mysql trecho=if "DB_HOST" in env_texto or "mysql" in env_texto.lower():
- etapa_01_auditoria_estatica.py:246 termos=mysql trecho=sinais_mysql.append(".env indica configuracao compativel com MySQL")
- etapa_01_auditoria_estatica.py:251 termos=mysql trecho=if "mysql" in compose_texto.lower():
- etapa_01_auditoria_estatica.py:252 termos=mysql trecho=sinais_mysql.append("docker-compose.yml menciona MySQL")
- etapa_01_auditoria_estatica.py:254 termos=mysql trecho=inconsistente = bool(sinais_mysql and sinais_postgres)
- etapa_01_auditoria_estatica.py:259 termos=mysql trecho="sinais_mysql": sinais_mysql,
- etapa_01_auditoria_estatica.py:416 termos=mysql trecho=for item in bd["sinais_mysql"]:
- PENDENCIAS.md:9 termos=mysql trecho=Corrigir inconsistencia entre MySQL no ambiente e PostgreSQL no docker-compose.yml.
- PENDENCIAS.md:23 termos=3306 trecho=Confirmar se a porta 3306 deve ficar exposta publicamente ou apenas internamente.
- PENDENCIAS.md:34 termos=mysql trecho=Revisar rastros MySQL listados no relatorio da Etapa 03.1.
- MELHORIAS.md:178 termos=mysql trecho=DB_HOST=mysql.lcsolucoesdigital.com.br
- MELHORIAS.md:214 termos=mysql trecho=- ✅ Conexão MySQL
- DECISOES_TECNICAS.md:19 termos=mysql trecho=Decidido alinhar Docker ao MySQL porque o ambiente do projeto usa variaveis DB_HOST, DB_USER, DB_PASS e DB_NAME.
- CONTEXTO_PROJETO.md:15 termos=mysql trecho=## Etapa 03 - Docker alinhado ao MySQL
- CONTEXTO_PROJETO.md:19 termos=mysql trecho=Foi corrigida a configuracao do docker-compose.yml para usar MySQL 8.
- CONTEXTO_PROJETO.md:34 termos=mysql trecho=Foram encontrados 133 rastros de MySQL para analise na proxima etapa.
- etapa_02_saneamento_seguro.py:463 termos=mysql trecho="Corrigir inconsistencia entre MySQL no ambiente e PostgreSQL no docker-compose.yml.",
- etapa_03_corrigir_docker_mysql.py:5 termos=mysql trecho=Etapa 03 - Corrigir Docker para MySQL
- etapa_03_corrigir_docker_mysql.py:10 termos=mysql trecho=- Substituir docker-compose.yml com configuracao MySQL coerente com .env.
- etapa_03_corrigir_docker_mysql.py:12 termos=mysql, MYSQL_ trecho=- Atualizar .env.example com MYSQL_ROOT_PASSWORD se necessario.
- etapa_03_corrigir_docker_mysql.py:215 termos=mysql trecho=def conteudo_docker_compose_mysql():
- etapa_03_corrigir_docker_mysql.py:238 termos=mysql trecho=image: mysql:8.0
- etapa_03_corrigir_docker_mysql.py:241 termos=mysql, MYSQL_ trecho=command: --default-authentication-plugin=mysql_native_password
- etapa_03_corrigir_docker_mysql.py:243 termos=mysql, MYSQL_ trecho=MYSQL_DATABASE: ${DB_NAME}
- Lista truncada no Markdown. Consulte o JSON completo.

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 04: validar e corrigir config/db.js, setup_db.js, controllers, rotas, imports e queries para PostgreSQL.

