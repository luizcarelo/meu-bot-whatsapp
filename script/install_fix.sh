#!/bin/bash

echo "========================================="
echo "  CORREÇÃO DE DEPENDÊNCIAS - SISTEMAS DE GESTÃO"
echo "========================================="

# 1. Instalar o gerenciador de sessões (Corrige o erro atual)
echo "1. Instalando express-session..."
npm install express-session

# 2. Instalar dependências do Tailwind CSS (Versão Estável 3.4)
# Isso previne erros futuros de build de CSS
echo "2. Instalando Tailwind CSS Estável..."
npm install -D tailwindcss@3.4 postcss autoprefixer

echo "========================================="
echo "✅ Correções aplicadas."
echo "👉 Agora execute: npm start"
echo "========================================="