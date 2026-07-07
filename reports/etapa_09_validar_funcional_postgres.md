# Etapa 09 - Validacao funcional controlada PostgreSQL

Data: 2026-07-06T21:11:11

## Resumo

- Backup criado em: backups/etapa_09_20260706_211107
- Manifesto antes: reports/etapa_09_manifesto_antes.json
- Manifesto depois: reports/etapa_09_manifesto_depois.json
- Node check falhas: 0
- Node check ausentes: 0
- Docker OK: True
- Docker Compose OK: True
- Servico db parece rodando: True
- Banco somente leitura OK: False
- Tabelas essenciais OK: False
- Colunas essenciais OK: False

## Node check

- Arquivos verificados: 16
- OK: 16
- Falhas: 0
- Ausentes: 0

## Docker

- docker --version ok: True
  - Docker version 29.6.1, build 8900f1d
- docker compose version ok: True
  - Docker Compose version v5.3.0
- servico db mencionado: True
- servico db healthy: True

## Banco - tabelas essenciais

- empresas: existe=True, count_ok=True, total_registros=2
- usuarios_painel: existe=True, count_ok=True, total_registros=1
- contatos: existe=True, count_ok=True, total_registros=0
- mensagens: existe=True, count_ok=True, total_registros=0
- setores: existe=True, count_ok=True, total_registros=0
- horarios_atendimento: existe=False, count_ok=False, total_registros=None

## Banco - colunas essenciais

- empresas: ok=True, faltantes=
- usuarios_painel: ok=True, faltantes=
- contatos: ok=True, faltantes=
- mensagens: ok=True, faltantes=
- setores: ok=False, faltantes=ordem
- horarios_atendimento: ok=False, faltantes=id, empresa_id, dia_semana, ativo

## Observacoes

- Nenhuma senha foi impressa pelo script.
- Nenhuma alteracao foi aplicada ao banco.
- Nenhuma migration foi executada.
- Consultas executadas foram somente leitura.

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 10: executar testes funcionais com escrita em ambiente controlado.

