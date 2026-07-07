# Etapa 10.1 - Corrigir sequences PostgreSQL

Data: 2026-07-06T21:21:38

## Resumo

- Backup documental criado em: backups/etapa_10_1_20260706_212129
- Backup logico criado: True
- Arquivo backup logico: backups/etapa_10_1_20260706_212129/pg_dump_pre_etapa_10_1_20260706_212129.dump
- Manifesto antes: reports/etapa_10_1_manifesto_antes.json
- Manifesto depois: reports/etapa_10_1_manifesto_depois.json
- Sequences desalinhadas antes: 0
- Correcao necessaria: False
- Correcao executada: False
- Sequences desalinhadas depois: 0

## Auditoria antes

- empresas: existe=True, sequence=public.empresas_id_seq, max_id=2, last_value=3, proximo=4, desalinhada=False
- usuarios_painel: existe=True, sequence=public.usuarios_painel_id_seq, max_id=1, last_value=1, proximo=2, desalinhada=False
- contatos: existe=True, sequence=public.contatos_id_seq, max_id=0, last_value=1, proximo=1, desalinhada=False
- mensagens: existe=True, sequence=public.mensagens_id_seq, max_id=0, last_value=1, proximo=1, desalinhada=False
- setores: existe=True, sequence=public.setores_id_seq, max_id=0, last_value=1, proximo=1, desalinhada=False
- horarios_atendimento: existe=True, sequence=public.horarios_atendimento_id_seq, max_id=0, last_value=1, proximo=1, desalinhada=False

## Correcao

- Necessaria: False
- Executada: False
- Tabelas planejadas: 
- SQL SHA256: 0b2fc718a04857d53f7390d69ade7766282038e2459e14f223a8517902e6953f
- Execucao OK: True
- stdout:
  - Nenhuma sequence desalinhada encontrada.

## Auditoria depois

- empresas: existe=True, sequence=public.empresas_id_seq, max_id=2, last_value=3, proximo=4, desalinhada=False
- usuarios_painel: existe=True, sequence=public.usuarios_painel_id_seq, max_id=1, last_value=1, proximo=2, desalinhada=False
- contatos: existe=True, sequence=public.contatos_id_seq, max_id=0, last_value=1, proximo=1, desalinhada=False
- mensagens: existe=True, sequence=public.mensagens_id_seq, max_id=0, last_value=1, proximo=1, desalinhada=False
- setores: existe=True, sequence=public.setores_id_seq, max_id=0, last_value=1, proximo=1, desalinhada=False
- horarios_atendimento: existe=True, sequence=public.horarios_atendimento_id_seq, max_id=0, last_value=1, proximo=1, desalinhada=False

## Backup logico

- OK: True
- Arquivo: backups/etapa_10_1_20260706_212129/pg_dump_pre_etapa_10_1_20260706_212129.dump
- SHA256: 4b1908bfdff5b5a1597a84ea7a5f73ff623c2ebf377432c0d2f82c5f23949d75
- Tamanho bytes: 18912

## Observacoes

- Nenhuma senha foi impressa pelo script.
- Nenhum dado de teste foi inserido nesta etapa.
- A alteracao executada foi limitada a ajuste de sequences.

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Reexecutar a Etapa 10 de testes funcionais com escrita controlada.

