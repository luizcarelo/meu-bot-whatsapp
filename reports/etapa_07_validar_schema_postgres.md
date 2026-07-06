# Etapa 07 - Validar schema PostgreSQL

Data: 2026-07-06T20:23:50

## Resumo

- Backup criado em: backups/etapa_07_20260706_202350
- Manifesto antes: reports/etapa_07_manifesto_antes.json
- Manifesto depois: reports/etapa_07_manifesto_depois.json
- Arquivos de schema encontrados: 11
- Tabela contatos encontrada: True
- Unico empresa_id e telefone encontrado: True
- Migration necessaria: False
- Migration criada: False
- Arquivo migration: None

## Arquivos de schema encontrados

- script/apply_branding.js
- script/audit_sync.js
- script/backup_database.js
- script/check_auth.js
- script/export_full.js
- script/fix_access.js
- script/force_activate.js
- script/force_stop.js
- script/force_sync.js
- script/seed_data.js
- script/setup_reset.js

## Detalhes da auditoria

- script/apply_branding.js
  - tem_contatos: False
  - tem_unico_empresa_telefone: False
- script/audit_sync.js
  - tem_contatos: True
  - tem_unico_empresa_telefone: False
  - linha 33 termo=contatos trecho=// Ajuste 3: Garantir que contatos tem ultima_msg
  - linha 35 termo=contatos trecho=ALTER TABLE contatos
  - linha 38 termo=contatos trecho=console.log("✅ [Ajuste] Tabela 'contatos' sincronizada.");
- script/backup_database.js
  - tem_contatos: False
  - tem_unico_empresa_telefone: False
- script/check_auth.js
  - tem_contatos: False
  - tem_unico_empresa_telefone: False
  - linha 14 termo=empresa_id trecho=SELECT u.email, u.empresa_id, e.nome as empresa_nome, e.ativo
  - linha 16 termo=empresa_id trecho=JOIN empresas e ON u.empresa_id = e.id
- script/export_full.js
  - tem_contatos: False
  - tem_unico_empresa_telefone: False
- script/fix_access.js
  - tem_contatos: False
  - tem_unico_empresa_telefone: False
  - linha 19 termo=empresa_id trecho=const res = await client.query("UPDATE usuarios_painel SET ativo = true WHERE email = $1 RETURNING empresa_id", ['admin@saas.com']);
- script/force_activate.js
  - tem_contatos: False
  - tem_unico_empresa_telefone: False
  - linha 19 termo=empresa_id trecho=await client.query("UPDATE usuarios_painel SET empresa_id = 1 WHERE email = 'admin@saas.com'");
- script/force_stop.js
  - tem_contatos: False
  - tem_unico_empresa_telefone: False
- script/force_sync.js
  - tem_contatos: True
  - tem_unico_empresa_telefone: True
  - linha 34 termo=empresa_id trecho=empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
  - linha 36 termo=unique trecho=email VARCHAR(100) UNIQUE,
  - linha 45 termo=contatos trecho=CREATE TABLE IF NOT EXISTS contatos (
  - linha 47 termo=empresa_id trecho=empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
  - linha 48 termo=telefone trecho=telefone VARCHAR(100),
  - linha 53 termo=empresa_id trecho=UNIQUE (empresa_id, telefone)
  - linha 53 termo=telefone trecho=UNIQUE (empresa_id, telefone)
  - linha 53 termo=unique trecho=UNIQUE (empresa_id, telefone)
  - linha 58 termo=empresa_id trecho=empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
- script/seed_data.js
  - tem_contatos: False
  - tem_unico_empresa_telefone: False
  - linha 28 termo=empresa_id trecho=INSERT INTO usuarios_painel (empresa_id, nome, email, senha, is_super_admin, is_admin, cargo, ativo)
- script/setup_reset.js
  - tem_contatos: True
  - tem_unico_empresa_telefone: True
  - linha 90 termo=empresa_id trecho=empresa_id INT,
  - linha 95 termo=empresa_id trecho=FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
  - linha 100 termo=empresa_id trecho=empresa_id INT,
  - linha 102 termo=unique trecho=email VARCHAR(100) UNIQUE,
  - linha 111 termo=empresa_id trecho=FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
  - linha 114 termo=contatos trecho=CREATE TABLE contatos (
  - linha 116 termo=empresa_id trecho=empresa_id INT,
  - linha 117 termo=telefone trecho=telefone VARCHAR(100),
  - linha 127 termo=empresa_id trecho=UNIQUE (empresa_id, telefone),
  - linha 127 termo=telefone trecho=UNIQUE (empresa_id, telefone),

## Migration

- Necessaria: False
- Criada: False
- Arquivo: None
- Motivo: Indice ou constraint unica ja encontrada em arquivos locais

## Validacao da migration

- OK: False

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 08: revisar queries de media severidade, especialmente agregacoes e retorno de inserts.

