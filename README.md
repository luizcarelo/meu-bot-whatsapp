# 🚀 Meu Bot WhatsApp – SaaS CRM
Sistema de CRM multi-empresa com integração ao WhatsApp Web via Baileys, atendimento em tempo real (Socket.IO), painel administrativo, avaliações, mensagens rápidas, broadcast e integração opcional com IA (OpenAI).

![Node](https://img.shields.io/badge/node-%3E%3D20.0.0-green.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg) ![Status](https://img.shields.io/badge/status-ativo-blue.svg)

> Repositório: [https://github.com/luizcarelo/meu-bot-whatsapp.git](https://github.com/luizcarelo/meu-bot-whatsapp.git)  
> Autor: LC Soluções Digital · Site: [https://lcsolucoesdigital.com.br](https://lcsolucoesdigital.com.br) · Email: <comercial@lcsolucoesdigital.com.br>

---

## ✨ Recursos

### Core
- ✅ Multi-empresa (SaaS)
- ✅ WhatsApp Web (Baileys) – sem API oficial
- ✅ CRM de atendimento – filas, assumir, transferir e encerrar
- ✅ Mensagens Rápidas (atalhos)
- ✅ Broadcast (envio em massa)
- ✅ Sistema de Avaliação (NPS simplificado)
- ✅ Uploads de mídia (imagem, áudio, vídeo, docs)

### Automação & IA
- ✅ Mensagem de ausência fora do horário
- ✅ Menu interativo (botões/lista) (opcional)
- ✅ Chatbot com OpenAI (configurável por empresa)

### Painéis
- ✅ Super Admin – gestão de clientes
- ✅ Admin da Empresa – configurações, equipe e setores
- ✅ Dashboard do Cliente – métricas de uso

---

## 🔧 Requisitos
- Node.js ≥ 20.0.0
- PostgreSQL 15 ou superior (ou PostgreSQL 15 ou superior)
- NPM ≥ 9

> Servidor recomendado: 2 vCPU · 4GB RAM · 20GB SSD · internet estável.

---

## 📦 Instalação

```bash
# 1) Clone o repositório
git clone https://github.com/luizcarelo/meu-bot-whatsapp.git
cd meu-bot-whatsapp

# 2) Instale dependências
npm install

# 3) Configure o ambiente
cp .env.example .env   # se existir; caso contrário, crie o .env manualmente

# 4) Configure/prepare o banco de dados
npm run setup          # cria/atualiza estrutura de tabelas

# 5) Execute
npm run dev            # desenvolvimento
npm start              # produção
```

---

## ⚙️ Configuração

Crie um arquivo `.env` com as variáveis essenciais:

```env
# Banco
DB_HOST=seu-host
DB_USER=seu-usuario
DB_PASS=altere_aqui
DB_NAME=seu-banco

# Servidor
PORT=4000
NODE_ENV=production

# Super Admin (senha mestra)
SUPER_ADMIN_PASS=altere_aqui

# SMTP (recuperação de senha)
SMTP_HOST=smtp.seuprovedor.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=nao-responda@seu-dominio.com
SMTP_PASS=altere_aqui
```

> Importante: nunca faça commit do `.env`. Utilize variáveis de ambiente no provedor de hospedagem.

---

## 🗂 Estrutura do Projeto

```
meu-bot-whatsapp/
├── config/               # Conexao PostgreSQL
├── controllers/          # Lógica de negócio (Auth, Admin, CRM, WhatsApp)
├── routes/               # Rotas API e views
├── src/
│   ├── managers/         # SessionManager (Baileys), OpenAIManager
│   └── middleware/       # Auth e helpers
├── views/                # EJS templates (login, CRM, admin, super-admin)
├── public/               # Assets estáticos e uploads
├── script/               # Scripts (setup/reset/backup)
├── .env                  # Configurações (não versionar)
├── package.json
└── server.js             # Entrada principal
```

---

## 🔌 API (exemplos)

### Autenticação
```http
POST /api/auth/login
Body: { "email": "usuario@dominio.com", "senha": "senha123" }
```

### Enviar texto
```http
POST /api/crm/enviar
Headers: { "x-empresa-id": 1, "x-user-id": 1 }
Body: { "telefone": "5511999999999@s.whatsapp.net", "texto": "Olá!" }
```

### Enviar mídia
```http
POST /api/crm/enviar-midia
Content-Type: multipart/form-data (file)
Headers: { "x-empresa-id": 1, "x-user-id": 1 }
Body: { "telefone": "5511999999999@s.whatsapp.net", "caption": "Veja" }
```

> A documentação completa pode ser expandida com Swagger ou Postman.

---

## 🛡️ Segurança (boas práticas)
- Use HTTPS em produção e habilite `helmet`:
```bash
npm i helmet
```
```js
const helmet = require('helmet');
app.use(helmet({ crossOriginResourcePolicy: { policy: 'cross-origin' } }));
```
- Configure CORS apenas para seus domínios.
- Rotacione senhas do PostgreSQL/SMTP/SUPER_ADMIN_PASS regularmente.
- Evite picos de envio (use rate limiting e intervalos aleatórios).

---

## 🧪 Qualidade & Operação
- Logs estruturados com Pino
- Jobs de manutenção: inatividade/avaliação, lembretes (tarefas)
- Monitoramento: Prometheus/Grafana (opcional)
- CI/CD: GitHub Actions (opcional)

---

## 🤝 Contribuição

1. Faça um fork do repositório.  
2. Crie uma branch: `git checkout -b feature/minha-feature`.  
3. Commit: `git commit -m "feat: descrição da mudança"`.  
4. Push: `git push origin feature/minha-feature`.  
5. Abra um Pull Request.

> Padrão de commits sugerido: Conventional Commits.

---

## 📄 Licença

Este projeto está sob a licença MIT. Sinta-se livre para usar, modificar e distribuir.

---

## 👨‍💻 Contato

- Autor: LC Soluções Digital
- Site: [https://lcsolucoesdigital.com.br](https://lcsolucoesdigital.com.br)
- Email: <comercial@lcsolucoesdigital.com.br>

> Última atualização: 2025-12-14
