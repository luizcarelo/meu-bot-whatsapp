#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 07 - Validar schema e migration PostgreSQL

Objetivo:
- Criar backup antes de alterar.
- Gerar manifesto antes e depois.
- Procurar arquivos de schema e migrations existentes.
- Auditar existencia da tabela contatos em arquivos locais.
- Auditar existencia de indice ou constraint unica para empresa_id e telefone.
- Criar migration PostgreSQL idempotente se a constraint ou indice nao for encontrado.
- Nao executar a migration automaticamente.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Escopo:
- Nao executa banco.
- Nao executa Docker.
- Nao altera .env.
- Nao altera controllers.
- Nao altera managers.
- Cria apenas arquivo de migration se necessario.
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

MAX_LEITURA = 3145728

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

ARQUIVOS_BACKUP_DIRETO = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md",
    "setup_db.js",
    "schema.sql",
    "init.sql"
]

DIRS_SCHEMA = [
    "migrations",
    "database",
    "db",
    "sql",
    "scripts",
    "script"
]

EXTENSOES_SCHEMA = [
    ".sql",
    ".js",
    ".md",
    ".txt"
]

IGNORAR_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "public/uploads",
    "reports"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_data():
    return datetime.now().strftime("%Y%m%d")


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


def deve_ignorar(path):
    partes = set(path.parts)
    for nome in IGNORAR_DIRS:
        sub = nome.split("/")
        if len(sub) == 1 and sub[0] in partes:
            return True
        rel_path = rel(path)
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
            if deve_ignorar(p):
                continue
            novos_dirs.append(nome_dir)

        dirs[:] = novos_dirs

        for nome in files:
            p = base_path / nome
            if deve_ignorar(p):
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


def copiar_item(origem, destino):
    if origem.is_dir():
        shutil.copytree(origem, destino, dirs_exist_ok=True)
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)


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
            copiar_item(origem, destino_item)
            copiados.append(nome)
        except Exception as exc:
            erros.append({
                "item": nome,
                "erro": str(exc)
            })

    for nome_dir in DIRS_SCHEMA:
        origem_dir = ROOT / nome_dir
        destino_dir = destino / nome_dir

        if not origem_dir.exists() or not origem_dir.is_dir():
            continue

        try:
            copiar_item(origem_dir, destino_dir)
            copiados.append(nome_dir + "/")
        except Exception as exc:
            erros.append({
                "item": nome_dir,
                "erro": str(exc)
            })

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def listar_arquivos_schema():
    encontrados = {}

    candidatos_raiz = [
        "setup_db.js",
        "schema.sql",
        "init.sql"
    ]

    for nome in candidatos_raiz:
        p = ROOT / nome
        if p.exists() and p.is_file():
            encontrados[rel(p)] = p

    for nome_dir in DIRS_SCHEMA:
        base = ROOT / nome_dir
        if not base.exists() or not base.is_dir():
            continue

        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if deve_ignorar(p):
                continue
            if p.suffix.lower() in EXTENSOES_SCHEMA:
                encontrados[rel(p)] = p

    return [encontrados[k] for k in sorted(encontrados.keys())]


def normalizar_sql(texto):
    return re.sub(r"\s+", " ", texto.lower())


def arquivo_tem_contatos(texto):
    if texto is None:
        return False

    lower = texto.lower()

    if re.search(r"\bcreate\s+table\s+(if\s+not\s+exists\s+)?contatos\b", lower):
        return True

    if re.search(r"\bcreate\s+table\s+(if\s+not\s+exists\s+)?public\.contatos\b", lower):
        return True

    if " contatos " in (" " + lower + " "):
        return True

    return False


def arquivo_tem_unico_empresa_telefone(texto):
    if texto is None:
        return False

    normal = normalizar_sql(texto)

    padroes = [
        r"unique\s*\(\s*empresa_id\s*,\s*telefone\s*\)",
        r"unique\s+index\s+.*?\s+on\s+contatos\s*\(\s*empresa_id\s*,\s*telefone\s*\)",
        r"create\s+unique\s+index\s+.*?\s+on\s+contatos\s*\(\s*empresa_id\s*,\s*telefone\s*\)",
        r"create\s+unique\s+index\s+.*?\s+on\s+public\.contatos\s*\(\s*empresa_id\s*,\s*telefone\s*\)",
        r"constraint\s+.*?\s+unique\s*\(\s*empresa_id\s*,\s*telefone\s*\)"
    ]

    for padrao in padroes:
        if re.search(padrao, normal, flags=re.IGNORECASE):
            return True

    return False


def encontrar_linhas(texto, termos):
    achados = []

    if texto is None:
        return achados

    linhas = texto.splitlines()

    for numero, linha in enumerate(linhas, start=1):
        lower = linha.lower()
        for termo in termos:
            if termo.lower() in lower:
                achados.append({
                    "linha": numero,
                    "termo": termo,
                    "trecho": linha.strip()[:220]
                })

    return achados


