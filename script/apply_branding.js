const fs = require('fs');
const path = require('path');

const viewsDir = path.join(__dirname, '../views');

function updateFiles(dir) {
    fs.readdirSync(dir).forEach(file => {
        const fullPath = path.join(dir, file);
        if (fs.lstatSync(fullPath).isDirectory()) {
            updateFiles(fullPath);
        } else if (file.endsWith('.ejs') || file.endsWith('.html')) {
            let content = fs.readFileSync(fullPath, 'utf8');
            
            // 1. Atualiza Favicon
            content = content.replace(/favicon\.(ico|png)/gi, 'lh_chatbot_favicon.png');
            
            // 2. Atualiza Logo Principal (procura padrões comuns)
            content = content.replace(/logo\.(png|svg|jpg)/gi, 'lhsolucao_logo.png');
            
            // 3. Atualiza Logo do Chatbot (procura padrões comuns)
            content = content.replace(/chatbot_logo\.(png|svg|jpg)/gi, 'chatbot_logo.png');

            fs.writeFileSync(fullPath, content, 'utf8');
            console.log(`✅ Atualizado: ${file}`);
        }
    });
}

console.log("🎨 Aplicando branding LH Solução...");
updateFiles(viewsDir);
console.log("✨ Branding aplicado com sucesso!");