# 🚀 SaaS WhatsApp CRM

Sistema completo de CRM multi-empresa com integração WhatsApp via Baileys, chatbot com IA, gestão de atendimento e muito mais.

![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)
![Node](https://img.shields.io/badge/node-%3E%3D20.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📋 Índice

- [Características](#-características)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Configuração](#️-configuração)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [API](#-api)
- [Segurança](#-segurança)
- [Deploy](#-deploy)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)

## ✨ Características

### Core
- ✅ **Multi-empresa (SaaS)** - Sistema preparado para múltiplos clientes
- ✅ **WhatsApp Web via Baileys** - Conexão direta sem API oficial
- ✅ **Sistema de Filas** - Gestão inteligente de atendimentos
- ✅ **Transferência de Atendimento** - Entre setores e usuários
- ✅ **Chatbot com IA** - Integração com OpenAI GPT
- ✅ **Mensagens Rápidas** - Atalhos para respostas comuns
- ✅ **Broadcast** - Envio em massa para todos os contatos
- ✅ **Sistema de Avaliação** - Feedback dos clientes

### Gestão
- ✅ **Painel Super Admin** - Gestão de todas as empresas
- ✅ **Painel Administrativo** - Configurações por empresa
- ✅ **Gestão de Equipe** - Controle de usuários e permissões
- ✅ **Relatórios** - Estatísticas e métricas de atendimento
- ✅ **Agenda Global** - Lista de todos os contatos

### Automação
- ✅ **Horário de Atendimento** - Mensagem automática fora do horário
- ✅ **Menu Interativo** - Botões nativos do WhatsApp
- ✅ **Setores Personalizados** - Com cores e mensagens próprias
- ✅ **Detecção de Inatividade** - Encerramento automático
- ✅ **Reconexão Automática** - Sessões restauradas ao reiniciar

### Interface
- ✅ **Design Moderno** - Interface limpa e intuitiva
- ✅ **Modo Escuro** - Proteção para os olhos
- ✅ **Responsivo** - Funciona em desktop e mobile
- ✅ **Tempo Real** - Socket.IO para atualizações instantâneas

## 🔧 Requisitos

### Software
- Node.js >= 20.0.0
- MySQL >= 5.7 ou MariaDB >= 10.3
- NPM >= 9.0.0

### Servidor Recomendado
- RAM: Mínimo 2GB (Recomendado 4GB)
- CPU: 2 cores
- Armazenamento: 20GB
- Conexão estável com internet

## 📦 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/saas-whatsapp-crm.git
cd saas-whatsapp-crm
```

### 2. Instale as dependências
```bash
npm install
```

### 3. Configure o ambiente
```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:
```env
DB_HOST=mysql.lcsolucoesdigital.com.br
DB_USER=lcsolucoes_add2
DB_PASS=Whatsapp2025
DB_NAME=lcsolucoesdigi
PORT=4000
SUPER_ADMIN_PASS=Mudar123
```

### 4. Configure o banco de dados
```bash
npm run setup
```

### 5. Inicie o servidor
```bash
# Desenvolvimento
npm run dev

# Produção
npm start
```

O sistema estará disponível em: `http://localhost:4000`

## ⚙️ Configuração

### Banco de Dados

O script `setup_db.js` cria automaticamente todas as tabelas necessárias:

- `empresas` - Dados das empresas clientes
- `usuarios_painel` - Usuários do sistema
- `contatos` - Contatos do WhatsApp
- `mensagens` - Histórico de mensagens
- `setores` - Departamentos de atendimento
- `avaliacoes` - Feedback dos clientes
- `mensagens_rapidas` - Atalhos de mensagem
- `usuarios_setores` - Relação usuário-setor

### Email (SMTP)

Para recuperação de senha, configure:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASS=sua-senha-app
```

### OpenAI (Opcional)

Para usar o chatbot com IA:

1. Obtenha sua API Key em: https://platform.openai.com/api-keys
2. Configure no painel admin de cada empresa
3. Personalize o prompt do sistema

## 🎯 Uso

### Primeiro Acesso

1. **Super Admin**
   - URL: `/super-admin`
   - Email: `admin@saas.com`
   - Senha: `123456`

2. **Criar Empresa**
   - Acesse o super admin
   - Clique em "Novo Cliente"
   - Preencha os dados
   - Use a senha mestra configurada no `.env`

3. **Login Cliente**
   - URL: `/login`
   - Informe: Nome da Empresa, Email e Senha

### Conectar WhatsApp

1. Acesse `/admin/painel`
2. Aba "Conexão"
3. Clique em "CONECTAR"
4. Escaneie o QR Code com o WhatsApp

### Configurar Atendimento

1. **Setores**: Aba "Fluxo" - Crie departamentos
2. **Equipe**: Aba "Equipe" - Adicione atendentes
3. **Mensagens**: Aba "Msgs Rápidas" - Crie atalhos
4. **Horários**: Aba "Automação & IA" - Defina horários

### Atender Clientes

1. Acesse `/crm`
2. Mensagens chegam na aba "Fila"
3. Clique em "ASSUMIR" para atender
4. Use as ferramentas:
   - Enviar texto, imagem, áudio, vídeo
   - Mensagens rápidas
   - Transferir atendimento
   - Encerrar conversa

## 📁 Estrutura do Projeto

```
saas-whatsapp-crm/
├── config/
│   └── db.js                 # Conexão MySQL
├── controllers/
│   ├── AdminController.js    # Super Admin
│   ├── AuthController.js     # Autenticação
│   ├── CrmController.js      # CRM Principal
│   └── WhatsAppController.js # WhatsApp
├── routes/
│   ├── api.js               # Rotas API
│   └── index.js             # Rotas Views
├── src/
│   ├── managers/
│   │   ├── OpenAIManager.js  # Integração OpenAI
│   │   └── SessionManager.js # Gestão WhatsApp
│   └── middleware/
│       └── auth.js          # Autenticação
├── views/
│   ├── admin-panel.ejs      # Painel Admin
│   ├── crm.ejs              # Interface CRM
│   ├── login.ejs            # Login
│   └── super-admin.ejs      # Super Admin
├── public/
│   └── uploads/             # Arquivos enviados
├── auth_sessions/           # Sessões WhatsApp (auto-criado)
├── .env                     # Configurações
├── package.json
└── server.js                # Entrada principal
```

## 🔌 API

### Autenticação

```javascript
POST /api/auth/login
Body: {
  nomeEmpresa: "Minha Empresa",
  email: "usuario@email.com",
  senha: "senha123"
}
```

### Enviar Mensagem

```javascript
POST /api/crm/enviar
Headers: {
  x-empresa-id: 1,
  x-user-id: 1
}
Body: {
  telefone: "5511999999999@s.whatsapp.net",
  texto: "Olá!"
}
```

### Listar Contatos

```javascript
GET /api/crm/contatos?status=meus
Headers: {
  x-empresa-id: 1,
  x-user-id: 1
}
```

[Documentação completa da API em breve]

## 🔒 Segurança

### Implementado
- ✅ Senhas criptografadas (bcrypt)
- ✅ Prepared statements (SQL Injection)
- ✅ Validação de inputs
- ✅ Sanitização de arquivos
- ✅ Verificação de empresa ativa
- ✅ Timeout em conexões
- ✅ CORS configurado

### Recomendações
- Use HTTPS em produção
- Mantenha dependências atualizadas
- Configure firewall adequadamente
- Faça backups regulares
- Monitore logs de acesso
- Use senhas fortes

## 🚀 Deploy

### Opção 1: VPS (Ubuntu)

```bash
# 1. Instale Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 2. Instale MySQL
sudo apt install mysql-server

# 3. Clone e configure o projeto
git clone seu-repo
cd saas-whatsapp-crm
npm install
nano .env

# 4. Use PM2 para manter rodando
npm install -g pm2
pm2 start server.js --name saas-crm
pm2 save
pm2 startup
```

### Opção 2: Docker

```dockerfile
# Dockerfile (criar na raiz)
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE 4000
CMD ["npm", "start"]
```

```bash
docker build -t saas-crm .
docker run -d -p 4000:4000 --env-file .env saas-crm
```

### Opção 3: Heroku, Railway, Render

Configure as variáveis de ambiente no painel e faça deploy via Git.

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📝 Changelog

### v4.0.0 (2024-11)
- ✨ Código completamente revisado e comentado
- ✨ Melhorias de segurança
- ✨ Otimização de performance
- ✨ Documentação completa
- 🐛 Correção de bugs menores

### v3.7.0 (2024-10)
- ✨ Chatbot com OpenAI
- ✨ Menu interativo nativo
- ✨ Sistema de inatividade
- ✨ Broadcast de mensagens

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👨‍💻 Autor

**LC Soluções Digital**

- Website: [lcsolucoesdigital.com.br](https://lcsolucoesdigital.com.br)
- Email: contato@lcsolucoesdigital.com.br

## 🙏 Agradecimentos

- [@WhiskeySockets/Baileys](https://github.com/WhiskeySockets/Baileys) - Biblioteca WhatsApp
- OpenAI - API de IA
- Comunidade Node.js

---

⭐ Se este projeto foi útil para você, considere dar uma estrela!

📫 Dúvidas? Abra uma [issue](https://github.com/seu-usuario/saas-whatsapp-crm/issues)