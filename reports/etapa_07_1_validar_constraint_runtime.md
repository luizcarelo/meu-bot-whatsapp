# Etapa 07.1 - Validar constraint runtime PostgreSQL

Data: 2026-07-06T20:26:42

## Resumo

- Backup criado em: backups/etapa_07_1_20260706_202642
- Manifesto antes: reports/etapa_07_1_manifesto_antes.json
- Manifesto depois: reports/etapa_07_1_manifesto_depois.json
- Probe executado OK: False
- Conectado ao banco: False
- Host usado: None

## Resultado runtime

- Checks nao executados ou sem retorno.

## Hosts tentados

- host=db conectado=False codigo=EAI_AGAIN erro=getaddrinfo EAI_AGAIN db
- host=127.0.0.1 conectado=False codigo=ECONNREFUSED erro=connect ECONNREFUSED 127.0.0.1:5432
- host=localhost conectado=False codigo=ECONNREFUSED erro=connect ECONNREFUSED 127.0.0.1:5432

## Indices unicos encontrados

- Nenhum indice unico retornado.

## Constraints encontradas

- Nenhuma constraint retornada.

## Duplicidades

- Nenhuma duplicidade retornada.

## Observacoes

- Nenhuma senha foi impressa pelo script.
- Nenhuma alteracao foi aplicada ao banco.
- Nenhuma migration foi executada.

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 08: revisar queries de media severidade, especialmente agregacoes e retorno de inserts.

