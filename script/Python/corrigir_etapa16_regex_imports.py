#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

ARQUIVO = Path("etapa_16_auditar_melhorias_frontend.py")

NOVA_FUNCAO = r'''def extrair_imports_js(texto):
    refs = []

    padroes = [
        r"import\s+(?:[^\"']+[\"']",
        r"from\s+[^\"']+[\"']",
        r"require\(\s*[^\"']+[\"']\s*\)"
    ]

    for padrao in padroes:
        for m in re.finditer(padrao, texto, flags=re.IGNORECASE):
            try:
                valor = m.group(1).strip()
            except Exception:
                valor = ""

            if valor:
                refs.append(valor)

    unicos = []
    vistos = set()

    for ref in refs:
        if ref not in vistos:
            vistos.add(ref)
            unicos.append(ref)

    return unicos
'''


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    inicio = texto.find("def extrair_imports_js(texto):")
    if inicio < 0:
        raise SystemExit("Funcao extrair_imports_js nao encontrada.")

    proximo = texto.find("\ndef ", inicio + 1)
    if proximo < 0:
        raise SystemExit("Nao foi possivel localizar fim da funcao.")

    novo = texto[:inicio] + NOVA_FUNCAO + texto[proximo + 1:]

    backup = Path("backups") / "etapa_16_regex_imports_backup.py"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(texto, encoding="utf-8")

    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Correcao aplicada.")
    print("Backup criado em: " + str(backup))
    print("Agora execute:")
    print("python3 etapa_16_auditar_melhorias_frontend.py")


if __name__ == "__main__":
    main()