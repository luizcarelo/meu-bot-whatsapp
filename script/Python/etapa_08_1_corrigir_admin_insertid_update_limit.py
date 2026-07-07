#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 08.1 - Corrigir insertId e UPDATE LIMIT no AdminController

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Corrigir INSERT de empresas para usar RETURNING id.
- Corrigir leitura de id de resEmp.insertId para resEmp.rows[0].id.
- Remover LIMIT 1 de UPDATE em usuarios_painel no AdminController.
- Rodar node --check no AdminController.
- Rodar scan focado em padroes criticos restantes.
- Ignorar SELECT ... LIMIT 1 valido em PostgreSQL.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Altera apenas controllers/AdminController.js e documentos obrigatorios.
- Nao altera schema.
- Nao executa banco.
- Nao executa Docker.
- Nao altera .env.
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

ARQUIVO_ALVO = "controllers/AdminController.js"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "controllers/AdminController.js",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

IGNORAR_MANIFESTO_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "public/uploads"
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
    rel_path = rel(path)

    for nome in IGNORAR_MANIFESTO_DIRS:
        sub = nome.split("/")
        if len(sub) == 1 and sub[0] in partes:
            return True
        if rel_path == nome or rel_path.startswith(nome + "/"):
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
                "item": nome,
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


def scan_critico_admin():
    path = ROOT / ARQUIVO_ALVO
    texto = ler_texto(path)
    achados = []

    if texto is None:
        return achados

    linhas = texto.splitlines()

    for numero, linha in enumerate(linhas, start=1):
        upper = linha.upper()

        if "INSERTID" in upper:
            achados.append({
                "arquivo": ARQUIVO_ALVO,
                "linha": numero,
                "termo": "insertId",
                "trecho": linha.strip()[:240]
            })

        if "UPDATE" in upper and "LIMIT 1" in upper:
            achados.append({
                "arquivo": ARQUIVO_ALVO,
                "linha": numero,
                "termo": "UPDATE LIMIT 1",
                "trecho": linha.strip()[:240]
            })

    return achados


def adicionar_returning_id_em_insert_empresas(texto, resultado):
    novo = texto

    # Caso mais comum: fechamento do VALUES no insert de empresas.
    # A string fica em template literal e termina com backtick e virgula.
    padroes = [
        (
            "NOW(), 'DESCONECTADO')`",
            "NOW(), 'DESCONECTADO') RETURNING id`"
        ),
        (
            "NOW(), 'DESCONECTADO')`,",
            "NOW(), 'DESCONECTADO') RETURNING id`,"
        )
    ]

    for antigo, novo_valor in padroes:
        if antigo in novo and "RETURNING id" not in trecho_insert_empresas(novo):
            qtd = novo.count(antigo)
            novo = novo.replace(antigo, novo_valor, 1)
            resultado["substituicoes"].append({
                "de": antigo,
                "para": novo_valor,
                "quantidade": 1,
                "observacao": "Adicionado RETURNING id no insert de empresas"
            })
            return novo

    # Fallback mais generico: se existir INSERT INTO empresas e nao existir RETURNING id
    # no bloco proximo, insere antes do fechamento do template literal mais provavel.
    trecho = trecho_insert_empresas(novo)
    if trecho and "RETURNING id" not in trecho:
        alvo = ")\n                VALUES"
        if alvo in trecho:
            # Nao altera aqui porque o ponto seguro e o final do VALUES.
            pass

    return novo


def trecho_insert_empresas(texto):
    idx = texto.find("INSERT INTO empresas")
    if idx < 0:
        return ""

    fim = texto.find("`", idx + 1)
    if fim < 0:
        return texto[idx:idx + 1200]

    return texto[idx:fim + 1]


