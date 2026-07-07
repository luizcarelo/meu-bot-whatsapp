#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 06.1 - Corrigir upsert restante no SessionManager para PostgreSQL

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Corrigir o padrao antigo de upsert restante em src/managers/SessionManager.js.
- Validar sintaxe com node --check.
- Confirmar ausencia de padroes antigos em controllers e src.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Altera apenas src/managers/SessionManager.js e documentos obrigatorios.
- Nao altera schema do banco.
- Nao cria migration.
- Nao executa banco.
- Nao executa Docker.
"""

import os
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

ARQUIVO_ALVO = "src/managers/SessionManager.js"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "src/managers/SessionManager.js",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

PADROES_PROIBIDOS = [
    "INSERT IGNORE",
    "ON DUPLICATE KEY"
]

IGNORAR_MANIFESTO_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions"
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


def trecho_contexto(texto, termo, margem=4):
    if texto is None:
        return []

    linhas = texto.splitlines()
    alvo = -1

    for i, linha in enumerate(linhas):
        if termo.upper() in linha.upper():
            alvo = i
            break

    if alvo < 0:
        return []

    ini = max(0, alvo - margem)
    fim = min(len(linhas), alvo + margem + 1)

    resultado = []
    for i in range(ini, fim):
        resultado.append({
            "linha": i + 1,
            "conteudo": linhas[i].strip()[:220]
        })

    return resultado


def corrigir_session_manager():
    path = ROOT / ARQUIVO_ALVO
    texto = ler_texto(path)

    resultado = {
        "arquivo": ARQUIVO_ALVO,
        "existe": path.exists(),
        "alterado": False,
        "ocorrencias_antes": {},
        "ocorrencias_depois": {},
        "substituicoes": [],
        "contexto_antes": [],
        "contexto_depois": []
    }

    if texto is None:
        resultado["erro"] = "Arquivo ausente ou ilegivel"
        return resultado

    resultado["ocorrencias_antes"]["ON DUPLICATE KEY"] = contar_ocorrencias(texto, "ON DUPLICATE KEY")
    resultado["contexto_antes"] = trecho_contexto(texto, "ON DUPLICATE KEY")

    novo = texto

    substituicoes = [
        (
            "ON DUPLICATE KEY UPDATE",
            "ON CONFLICT (empresa_id, telefone) DO UPDATE SET"
        ),
        (
            "nome = VALUES(nome)",
            "nome = EXCLUDED.nome"
        ),
        (
            "foto_perfil = VALUES(foto_perfil)",
            "foto_perfil = EXCLUDED.foto_perfil"
        )
    ]

    for antigo, novo_valor in substituicoes:
        if antigo in novo:
            qtd = novo.count(antigo)
            novo = novo.replace(antigo, novo_valor)
            resultado["substituicoes"].append({
                "de": antigo,
                "para": novo_valor,
                "quantidade": qtd
            })

    if novo != texto:
        gravar_texto(path, novo)
        resultado["alterado"] = True

    texto_depois = ler_texto(path)
    resultado["ocorrencias_depois"]["ON DUPLICATE KEY"] = contar_ocorrencias(texto_depois, "ON DUPLICATE KEY")
    resultado["contexto_depois"] = trecho_contexto(texto_depois, "ON CONFLICT (empresa_id, telefone)")
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
                            "trecho": linha.strip()[:220]
                        })

    return achados


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_06_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_06_1_FIM -->"

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
    node_ok = str(relatorio["node_check"]["ok"])

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 06.1 - Upsert restante corrigido",
        [
            "Data: " + data,
            "",
            "Foi corrigido o upsert restante em src/managers/SessionManager.js.",
            "A query passou a usar sintaxe PostgreSQL com conflito por empresa_id e telefone.",
            "Padroes antigos restantes em controllers e src: " + proibidos + ".",
            "Node check do arquivo alterado OK: " + node_ok + ".",
            "A validacao de constraint unica continua planejada para a etapa de schema."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 06.1 - Finalizacao dos upserts PostgreSQL",
        [
            "Data: " + data,
            "",
            "Finalizada a correcao do upsert restante em src/managers/SessionManager.js.",
            "Executado node --check no arquivo alterado.",
            "Executado scan de padroes antigos em controllers e src.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 06.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido finalizar a correcao de sintaxe no codigo antes de alterar schema.",
            "Decidido manter a chave logica empresa_id e telefone para conflito de contatos.",
            "Decidido deixar constraint e migrations para etapa dedicada de schema."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 06.1",
        [
            "Data: " + data,
            "",
            "Validar constraint unica em contatos por empresa_id e telefone.",
            "Criar migration PostgreSQL caso a constraint nao exista.",
            "Revisar queries com funcoes agregadas especificas e retorno de inserts.",
            "Executar teste funcional de recebimento de mensagem e criacao de contato.",
            "Executar teste funcional de envio de mensagem e registro no historico."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 06.1 - Corrigir upsert restante do SessionManager")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivo alterado: " + str(relatorio["correcao"]["alterado"]))
    linhas.append("- Ocorrencias proibidas restantes: " + str(len(relatorio["grep_proibidos"])))
    linhas.append("")

    linhas.append("## Correcao aplicada")
    linhas.append("")
    cor = relatorio["correcao"]
    linhas.append("- Arquivo: " + cor["arquivo"])
    linhas.append("- Alterado: " + str(cor["alterado"]))
    linhas.append("- Ocorrencias antes: " + json.dumps(cor.get("ocorrencias_antes", {}), ensure_ascii=False))
    linhas.append("- Ocorrencias depois: " + json.dumps(cor.get("ocorrencias_depois", {}), ensure_ascii=False))

    if cor.get("substituicoes"):
        linhas.append("- Substituicoes:")
        for sub in cor["substituicoes"]:
            linhas.append("  - " + sub["de"] + " -> " + sub["para"] + " qtd=" + str(sub["quantidade"]))
    else:
        linhas.append("- Substituicoes: nenhuma")

    linhas.append("")
    linhas.append("## Contexto depois")
    linhas.append("")
    if cor.get("contexto_depois"):
        for item in cor["contexto_depois"]:
            trecho = item["conteudo"].replace(chr(42), "[asterisco]")
            linhas.append("- linha " + str(item["linha"]) + ": " + trecho)
    else:
        linhas.append("- Contexto nao encontrado.")

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    nc = relatorio["node_check"]
    linhas.append("- " + nc["arquivo"] + ": ok=" + str(nc["ok"]))
    if not nc.get("ok"):
        detalhe = nc.get("stderr") or nc.get("erro") or "Falha sem detalhe"
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
    linhas.append("- Etapa 07: validar schema, constraints e migrations PostgreSQL, especialmente contatos por empresa e telefone.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_06_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_06_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    correcao = corrigir_session_manager()
    node_resultado = node_check_arquivo(ARQUIVO_ALVO)
    proibidos = grep_proibidos()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "correcao": correcao,
        "node_check": node_resultado,
        "grep_proibidos": proibidos
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_06_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_06_1_corrigir_session_upsert.json"
    md_path = REPORTS_DIR / "etapa_06_1_corrigir_session_upsert.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 06.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Arquivo alterado: " + str(correcao["alterado"]))
    print("Node check OK: " + str(node_resultado["ok"]))
    print("Padroes antigos restantes: " + str(len(proibidos)))

    if not node_resultado.get("ok"):
        print("")
        print("Falha em node --check. Consulte o relatorio Markdown.")

    if proibidos:
        print("")
        print("Ainda existem padroes antigos:")
        for item in proibidos:
            print("- " + item["arquivo"] + ":" + str(item["linha"]) + " " + item["termo"])


if __name__ == "__main__":
    main()