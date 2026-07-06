#!/bin/bash
# ==============================================================================
# Script de Configuração Segura do Nginx (Reverse Proxy)
# Objetivo: Direcionar bot.lhsolucao.com.br para o Docker na porta 50010
# ==============================================================================

# Garante que o script pare se houver algum erro grave
set -e

echo "🚀 Iniciando configuração segura do Nginx para bot.lhsolucao.com.br..."

# Verifica se o usuário tem privilégios de root (sudo)
if [ "$EUID" -ne 0 ]; then
  echo "❌ Por favor, execute este script usando sudo."
  exit 1
fi

# Instala a ferramenta 'tree' caso não exista no servidor (para visualização)
if ! command -v tree &> /dev/null; then
    echo "📦 Instalando o pacote 'tree' para visualização de diretórios..."
    apt-get update -yqq && apt-get install tree -yqq
fi

DOMAIN="bot.lhsolucao.com.br"
PORT="50010"
NGINX_AVAILABLE="/etc/nginx/sites-available/$DOMAIN"
NGINX_ENABLED="/etc/nginx/sites-enabled/$DOMAIN"

echo "📝 Criando arquivo de bloco de servidor (Server Block) isolado usando 'cat'..."

# O comando 'cat << EOF' cria o arquivo sem precisar abrir um editor de texto
cat << EOF > $NGINX_AVAILABLE
server {
    listen 80;
    server_name $DOMAIN;

    # Configuração de limite de upload (50MB igual ao do seu server.js)
    client_max_body_size 50M;

    location / {
        # Direciona o tráfego para o seu contêiner Docker
        proxy_pass http://127.0.0.1:$PORT;
        
        # Configurações Essenciais para o Socket.IO (WhatsApp em tempo real) funcionar no Nginx
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Repassa as informações reais do visitante para o Node.js
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

echo "🔗 Criando o link simbólico para ativar o site..."
# Remove o link antigo se existir, para evitar erros
rm -f $NGINX_ENABLED
# Cria o link conectando o sites-available ao sites-enabled
ln -s $NGINX_AVAILABLE $NGINX_ENABLED

echo "🌳 Estrutura atual dos seus sites ativados no Nginx:"
# O comando tree vai mostrar visualmente que não apagamos os outros sites
tree /etc/nginx/sites-enabled/

echo "🔍 Testando a sintaxe geral do Nginx para garantir que nada foi quebrado..."
if nginx -t; then
    echo "✅ Teste do Nginx aprovado! Nenhuma outra configuração foi afetada."
    
    echo "🔄 Reiniciando o Nginx para aplicar as mudanças..."
    systemctl reload nginx
    echo "🎉 Sucesso! O Nginx agora está direcionando $DOMAIN para a porta $PORT."
else
    echo "❌ Ops! O Nginx detectou um erro de sintaxe. Desfazendo a ativação por segurança..."
    rm -f $NGINX_ENABLED
    systemctl reload nginx
    echo "♻️ Sistema revertido para o estado anterior. Seus outros sites continuam seguros."
    exit 1
fi