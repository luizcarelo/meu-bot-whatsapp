# Padrao de Respostas de API

Data: 2026-07-08T20:15:43

## Objetivo

Definir o catalogo inicial de status HTTP e codigos de erro do backend modular.

Esta fase nao altera rotas, handlers, banco, Docker, frontend React ou backend legado.

## Formato de sucesso

JSON de sucesso:

{
  "success": true,
  "data": {},
  "error": null
}

## Formato de erro

JSON de erro:

{
  "success": false,
  "data": null,
  "error": {
    "code": "CODIGO_DO_ERRO",
    "message": "Mensagem amigavel em PT-BR"
  }
}

## Status HTTP catalogados

OK
CREATED
BAD_REQUEST
UNAUTHORIZED
FORBIDDEN
NOT_FOUND
CONFLICT
UNPROCESSABLE_ENTITY
INTERNAL_SERVER_ERROR

## Codigos de erro catalogados

AUTH_REQUIRED
AUTH_INVALID_CREDENTIALS
VALIDATION_ERROR
RESOURCE_NOT_FOUND
WHATSAPP_DISCONNECTED
WHATSAPP_STATUS_UNAVAILABLE
TENANT_NOT_FOUND
USER_NOT_FOUND
INTERNAL_ERROR

## Proximas fases

Etapa 29.2: reforcar apiResponse.js e errors.js.

Etapa 29.3: padronizar errorHandler e notFoundHandler.

Etapa 29.4: validar endpoints health com contrato padronizado.
