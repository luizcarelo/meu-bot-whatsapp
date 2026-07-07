# Etapa 08 - Corrigir queries de media severidade PostgreSQL

Data: 2026-07-06T20:32:39

## Resumo

- Backup criado em: backups/etapa_08_20260706_203239
- Manifesto antes: reports/etapa_08_manifesto_antes.json
- Manifesto depois: reports/etapa_08_manifesto_depois.json
- Padroes antes: 10
- Padroes depois: 4

## Correcoes aplicadas

- controllers/AdminController.js: alterado=True
  - ocorrencias antes: {"GROUP_CONCAT": 0, "JSON_ARRAYAGG": 0, "JSON_OBJECT": 0, "insertId": 1, "LIMIT 1": 2}
  - ocorrencias depois: {"GROUP_CONCAT": 0, "JSON_ARRAYAGG": 0, "JSON_OBJECT": 0, "insertId": 1, "LIMIT 1": 1}
  - substituicao qtd=1: UPDATE usuarios_painel SET email = ? WHERE empresa_id = ? AND is_admin = 1 LIMIT 1 -> UPDATE usuarios_painel SET email = ? WHERE empresa_id = ? AND is_admin = 1
- controllers/CrmController.js: alterado=True
  - ocorrencias antes: {"GROUP_CONCAT": 2, "JSON_ARRAYAGG": 1, "JSON_OBJECT": 1, "insertId": 1, "LIMIT 1": 2}
  - ocorrencias depois: {"GROUP_CONCAT": 0, "JSON_ARRAYAGG": 0, "JSON_OBJECT": 0, "insertId": 0, "LIMIT 1": 2}
  - substituicao qtd=1: SELECT JSON_ARRAYAGG(JSON_OBJECT('id', e.id, 'nome', e.nome, 'cor', e.cor)) -> SELECT json_agg(json_build_object('id', e.id, 'nome', e.nome, 'cor', e.cor))
  - substituicao qtd=1: (SELECT GROUP_CONCAT(s.nome SEPARATOR ', ') -> (SELECT STRING_AGG(s.nome, ', ' ORDER BY s.nome)
  - substituicao qtd=1: (SELECT GROUP_CONCAT(s.id SEPARATOR ',') -> (SELECT STRING_AGG(s.id::text, ',' ORDER BY s.id)
  - substituicao qtd=1: 'INSERT INTO usuarios_painel (empresa_id, nome, email, senha, is_admin, telefone, cargo, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)' -> 'INSERT INTO usuarios_painel (empresa_id, nome, email, senha, is_admin, telefone, cargo, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id'
  - substituicao qtd=1: resUser.insertId -> resUser.rows[0].id

## Node check

- controllers/AdminController.js: ok=True
- controllers/CrmController.js: ok=True

## Padroes restantes

- controllers/AdminController.js:146 termo=insertId trecho=const empId = resEmp.insertId;
- controllers/AdminController.js:239 termo=LIMIT 1 trecho=`UPDATE usuarios_painel SET senha = ? WHERE empresa_id = ? AND is_admin = 1 LIMIT 1`,
- controllers/CrmController.js:125 termo=LIMIT 1 trecho=(SELECT conteudo FROM mensagens m WHERE m.remote_jid = c.telefone AND m.empresa_id = c.empresa_id ORDER BY id DESC LIMIT 1) as ultima_msg,
- controllers/CrmController.js:126 termo=LIMIT 1 trecho=(SELECT data_hora FROM mensagens m WHERE m.remote_jid = c.telefone AND m.empresa_id = c.empresa_id ORDER BY id DESC LIMIT 1) as ordenacao,

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 09: executar testes funcionais controlados nas rotas/telas afetadas e revisar booleanos numericos.