def auditar_schema():
    arquivos = listar_arquivos_schema()

    resultados = []
    encontrou_contatos = False
    encontrou_unico = False

    for path in arquivos:
        texto = ler_texto(path)
        tem_contatos = arquivo_tem_contatos(texto)
        tem_unico = arquivo_tem_unico_empresa_telefone(texto)

        if tem_contatos:
            encontrou_contatos = True

        if tem_unico:
            encontrou_unico = True

        resultados.append({
            "arquivo": rel(path),
            "tamanho_bytes": path.stat().st_size,
            "tem_contatos": tem_contatos,
            "tem_unico_empresa_telefone": tem_unico,
            "linhas_relevantes": encontrar_linhas(
                texto,
                [
                    "contatos",
                    "empresa_id",
                    "telefone",
                    "unique",
                    "index"
                ]
            )[:30]
        })

    return {
        "arquivos_schema_encontrados": [rel(p) for p in arquivos],
        "total_arquivos_schema": len(arquivos),
        "encontrou_tabela_contatos": encontrou_contatos,
        "encontrou_unico_empresa_telefone": encontrou_unico,
        "detalhes": resultados
    }


def conteudo_migration_unico():
    conteudo = """-- Etapa 07 - Migration PostgreSQL
-- Objetivo: garantir suporte ao ON CONFLICT por empresa e telefone em contatos
-- Nao executar sem revisar duplicidades existentes antes

CREATE UNIQUE INDEX IF NOT EXISTS idx_contatos_empresa_telefone
ON contatos (empresa_id, telefone);
"""
    validar_sem_asterisco_indevido(conteudo, "migration contatos empresa telefone")
    return conteudo


def criar_migration_se_necessario(auditoria):
    resultado = {
        "necessaria": not auditoria["encontrou_unico_empresa_telefone"],
        "criada": False,
        "arquivo": None,
        "motivo": ""
    }

    if auditoria["encontrou_unico_empresa_telefone"]:
        resultado["motivo"] = "Indice ou constraint unica ja encontrada em arquivos locais"
        return resultado

    migrations_dir = ROOT / "database" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = agora_data() + "_add_unique_contatos_empresa_telefone.sql"
    path = migrations_dir / nome_arquivo

    if path.exists():
        resultado["arquivo"] = rel(path)
        resultado["criada"] = False
        resultado["motivo"] = "Arquivo de migration ja existia"
        return resultado

    conteudo = conteudo_migration_unico()
    gravar_texto(path, conteudo)

    resultado["arquivo"] = rel(path)
    resultado["criada"] = True
    resultado["motivo"] = "Indice ou constraint unica nao encontrada em arquivos locais"
    resultado["sha256_depois"] = sha256_arquivo(path)

    return resultado


