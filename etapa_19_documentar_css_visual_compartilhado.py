#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import hashlib
import shutil
import json

ROOT = Path.cwd()
CSS_PATH = ROOT / "public" / "css" / "style.css"
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]


def agora():
    return datetime.now().isoformat(timespec="seconds")


def stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path):
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def sha256(path):
    if not path.exists():
        return None

    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            bloco = f.read(1048576)
            if not bloco:
                break
            h.update(bloco)

    return h.hexdigest()


def ler(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def gravar(path, texto):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def sem_asterisco(texto, nome):
    if chr(42) in texto:
        raise SystemExit("Bloqueado por conter asterisco em " + nome)


def backup_docs():
    destino = BACKUPS_DIR / ("etapa_19_docs_" + stamp())
    destino.mkdir(parents=True, exist_ok=True)

    copiados = []
    ausentes = []

    if CSS_PATH.exists():
        alvo_css = destino / "public" / "css" / "style.css"
        alvo_css.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CSS_PATH, alvo_css)
        copiados.append("public/css/style.css")
    else:
        ausentes.append("public/css/style.css")

    for nome in DOCS:
        origem = ROOT / nome
        if origem.exists():
            shutil.copy2(origem, destino / nome)
            copiados.append(nome)
        else:
            ausentes.append(nome)

    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes
    }


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    atual = ler(path)

    if not atual:
        atual = "# " + nome.replace(".md", "") + "\n"

    ini = "<!-- ETAPA_19_INICIO -->"
    fim = "<!-- ETAPA_19_FIM -->"

    bloco = []
    bloco.append("")
    bloco.append(ini)
    bloco.append("## " + titulo)
    bloco.append("")
    for linha in linhas:
        bloco.append(linha)
    bloco.append(fim)
    bloco.append("")

    novo_bloco = "\n".join(bloco)

    pos_ini = atual.find(ini)
    pos_fim = atual.find(fim)

    if pos_ini >= 0 and pos_fim >= pos_ini:
        pos_fim = pos_fim + len(fim)
        novo = atual[:pos_ini] + novo_bloco.strip() + atual[pos_fim:]
    else:
        if not atual.endswith("\n"):
            atual = atual + "\n"
        novo = atual + novo_bloco

    novo = novo.replace(chr(42), "")
    sem_asterisco(novo, nome)
    gravar(path, novo)


def validar_css():
    texto = ler(CSS_PATH)

    return {
        "arquivo": "public/css/style.css",
        "existe": CSS_PATH.exists(),
        "sha256": sha256(CSS_PATH),
        "tem_er_card": ".er-card" in texto,
        "tem_er_btn": ".er-btn" in texto,
        "tem_er_badge": ".er-badge" in texto,
        "tem_variaveis": "--er-red" in texto and "--er-bg" in texto,
        "sem_asterisco": chr(42) not in texto
    }


def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)

    validacao = validar_css()

    if not validacao["existe"]:
        raise SystemExit("Arquivo public/css/style.css nao encontrado.")

    if not validacao["sem_asterisco"]:
        raise SystemExit("Arquivo public/css/style.css contem asterisco.")

    backup = backup_docs()
    data = agora()

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Etapa 19 - CSS visual compartilhado",
        [
            "Data: " + data,
            "",
            "Foi criado public/css/style.css como base visual compartilhada.",
            "O arquivo define cores, cards, botoes, inputs, tabelas, badges e responsividade.",
            "Nenhuma view, backend, rota, autenticacao ou banco foi alterado nesta etapa.",
            "CSS existe: " + str(validacao["existe"]) + ".",
            "CSS sem asterisco: " + str(validacao["sem_asterisco"]) + ".",
            "SHA256: " + str(validacao["sha256"]) + "."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 19 - CSS compartilhado criado",
        [
            "Data: " + data,
            "",
            "Criado arquivo public/css/style.css.",
            "Adicionada base visual compartilhada para telas antigas.",
            "Nenhuma view foi modificada.",
            "Nenhum backend ou banco foi modificado."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 19 - Decisoes tecnicas frontend",
        [
            "Data: " + data,
            "",
            "Decidido criar CSS compartilhado antes de alterar views antigas.",
            "Decidido evitar seletor universal para reduzir efeito colateral.",
            "Decidido manter escopo visual por classes er.",
            "Decidido manter esta etapa limitada a CSS e documentacao."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 19",
        [
            "Data: " + data,
            "",
            "Validar visual de admin-panel, crm e super-admin no navegador.",
            "Planejar etapa para aplicar classes er de forma controlada nas views antigas.",
            "Planejar internalizacao de FontAwesome, Alpine, Tailwind e imagens externas.",
            "Mapear scripts inline antes de CSP forte."
        ]
    )

    relatorio = {
        "gerado_em": data,
        "backup": backup,
        "validacao_css": validacao,
        "documentacao_atualizada": DOCS
    }

    json_path = REPORTS_DIR / "etapa_19_documentar_css_visual_compartilhado.json"
    md_path = REPORTS_DIR / "etapa_19_documentar_css_visual_compartilhado.md"

    gravar(json_path, json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n")

    md = []
    md.append("# Etapa 19 - CSS visual compartilhado")
    md.append("")
    md.append("Data: " + data)
    md.append("")
    md.append("## Resumo")
    md.append("")
    md.append("- CSS existe: " + str(validacao["existe"]))
    md.append("- CSS sem asterisco: " + str(validacao["sem_asterisco"]))
    md.append("- Tem .er-card: " + str(validacao["tem_er_card"]))
    md.append("- Tem .er-btn: " + str(validacao["tem_er_btn"]))
    md.append("- Tem .er-badge: " + str(validacao["tem_er_badge"]))
    md.append("- Tem variaveis visuais: " + str(validacao["tem_variaveis"]))
    md.append("- SHA256: " + str(validacao["sha256"]))
    md.append("")
    md.append("## Backup")
    md.append("")
    md.append("- Destino: " + backup["destino"])
    md.append("")
    md.append("## Observacoes")
    md.append("")
    md.append("- Nenhuma view foi alterada.")
    md.append("- Nenhum backend foi alterado.")
    md.append("- Nenhum banco foi alterado.")
    md.append("- Esta etapa aplicou somente CSS e documentacao.")
    md.append("")
    md.append("## Documentacao atualizada")
    md.append("")
    for nome in DOCS:
        md.append("- " + nome)

    md_texto = "\n".join(md) + "\n"
    sem_asterisco(md_texto, "relatorio markdown")
    gravar(md_path, md_texto)

    print("Etapa 19 documentada.")
    print("CSS: public/css/style.css")
    print("Backup: " + backup["destino"])
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("CSS sem asterisco: " + str(validacao["sem_asterisco"]))
    print("Documentacao atualizada: " + ", ".join(DOCS))


if __name__ == "__main__":
    main()
