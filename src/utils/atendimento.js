/**
 * src/utils/atendimento.js
 * Módulo de Verificação de Horário de Atendimento (Enterprise Edition)
 * Desenvolvido por: Sistemas de Gestão
 */

const moment = require('moment');

/**
 * Verifica se a empresa está dentro do horário de atendimento.
 * * @param {Object} dbConnection - Conexão Pool do MySQL/MariaDB
 * @param {number} empresaId - ID da empresa no banco de dados
 * @returns {Promise<Object>} - Retorna objeto { dentroDoHorario: boolean, mensagem: string | null }
 */
const verificarHorarioAtendimento = async (dbConnection, empresaId) => {
    try {
        // Obter data e hora atual do sistema (Considerando timezone do servidor ou configurado)
        const agora = moment();
        const diaSemanaAtual = agora.day(); // 0 (Dom) a 6 (Sab)
        const horaAtual = agora.format('HH:mm:ss');

        // Buscar configuração específica para o dia de hoje
        const sql = `
            SELECT * FROM horarios_atendimento 
            WHERE empresa_id = ? AND dia_semana = ? AND ativo = 1
            LIMIT 1
        `;

        const [rows] = await dbConnection.execute(sql, [empresaId, diaSemanaAtual]);

        // Se não houver registro ou estiver marcado como inativo para o dia
        if (rows.length === 0) {
            return {
                dentroDoHorario: false,
                mensagem: 'No momento estamos fora do nosso horário de atendimento. Retornaremos em breve.'
            };
        }

        const regra = rows[0];
        
        // Conversão para objetos moment para comparação
        const abertura = moment(regra.horario_abertura, 'HH:mm:ss');
        const fechamento = moment(regra.horario_fechamento, 'HH:mm:ss');
        const atual = moment(horaAtual, 'HH:mm:ss');

        // 1. Verificação Base (Abertura e Fechamento)
        if (atual.isBefore(abertura) || atual.isAfter(fechamento)) {
            return {
                dentroDoHorario: false,
                mensagem: `Nosso horário de atendimento hoje é das ${regra.horario_abertura.slice(0,5)} às ${regra.horario_fechamento.slice(0,5)}.`
            };
        }

        // 2. Verificação de Almoço (Intervalo)
        if (regra.inicio_almoco && regra.fim_almoco) {
            const inicioAlmoco = moment(regra.inicio_almoco, 'HH:mm:ss');
            const fimAlmoco = moment(regra.fim_almoco, 'HH:mm:ss');

            if (atual.isBetween(inicioAlmoco, fimAlmoco)) {
                return {
                    dentroDoHorario: false,
                    mensagem: `Estamos em horário de almoço. Atendimento retorna às ${regra.fim_almoco.slice(0,5)}.`
                };
            }
        }

        // Se passou por tudo, está aberto
        return {
            dentroDoHorario: true,
            mensagem: null
        };

    } catch (error) {
        console.error('[Atendimento] Erro ao verificar horário:', error);
        // Fail-safe: Em caso de erro de banco, permite atendimento para não bloquear clientes (ou bloqueia, dependendo da regra de negócio)
        return { dentroDoHorario: true, mensagem: null }; 
    }
};

/**
 * Função utilitária para formatar a mensagem de saudação baseada no horário
 */
const getSaudacao = () => {
    const hora = moment().hour();
    if (hora >= 5 && hora < 12) return 'Bom dia';
    if (hora >= 12 && hora < 18) return 'Boa tarde';
    return 'Boa noite';
};

module.exports = {
    verificarHorarioAtendimento,
    getSaudacao
};