def corrigir_admin_controller():
    path = ROOT / ARQUIVO_ALVO
    texto = ler_texto(path)

    resultado = {
        "arquivo": ARQUIVO_ALVO,
        "existe": path.exists(),
        "alterado": False,
        "ocorrencias_antes": {},
        "ocorrencias_depois": {},
        "substituicoes": []
    }

    if texto is None:
        resultado["erro"] = "Arquivo ausente ou ilegivel"
        return resultado

    resultado["ocorrencias_antes"]["insertId"] = contar_ocorrencias(texto, "insertId")
    resultado["ocorrencias_antes"]["UPDATE_LIMIT_1"] = len(scan_update_limit_admin(texto))

    novo = texto

    novo = adicionar_returning_id_em_insert_empresas(novo, resultado)

    substituicoes = [
        (
            "const empId = resEmp.insertId;",
            "const empId = resEmp.rows[0].id;"
        ),
        (
            "UPDATE usuarios_painel SET senha = ? WHERE empresa_id = ? AND is_admin = 1 LIMIT 1",
            "UPDATE usuarios_painel SET senha = ? WHERE empresa_id = ? AND is_admin = 1"
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
    resultado["ocorrencias_depois"]["insertId"] = contar_ocorrencias(texto_depois, "insertId")
    resultado["ocorrencias_depois"]["UPDATE_LIMIT_1"] = len(scan_update_limit_admin(texto_depois))
    resultado["sha256_depois"] = sha256_arquivo(path)

    return resultado


def scan_update_limit_admin(texto):
    achados = []

    if texto is None:
        return achados

    for numero, linha in enumerate(texto.splitlines(), start=1):
        upper = linha.upper()
        if "UPDATE" in upper and "LIMIT 1" in upper:
            achados.append({
                "linha": numero,
                "trecho": linha.strip()[:240]
            })

    return achados


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
            "stderr": proc.stderr.strip()[:1500]
        }
    except Exception as exc:
        return {
            "arquivo": nome,
            "existe": True,
            "ok": False,
            "erro": str(exc)
        }


def grep_validacao_final():
    path = ROOT / ARQUIVO_ALVO
    texto = ler_texto(path)

    resultado = {
        "insertId": [],
        "update_limit_1": [],
        "select_limit_1": []
    }

    if texto is None:
        return resultado

    for numero, linha in enumerate(texto.splitlines(), start=1):
        upper = linha.upper()

        if "INSERTID" in upper:
            resultado["insertId"].append({
                "linha": numero,
                "trecho": linha.strip()[:240]
            })

        if "LIMIT 1" in upper and "UPDATE" in upper:
            resultado["update_limit_1"].append({
                "linha": numero,
                "trecho": linha.strip()[:240]
            })

        if "LIMIT 1" in upper and "SELECT" in upper:
            resultado["select_limit_1"].append({
                "linha": numero,
                "trecho": linha.strip()[:240]
            })

    return resultado


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_08_1_INICIO -->"
    marcador_fim = "<!-- ETAPA_08_1_FIM -->"

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
    criticos = relatorio["validacao_final"]
    total_criticos = (
        len(criticos["insertId"]) +
        len(criticos["update_limit_1"])
    )
    node_ok = str(relatorio["node_check"]["ok"])

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 08.1 - AdminController PostgreSQL",
        [
            "Data: " + data,
            "",
            "Foram corrigidos os padroes restantes no AdminController.",
            "O insert de empresa passou a retornar id via RETURNING id.",
            "A leitura de id deixou de usar insertId.",
            "O update de senha deixou de usar LIMIT em comando UPDATE.",
            "Padroes criticos restantes no AdminController: " + str(total_criticos) + ".",
            "Node check do arquivo alterado OK: " + node_ok + "."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 08.1 - Correcao final do AdminController",
        [
            "Data: " + data,
            "",
            "Adicionado RETURNING id no insert de empresas.",
            "Substituido uso de insertId por retorno de rows.",
            "Removido LIMIT de UPDATE de senha.",
            "Executado node --check no AdminController.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 08.1 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido usar RETURNING id para capturar identificadores em PostgreSQL.",
            "Decidido remover LIMIT de comandos UPDATE por incompatibilidade com PostgreSQL.",
            "Decidido considerar SELECT com LIMIT como valido e fora do escopo desta correcao."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Executar testes funcionais de criacao e edicao de empresas.",
        "Executar testes funcionais de alteracao de senha do admin da empresa.",
        "Validar telas do CRM que usam consultas com SELECT LIMIT.",
        "Revisar achados de baixa severidade, especialmente booleanos numericos.",
        "Planejar hardening de seguranca HTTP, CORS, rate limit e sessoes."
    ]

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 08.1",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    linhas.append("# Etapa 08.1 - Corrigir AdminController insertId e UPDATE LIMIT")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Padroes criticos antes: " + str(len(relatorio["scan_antes"])))
    linhas.append("- Padroes criticos depois: " + str(len(relatorio["scan_depois"])))
    linhas.append("- Node check OK: " + str(relatorio["node_check"]["ok"]))
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
            linhas.append("  - qtd=" + str(sub["quantidade"]) + ": " + sub["de"] + " -> " + sub["para"])
    else:
        linhas.append("- Substituicoes: nenhuma")

    linhas.append("")
    linhas.append("## Node check")
    linhas.append("")
    nc = relatorio["node_check"]
    linhas.append("- " + nc["arquivo"] + ": ok=" + str(nc["ok"]))
    if not nc.get("ok"):
        detalhe = nc.get("stderr") or nc.get("erro") or "Falha sem detalhe"
        detalhe = detalhe.replace(chr(42), "[asterisco]")
        linhas.append("  - detalhe: " + detalhe[:500])

    linhas.append("")
    linhas.append("## Validacao final")
    linhas.append("")
    vf = relatorio["validacao_final"]
    linhas.append("- insertId restante: " + str(len(vf["insertId"])))
    linhas.append("- UPDATE com LIMIT 1 restante: " + str(len(vf["update_limit_1"])))
    linhas.append("- SELECT com LIMIT 1 encontrado, valido em PostgreSQL: " + str(len(vf["select_limit_1"])))

    if vf["insertId"] or vf["update_limit_1"]:
        linhas.append("")
        linhas.append("### Pendencias criticas restantes")
        for item in vf["insertId"]:
            linhas.append("- insertId linha " + str(item["linha"]) + ": " + item["trecho"])
        for item in vf["update_limit_1"]:
            linhas.append("- UPDATE LIMIT linha " + str(item["linha"]) + ": " + item["trecho"])
    else:
        linhas.append("- Nenhum padrao critico restante no AdminController.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 09: executar testes funcionais controlados nas rotas e telas afetadas.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_08_1_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_08_1_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    scan_antes = scan_critico_admin()
    correcao = corrigir_admin_controller()
    node_resultado = node_check_arquivo(ARQUIVO_ALVO)
    scan_depois = scan_critico_admin()
    validacao_final = grep_validacao_final()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "scan_antes": scan_antes,
        "correcao": correcao,
        "node_check": node_resultado,
        "scan_depois": scan_depois,
        "validacao_final": validacao_final
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_08_1_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_08_1_corrigir_admin_insertid_update_limit.json"
    md_path = REPORTS_DIR / "etapa_08_1_corrigir_admin_insertid_update_limit.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    total_criticos = (
        len(validacao_final["insertId"]) +
        len(validacao_final["update_limit_1"])
    )

    print("Etapa 08.1 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Node check OK: " + str(node_resultado["ok"]))
    print("Padroes criticos restantes: " + str(total_criticos))
    print("SELECT LIMIT 1 validos encontrados: " + str(len(validacao_final["select_limit_1"])))

    if total_criticos > 0:
        print("")
        print("Ainda existem padroes criticos:")
        for item in validacao_final["insertId"]:
            print("- insertId linha " + str(item["linha"]))
        for item in validacao_final["update_limit_1"]:
            print("- UPDATE LIMIT linha " + str(item["linha"]))


if __name__ == "__main__":
    main()