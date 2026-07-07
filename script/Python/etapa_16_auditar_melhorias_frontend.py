#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 16 - Auditar frontend e preparar melhorias

Objetivo:
- Criar backup documental.
- Gerar manifesto antes e depois.
- Auditar arquivos em views, public, routes e arquivos principais.
- Identificar CDNs e dependencias externas.
- Identificar scripts, CSS, imagens e links externos.
- Identificar estilos inline e scripts inline.
- Identificar assets locais referenciados.
- Verificar existencia basica de assets locais.
- Gerar recomendacoes de melhoria visual e tecnica.
- Nao alterar frontend nesta etapa.
- Nao alterar banco.
- Nao reiniciar app.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Gerar relatorios JSON e Markdown em reports.

Como executar:
python3 etapa_16_auditar_melhorias_frontend.py
"""

import os
import re
import json
import shutil
import hashlib
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path.cwd()
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

DIRETORIOS_FRONTEND = [
    "views",
    "public",
    "routes"
]

ARQUIVOS_EXTRAS = [
    "server.js",
    "package.json",
    "tailwind.config.js",
    "postcss.config.js"
]

EXTENSOES_ANALISE = [
    ".ejs",
    ".html",
    ".css",
    ".js",
    ".json"
]

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
    "PENDENCIAS.md"
]

IGNORAR_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "auth_sessions",
    "reports",
    "__pycache__"
]


class ExtratorHTML(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.refs = []
        self.tags_script = 0
        self.tags_style = 0
        self.attrs_style = 0

    def handle_starttag(self, tag, attrs):
        tag_lower = str(tag or "").lower()

        if tag_lower == "script":
            self.tags_script += 1

        if tag_lower == "style":
            self.tags_style += 1

        for nome, valor in attrs:
            nome_lower = str(nome or "").lower()
            valor_str = str(valor or "").strip()

            if nome_lower == "style":
                self.attrs_style += 1

            if nome_lower in ["href", "src", "action"]:
                if valor_str:
                    self.refs.append(valor_str)


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
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def gravar_texto(path, conteudo):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8")


def validar_sem_asterisco_indevido(conteudo, nome):
    if chr(42) in conteudo:
        raise ValueError("Validacao bloqueou " + nome + " por conter asterisco.")


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


def salvar_json(path, dados):
    texto = json.dumps(dados, ensure_ascii=False, indent=2) + "\n"
    texto = texto.replace(chr(42), "[asterisco]")
    gravar_texto(path, texto)


def deve_ignorar(path):
    partes = set(path.parts)

    for nome in IGNORAR_DIRS:
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


def copiar_item(origem, destino):
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

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def arquivo_eh_analisavel(path):
    if not path.is_file():
        return False

    return path.suffix.lower() in EXTENSOES_ANALISE


def listar_arquivos_frontend():
    arquivos = []

    for nome_dir in DIRETORIOS_FRONTEND:
        base = ROOT / nome_dir

        if not base.exists():
            continue

        for p in base.rglob("*"):
            if deve_ignorar(p):
                continue

            if arquivo_eh_analisavel(p):
                arquivos.append(p)

    for nome in ARQUIVOS_EXTRAS:
        p = ROOT / nome
        if p.exists() and arquivo_eh_analisavel(p):
            arquivos.append(p)

    unicos = []
    vistos = set()

    for p in arquivos:
        rp = rel(p)
        if rp not in vistos:
            vistos.add(rp)
            unicos.append(p)

    return sorted(unicos)


def classificar_url(url):
    valor = str(url or "").strip()
    host = urlparse(valor).netloc.lower()
    lower = valor.lower()

    if not host:
        return "local"

    if "tailwindcss" in host:
        return "tailwind_cdn"

    if "cdnjs.cloudflare.com" in host:
        return "cdnjs_cdn"

    if "font-awesome" in lower or "fontawesome" in lower:
        return "fontawesome_cdn"

    if "cdn.jsdelivr.net" in host:
        return "jsdelivr_cdn"

    if "unpkg.com" in host:
        return "unpkg_cdn"

    if "alpinejs" in lower:
        return "alpine_cdn"

    if "githubusercontent.com" in host:
        return "imagem_externa"

    if lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "imagem_externa"

    if lower.endswith(".webp") or lower.endswith(".svg") or lower.endswith(".gif"):
        return "imagem_externa"

    return "externo"


def extrair_refs_css(texto):
    refs = []

    for m in re.finditer(r"url\(([^)]+)\)", texto, flags=re.IGNORECASE):
        valor = m.group(1).strip().strip("'").strip('"')
        if valor:
            refs.append(valor)

    return refs


def extrair_urls_http(texto):
    urls = []

    for m in re.finditer(r"https?://[^\s\"'<>\\)]+", texto, flags=re.IGNORECASE):
        valor = m.group(0).strip()
        if valor:
            urls.append(valor)

    return urls


def extrair_imports_js(texto):
    refs = []

    padroes = [
        r"import\s+[^\"']+[\"']",
        r"import\s+[^\"']+[\"']",
        r"require\(\s*[^\"']+[\"']\s*\)"
    ]

    for padrao in padroes:
        try:
            encontrados = re.findall(padrao, texto, flags=re.IGNORECASE)
        except Exception:
            encontrados = []

        for valor in encontrados:
            valor = str(valor or "").strip()
            if valor:
                refs.append(valor)

    unicos = []
    vistos = set()

    for ref in refs:
        if ref not in vistos:
            vistos.add(ref)
            unicos.append(ref)

    return unicos
def extrair_referencias(texto, extensao):
    refs = []

    if extensao in [".html", ".ejs"]:
        parser = ExtratorHTML()
        try:
            parser.feed(texto)
            refs.extend(parser.refs)
        except Exception:
            pass

    refs.extend(extrair_refs_css(texto))
    refs.extend(extrair_urls_http(texto))
    refs.extend(extrair_imports_js(texto))

    unicos = []
    vistos = set()

    for ref in refs:
        if ref not in vistos:
            vistos.add(ref)
            unicos.append(ref)

    return unicos


def normalizar_local_referencia(valor):
    ref = str(valor or "").strip()

    if not ref:
        return ""

    if ref.startswith("#"):
        return ""

    if ref.startswith("mailto:"):
        return ""

    if ref.startswith("tel:"):
        return ""

    if ref.startswith("javascript:"):
        return ""

    if ref.startswith("http://") or ref.startswith("https://"):
        return ""

    if ref.startswith("//"):
        return ""

    if ref.startswith("data:"):
        return ""

    return ref


def verificar_asset_local(valor, arquivo_origem):
    ref = normalizar_local_referencia(valor)

    if not ref:
        return None

    candidatos = []

    if ref.startswith("/"):
        candidatos.append(ROOT / "public" / ref.lstrip("/"))
        candidatos.append(ROOT / ref.lstrip("/"))
    else:
        candidatos.append(arquivo_origem.parent / ref)
        candidatos.append(ROOT / "public" / ref)
        candidatos.append(ROOT / ref)

    existe = False
    caminho_encontrado = ""

    for c in candidatos:
        if c.exists():
            existe = True
            caminho_encontrado = rel(c)
            break

    return {
        "referencia": valor,
        "normalizada": ref,
        "existe": existe,
        "caminho_encontrado": caminho_encontrado
    }


def contar_ocorrencias(texto, extensao):
    lower = texto.lower()

    cont = {
        "tags_script": 0,
        "tags_style": 0,
        "atributo_style": 0,
        "tailwind_cdn": lower.count("cdn.tailwindcss.com"),
        "fontawesome_cdn": lower.count("font-awesome") + lower.count("fontawesome"),
        "alpine_cdn": lower.count("alpinejs") + lower.count("cdn.jsdelivr.net/npm/alpinejs"),
        "socket_io": lower.count("socket.io"),
        "fetch_calls": lower.count("fetch("),
        "axios_calls": lower.count("axios."),
        "cdn_mentions": lower.count("cdn."),
        "http_externo": lower.count("https://") + lower.count("http://")
    }

    if extensao in [".html", ".ejs"]:
        parser = ExtratorHTML()
        try:
            parser.feed(texto)
            cont["tags_script"] = parser.tags_script
            cont["tags_style"] = parser.tags_style
            cont["atributo_style"] = parser.attrs_style
        except Exception:
            cont["tags_script"] = lower.count("<script")
            cont["tags_style"] = lower.count("<style")
            cont["atributo_style"] = lower.count(" style=")

    return cont


def auditar_arquivo(path):
    texto = ler_texto(path)

    item = {
        "arquivo": rel(path),
        "extensao": path.suffix.lower(),
        "tamanho_bytes": path.stat().st_size if path.exists() else None,
        "referencias": [],
        "externos": [],
        "locais": [],
        "assets_locais": [],
        "contagens": {}
    }

    if texto is None:
        item["erro"] = "Arquivo ilegivel"
        return item

    refs = extrair_referencias(texto, item["extensao"])
    item["contagens"] = contar_ocorrencias(texto, item["extensao"])

    for ref in refs:
        tipo = classificar_url(ref)

        registro = {
            "referencia": ref,
            "tipo": tipo
        }

        item["referencias"].append(registro)

        if tipo == "local":
            item["locais"].append(ref)
            asset = verificar_asset_local(ref, path)
            if asset:
                item["assets_locais"].append(asset)
        else:
            item["externos"].append(registro)

    return item


def consolidar_auditoria(itens):
    resumo = {
        "total_arquivos": len(itens),
        "arquivos_por_extensao": {},
        "total_referencias": 0,
        "total_externos": 0,
        "total_locais": 0,
        "externos_por_tipo": {},
        "externos_unicos": [],
        "assets_locais_total": 0,
        "assets_locais_ausentes": [],
        "arquivos_com_script_inline": [],
        "arquivos_com_style_inline": [],
        "arquivos_com_tailwind_cdn": [],
        "arquivos_com_fontawesome_cdn": [],
        "arquivos_com_alpine_cdn": [],
        "arquivos_com_fetch": [],
        "arquivos_com_socket": []
    }

    externos_vistos = set()

    for item in itens:
        ext = item.get("extensao") or ""
        resumo["arquivos_por_extensao"][ext] = resumo["arquivos_por_extensao"].get(ext, 0) + 1

        referencias = item.get("referencias") or []
        externos = item.get("externos") or []
        locais = item.get("locais") or []
        assets = item.get("assets_locais") or []
        cont = item.get("contagens") or {}

        resumo["total_referencias"] += len(referencias)
        resumo["total_externos"] += len(externos)
        resumo["total_locais"] += len(locais)
        resumo["assets_locais_total"] += len(assets)

        for e in externos:
            tipo = e.get("tipo")
            resumo["externos_por_tipo"][tipo] = resumo["externos_por_tipo"].get(tipo, 0) + 1
            ref = e.get("referencia")
            chave = tipo + "|" + str(ref)

            if ref and chave not in externos_vistos:
                externos_vistos.add(chave)
                resumo["externos_unicos"].append(e)

        for asset in assets:
            if not asset.get("existe"):
                resumo["assets_locais_ausentes"].append({
                    "arquivo": item["arquivo"],
                    "referencia": asset["referencia"]
                })

        if cont.get("tags_script", 0) > 0:
            resumo["arquivos_com_script_inline"].append(item["arquivo"])

        if cont.get("tags_style", 0) > 0 or cont.get("atributo_style", 0) > 0:
            resumo["arquivos_com_style_inline"].append(item["arquivo"])

        if cont.get("tailwind_cdn", 0) > 0:
            resumo["arquivos_com_tailwind_cdn"].append(item["arquivo"])

        if cont.get("fontawesome_cdn", 0) > 0:
            resumo["arquivos_com_fontawesome_cdn"].append(item["arquivo"])

        if cont.get("alpine_cdn", 0) > 0:
            resumo["arquivos_com_alpine_cdn"].append(item["arquivo"])

        if cont.get("fetch_calls", 0) > 0 or cont.get("axios_calls", 0) > 0:
            resumo["arquivos_com_fetch"].append(item["arquivo"])

        if cont.get("socket_io", 0) > 0:
            resumo["arquivos_com_socket"].append(item["arquivo"])

    return resumo


def gerar_recomendacoes(resumo):
    recomendacoes = []

    if resumo["total_externos"] > 0:
        recomendacoes.append({
            "prioridade": "alta",
            "tema": "Dependencias externas",
            "acao": "Planejar internalizacao gradual dos assets externos criticos."
        })

    if resumo["arquivos_com_tailwind_cdn"]:
        recomendacoes.append({
            "prioridade": "alta",
            "tema": "Tailwind CDN",
            "acao": "Planejar build local do Tailwind com cuidado para preservar layout atual."
        })

    if resumo["arquivos_com_fontawesome_cdn"]:
        recomendacoes.append({
            "prioridade": "media",
            "tema": "Icones externos",
            "acao": "Substituir FontAwesome CDN por pacote local ou SVGs internos."
        })

    if resumo["arquivos_com_alpine_cdn"]:
        recomendacoes.append({
            "prioridade": "media",
            "tema": "Alpine externo",
            "acao": "Servir Alpine localmente por public/vendor ou pacote instalado."
        })

    if resumo["assets_locais_ausentes"]:
        recomendacoes.append({
            "prioridade": "alta",
            "tema": "Assets locais ausentes",
            "acao": "Corrigir referencias locais ausentes antes de aplicar melhoria visual."
        })

    if resumo["arquivos_com_style_inline"]:
        recomendacoes.append({
            "prioridade": "media",
            "tema": "CSS inline",
            "acao": "Extrair estilos repetidos para public/css em etapa futura."
        })

    if resumo["arquivos_com_script_inline"]:
        recomendacoes.append({
            "prioridade": "media",
            "tema": "Scripts inline",
            "acao": "Mapear scripts inline antes de aplicar CSP forte."
        })

    recomendacoes.append({
        "prioridade": "alta",
        "tema": "Primeira melhoria visual",
        "acao": "Aplicar melhoria controlada na tela de login antes de mexer no dashboard."
    })

    return recomendacoes


def auditar_frontend():
    arquivos = listar_arquivos_frontend()
    detalhes = []

    for p in arquivos:
        detalhes.append(auditar_arquivo(p))

    resumo = consolidar_auditoria(detalhes)
    recomendacoes = gerar_recomendacoes(resumo)

    return {
        "arquivos_analisados": [rel(p) for p in arquivos],
        "detalhes": detalhes,
        "resumo": resumo,
        "recomendacoes": recomendacoes
    }


def acrescentar_secao_documento(nome, titulo, corpo):
    path = ROOT / nome
    texto_atual = ler_texto(path)

    if texto_atual is None:
        texto_atual = "# " + nome.replace(".md", "") + "\n"

    marcador_inicio = "<!-- ETAPA_16_INICIO -->"
    marcador_fim = "<!-- ETAPA_16_FIM -->"

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
    resumo = relatorio["auditoria_frontend"]["resumo"]

    acrescentar_secao_documento(
        "CONTEXTO_PROJETO.md",
        "Etapa 16 - Auditoria frontend e melhorias",
        [
            "Data: " + data,
            "",
            "Foi executada auditoria do frontend sem alterar telas ou regras de negocio.",
            "Arquivos analisados: " + str(resumo["total_arquivos"]) + ".",
            "Referencias externas encontradas: " + str(resumo["total_externos"]) + ".",
            "Referencias locais encontradas: " + str(resumo["total_locais"]) + ".",
            "Assets locais ausentes: " + str(len(resumo["assets_locais_ausentes"])) + ".",
            "Arquivos com Tailwind CDN: " + str(len(resumo["arquivos_com_tailwind_cdn"])) + ".",
            "Arquivos com FontAwesome CDN: " + str(len(resumo["arquivos_com_fontawesome_cdn"])) + ".",
            "Arquivos com Alpine CDN: " + str(len(resumo["arquivos_com_alpine_cdn"])) + ".",
            "Nenhuma alteracao foi aplicada ao frontend nesta etapa."
        ]
    )

    acrescentar_secao_documento(
        "CHANGELOG.md",
        "Etapa 16 - Auditoria frontend",
        [
            "Data: " + data,
            "",
            "Mapeados arquivos de frontend em views, public, routes e arquivos principais.",
            "Identificadas dependencias externas e CDNs.",
            "Identificados estilos e scripts inline.",
            "Identificados assets locais referenciados.",
            "Gerados relatorios JSON e Markdown da auditoria."
        ]
    )

    acrescentar_secao_documento(
        "DECISOES_TECNICAS.md",
        "Etapa 16 - Decisoes tecnicas frontend",
        [
            "Data: " + data,
            "",
            "Decidido auditar antes de alterar telas.",
            "Decidido separar melhorias visuais de internalizacao de dependencias.",
            "Decidido iniciar melhorias futuras por login e dashboard.",
            "Decidido tratar Tailwind CDN com cautela para evitar quebra de layout."
        ]
    )

    pendencias = [
        "Data: " + data,
        "",
        "Definir primeira melhoria visual controlada para a tela de login.",
        "Planejar internalizacao gradual de dependencias externas.",
        "Avaliar substituicao de FontAwesome CDN por assets locais.",
        "Avaliar Alpine local em public/vendor.",
        "Planejar build local do Tailwind sem quebrar classes existentes.",
        "Mapear scripts inline antes de aplicar CSP forte."
    ]

    if resumo["assets_locais_ausentes"]:
        pendencias.insert(2, "Corrigir referencias locais ausentes identificadas na auditoria.")

    acrescentar_secao_documento(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 16",
        pendencias
    )

    return DOCS_OBRIGATORIOS


def gerar_markdown_relatorio(relatorio):
    auditoria = relatorio["auditoria_frontend"]
    resumo = auditoria["resumo"]

    linhas = []

    linhas.append("# Etapa 16 - Auditar frontend e preparar melhorias")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup documental criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivos analisados: " + str(resumo["total_arquivos"]))
    linhas.append("- Referencias totais: " + str(resumo["total_referencias"]))
    linhas.append("- Referencias externas: " + str(resumo["total_externos"]))
    linhas.append("- Referencias locais: " + str(resumo["total_locais"]))
    linhas.append("- Assets locais referenciados: " + str(resumo["assets_locais_total"]))
    linhas.append("- Assets locais ausentes: " + str(len(resumo["assets_locais_ausentes"])))
    linhas.append("- Arquivos com Tailwind CDN: " + str(len(resumo["arquivos_com_tailwind_cdn"])))
    linhas.append("- Arquivos com FontAwesome CDN: " + str(len(resumo["arquivos_com_fontawesome_cdn"])))
    linhas.append("- Arquivos com Alpine CDN: " + str(len(resumo["arquivos_com_alpine_cdn"])))
    linhas.append("- Arquivos com scripts inline: " + str(len(resumo["arquivos_com_script_inline"])))
    linhas.append("- Arquivos com estilos inline: " + str(len(resumo["arquivos_com_style_inline"])))
    linhas.append("")

    linhas.append("## Arquivos analisados")
    linhas.append("")
    for arquivo in auditoria["arquivos_analisados"]:
        linhas.append("- " + arquivo)

    linhas.append("")
    linhas.append("## Dependencias externas unicas")
    linhas.append("")
    if resumo["externos_unicos"]:
        for item in resumo["externos_unicos"]:
            linhas.append("- tipo=" + item["tipo"] + " referencia=" + item["referencia"])
    else:
        linhas.append("- Nenhuma dependencia externa encontrada.")

    linhas.append("")
    linhas.append("## Externos por tipo")
    linhas.append("")
    if resumo["externos_por_tipo"]:
        for chave, valor in sorted(resumo["externos_por_tipo"].items()):
            linhas.append("- " + chave + ": " + str(valor))
    else:
        linhas.append("- Nenhum externo por tipo.")

    linhas.append("")
    linhas.append("## Assets locais ausentes")
    linhas.append("")
    if resumo["assets_locais_ausentes"]:
        for item in resumo["assets_locais_ausentes"]:
            linhas.append("- arquivo=" + item["arquivo"] + " referencia=" + item["referencia"])
    else:
        linhas.append("- Nenhum asset local ausente identificado.")

    linhas.append("")
    linhas.append("## Arquivos com CDN")
    linhas.append("")
    linhas.append("### Tailwind")
    if resumo["arquivos_com_tailwind_cdn"]:
        for item in resumo["arquivos_com_tailwind_cdn"]:
            linhas.append("- " + item)
    else:
        linhas.append("- Nenhum arquivo com Tailwind CDN.")

    linhas.append("")
    linhas.append("### FontAwesome")
    if resumo["arquivos_com_fontawesome_cdn"]:
        for item in resumo["arquivos_com_fontawesome_cdn"]:
            linhas.append("- " + item)
    else:
        linhas.append("- Nenhum arquivo com FontAwesome CDN.")

    linhas.append("")
    linhas.append("### Alpine")
    if resumo["arquivos_com_alpine_cdn"]:
        for item in resumo["arquivos_com_alpine_cdn"]:
            linhas.append("- " + item)
    else:
        linhas.append("- Nenhum arquivo com Alpine CDN.")

    linhas.append("")
    linhas.append("## Arquivos com scripts inline")
    linhas.append("")
    if resumo["arquivos_com_script_inline"]:
        for item in resumo["arquivos_com_script_inline"]:
            linhas.append("- " + item)
    else:
        linhas.append("- Nenhum script inline identificado.")

    linhas.append("")
    linhas.append("## Arquivos com estilos inline")
    linhas.append("")
    if resumo["arquivos_com_style_inline"]:
        for item in resumo["arquivos_com_style_inline"]:
            linhas.append("- " + item)
    else:
        linhas.append("- Nenhum estilo inline identificado.")

    linhas.append("")
    linhas.append("## Recomendacoes")
    linhas.append("")
    for rec in auditoria["recomendacoes"]:
        linhas.append("- prioridade=" + rec["prioridade"] + " tema=" + rec["tema"] + " acao=" + rec["acao"])

    linhas.append("")
    linhas.append("## Observacoes")
    linhas.append("")
    linhas.append("- Nenhuma tela foi alterada nesta etapa.")
    linhas.append("- Nenhuma regra de negocio foi alterada.")
    linhas.append("- Nenhum banco foi alterado.")
    linhas.append("- Nenhum container foi reiniciado.")
    linhas.append("- Esta etapa prepara melhorias visuais controladas.")

    linhas.append("")
    linhas.append("## Documentacao atualizada")
    linhas.append("")
    for nome in relatorio["documentacao_atualizada"]:
        linhas.append("- " + nome)

    linhas.append("")
    linhas.append("## Proxima etapa recomendada")
    linhas.append("")
    linhas.append("- Etapa 17: aplicar melhoria visual controlada na tela de login, com backup, validacao e rollback.")
    linhas.append("")

    conteudo = "\n".join(linhas) + "\n"
    conteudo = conteudo.replace(chr(42), "[asterisco]")
    validar_sem_asterisco_indevido(conteudo, "relatorio markdown")
    return conteudo


def main():
    garantir_dirs()

    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_16_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_16_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    auditoria = auditar_frontend()

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "auditoria_frontend": auditoria
    }

    documentacao = atualizar_documentacao(relatorio)
    relatorio["documentacao_atualizada"] = documentacao

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_16_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_16_auditar_melhorias_frontend.json"
    md_path = REPORTS_DIR / "etapa_16_auditar_melhorias_frontend.md"

    salvar_json(json_path, relatorio)
    gravar_texto(md_path, gerar_markdown_relatorio(relatorio))

    resumo = auditoria["resumo"]

    print("Etapa 16 concluida.")
    print("Backup documental: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Arquivos analisados: " + str(resumo["total_arquivos"]))
    print("Referencias externas: " + str(resumo["total_externos"]))
    print("Referencias locais: " + str(resumo["total_locais"]))
    print("Assets locais ausentes: " + str(len(resumo["assets_locais_ausentes"])))
    print("Arquivos com Tailwind CDN: " + str(len(resumo["arquivos_com_tailwind_cdn"])))
    print("Arquivos com FontAwesome CDN: " + str(len(resumo["arquivos_com_fontawesome_cdn"])))
    print("Arquivos com Alpine CDN: " + str(len(resumo["arquivos_com_alpine_cdn"])))
    print("Arquivos com scripts inline: " + str(len(resumo["arquivos_com_script_inline"])))
    print("Arquivos com estilos inline: " + str(len(resumo["arquivos_com_style_inline"])))
    print("")
    print("Nenhuma tela foi alterada nesta etapa.")


if __name__ == "__main__":
    main()