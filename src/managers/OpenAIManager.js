const OpenAI = require("openai");

class OpenAIManager {
    constructor(db) {
        this.db = db;
        this.clients = new Map(); // Cache de clientes OpenAI por empresa
    }

    async getResponse(empresaId, userMessage, remoteJid) {
        try {
            // 1. Busca configuração da empresa
            const [rows] = await this.db.execute(
                "SELECT openai_key, openai_prompt, openai_ativo FROM empresas WHERE id = ?", 
                [empresaId]
            );

            if (rows.length === 0 || !rows[0].openai_ativo || !rows[0].openai_key) {
                return null; // IA desativada ou não configurada
            }

            const config = rows[0];

            // 2. Instancia ou recupera cliente OpenAI
            let openai = this.clients.get(empresaId);
            if (!openai || openai.apiKey !== config.openai_key) {
                openai = new OpenAI({ apiKey: config.openai_key });
                this.clients.set(empresaId, openai);
            }

            // 3. Busca histórico recente (Contexto) - Últimas 6 mensagens
            const [historico] = await this.db.execute(
                "SELECT from_me, conteudo FROM mensagens WHERE empresa_id = ? AND remote_jid = ? ORDER BY id DESC LIMIT 6",
                [empresaId, remoteJid]
            );

            const messages = [
                { role: "system", content: config.openai_prompt || "Você é um assistente virtual útil." },
                ...historico.reverse().map(msg => ({
                    role: msg.from_me ? "assistant" : "user",
                    content: msg.conteudo
                })),
                { role: "user", content: userMessage }
            ];

            // 4. Chama API
            const completion = await openai.chat.completions.create({
                messages: messages,
                model: "gpt-3.5-turbo", // Ou gpt-4 se preferir (mais caro)
            });

            return completion.choices[0].message.content;

        } catch (error) {
            console.error(`[OpenAI] Erro na empresa ${empresaId}:`, error.message);
            return null; // Falha silenciosa, deixa o fluxo normal seguir
        }
    }
}

module.exports = OpenAIManager;