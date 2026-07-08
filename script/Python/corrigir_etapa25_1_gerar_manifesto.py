#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess

ARQUIVO = Path("etapa_25_1_corrigir_frontend_shell_seguro.py")

MARCADOR = '''
def criar_backup(destino):
'''

FUNCAO = r'''
def deve_ignorar_manifesto(path):
    partes = set(path.parts)
    rel_path = rel(path)

    ignorar = [
        "node_modules",
        ".git",
        "backups",
        "auth_sessions",
        "reports",
        "__pycache__",
        "tmp_etapa_24"
    ]

    for nome in ignorar:
        if nome in partes:
            return True
        if rel_path == nome or rel_path.startswith(nome + "/"):
            return True

    return False


def gerar_manifesto():
    itens = []

    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)
        dirs[:] = [d for d in dirs if not deve_ignorar_manifesto(base_path / d)]

        for nome in files:
            p = base_path / nome

            if deve_ignorar_manifesto(p):
                continue

            try:
                st = p.stat()
                itens.append({
                    "arquivo": rel(p),
                    "tamanho_bytes": st.st_size,
                    "sha256": sha256(p)
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
        "arquivos": sorted(itens, key=lambda x: x.get("arquivo", ""))
    }


'''


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    if "def gerar_manifesto():" in texto:
        print("gerar_manifesto ja existe. Nada a alterar.")
        return

    if MARCADOR not in texto:
        raise SystemExit("Marcador para insercao nao encontrado. Nao alterei o arquivo.")

    backup = Path("backups") / "etapa_25_1_antes_hotfix_gerar_manifesto.py"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(texto, encoding="utf-8")

    novo = texto.replace(MARCADOR, FUNCAO + MARCADOR, 1)
    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Hotfix aplicado: gerar_manifesto adicionada.")
    print("Backup: " + str(backup))

    r = subprocess.run(
        ["python3", "-m", "py_compile", str(ARQUIVO)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    print("Py compile OK: " + str(r.returncode == 0))

    if r.stdout:
        print(r.stdout)

    if r.stderr:
        print(r.stderr)

    if r.returncode != 0:
        raise SystemExit("Falha no py_compile. Nao rode a Etapa 25.1 ainda.")


if __name__ == "__main__":
    main()
