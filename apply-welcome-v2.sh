
#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------
# Config
# --------------------------------------------
SM="src/managers/SessionManager.js"
UTIL_DIR="src/utils"
UTIL_FILE="${UTIL_DIR}/atendimento.js"
MIG_FILE="script/migrate_add_last_welcome_at.sql"

echo "==> Iniciando welcome patch v2..."

# --------------------------------------------
# 1) Criar utilitário de horário
# --------------------------------------------
mkdir -p "${UTIL_DIR}"
cat > "${UTIL_FILE}" <<'EOF'
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
EOF

# --------------------------------------------
# 2) Migration SQL para last_welcome_at
# --------------------------------------------
mkdir -p script
cat > "${MIG_FILE}" <<'EOF'
-- Migration: adiciona coluna para controle de boas-vindas
ALTER TABLE contatos
  ADD COLUMN last_welcome_at DATETIME NULL;
CREATE INDEX idx_last_welcome ON contatos(last_welcome_at);
EOF

# --------------------------------------------
# 3) Garantir import no topo do SessionManager
#    Inserimos logo após "const path = require('path');"
# --------------------------------------------
perl -0777 -pe "s|const path = require\\('path'\\);|const path = require('path');\\nconst { estaNoHorario } = require('../utils/atendimento');|s" -i "${SM}"

