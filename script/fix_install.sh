#!/bin/bash

# Script de Correção de Dependências - Sistemas de Gestão
# Executar como root ou com sudo

echo ">>> Iniciando Protocolo de Correção de Ambiente..."

# 1. Navegar para o diretório
cd /root/app/meu-bot-whatsapp

# 2. Remover node_modules para garantir instalação limpa (evita conflitos de versão)
echo ">>> Removendo node_modules antigos e lockfiles..."
rm -rf node_modules
rm -f package-lock.json

# 3. Instalar dependências baseadas no novo package.json
# A flag --no-audit acelera o processo em produção
echo ">>> Instalando dependências (incluindo 'compression')..."
npm install --no-audit

# 4. Verificar se a instalação do 'compression' foi bem sucedida
if [ -d "./node_modules/compression" ]; then
    echo ">>> SUCESSO: Módulo 'compression' verificado."
else
    echo ">>> ERRO CRÍTICO: Falha ao instalar 'compression'. Tentando instalação manual..."
    npm install compression --save
fi

# 5. Reiniciar a aplicação
echo ">>> Reiniciando a aplicação..."
npm start