#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 06 - Corrigir upserts para PostgreSQL

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Corrigir INSERT IGNORE em controllers/WhatsAppController.js.
- Corrigir ON DUPLICATE KEY UPDATE em src/managers/SessionManager.js.
- Rodar node --check nos arquivos alterados.
- Confirmar ausencia de INSERT IGNORE e ON DUPLICATE KEY em controllers e src.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Corrige apenas achados de alta severidade da Etapa 05.
- Nao altera schema do banco nesta etapa.
- Nao cria migrations nesta etapa.
- Nao executa banco.
- Nao executa Docker.
"""

import os
import re
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

MAX_LEITURA = 3145728

ARQUIVOS_ALVO = [
    "controllers/WhatsAppController.js",
    "src/managers/SessionManager.js"
]

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "controllers/WhatsAppController.js",
    "src/managers/SessionManager.js",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

IGNORAR_MANIFESTO_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions"
]

PADROES_PROIBIDOS = [
    "INSERT IGNORE",
    "ON DUPLICATE KEY"
]


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


def validar_sem_asterisco_indevido(conteudo, nome):
    if chr(42) in conteudo:
        raise ValueError(
            "Validacao bloqueou a geracao de "
            + nome
            + " por conter caractere asterisco."
        )


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
    for nome in IGNORAR_MANIFESTO_DIRS:
        if nome in partes:
            return True
    return False


def listar_arquivos_manifesto():
    arquivos = []

    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)
        novos_dirs = []

        for nome_dir in dirs:
            p = base_path / nome_dir
            if deve_ignorar_manifesto(p):
                continue
            novos_dirs.append(nome_dir)

        dirs[:] = novos_dirs

        for nome in files:
            p = base_path / nome
            if deve_ignorar_manifesto(p):
                continue
            arquivos.append(p)

    return sorted(arquivos)


def gerar_manifesto():
    itens = []

    for p in listar_arquivos_manifesto():
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


def salvar_json(path, dados):
    gravar_texto(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def criar_backup(destino):
    destino.mkdir(parents=True, exist_ok=True)

    copiados = []
    ausentes = []
    erros = []

    for nome in ARQUIVOS_BACKUP_DIRETO:
        origem = ROOT / nome
        destino_item = destino / nome

        if not origem.exists():
            ausentes.append(nome)
            continue

        try:
            destino_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino_item)
            copiados.append(nome)
        except Exception as exc:
            erros.append({
                "arquivo": nome,
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def contar_ocorrencias(texto, termo):
    if texto is None:
        return 0
    return texto.upper().count(termo.upper())


def corrigir_whatsapp_controller():
    nome = "controllers/WhatsAppController.js"
    path = ROOT / nome
    texto = ler_texto(path)

    resultado = {
        "arquivo": nome,
        "existe": path.exists(),
        "alterado": False,
        "ocorrencias_antes": {},
        "ocorrencias_depois": {},
        "substituicoes": []
    }

    if texto is None:
        resultado["erro"] = "Arquivo ausente ou ilegivel"
        return resultado

    resultado["ocorrencias_antes"]["INSERT IGNORE"] = contar_ocorrencias(texto, "INSERT IGNORE")

    novo = texto

    substituicoes = [
        (
            "Upsert simplificado via INSERT IGNORE",
            "Upsert PostgreSQL via ON CONFLICT"
        ),
        (
            "INSERT IGNORE INTO contatos (empresa_id, telefone, nome) VALUES (?, ?, ?)",
            "INSERT INTO contatos (empresa_id, telefone, nome) VALUES (?, ?, ?) ON CONFLICT (empresa_id, telefone) DO NOTHING"
        )
    ]

    for antigo, novo_valor in substituicoes:
        if antigo in novo:
            novo = novo.replace(antigo, novo_valor)
            resultado["substituicoes"].append({
                "de": antigo,
                "para": novo_valor
            })

    if novo != texto:
        gravar_texto(path, novo)
        resultado["alterado"] = True

    texto_depois = ler_texto(path)
    resultado["ocorrencias_depois"]["INSERT IGNORE"] = contar_ocorrencias(texto_depois, "INSERT IGNORE")
    resultado["sha256_depois"] = sha256_arquivo(path)

    return resultado


def corrigir_session_manager():
    nome = "src/managers/SessionManager.js"
    path = ROOT / nome
    texto = ler_texto(path)

    resultado = {
        "arquivo": nome,
        "existe": path.exists(),
        "alterado": False,
        "ocorrencias_antes": {},
        "ocorrencias_depois": {},
        "substituicoes": []
    }

    if texto is None:
        resultado["erro"] = "Arquivo ausente ou ilegivel"
        return resultado

    resultado["ocorrencias_antes"]["ON DUPLICATE KEY"] = contar_ocorrencias(texto, "ON DUPLICATE KEY")

    novo = texto

    padrao = re.compile(
        r"INSERT INTO contatos\s*\(\s*empresa_id,\s*telefone,\s*nome,\s*foto_perfil,\s*status_atendimento,\s*created_at,\s*ultima_msg\s*\)\s*"
        r"VALUES\s*\(\s*\?,\s*\?,\s*\?,\s*\?,\s*'ABERTO',\s*NOW\(\),\s*NOW\(\)\s*\)\s*"
        r"ON DUPLICATE KEY UPDATE\s*"
        r"nome\s*=\s*VALUES\(nome\),\s*"
        r"foto_perfil\s*=\s*VALUES\(foto_perfil\),\s*"
        r"ultima_msg\s*=\s*NOW\(\)",
        re.IGNORECASE | re.MULTILINE
    )

    substituto = (
        "INSERT INTO contatos (empresa_id, telefone, nome, foto_perfil, status_atendimento, created_at, ultima_msg)\n"
        "                VALUES (?, ?, ?, ?, 'ABERTO', NOW(), NOW())\n"
        "                ON CONFLICT (empresa_id, telefone) DO UPDATE SET\n"
        "                    nome = EXCLUDED.nome,\n"
        "                    foto_perfil = EXCLUDED.foto_perfil,\n"
        "                    ultima_msg = NOW()"
    )

    novo2, qtd = padrao.subn(substituto, novo)

    if qtd > 0:
        novo = novo2
        resultado["substituicoes"].append({
            "tipo": "regex",
            "descricao": "Substituido ON DUPLICATE KEY UPDATE por ON CONFLICT em contatos",
            "quantidade": qtd
        })
    else:
        # Fallback textual mais simples para caso a indentacao tenha variado pouco.
        antigo = (
            "ON DUPLICATE KEY UPDATE\n"
            "                    nome = VALUES(nome),\n"
            "                    foto_perfil = VALUES(foto_perfil),\n"
            "                    ultima_msg = NOW()"
        )
        novo_valor = (
            "ON CONFLICT (empresa_id, telefone) DO UPDATE SET\n"
            "                    nome = EXCLUDED.nome,\n"
            "                    foto_perfil = EXCLUDED.foto_perfil,\n"
            "                    ultima_msg = NOW()"
        )

        if antigo in novo:
            novo = novo.replace(antigo, novo_valor)
            resultado["substituicoes"].append({
                "tipo": "texto",
                "descricao": "Fallback textual aplicado em ON DUPLICATE KEY UPDATE",
                "quantidade": 1
            })

    if novo != texto:
        gravar_texto(path, novo)
        resultado["alterado"] = True

    texto_depois = ler_texto(path)
    resultado["ocorrencias_depois"]["ON DUPLICATE KEY"] = contar_ocorrencias(texto_depois, "ON DUPLICATE KEY")
    resultado["sha256_depois"] = sha256_arquivo(path)

    return resultado


def node_check_arquivo(nome):
    path = ROOT / nome

    if not path.exists():
        return {
            "arquivo": nome,
            "existe": False,
            "ok": False,
            "erro": "Arquivo ausente"
        }

    try:
        proc = subprocess.run(
            ["node", "--check", str(path)],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=40
        )

        return {
            "arquivo": nome,
            "existe": True,
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip()[:500],
            "stderr": proc.stderr.strip()[:1000]
        }
    except Exception as exc:
        return {
            "arquivo": nome,
            "existe": True,
            "ok": False,
            "erro": str(exc)
        }


def node_check_alvos():
    return [node_check_arquivo(nome) for nome in ARQUIVOS_ALVO]


def grep_proibidos():
    achados = []

    bases = [
        ROOT / "controllers",
        ROOT / "src"
    ]

    for base in bases:
        if not base.exists():
            continue

        for path in base.rglob("*.js"):
            texto = ler_texto(path)
            if texto is None:
                continue

            for numero, linha in enumerate(texto.splitlines(), start=1):
                upper = linha.upper()
                for termo in PADROES_PROIBIDOS:
                    if termo.upper() in upper:
                        achados.append({
                            "arquivo": rel(path),
                            "linha": numero,
                            "termo": termo,
                            "trecho": linha.strip()[:200]
                        })

    return achados


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_06_INICIO -->"
    marcador_fim = "<!-- ETAPA_06_FIM -->"

    secao = []
    secao.append("")
    secao.append(marcador_inicio)
    secao.append("## " + titulo)
    secao.append("")
    secao.extend(corpo)
    secao.append(marcador_fim)
    secao.append("")

    bloco = "\n".join(secao)

    inicio = texto_atual.find(marcador_inicio)
    fim = texto_atual.find(marcador_fim)

    if inicio >= 0 and fim >= inicio:
        fim = fim + len(marcador_fim)
        novo = texto_atual[:inicio] + bloco.strip() + texto_atual[fim:]
    else:
        if not texto_atual.endswith("\n"):
            texto_atual += "\n"
        novo = texto_atual + bloco

    novo = novo.replace(chr(42), "")
    validar_sem_asterisco_indevido(novo, nome)
    gravar_texto(path, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    proibidos = str(len(relatorio["grep_proibidos"]))
    node_falhas = str(sum(1 for item in relatorio["node_check"] if not item.get("ok")))

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 06 - Upserts PostgreSQL",
        [
            "Data: " + data,
            "",
            "Foram corrigidos os upserts de alta severidade para sintaxe PostgreSQL.",
            "controllers/WhatsAppController.js foi ajustado para usar ON CONFLICT DO NOTHING.",
            "src/managers/SessionManager.js foi ajustado para usar ON CONFLICT DO UPDATE.",
            "Ocorrencias proibidas restantes em controllers e src: " + proibidos + ".",
            "Falhas em node --check nos alvos alterados: " + node_falhas + ".",
            "A constraint unica de contatos por empresa e telefone deve ser validada em etapa de schema."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 06 - Correcao de upserts PostgreSQL",
        [
            "Data: " + data,
            "",
            "Substituido uso de INSERT IGNORE por ON CONFLICT DO NOTHING.",
            "Substituido uso de ON DUPLICATE KEY UPDATE por ON CONFLICT DO UPDATE.",
            "Executado node --check nos arquivos alterados.",
            "Executado scan para confirmar ausencia de padroes antigos em controllers e src.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 06 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido corrigir primeiro apenas achados de alta severidade.",
            "Decidido usar ON CONFLICT com chave logica empresa_id e telefone.",
            "Decidido nao alterar schema nesta etapa para reduzir risco operacional.",
            "Decidido validar constraints e migrations em etapa posterior."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 06",
        [
            "Data: " + data,
            "",
            "Validar se contatos possui constraint unica em empresa_id e telefone.",
            "Criar ou ajustar migration caso a constraint unica nao exista.",
            "Revisar queries restantes com funcoes agregadas e retorno de inserts.",
            "Validar fluxo funcional de recebimento e envio de mensagens.",
            "Executar testes em ambiente controlado com PostgreSQL."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 06 - Corrigir upserts PostgreSQL")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Ocorrencias proibidas restantes: " + str(len(relatorio["grep_proibidos"])))
    linhas.append("")

    linhas.append("## Correcoes aplicadas")
    linhas.append("")
    for item in relatorio["correcoes"]:
        linhas.append("- " + item["arquivo"] + ": alterado=" + str(item["alterado"]))
        if "erro" in item:
            linhas.append("  - erro: " + item["erro"])
        linhas.append("  - ocorrencias antes: " + json.dumps(item.get("ocorrencias_antes", {}), ensure_ascii=False))
        linhas.append("  - ocorrencias depois: " + json.dumps(item.get("ocorrencias_depois", {}), ensure_ascii=False))
        for sub in item.get("substituicoes", []):
            desc = sub.get("descricao") or sub.get("de", "substituicao")
            linhas.append("  - substituicao: " + desc)

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    for item in relatorio["node_check"]:
        linhas.append("- " + item["arquivo"] + ": ok=" + str(item["ok"]))
        if not item.get("ok"):
            detalhe = item.get("stderr") or item.get("erro") or "Falha sem detalhe"
            detalhe = detalhe.replace(chr(42), "[asterisco]")
            linhas.append("  - detalhe: " + detalhe[:300])

    linhas.append("")
    linhas.append("## Scan de padroes antigos")
    linhas.append("")
    if relatorio["grep_proibidos"]:
        for item in relatorio["grep_proibidos"]:
            trecho = item["trecho"].replace(chr(42), "[asterisco]")
            linhas.append(
                "- "
                + item["arquivo"]
                + ":"
                + str(item["linha"])
                + " termo="
                + item["termo"]
                + " trecho="
                + trecho
            )
    else:
        linhas.append("- Nenhum padrao antigo encontrado em controllers e src.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 07: validar schema, constraints e migrations PostgreSQL, especialmente contatos(empresa_id, telefone).")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_06_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_06_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    correcao_whatsapp = corrigir_whatsapp_controller()
    correcao_session = corrigir_session_manager()
    node_resultado = node_check_alvos()
    proibidos = grep_proibidos()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "correcoes": [
            correcao_whatsapp,
            correcao_session
        ],
        "node_check": node_resultado,
        "grep_proibidos": proibidos
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_06_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_06_corrigir_upserts_postgres.json"
    md_path = REPORTS_DIR / "etapa_06_corrigir_upserts_postgres.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    node_falhas = sum(1 for item in node_resultado if not item.get("ok"))

    print("Etapa 06 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Node check falhas: " + str(node_falhas))
    print("Padroes antigos restantes: " + str(len(proibidos)))

    if node_falhas > 0:
        print("")
        print("Falhas em node --check. Consulte o relatorio Markdown.")

    if proibidos:
        print("")
        print("Ainda existem padroes antigos:")
        for item in proibidos:
            print("- " + item["arquivo"] + ":" + str(item["linha"]) + " " + item["termo"])


if __name__ == "__main__":
    main()