# --------------------------------------------
# 4) Inserir fluxo de boas-vindas após o marcador:
#    // Persistência e Lógica de CRM
#    O bloco é inserido imediatamente DEPOIS de salvar a mensagem e emitir para web,
#    para evitar duplicidade com o auto-resposta atual.
# --------------------------------------------
perl -0777 -pe '
s|(// Persistência e Lógica de CRM[^\n]*\n)(\s*const \[contatoExistente\][\s\S]*?this\.io\.to\([^\)]*\)\.emit\([^\)]*\);\n)|
$1$2
// ---- Fluxo de Boas-Vindas Automático (v2) ----
try {
  // Config da empresa
  const [empRows] = await this.db.execute(
    "SELECT nome, mensagens_padrao, msg_ausencia, welcome_media_url, welcome_media_type, horario_inicio, horario_fim, dias_funcionamento FROM empresas WHERE id = ?",
    [empresaId]
  );
  const emp = empRows[0];

  // Contato + último welcome
  const [contRows] = await this.db.execute(
    "SELECT id, last_welcome_at FROM contatos WHERE empresa_id = ? AND telefone = ?",
    [empresaId, remoteJid]
  );
  let contatoId = contRows[0]?.id;
  let lastWelcomeAt = contRows[0]?.last_welcome_at;

  if (!contatoId) {
    const [ins] = await this.db.execute(
      "INSERT INTO contatos (empresa_id, telefone, status_atendimento, created_at) VALUES (?, ?, 'ABERTO', NOW())",
      [empresaId, remoteJid]
    );
    contatoId = ins.insertId;
    lastWelcomeAt = null;
  }

  // Decide se precisa enviar boas-vindas (24h)
  const precisaWelcome = (() => {
    if (!lastWelcomeAt) return true;
    const horas = (Date.now() - new Date(lastWelcomeAt).getTime()) / 3600000;
    return horas >= 24;
  })();

  // Lista setores (para mostrar ao cliente e interpretar números)
  const [setores] = await this.db.execute(
    "SELECT id, nome, mensagem_saudacao, cor FROM setores WHERE empresa_id = ? ORDER BY ordem ASC, id ASC",
    [empresaId]
  );

  // Se cliente respondeu com 1/2/3..., transfere para setor
  const numSel = parseInt((conteudo || "").trim(), 10);
  if (!isNaN(numSel) && numSel >= 1 && numSel <= setores.length) {
    const setorEscolhido = setores[numSel - 1];
    await this.db.execute(
      "UPDATE contatos SET status_atendimento = 'FILA', setor_id = ?, atendente_id = NULL WHERE empresa_id = ? AND telefone = ?",
      [setorEscolhido.id, empresaId, remoteJid]
    );
    const aviso = `🔄 Transferido para setor: *${setorEscolhido.nome}*`;
    await sock.sendMessage(remoteJid, { text: aviso });
    await this.db.execute(
      "INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'sistema', ?)",
      [empresaId, remoteJid, aviso]
    );
    this.emitirMensagemEnviada(empresaId, remoteJid, aviso, "sistema");
    // não segue para boas-vindas se já houve seleção
  } else if (precisaWelcome) {
    const inHorario = estaNoHorario(emp);
    // Texto padrão de boas-vindas
    let boasVindasText = "Olá! Seja bem-vindo(a).";
    try {
      const padrao = JSON.parse(emp.mensagens_padrao || "[]");
      const msgBV = padrao.find(p => String(p.titulo || "").toLowerCase() === "boasvindas");
      if (msgBV?.texto) boasVindasText = msgBV.texto;
    } catch {}
    const ausenciaText = emp.msg_ausencia || "Estamos fora do horário. Retornaremos assim que possível.";

    const listaSetoresTexto = setores.length
      ? "Setores disponíveis:\\n" + setores.map((s, i) => `${i + 1}) ${s.nome}`).join("\\n")
      : "No momento, não há setores cadastrados.";

    const textoFinal = inHorario
      ? `${boasVindasText}\\n\\n${listaSetoresTexto}\\n\\n*Responda com o número do setor para continuar.*`
      : `${ausenciaText}\\n\\n${listaSetoresTexto}`;

    await sock.sendMessage(remoteJid, { text: textoFinal });
    await this.db.execute(
      "INSERT INTO mensagens (empresa_id, remote_jid, from_me, tipo, conteudo) VALUES (?, ?, 1, 'sistema', ?)",
      [empresaId, remoteJid, textoFinal]
    );
    this.emitirMensagemEnviada(empresaId, remoteJid, textoFinal, "sistema");

    // Mídia opcional de boas-vindas
    if (emp.welcome_media_url && emp.welcome_media_type) {
      const safePath = path.join(this.rootDir, "public", emp.welcome_media_url.replace(/^\\/+/, ""));
      const type = String(emp.welcome_media_type).toLowerCase();
      const msgSend =
        (type === "imagem") ? { image: { url: safePath }, caption: boasVindasText } :
        (type === "video")  ? { video: { url: safePath }, caption: boasVindasText } :
        (type === "audio")  ? { audio: { url: safePath } } :
                              { document: { url: safePath }, caption: boasVindasText };
      await sock.sendMessage(remoteJid, msgSend);
      this.emitirMensagemEnviada(empresaId, remoteJid, "[Mídia Boas-Vindas]", type, emp.welcome_media_url);
    }

    // Marca última boas-vindas
    await this.db.execute("UPDATE contatos SET last_welcome_at = NOW() WHERE id = ?", [contatoId]);
  }
} catch (e) {
  console.error("[WelcomeFlow] Erro:", e.message);
}
// ---- Fim do fluxo de boas-vindas ----

|s' -i "${SM}"

# --------------------------------------------
# 5) Gerar patch limpo a partir do seu repo
# --------------------------------------------
echo "==> Gerando diff (patch)..."
git add -A
git diff --cached > patch-boasvindas-v2-from-repo.diff

echo "==> Concluído:"
echo "  - Utils: ${UTIL_FILE}"
echo "  - Migration: ${MIG_FILE}"
echo "  - SessionManager modificado: ${SM}"
echo "  - Patch gerado: patch-boasvindas-v2-from-repo.diff"

echo "==> Agora aplique a migration no MySQL (uma vez):"
echo "     mysql -u <USER> -p <DB> < ${MIG_FILE}"
echo "   ou execute o SQL manualmente:"
echo "     ALTER TABLE contatos ADD COLUMN last_welcome_at DATETIME NULL;"
echo "     CREATE INDEX idx_last_welcome ON contatos(last_welcome_at);"

echo "==> Depois: commit & push"
echoecho "     git commit -m \"feat: boas-vindas automáticas + setores + last_welcome_at\""
