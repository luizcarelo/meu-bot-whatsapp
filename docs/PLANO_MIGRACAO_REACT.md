# Plano de Migracao Progressiva para React

Data: 2026-07-07T01:29:02

## Objetivo

Migrar o sistema para frontend React e backend modular sem interromper o funcionamento atual.

## Principios

- Migracao progressiva.
- Sem big bang.
- Sem quebrar operacao atual.
- Rotas antigas continuam ativas ate substituicao validada.
- APIs passam a ter contratos padronizados.
- Frontend novo consome apenas APIs JSON.
- Backend passa a ser modularizado por dominio.

## Fases futuras

### Etapa 27

Criar base do frontend React com TypeScript, Vite e Material UI.

### Etapa 28

Criar estrutura base de backend modular em paralelo.

### Etapa 29

Padronizar respostas de API.

### Etapa 30

Migrar login e sessao para consumo do frontend React.

### Etapa 31

Migrar dashboard para React e Material UI.

### Etapa 32

Criar gestao WhatsApp web.

### Etapa 33

Migrar CRM atendimento.

### Etapa 34

Criar automacoes de atendimento.

### Etapa 35

Isolar Baileys em modulo dedicado.

### Etapa 36

Revisar Docker, build e producao.

## Riscos

- Divergencia entre sessao do EJS e sessao consumida pelo React.
- Endpoints atuais retornando formatos inconsistentes.
- Logica de WhatsApp acoplada em controllers antigos.
- Dependencia de variaveis globais no frontend legado.
- Rotas antigas com comportamento misto HTML e JSON.

## Mitigacoes

- Criar contratos antes de migrar telas.
- Criar cliente HTTP padronizado no frontend.
- Criar middleware de erro padronizado no backend.
- Criar resposta padrao em todos endpoints novos.
- Migrar por rota e por feature.
- Manter backup e manifesto por etapa.
