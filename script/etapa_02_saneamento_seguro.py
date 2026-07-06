#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 02 - Saneamento seguro do projeto WhatsApp CRM

Objetivo:
- Criar backup antes de qualquer alteracao.
- Gerar manifesto antes e depois.
- Criar .env.example seguro.
- Sanitizar exemplos sensiveis em README.md e MELHORIAS.md.
- Alertar sobre itens que nao devem ir em pacote/deploy compartilhavel.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorio JSON e Markdown em reports/.

Observacoes:
- Nao apaga o arquivo .env.
- Nao altera controllers, Docker, banco ou dependencias nesta etapa.
- Saida e documentacao em PT-BR.
"""

import os
import re
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

ARQUIVOS_DOC_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_PARA_SANITIZAR = [
    "README.md",
    "MELHORIAS.md"
]

ITENS_ALERTA_PACOTE = [
    ".env",
    ".git",
    "node_modules",
    "auth_sessions",
    "public/uploads",
    "backups"
]

CHAVES_ENV_SEGURAS = [
    ("DB_HOST", "localhost"),
    ("DB_USER", "usuario_do_banco"),
    ("DB_PASS", "altere_aqui"),
    ("DB_NAME", "nome_do_banco"),
    ("PORT", "50010"),
    ("NODE_ENV", "production"),
    ("SMTP_HOST", "smtp.exemplo.com"),
    ("SMTP_PORT", "587"),
    ("SMTP_SECURE", "false"),
    ("SMTP_USER", "nao-responda@exemplo.com"),
    ("SMTP_PASS", "altere_aqui"),
    ("SUPER_ADMIN_PASS", "altere_aqui"),
    ("JWT_SECRET", "gere_uma_chave_forte"),
    ("SESSION_SECRET", "gere_uma_chave_forte"),
    ("REDIS_HOST", "127.0.0.1"),
    ("REDIS_PORT", "6379"),
    ("REDIS_PASSWORD", "altere_aqui")
]

CHAVES_SENSIVEIS = [
    "DB_PASS",
    "SMTP_PASS",
    "SUPER_ADMIN_PASS",
    "JWT_SECRET",
    "SESSION_SECRET",
    "REDIS_PASSWORD",
    "OPENAI_API_KEY",
    "OPENAI_KEY",
    "API_KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "SENHA"
]

MAX_LEITURA = 2097152


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def rel(path):
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


def ler_texto(path):
    try:
        if not path.exists():
            return None
        if path.stat().st_size > MAX_LEITURA:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def gravar_texto(path, conteudo):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8")


def sha256_arquivo(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                bloco = f.read(1048576)
                if not bloco:
                    break
                h.update(bloco)
        return h.hexdigest()
    except Exception:
        return None


def deve_ignorar_manifesto(path):
    partes = set(path.parts)
    if "node_modules" in partes:
        return True
    if ".git" in partes:
        return True
    if "backups" in partes:
        return True
    if "auth_sessions" in partes:
        return True
    return False


def listar_arquivos_manifesto():
    arquivos = []
    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)

        dirs_filtrados = []
        for d in dirs:
            p = base_path / d
            if deve_ignorar_manifesto(p):
                continue
            dirs_filtrados.append(d)
        dirs[:] = dirs_filtrados

        for nome in files:
            p = base_path / nome
            if deve_ignorar_manifesto(p):
                continue
            arquivos.append(p)

    return sorted(arquivos)


def gerar_manifesto():
    arquivos = listar_arquivos_manifesto()
    itens = []

    for p in arquivos:
        try:
            st = p.stat()
            itens.append({
                "arquivo": rel(p),
                "tamanho_bytes": st.st_size,
                "sha256": sha256_arquivo(p)
            })
        except Exception as exc:
            itens.append({
                "arquivo": rel(p),
                "erro": str(exc)
            })

    return {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "total_arquivos": len(itens),
        "arquivos": itens
    }


def copiar_backup(destino):
    destino.mkdir(parents=True, exist_ok=True)

    ignorar_nomes = {
        "node_modules",
        "backups",
        ".git"
    }

    total = 0
    erros = []

    for item in ROOT.iterdir():
        if item.name in ignorar_nomes:
            continue

        destino_item = destino / item.name

        try:
            if item.is_dir():
                shutil.copytree(item, destino_item, dirs_exist_ok=True)
            else:
                shutil.copy2(item, destino_item)
            total += 1
        except Exception as exc:
            erros.append({
                "item": rel(item),
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "itens_copiados_raiz": total,
        "erros": erros
    }


def criar_env_example():
    linhas = []
    linhas.append("# ============================================")
    linhas.append("# Exemplo de variaveis de ambiente")
    linhas.append("# Copie este arquivo para .env e preencha valores reais")
    linhas.append("# Nunca commite o arquivo .env")
    linhas.append("# ============================================")
    linhas.append("")
    linhas.append("# Banco de dados")
    for chave, valor in CHAVES_ENV_SEGURAS[0:4]:
        linhas.append(chave + "=" + valor)

    linhas.append("")
    linhas.append("# Servidor")
    for chave, valor in CHAVES_ENV_SEGURAS[4:6]:
        linhas.append(chave + "=" + valor)

    linhas.append("")
    linhas.append("# Email SMTP")
    for chave, valor in CHAVES_ENV_SEGURAS[6:11]:
        linhas.append(chave + "=" + valor)

    linhas.append("")
    linhas.append("# Seguranca")
    for chave, valor in CHAVES_ENV_SEGURAS[11:15]:
        linhas.append(chave + "=" + valor)

    linhas.append("")
    linhas.append("# Redis")
    for chave, valor in CHAVES_ENV_SEGURAS[15:18]:
        linhas.append(chave + "=" + valor)

    linhas.append("")
    conteudo = "\n".join(linhas)

    path = ROOT / ".env.example"
    gravar_texto(path, conteudo)
    return rel(path)


def linha_tem_chave_sensivel(linha):
    texto = linha.upper()
    for chave in CHAVES_SENSIVEIS:
        if chave in texto:
            return True
    return False


def sanitizar_linha_env_like(linha):
    if "=" not in linha:
        return linha

    esquerda, direita = linha.split("=", 1)
    chave_limpa = esquerda.strip().lstrip("#").strip()

    if not linha_tem_chave_sensivel(chave_limpa):
        return linha

    prefixo = ""
    if esquerda.lstrip().startswith("#"):
        prefixo = "# "

    return prefixo + chave_limpa + "=altere_aqui"


def sanitizar_docs():
    resultado = []

    for nome in ARQUIVOS_PARA_SANITIZAR:
        path = ROOT / nome
        texto = ler_texto(path)

        if texto is None:
            resultado.append({
                "arquivo": nome,
                "existe": path.exists(),
                "alterado": False,
                "motivo": "Arquivo ausente ou muito grande para leitura segura"
            })
            continue

        linhas_originais = texto.splitlines()
        linhas_novas = []
        alteracoes = 0

        for linha in linhas_originais:
            nova = sanitizar_linha_env_like(linha)
            if nova != linha:
                alteracoes += 1
            linhas_novas.append(nova)

        novo_texto = "\n".join(linhas_novas)
        if texto.endswith("\n"):
            novo_texto += "\n"

        if novo_texto != texto:
            gravar_texto(path, novo_texto)

        resultado.append({
            "arquivo": nome,
            "existe": True,
            "alterado": novo_texto != texto,
            "linhas_sanitizadas": alteracoes
        })

    return resultado


def verificar_itens_pacote():
    encontrados = []

    for item in ITENS_ALERTA_PACOTE:
        p = ROOT / item
        if p.exists():
            encontrados.append({
                "item": item,
                "tipo": "diretorio" if p.is_dir() else "arquivo",
                "recomendacao": "Nao incluir em pacote compartilhavel ou deploy manual"
            })

    return encontrados


def validar_sem_asterisco_indevido(conteudo, nome):
    if "*" in conteudo:
        raise ValueError(
            "Validacao bloqueou a geracao de "
            + nome
            + " por conter caractere asterisco."
        )


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_02_INICIO -->"
    marcador_fim = "<!-- ETAPA_02_FIM -->"

    secao = []
    secao.append("")
    secao.append(marcador_inicio)
    secao.append("## " + titulo)
    secao.append("")
    secao.extend(corpo)
    secao.append(marcador_fim)
    secao.append("")

    bloco = "\n".join(secao)

    padrao = re.compile(
        re.escape(marcador_inicio)
        + r".*?"
        + re.escape(marcador_fim),
        re.DOTALL
    )

    if padrao.search(texto_atual):
        novo = padrao.sub(bloco.strip(), texto_atual)
    else:
        if not texto_atual.endswith("\n"):
            texto_atual += "\n"
        novo = texto_atual + bloco

    validar_sem_asterisco_indevido(novo, nome)
    gravar_texto(path, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 02 - Saneamento seguro",
        [
            "Data: " + data,
            "",
            "Foi executada uma etapa de saneamento seguro antes de alteracoes funcionais.",
            "A etapa criou backup, manifestos, .env.example seguro e relatorios em reports/.",
            "O arquivo .env real foi preservado localmente e nao foi removido automaticamente.",
            "A etapa nao alterou regras de negocio, banco, Docker, controllers ou dependencias."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 02 - Saneamento seguro",
        [
            "Data: " + data,
            "",
            "Adicionado .env.example com valores de exemplo seguros.",
            "Sanitizados exemplos sensiveis em arquivos de documentacao quando encontrados.",
            "Gerados manifestos antes e depois da etapa.",
            "Gerados relatorios JSON e Markdown da etapa.",
            "Criado backup local antes das alteracoes."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 02 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido nao apagar o .env automaticamente para evitar indisponibilidade do ambiente.",
            "Decidido criar .env.example como referencia segura para configuracao.",
            "Decidido tratar Docker, banco, controllers e dependencias em etapas separadas.",
            "Decidido manter manifestos com hash para auditoria antes e depois das alteracoes."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 02",
        [
            "Data: " + data,
            "",
            "Rotacionar credenciais reais expostas anteriormente em arquivos locais ou historico.",
            "Corrigir inconsistencia entre MySQL no ambiente e PostgreSQL no docker-compose.yml.",
            "Revisar CORS, Helmet, rate limit e politicas de sessao.",
            "Revisar dependencias com alerta, incluindo multer e fluent-ffmpeg.",
            "Validar sintaxe e testes dos controllers e rotas principais.",
            "Criar rotina de pacote limpo sem .env, .git, node_modules, auth_sessions, uploads e backups."
        ]
    )

    return ARQUIVOS_DOC_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 02 - Saneamento seguro")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivo de exemplo criado: " + relatorio["env_example"])
    linhas.append("")

    linhas.append("## Sanitizacao de documentacao")
    linhas.append("")
    for item in relatorio["docs_sanitizados"]:
        linhas.append("- Arquivo: " + item["arquivo"])
        linhas.append("  - Existe: " + str(item.get("existe")))
        linhas.append("  - Alterado: " + str(item.get("alterado")))
        if "linhas_sanitizadas" in item:
            linhas.append("  - Linhas sanitizadas: " + str(item["linhas_sanitizadas"]))
        if "motivo" in item:
            linhas.append("  - Motivo: " + item["motivo"])
    linhas.append("")

    linhas.append("## Itens que nao devem ir para pacote compartilhavel")
    linhas.append("")
    if relatorio["alertas_pacote"]:
        for item in relatorio["alertas_pacote"]:
            linhas.append("- " + item["item"] + " - " + item["tipo"])
    else:
        linhas.append("- Nenhum item de alerta encontrado.")
    linhas.append("")

    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)
    linhas.append("")

    linhas.append("## Pendencias tecnicas")
    linhas.append("")
    linhas.append("- Rotacionar credenciais reais.")
    linhas.append("- Corrigir docker-compose.yml para o banco correto.")
    linhas.append("- Revisar seguranca HTTP e CORS.")
    linhas.append("- Atualizar dependencias em etapa propria.")
    linhas.append("- Validar controllers, rotas e testes.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def salvar_json(path, dados):
    gravar_texto(
        path,
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n"
    )


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_02_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_02_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = copiar_backup(backup_dir)

    env_example = criar_env_example()
    docs_sanitizados = sanitizar_docs()
    alertas_pacote = verificar_itens_pacote()

    relatorio_base = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "env_example": env_example,
        "docs_sanitizados": docs_sanitizados,
        "alertas_pacote": alertas_pacote
    }

    documentacao_atualizada = atualizar_documentacao(relatorio_base)
    relatorio_base["documentacao_atualizada"] = documentacao_atualizada

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_02_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio_base["manifesto_depois"] = rel(manifesto_depois_path)

    json_report_path = REPORTS_DIR / "etapa_02_saneamento_seguro.json"
    md_report_path = REPORTS_DIR / "etapa_02_saneamento_seguro.md"

    salvar_json(json_report_path, relatorio_base)
    gravar_texto(md_report_path, gerar_markdown_relatorio(relatorio_base))

    print("Etapa 02 concluida com sucesso.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_report_path))
    print("Relatorio Markdown: " + rel(md_report_path))
    print("Env example: " + env_example)

    if alertas_pacote:
        print("")
        print("Alertas de pacote/deploy:")
        for item in alertas_pacote:
            print("- " + item["item"] + " nao deve ser incluido em pacote compartilhavel.")


if __name__ == "__main__":
    main()