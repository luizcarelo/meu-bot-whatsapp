
#!/usr/bin/env bash
set -euo pipefail

echo "==> Iniciando correções no projeto..."

# 0) Sanitiza todos os .js removendo espaços em branco ao final das linhas (evita diffs sujos)
find . -type f -name "*.js" -print0 | xargs -0 sed -i 's/[[:space:]]\+$//'

# 1) AuthController.js - transporter e fallbacks
file="controllers/AuthController.js"
if [ -f "$file" ]; then
  # Corrige transporter fallback
  perl -0777 -pe "s/nodemailer\\.createTransport\\(\\{\\s*host:[^}]*\\}\\);/nodemailer.createTransport({\n  host: process.env.SMTP_HOST || 'smtp.gmail.com',\n  port: Number(process.env.SMTP_PORT) || 587,\n  secure: false,\n  auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS }\n});/s" -i "$file"

  # Corrige JSON.parse fallback
  sed -i "s/JSON.parse(user.mensagens_padrao[[:space:]]*\\\\ '[]')/JSON.parse(user.mensagens_padrao || '[]')/g" "$file"

  # Corrige cor padrão
  sed -i "s/cor:[[:space:]]*user.cor_primaria[[:space:]]*\\\\ '#4f46e5'/cor: user.cor_primaria || '#4f46e5'/g" "$file"
fi

# 2) AdminController.js - uso_percentual e defaults
file="controllers/AdminController.js"
if [ -f "$file" ]; then
  sed -i "s/uso_percentual:[[:space:]]*Math.round((cliente.total_users[[:space:]]*\\/[[:space:]]*cliente.limite_usuarios)[[:space:]]*\\*[[:space:]]*100)/uso_percentual: Math.round(((cliente.total_users || 0) \\/ (cliente.limite_usuarios || 1)) * 100)/" "$file"
  sed -i "s/status_whatsapp:[[:space:]]*cliente.whatsapp_status[[:space:]]*\\\\ 'DESCONECTADO'/status_whatsapp: cliente.whatsapp_status || 'DESCONECTADO'/" "$file"
  sed -i "s/plano[[:space:]]*\\\\ 'pro'/(plano || 'pro')/" "$file"
  sed -i "s/limite_usuarios[[:space:]]*\\\\ 5/(limite_usuarios || 5)/" "$file"
fi

# 3) CrmController.js - getContatos parametrizado, fallbacks, getAgenda, bcrypt em createAtendente e mídia
file="controllers/CrmController.js"
if [ -f "$file" ]; then
  # Corrige operador isAdmin corrompido e troca construção de SQL por parametrizado
  perl -0777 -pe "s/const isAdmin = users\\[0\\] && \\(users\\[0\\]\\.is_admin == 1 \\\\\\ users\\[0\\]\\.is_admin === true\\);/const isAdmin = users[0] && (users[0].is_admin == 1 || users[0].is_admin === true);/s" -i "$file"

  # Regrava o método getContatos com versão segura (parametrizada)
  perl -0777 -pe "s/async getContatos\\([^{]*\\{[\\s\\S]*?\\}\\s*\\}/async getContatos(req, res) {\n  const userId = req.headers['x-user-id'];\n  const statusFiltro = req.query.status;\n  try {\n    const [users] = await this.db.execute('SELECT is_admin FROM usuarios_painel WHERE id = ?', [userId]);\n    const isAdmin = users[0] && (users[0].is_admin == 1 || users[0].is_admin === true);\n    let sql = `\n      SELECT c.*,\n        (SELECT conteudo FROM mensagens m WHERE m.remote_jid = c.telefone AND m.empresa_id = c.empresa_id ORDER BY id DESC LIMIT 1) as ultima_msg,\n        (SELECT data_hora FROM mensagens m WHERE m.remote_jid = c.telefone AND m.empresa_id = c.empresa_id ORDER BY id DESC LIMIT 1) as ordenacao,\n        s.nome as nome_setor,\n        s.cor as cor_setor,\n        u.nome as nome_atendente\n      FROM contatos c\n      LEFT JOIN setores s ON c.setor_id = s.id\n      LEFT JOIN usuarios_painel u ON c.atendente_id = u.id\n      WHERE c.empresa_id = ?\n    `;\n    const params = [req.empresaId];\n    if (statusFiltro === 'meus') {\n      sql += ` AND c.status_atendimento = 'ATENDENDO' AND c.atendente_id = ?`;\n      params.push(userId);\n    } else if (statusFiltro === 'fila') {\n      sql += ` AND c.status_atendimento = 'FILA'`;\n      if (!isAdmin) {\n        sql += ` AND c.setor_id IN (SELECT setor_id FROM usuarios_setores WHERE usuario_id = ?)`;\n        params.push(userId);\n      }\n    } else if (statusFiltro === 'todos') {\n      if (isAdmin) {\n        sql += ` AND c.status_atendimento IN ('ATENDENDO','FILA','ABERTO')`;\n      } else {\n        sql += ` AND (\n          (c.status_atendimento = 'FILA' AND c.setor_id IN (SELECT setor_id FROM usuarios_setores WHERE usuario_id = ?))\n          OR\n          (c.status_atendimento = 'ATENDENDO' AND c.atendente_id = ?)\n        )`;\n        params.push(userId, userId);\n      }\n    }\n    sql += ` ORDER BY CASE WHEN ordenacao IS NULL THEN 0 ELSE 1 END, ordenacao DESC`;\n    const [rows] = await this.db.execute(sql, params);\n    res.json(rows);\n  } catch (e) {\n    console.error(e);\n    res.status(500).json({ error: 'Erro ao buscar contatos' });\n  }\n}/s" -i "$file"

  # Fallbacks diversos
  sed -i "s/\\?\\.nome[[:space:]]*\\\\ 'Um atendente'/?.nome || 'Um atendente'/" "$file"
  sed -i "s/mensagem_saudacao[[:space:]]*\\\\ \\`Transferindo para \\$\\{setor\\[0\\]\\?\\.nome[[:space:]]*\\\\ 'o setor'\\}\\`/mensagem_saudacao || \`Transferindo para \${setor[0]?.nome || 'o setor'}.\`/" "$file"
  sed -i "s/\\?\\.nome[[:space:]]*\\\\ 'Outro atendente'/?.nome || 'Outro atendente'/" "$file"
  sed -i "s/msg_avaliacao[[:space:]]*\\\\ padrao/msg_avaliacao || padrao/" "$file"
  sed -i "s/cor[[:space:]]*\\\\ '#cbd5e1'/(cor || '#cbd5e1')/" "$file"
  sed -i "s/caption[[:space:]]*\\\\ ''/caption || ''/" "$file"
  sed -i "s/(caption[[:space:]]*\\\\ req.file.originalname)/(caption || req.file.originalname)/" "$file"

  # Adiciona getAgenda (se não existir)
  if ! grep -q "async getAgenda" "$file"; then
    cat >> "$file" <<'EOF'

  // NOVO: Agenda (rota já existe em routes/api.js)
  async getAgenda(req, res) {
    try {
      const [rows] = await this.db.execute(`
        SELECT c.*, s.nome as nome_setor
        FROM contatos c
        LEFT JOIN setores s ON c.setor_id = s.id
        WHERE c.empresa_id = ?
        ORDER BY c.nome ASC
      `, [req.empresaId]);
      res.json(rows);
    } catch (e) {
      res.status(500).json({ error: 'Erro ao carregar agenda' });
    }
  }
