/** @type {import('tailwindcss').Config} */
module.exports = {
  // Indica ao Tailwind onde procurar por classes CSS para gerar apenas o necessário
  content: [
    "./views/**/*.ejs",
    "./public/**/*.js",
    "./src/**/*.js"
  ],
  darkMode: 'class', // Ativa o modo escuro via classe 'dark' no HTML
  theme: {
    extend: {
      colors: {
        // Paleta de cores personalizada do seu Sistema de Gestão
        primary: '#4f46e5',   // Indigo
        secondary: '#10b981', // Emerald
        chatbg: '#efeae2',    // WhatsApp Light
        chatbgdark: '#0b141a' // WhatsApp Dark
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}