# Etapa 16 - Auditar frontend e preparar melhorias

Data: 2026-07-06T22:36:17

## Resumo

- Backup documental criado em: backups/etapa_16_20260706_223616
- Manifesto antes: reports/etapa_16_manifesto_antes.json
- Manifesto depois: reports/etapa_16_manifesto_depois.json
- Arquivos analisados: 12
- Referencias totais: 32
- Referencias externas: 24
- Referencias locais: 8
- Assets locais referenciados: 7
- Assets locais ausentes: 7
- Arquivos com Tailwind CDN: 2
- Arquivos com FontAwesome CDN: 5
- Arquivos com Alpine CDN: 2
- Arquivos com scripts inline: 5
- Arquivos com estilos inline: 5

## Arquivos analisados

- package.json
- postcss.config.js
- public/uploads/empresa_2/css/style.css
- routes/api.js
- routes/index.js
- server.js
- tailwind.config.js
- views/admin-panel.ejs
- views/crm.ejs
- views/dashboard.ejs
- views/login.ejs
- views/super-admin.ejs

## Dependencias externas unicas

- tipo=externo referencia=https://github.com/luizcarelo/meu-bot-whatsapp.git
- tipo=externo referencia=https://github.com/luizcarelo/meu-bot-whatsapp/issues
- tipo=externo referencia=https://github.com/luizcarelo/meu-bot-whatsapp#readme
- tipo=externo referencia=http://127.0.0.1:50010
- tipo=externo referencia=http://localhost:50010
- tipo=cdnjs_cdn referencia=https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js
- tipo=cdnjs_cdn referencia=https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css
- tipo=externo referencia=https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap
- tipo=imagem_externa referencia=https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png
- tipo=externo referencia=https://www.google.com/maps/search/?api=1&query=${loc.lat},${loc.lng}
- tipo=externo referencia=https://ui-avatars.com/api/?name=${c.nome||
- tipo=tailwind_cdn referencia=https://cdn.tailwindcss.com
- tipo=jsdelivr_cdn referencia=https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js
- tipo=externo referencia=https://ui-avatars.com/api/?name=<%= user.nome %>&background=random
- tipo=externo referencia=https://ui-avatars.com/api/?name=
- tipo=externo referencia=https://ui-avatars.com/api/?name=${chat.nome}`
- tipo=externo referencia=https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap

## Externos por tipo

- cdnjs_cdn: 6
- externo: 12
- imagem_externa: 2
- jsdelivr_cdn: 2
- tailwind_cdn: 2

## Assets locais ausentes

- arquivo=views/admin-panel.ejs referencia=/css/style.css
- arquivo=views/admin-panel.ejs referencia=/socket.io/socket.io.js
- arquivo=views/crm.ejs referencia=/css/style.css
- arquivo=views/crm.ejs referencia=/socket.io/socket.io.js
- arquivo=views/crm.ejs referencia=/admin/painel
- arquivo=views/dashboard.ejs referencia=/socket.io/socket.io.js
- arquivo=views/super-admin.ejs referencia=/css/style.css

## Arquivos com CDN

### Tailwind
- views/dashboard.ejs
- views/login.ejs

### FontAwesome
- views/admin-panel.ejs
- views/crm.ejs
- views/dashboard.ejs
- views/login.ejs
- views/super-admin.ejs

### Alpine
- views/dashboard.ejs
- views/login.ejs

## Arquivos com scripts inline

- views/admin-panel.ejs
- views/crm.ejs
- views/dashboard.ejs
- views/login.ejs
- views/super-admin.ejs

## Arquivos com estilos inline

- views/admin-panel.ejs
- views/crm.ejs
- views/dashboard.ejs
- views/login.ejs
- views/super-admin.ejs

## Recomendacoes

- prioridade=alta tema=Dependencias externas acao=Planejar internalizacao gradual dos assets externos criticos.
- prioridade=alta tema=Tailwind CDN acao=Planejar build local do Tailwind com cuidado para preservar layout atual.
- prioridade=media tema=Icones externos acao=Substituir FontAwesome CDN por pacote local ou SVGs internos.
- prioridade=media tema=Alpine externo acao=Servir Alpine localmente por public/vendor ou pacote instalado.
- prioridade=alta tema=Assets locais ausentes acao=Corrigir referencias locais ausentes antes de aplicar melhoria visual.
- prioridade=media tema=CSS inline acao=Extrair estilos repetidos para public/css em etapa futura.
- prioridade=media tema=Scripts inline acao=Mapear scripts inline antes de aplicar CSP forte.
- prioridade=alta tema=Primeira melhoria visual acao=Aplicar melhoria controlada na tela de login antes de mexer no dashboard.

## Observacoes

- Nenhuma tela foi alterada nesta etapa.
- Nenhuma regra de negocio foi alterada.
- Nenhum banco foi alterado.
- Nenhum container foi reiniciado.
- Esta etapa prepara melhorias visuais controladas.

## Documentacao atualizada

- CONTEXTO_PROJETO.md
- CHANGELOG.md
- DECISOES_TECNICAS.md
- PENDENCIAS.md

## Proxima etapa recomendada

- Etapa 17: aplicar melhoria visual controlada na tela de login, com backup, validacao e rollback.

