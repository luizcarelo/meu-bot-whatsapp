# Etapa 06.2 - Corrigir funcao legada no upsert PostgreSQL

Data: 2026-07-06T20:21:11

## Resumo

- Backup criado em: backups/etapa_06_2_20260706_202111
- Manifesto antes: reports/etapa_06_2_manifesto_antes.json
- Manifesto depois: reports/etapa_06_2_manifesto_depois.json
- Arquivo alterado: True
- Ocorrencias proibidas restantes: 0

## Correcao aplicada

- Arquivo: src/managers/SessionManager.js
- Alterado: True
- Ocorrencias antes: {"IFNULL": 1, "VALUES(foto_perfil)": 1}
- Ocorrencias depois: {"IFNULL": 0, "VALUES(foto_perfil)": 0}
- Substituicoes:
  - foto_perfil = IFNULL(VALUES(foto_perfil), foto_perfil), -> foto_perfil = COALESCE(EXCLUDED.foto_perfil, contatos.foto_perfil), qtd=1

## Contexto depois

- linha 389: INSERT INTO contatos (empresa_id, telefone, nome, foto_perfil, status_atendimento, created_at, ultima_msg)
- linha 390: VALUES (?, ?, ?, ?, 'ABERTO', NOW(), NOW())
- linha 391: ON CONFLICT (empresa_id, telefone) DO UPDATE SET
- linha 392: nome = EXCLUDED.nome,
- linha 393: foto_perfil = COALESCE(EXCLUDED.foto_perfil, contatos.foto_perfil),
- linha 394: ultima_msg = NOW()
- linha 395: `;
- linha 396: await this.db.execute(sql, [empresaId, remoteJid, pushName, fotoPerfil]);
- linha 397: }

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