EOF
  fi

  # Hash de senha em createAtendente
  perl -0777 -pe "s/const \\{ nome, email, senha, is_admin, setores, telefone, cargo, ativo \\} = req\\.body;\\s*const conn/const { nome, email, senha, is_admin, setores, telefone, cargo, ativo } = req.body;\\nconst bcrypt = require('bcryptjs');\\nconst senhaHash = await bcrypt.hash(senha, 10);\\nconst conn/s" -i "$file"
  perl -0777 -pe "s/\\[req\\.empresaId, nome, email, senha, is_admin \\? 1 : 0, telefone, cargo, ativo \\? 1 : 0\\]/[req.empresaId, nome, email, senhaHash, is_admin ? 1 : 0, telefone, cargo, ativo ? 1 : 0]/s" -i "$file"
fi

# 4) WhatsAppController.js - captionFinal/conteudoSalvo
file="controllers/WhatsAppController.js"
if [ -f "$file" ]; then
  sed -i "s/let captionFinal = caption[[:space:]]*\\\\ ''/let captionFinal = caption || ''/" "$file"
  sed -i "s/(caption[[:space:]]*\\\\ req.file.originalname)/(caption || req.file.originalname)/" "$file"
fi

# 5) routes/api.js - manter rota /crm/agenda (nada crítico a alterar)
# (somente se quiser validar, deixamos como está)

# 6) script/backup_database.js - regex de timestamp
file="script/backup_database.js"
if [ -f "$file" ]; then
  sed -i "s/replace(\\/\\[:\\.\\]\\/g, '-')/replace(/[:.]/g, '-')/" "$file"
fi

# 7) Renomeia reset_databse.js -> reset_database.js
if [ -f "script/reset_databse.js" ]; then
  git mv script/reset_databse.js script/reset_database.js || mv script/reset_databse.js script/reset_database.js
fi

# 8) .gitignore – não versionar sessões, .env, backups, node_modules
if [ ! -f ".gitignore" ]; then
  cat > .gitignore <<'EOF'
.env
node_modules/
auth_sessions/
backups/
EOF
else
  # Garante entradas essenciais
  grep -qxF ".env" .gitignore || echo ".env" >> .gitignore
  grep -qxF "node_modules/" .gitignore || echo "node_modules/" >> .gitignore
  grep -qxF "auth_sessions/" .gitignore || echo "auth_sessions/" >> .gitignore
  grep -qxF "backups/" .gitignore || echo "backups/" >> .gitignore
fi

echo "==> Correções aplicadas com sucesso."
echo "==> Faça commit e push:"
echoecho "   git add ."
echo "   git commit -m \"fix: correções de fallback, SQL parametrizada, agenda, bcrypt, mídia e scripts\""
