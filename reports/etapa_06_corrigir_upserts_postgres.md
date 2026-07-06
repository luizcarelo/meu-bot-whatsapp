# Etapa 06 - Corrigir upserts PostgreSQL

Data: 2026-07-06T20:17:02

## Resumo

- Backup criado em: backups/etapa_06_20260706_201702
- Manifesto antes: reports/etapa_06_manifesto_antes.json
- Manifesto depois: reports/etapa_06_manifesto_depois.json
- Ocorrencias proibidas restantes: 1

## Correcoes aplicadas

- controllers/WhatsAppController.js: alterado=True
  - ocorrencias antes: {"INSERT IGNORE": 2}
  - ocorrencias depois: {"INSERT IGNORE": 0}
  - substituicao: Upsert simplificado via INSERT IGNORE
  - substituicao: INSERT IGNORE INTO contatos (empresa_id, telefone, nome) VALUES (?, ?, ?)
- src/managers/SessionManager.js: alterado=False
  - ocorrencias antes: {"ON DUPLICATE KEY": 1}
  - ocorrencias depois: {"ON DUPLICATE KEY": 1}

## Node check

- controllers/WhatsAppController.js: ok=True
- src/managers/SessionManager.js: ok=True

## Scan de padroes antigos

- src/managers/SessionManager.js:391 termo=ON DUPLICATE KEY trecho=ON DUPLICATE KEY UPDATE

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 07: validar schema, constraints e migrations PostgreSQL, especialmente contatos(empresa_id, telefone).

