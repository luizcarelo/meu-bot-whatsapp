'use strict';
/**
 * Verifica se a empresa está em horário de atendimento.
 * Considera dias (["seg","ter","qua","qui","sex"]) e intervalo de hora (HH:mm).
 */
function estaNoHorario(emp) {
  let dias = [];
  try { dias = JSON.parse(emp.dias_funcionamento || '[]'); } catch {}
  const now = new Date();
  const dia = now.toLocaleString('pt-BR', { weekday: 'short' }).slice(0, 3).toLowerCase(); // seg/ter/...
  const inDia = dias.length ? dias.includes(dia) : true;

  const toMin = (s) => {
    const [H, M] = String(s || '08:00').split(':').map(Number);
    return (H * 60) + M;
  };
  const nowMin = (now.getHours() * 60) + now.getMinutes();
  const inHora = nowMin >= toMin(emp.horario_inicio || '08:00') && nowMin <= toMin(emp.horario_fim || '18:00');

  return inDia && inHora;
}
module.exports = { estaNoHorario };