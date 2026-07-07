# Decisao de Arquitetura Nova

Data: 2026-07-07T01:29:02

## Decisao aprovada

Fica aprovada a migracao progressiva do sistema para uma arquitetura mais robusta, com separacao clara entre backend modular e frontend modular.

## Stack aprovada para o novo frontend

- React.
- TypeScript.
- Vite.
- Material UI.
- React Router.
- Cliente HTTP padronizado.
- Tema claro e escuro.
- Layout responsivo.

## Diretriz aprovada para o backend

O backend devera evoluir para uma arquitetura modular por dominio.

Estrutura alvo por modulo:

```text
nome.routes.js
nome.controller.js
nome.service.js
nome.repository.js
nome.validators.js
nome.types.js
```

## Legado operacional

As telas atuais em EJS passam a ser consideradas legado operacional.

Isso significa:

- O legado pode continuar funcionando durante a migracao.
- O legado nao deve receber novas funcionalidades complexas de interface.
- Correcoes criticas no legado ainda podem ser feitas se forem necessarias para manter o sistema acessivel.
- Novas telas e fluxos complexos deverao ser criados no frontend React.
- O legado so sera removido quando houver substituto validado.

## Motivos da decisao

A decisao foi tomada porque o frontend atual acumulou HTML, CSS e JavaScript acoplados, causando conflitos visuais, problemas de responsividade e dificuldade de manutencao.

O objetivo e reduzir remendos no EJS e construir uma base previsivel para evoluir atendimento, CRM, WhatsApp, automacoes e administracao SaaS.

## Regras de seguranca da migracao

- Nao apagar arquivos legados sem substituto validado.
- Nao alterar banco nesta fase.
- Nao alterar Docker nesta fase.
- Nao criar frontend React nesta fase.
- Nao alterar rotas funcionais nesta fase.
- Cada nova fase deve criar backup.
- Cada nova fase deve gerar manifesto.
- Cada nova fase deve gerar relatorio.
- Cada nova fase deve atualizar documentacao obrigatoria.

## Fronteiras da Etapa 26

Esta etapa registra a decisao arquitetural, o mapa do legado, a arquitetura alvo, os contratos iniciais e o plano de migracao.

Esta etapa nao implementa backend modular.

Esta etapa nao cria o frontend React.

Esta etapa nao altera o funcionamento atual do sistema.
