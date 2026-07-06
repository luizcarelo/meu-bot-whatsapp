# Usa o Node.js versão 20 (leve)
FROM node:20-alpine

# Define a pasta de trabalho dentro do contêiner
WORKDIR /usr/src/app

# Instala ferramentas do Linux que algumas bibliotecas do WhatsApp e QR Code precisam
RUN apk add --no-cache build-base cairo-dev pango-dev jpeg-dev giflib-dev tzdata

# Configura o fuso horário para o Brasil
ENV TZ=America/Sao_Paulo

# Copia os arquivos de dependências primeiro
COPY package*.json ./

# Instala os pacotes (ignorando conflitos antigos)
RUN npm install --legacy-peer-deps

# Copia o restante do código do projeto
COPY . .

# Expõe a porta do servidor
EXPOSE 50010

# Comando para iniciar
CMD ["npm", "start"]
