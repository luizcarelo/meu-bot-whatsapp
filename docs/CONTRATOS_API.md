# Contratos Iniciais de API

Data: 2026-07-07T01:29:02

## Objetivo

Definir o padrao inicial para as respostas JSON usadas pelo frontend React.

## Resposta de sucesso

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

## Resposta de erro

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "CODIGO_DO_ERRO",
    "message": "Mensagem amigavel em PT-BR"
  }
}
```

## Regras gerais

- Toda API nova deve responder JSON.
- Toda resposta nova deve conter success.
- Toda resposta nova deve conter data.
- Toda resposta nova deve conter error.
- Erros tecnicos nao devem expor stack trace para o frontend.
- Mensagens exibidas ao usuario devem estar em PT-BR.
- Codigo HTTP deve refletir o resultado operacional.
- APIs de status operacional podem retornar HTTP 200 com status interno de negocio.

## Contratos iniciais previstos

### POST /api/auth/login

Entrada:

```json
{
  "email": "usuario@exemplo.com",
  "senha": "senha"
}
```

Saida prevista:

```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "nome": "Nome",
      "email": "usuario@exemplo.com",
      "role": "admin"
    },
    "empresa": {
      "id": 5,
      "nome": "Cliente Teste LTDA"
    },
    "redirectUrl": "/dashboard"
  },
  "error": null
}
```

### GET /api/auth/me

Retorna usuario autenticado e empresa atual.

### POST /api/auth/logout

Encerra sessao atual.

### GET /api/dashboard/summary

Retorna resumo operacional do dashboard.

### GET /api/whatsapp/status/:empresaId

Retorna status operacional do WhatsApp.

Valores previstos:

```text
DESCONECTADO
AGUARDANDO_QR
CONECTANDO
CONECTADO
RECONECTANDO
ERRO
LOGOUT
```

### POST /api/whatsapp/connect

Inicia fluxo de conexao.

### POST /api/whatsapp/disconnect

Desconecta sessao.

### GET /api/crm/contatos

Lista contatos com filtros e paginacao.

### GET /api/crm/mensagens/:telefone

Lista mensagens de um contato.

### POST /api/crm/enviar

Envia mensagem para contato.

<!-- ETAPA_29_1_INICIO -->
## Etapa 29.1 - Catalogo de status e erros

Criado catalogo inicial para padronizacao de respostas reais de API.

### Arquivos criados

backend/src/shared/http/statusCodes.js
backend/src/shared/http/errorCodes.js
docs/PADRAO_RESPOSTAS_API.md

### Codigos de erro catalogados

AUTH_REQUIRED
AUTH_INVALID_CREDENTIALS
VALIDATION_ERROR
RESOURCE_NOT_FOUND
WHATSAPP_DISCONNECTED
WHATSAPP_STATUS_UNAVAILABLE
TENANT_NOT_FOUND
USER_NOT_FOUND
INTERNAL_ERROR
<!-- ETAPA_29_1_FIM -->
