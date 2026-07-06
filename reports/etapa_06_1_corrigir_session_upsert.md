# Etapa 06.1 - Corrigir upsert restante do SessionManager

Data: 2026-07-06T20:19:13

## Resumo

- Backup criado em: backups/etapa_06_1_20260706_201913
- Manifesto antes: reports/etapa_06_1_manifesto_antes.json
- Manifesto depois: reports/etapa_06_1_manifesto_depois.json
- Arquivo alterado: True
- Ocorrencias proibidas restantes: 0

## Correcao aplicada

- Arquivo: src/managers/SessionManager.js
- Alterado: True
- Ocorrencias antes: {"ON DUPLICATE KEY": 1}
- Ocorrencias depois: {"ON DUPLICATE KEY": 0}
- Substituicoes:
  - ON DUPLICATE KEY UPDATE -> ON CONFLICT (empresa_id, telefone) DO UPDATE SET qtd=1
  - nome = VALUES(nome) -> nome = EXCLUDED.nome qtd=1

## Contexto depois

- linha 387: 
- linha 388: const sql = `
- linha 389: INSERT INTO contatos (empresa_id, telefone, nome, foto_perfil, status_atendimento, created_at, ultima_msg)
- linha 390: VALUES (?, ?, ?, ?, 'ABERTO', NOW(), NOW())
- linha 391: ON CONFLICT (empresa_id, telefone) DO UPDATE SET
- linha 392: nome = EXCLUDED.nome,
- linha 393: foto_perfil = IFNULL(VALUES(foto_perfil), foto_perfil),
- linha 394: ultima_msg = NOW()
- linha 395: `;

## Node check

- src/managers/SessionManager.js: ok=True

## Scan de padroes antigos

- Nenhum padrao antigo encontrado em controllers e src.

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 07: validar schema, constraints e migrations PostgreSQL, especialmente contatos por empresa e telefone.

