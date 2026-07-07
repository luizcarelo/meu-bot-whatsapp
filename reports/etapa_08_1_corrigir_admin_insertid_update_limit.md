# Etapa 08.1 - Corrigir AdminController insertId e UPDATE LIMIT

Data: 2026-07-06T21:08:22

## Resumo

- Backup criado em: backups/etapa_08_1_20260706_210822
- Manifesto antes: reports/etapa_08_1_manifesto_antes.json
- Manifesto depois: reports/etapa_08_1_manifesto_depois.json
- Padroes criticos antes: 2
- Padroes criticos depois: 0
- Node check OK: True

## Correcao aplicada

- Arquivo: controllers/AdminController.js
- Alterado: True
- Ocorrencias antes: {"insertId": 1, "UPDATE_LIMIT_1": 1}
- Ocorrencias depois: {"insertId": 0, "UPDATE_LIMIT_1": 0}
- Substituicoes:
  - qtd=1: NOW(), 'DESCONECTADO')` -> NOW(), 'DESCONECTADO') RETURNING id`
  - qtd=1: const empId = resEmp.insertId; -> const empId = resEmp.rows[0].id;
  - qtd=1: UPDATE usuarios_painel SET senha = ? WHERE empresa_id = ? AND is_admin = 1 LIMIT 1 -> UPDATE usuarios_painel SET senha = ? WHERE empresa_id = ? AND is_admin = 1

## Node check

- controllers/AdminController.js: ok=True

## Validacao final

- insertId restante: 0
- UPDATE com LIMIT 1 restante: 0
- SELECT com LIMIT 1 encontrado, valido em PostgreSQL: 0
- Nenhum padrao critico restante no AdminController.

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 09: executar testes funcionais controlados nas rotas e telas afetadas.

