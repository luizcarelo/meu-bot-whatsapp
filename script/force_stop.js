const { exec } = require('child_process');

const ports = [50010, 50011]; // Portas para limpar

console.log('🧹 A verificar portas presas...');

ports.forEach(port => {
    // Comando para Linux/Mac
    const cmd = `lsof -i :${port} -t | xargs kill -9`;

    exec(cmd, (error, stdout, stderr) => {
        if (error) {
            // Ignora erro se não houver processo (exit code 1)
            if (error.code !== 1) {
                console.log(`⚠️  Porta ${port}: Livre ou erro ao limpar.`);
            } else {
                console.log(`✅ Porta ${port}: Nenhum processo encontrado.`);
            }
            return;
        }
        console.log(`💀 Porta ${port}: Processos mortos com sucesso.`);
    });
});