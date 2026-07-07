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
