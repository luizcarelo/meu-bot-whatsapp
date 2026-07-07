# Etapa 09.1 - Corrigir schema funcional PostgreSQL

Data: 2026-07-06T21:13:14

## Resumo

- Backup criado em: backups/etapa_09_1_20260706_211313
- Manifesto antes: reports/etapa_09_1_manifesto_antes.json
- Manifesto depois: reports/etapa_09_1_manifesto_depois.json
- Runtime validado: True
- setores existe: True
- setores.ordem existe: False
- horarios_atendimento existe: False
- Migration criada: True
- Arquivo migration: database/migrations/20260706_schema_funcional_setores_horarios.sql
- Validacao migration OK: True

## Migration preparada

- Arquivo: database/migrations/20260706_schema_funcional_setores_horarios.sql
- Criada nesta etapa: True
- Existia antes: False
- SHA256: 3f4ab9aad97307e9ec05c30c77df0ec2c5504858d24b5c1cce9e32fa5d0d8e0e

## Validacao da migration

- OK: True
- Erros: nenhum

## Conteudo da migration

Arquivo gerado em: database/migrations/20260706_schema_funcional_setores_horarios.sql

```sql
-- Etapa 09.1 - Schema funcional PostgreSQL
-- Objetivo: complementar schema usado pelas telas e rotas de atendimento
-- Revisar em ambiente controlado antes de executar em producao

BEGIN;

ALTER TABLE setores
ADD COLUMN IF NOT EXISTS ordem INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS horarios_atendimento (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    dia_semana INTEGER NOT NULL,
    horario_abertura TIME,
    horario_fechamento TIME,
    inicio_almoco TIME,
    fim_almoco TIME,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_horarios_atendimento_empresa_dia
ON horarios_atendimento (empresa_id, dia_semana);

COMMIT;
```

## Observacoes

- Nenhuma alteracao foi aplicada ao banco.
- Nenhuma migration foi executada automaticamente.
- A execucao deve ser feita somente apos revisao.

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 9.2: executar a migration em ambiente controlado e repetir a validacao somente leitura.

