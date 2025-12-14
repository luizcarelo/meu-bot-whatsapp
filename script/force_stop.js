const { exec } = require('child_process');

// Lista de portas usadas pela aplicação
const ports = [50010, 50011]; 

console.log('\n========================================');
console.log('🧹 FORÇAR PARADA DE PROCESSOS');
console.log('========================================\n');

function checkAndKill(port) {
    return new Promise((resolve) => {
        // Passo 1: Encontrar o PID que está usando a porta
        exec(`lsof -t -i:${port}`, (error, stdout, stderr) => {
            // lsof retorna erro (exit code 1) se não encontrar nada
            if (error || !stdout) {
                console.log(`✅ Porta ${port}: Livre.`);
                return resolve(false);
            }

            // Se encontrou PIDs
            const pids = stdout.trim().replace(/\n/g, ' ');
            
            // Tenta obter o nome do processo para logar
            exec(`ps -p ${pids.replace(/ /g, ',')} -o comm=`, (err, psStdout) => {
                const nomes = psStdout ? psStdout.trim().replace(/\n/g, ', ') : 'Processo';
                
                console.log(`⚠️  Porta ${port}: Ocupada por [${nomes}] (PIDs: ${pids}). Encerrando...`);
                
                // Passo 2: Matar com SIGKILL
                exec(`kill -9 ${pids}`, (killError) => {
                    if (killError) {
                        console.error(`❌ Porta ${port}: Falha ao matar processo: ${killError.message}`);
                    } else {
                        console.log(`💀 Porta ${port}: Processo(s) mortos com sucesso.`);
                    }
                    resolve(true);
                });
            });
        });
    });
}

async function run() {
    // Executa limpeza
    for (const port of ports) {
        await checkAndKill(port);
    }

    // Verificação de persistência (Auto-Restart)
    console.log('\n⏳ Verificando reincidência (1s)...');
    setTimeout(() => {
        ports.forEach(port => {
            exec(`lsof -t -i:${port}`, (error, stdout) => {
                if (stdout) {
                    console.error(`🚨 ALERTA: A porta ${port} foi ocupada novamente! (PID: ${stdout.trim()})`);
                    console.error(`👉 DIAGNÓSTICO: Existe um gerenciador (como PM2, Systemd ou Docker) reiniciando sua aplicação automaticamente.`);
                    console.error(`   Pare o serviço principal antes de tentar rodar manual.`);
                } else {
                    console.log(`✨ Porta ${port}: Confirmada livre.`);
                }
            });
        });
    }, 1000);
}

run();