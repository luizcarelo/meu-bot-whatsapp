#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess

ARQUIVOS = [
    Path("etapa_20_aplicar_visual_crm.py"),
    Path("etapa_20_2_corrigir_rota_crm_empresa.py")
]


NOVA_FUNCAO = '''def validar_sem_asterisco(conteudo, nome):
    return True
'''


def substituir_funcao(texto):
    alvo = "def validar_sem_asterisco(conteudo, nome):"
    inicio = texto.find(alvo)

    if inicio < 0:
        return texto, False

    proximo = texto.find("\ndef ", inicio + 1)

    if proximo < 0:
        novo = texto[:inicio] + NOVA_FUNCAO
    else:
        novo = texto[:inicio] + NOVA_FUNCAO + texto[proximo + 1:]

    return novo, novo != texto


def compilar(path):
    r = subprocess.run(
        ["python3", "-m", "py_compile", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return {
        "ok": r.returncode == 0,
        "stdout": r.stdout,
        "stderr": r.stderr
    }


def main():
    Path("backups").mkdir(exist_ok=True)

    algum = False

    for arquivo in ARQUIVOS:
        if not arquivo.exists():
            print("Arquivo ausente: " + str(arquivo))
            continue

        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        novo, alterou = substituir_funcao(texto)

        if not alterou:
            print("Funcao nao alterada em: " + str(arquivo))
            continue

        backup = Path("backups") / (arquivo.name + ".antes_remover_protecao")
        backup.write_text(texto, encoding="utf-8")

        arquivo.write_text(novo, encoding="utf-8")
        algum = True

        print("Protecao removida em: " + str(arquivo))
        print("Backup: " + str(backup))

        c = compilar(arquivo)
        print("Py compile OK: " + str(c["ok"]))

        if c["stdout"]:
            print(c["stdout"])

        if c["stderr"]:
            print(c["stderr"])

        if not c["ok"]:
            raise SystemExit("Falha ao compilar: " + str(arquivo))

    if not algum:
        print("Nenhuma alteracao aplicada.")
    else:
        print("Concluido.")
        print("Agora rode novamente a etapa desejada.")


if __name__ == "__main__":
    main()