def validar_migration(path_rel):
    if not path_rel:
        return {
            "ok": False,
            "motivo": "Nenhum arquivo informado"
        }

    path = ROOT / path_rel
    texto = ler_texto(path)

    if texto is None:
        return {
            "ok": False,
            "motivo": "Arquivo ausente ou ilegivel"
        }

    erros = []
    obrigatorios = [
        "CREATE UNIQUE INDEX IF NOT EXISTS",
        "idx_contatos_empresa_telefone",
        "ON contatos",
        "empresa_id",
        "telefone"
    ]

    for termo in obrigatorios:
        if termo not in texto:
            erros.append("Termo obrigatorio ausente: " + termo)

    proibidos = [
        "mysql",
        "ON DUPLICATE KEY",
        "INSERT IGNORE",
        "IFNULL"
    ]

    lower = texto.lower()
    for termo in proibidos:
        if termo.lower() in lower:
            erros.append("Termo proibido encontrado: " + termo)

    return {
        "ok": len(erros) == 0,
        "erros": erros
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_07_INICIO -->"
    marcador_fim = "<!-- ETAPA_07_FIM -->"

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
    auditoria = relatorio["auditoria_schema"]
    migration = relatorio["migration"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 07 - Schema PostgreSQL validado",
        [
            "Data: " + data,
            "",
            "Foi executada auditoria local de schema e migrations PostgreSQL.",
            "Arquivos de schema encontrados: " + str(auditoria["total_arquivos_schema"]) + ".",
            "Tabela contatos encontrada em arquivos locais: " + str(auditoria["encontrou_tabela_contatos"]) + ".",
            "Indice ou constraint unica por empresa e telefone encontrada: " + str(auditoria["encontrou_unico_empresa_telefone"]) + ".",
            "Migration criada: " + str(migration["criada"]) + ".",
            "Arquivo de migration: " + str(migration["arquivo"]) + ".",
            "A migration nao foi executada automaticamente."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 07 - Validacao de schema PostgreSQL",
        [
            "Data: " + data,
            "",
            "Auditados arquivos locais de schema e migrations.",
            "Verificada necessidade de indice unico para contatos por empresa e telefone.",
            "Gerada migration idempotente quando necessario.",
            "Gerados backup, manifestos e relatorios da etapa."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 07 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido suportar ON CONFLICT por indice unico em empresa_id e telefone.",
            "Decidido nao executar migration automaticamente.",
            "Decidido criar migration idempotente quando nao houver indice ou constraint detectado localmente.",
            "Decidido validar duplicidades existentes antes de aplicar a migration em producao."
        ]
    )

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 07",
        [
            "Data: " + data,
            "",
            "Antes de aplicar a migration, verificar se existem contatos duplicados por empresa_id e telefone.",
            "Executar a migration em ambiente controlado.",
            "Validar recebimento de mensagem criando contato novo.",
            "Validar recebimento de mensagem atualizando contato existente.",
            "Revisar queries de media severidade apontadas na Etapa 05."
        ]
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    linhas = []

    auditoria = relatorio["auditoria_schema"]
    migration = relatorio["migration"]

    linhas.append("# Etapa 07 - Validar schema PostgreSQL")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivos de schema encontrados: " + str(auditoria["total_arquivos_schema"]))
    linhas.append("- Tabela contatos encontrada: " + str(auditoria["encontrou_tabela_contatos"]))
    linhas.append("- Unico empresa_id e telefone encontrado: " + str(auditoria["encontrou_unico_empresa_telefone"]))
    linhas.append("- Migration necessaria: " + str(migration["necessaria"]))
    linhas.append("- Migration criada: " + str(migration["criada"]))
    linhas.append("- Arquivo migration: " + str(migration["arquivo"]))
    linhas.append("")

    linhas.append("## Arquivos de schema encontrados")
    linhas.append("")
    if auditoria["arquivos_schema_encontrados"]:
        for nome in auditoria["arquivos_schema_encontrados"]:
            linhas.append("- " + nome)
    else:
        linhas.append("- Nenhum arquivo de schema encontrado nos caminhos analisados.")

    linhas.append("")
    linhas.append("## Detalhes da auditoria")
    linhas.append("")
    for item in auditoria["detalhes"]:
        linhas.append("- " + item["arquivo"])
        linhas.append("  - tem_contatos: " + str(item["tem_contatos"]))
        linhas.append("  - tem_unico_empresa_telefone: " + str(item["tem_unico_empresa_telefone"]))
        if item["linhas_relevantes"]:
            for linha in item["linhas_relevantes"][:10]:
                trecho = linha["trecho"].replace(chr(42), "[asterisco]")
                linhas.append(
                    "  - linha "
                    + str(linha["linha"])
                    + " termo="
                    + linha["termo"]
                    + " trecho="
                    + trecho
                )

    linhas.append("")
    linhas.append("## Migration")
    linhas.append("")
    linhas.append("- Necessaria: " + str(migration["necessaria"]))
    linhas.append("- Criada: " + str(migration["criada"]))
    linhas.append("- Arquivo: " + str(migration["arquivo"]))
    linhas.append("- Motivo: " + migration["motivo"])

    linhas.append("")
    linhas.append("## Validacao da migration")
    linhas.append("")
    linhas.append("- OK: " + str(relatorio["validacao_migration"]["ok"]))
    if relatorio["validacao_migration"].get("erros"):
        for erro in relatorio["validacao_migration"]["erros"]:
            linhas.append("  - " + erro)

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 08: revisar queries de media severidade, especialmente agregacoes e retorno de inserts.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_07_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_07_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)

    auditoria = auditar_schema()
    migration = criar_migration_se_necessario(auditoria)
    validacao_migration = validar_migration(migration["arquivo"])

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "auditoria_schema": auditoria,
        "migration": migration,
        "validacao_migration": validacao_migration
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_07_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_07_validar_schema_postgres.json"
    md_path = REPORTS_DIR / "etapa_07_validar_schema_postgres.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    print("Etapa 07 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Arquivos schema encontrados: " + str(auditoria["total_arquivos_schema"]))
    print("Tabela contatos encontrada: " + str(auditoria["encontrou_tabela_contatos"]))
    print("Unico empresa_id telefone encontrado: " + str(auditoria["encontrou_unico_empresa_telefone"]))
    print("Migration criada: " + str(migration["criada"]))
    print("Migration arquivo: " + str(migration["arquivo"]))
    print("Validacao migration OK: " + str(validacao_migration["ok"]))

    if validacao_migration.get("erros"):
        print("")
        print("Erros na validacao da migration:")
        for erro in validacao_migration["erros"]:
            print("- " + erro)


if __name__ == "__main__":
    main()