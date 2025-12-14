const OpenAI = require("openai");
const fs = require('fs');
const path = require('path');

class OpenAIManager {
    constructor(db) {
        this.db = db;
        this.clients = new Map(); // Cache de clientes OpenAI por empresa
    }

    // Método auxiliar para obter o cliente OpenAI configurado da empresa
    async getClient(empresaId) {
        // Tenta recuperar do cache
        let openai = this.clients.get(empresaId);
        if (openai) return openai;

        // Se não tiver no cache, busca no banco
        const [rows] = await this.db.execute(
            "SELECT openai_key, openai_ativo FROM empresas WHERE id = ?",
            [empresaId]
        );

        // Se não tiver chave ou estiver inativo, retorna null
        if (rows.length === 0 || !rows[0].openai_ativo || !rows[0].openai_key) {
            return null;
        }

        // Cria nova instância e salva no cache
        openai = new OpenAI({ apiKey: rows[0].openai_key });
        this.clients.set(empresaId, openai);
        return openai;
    }

    async getResponse(empresaId, userMessage, remoteJid) {
        try {
            const openai = await this.getClient(empresaId);
            if (!openai) return null; // IA não configurada

            // Busca configuração de prompt
            const [config] = await this.db.execute("SELECT openai_prompt FROM empresas WHERE id = ?", [empresaId]);
            const systemPrompt = config[0]?.openai_prompt || "Você é um assistente virtual útil.";

            // Busca histórico recente (Contexto)
            const [historico] = await this.db.execute(
                "SELECT from_me, conteudo FROM mensagens WHERE empresa_id = ? AND remote_jid = ? ORDER BY id DESC LIMIT 6",
                [empresaId, remoteJid]
            );

            const messages = [
                { role: "system", content: systemPrompt },
                ...historico.reverse().map(msg => ({
                    role: msg.from_me ? "assistant" : "user",
                    content: msg.conteudo
                })),
                { role: "user", content: userMessage }
            ];

            const completion = await openai.chat.completions.create({
                messages: messages,
                model: "gpt-3.5-turbo",
            });

            return completion.choices[0].message.content;

        } catch (error) {
            console.error(`[OpenAI] Erro Chat Empresa ${empresaId}:`, error.message);
            return null;
        }
    }

    // NOVO MÉTODO: Transcrição de Áudio (Whisper)
    async transcreverAudio(empresaId, caminhoArquivo) {
        try {
            const openai = await this.getClient(empresaId);
            if (!openai) return null;

            if (!fs.existsSync(caminhoArquivo)) {
                console.error("[OpenAI] Arquivo de áudio não encontrado:", caminhoArquivo);
                return null;
            }

            console.log(`[OpenAI] Transcrevendo áudio: ${caminhoArquivo}`);

            const transcription = await openai.audio.transcriptions.create({
                file: fs.createReadStream(caminhoArquivo),
                model: "whisper-1",
                language: "pt", // Força detecção em português
                response_format: "text"
            });

            return transcription; // Retorna o texto direto

        } catch (error) {
            console.error(`[OpenAI] Erro Transcrição:`, error.message);
            return null;
        }
    }
}

module.exports = OpenAIManager;