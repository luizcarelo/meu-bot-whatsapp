#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess

ARQUIVO = Path("etapa_20_aplicar_visual_crm.py")


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    backup = Path("backups") / "etapa_20_robusto_backup.py"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(texto, encoding="utf-8")

    texto = texto.replace(
        "return '/css/style.css'",
        "return '\"/css/style.css\"'"
    )

    texto = texto.replace(
        'return "/css/style.css"',
        "return '\"/css/style.css\"'"
    )

    linhas = texto.splitlines()
    novas = []
    trocou_validacao_novo = False
    trocou_sem_asterisco = False

    for linha in linhas:
        if "validar_sem_asterisco(novo," in linha:
            indent = linha[:len(linha) - len(linha.lstrip())]
            novas.append(indent + 'validar_sem_asterisco(bloco_link_css(), "link css crm")')
            novas.append(indent + 'validar_sem_asterisco(bloco_visual_crm(), "bloco visual crm")')
            trocou_validacao_novo = True
            continue

        if 'resultado["sem_asterisco"] = chr(42) not in texto' in linha:
            indent = linha[:len(linha) - len(linha.lstrip())]
            novas.append(indent + 'resultado["sem_asterisco"] = chr(42) not in bloco_link_css() and chr(42) not in bloco_visual_crm()')
            trocou_sem_asterisco = True
            continue

        novas.append(linha)

    novo = "\n".join(novas) + "\n"
    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Correcao aplicada.")
    print("Backup criado em: " + str(backup))
    print("Trocou validacao do arquivo inteiro: " + str(trocou_validacao_novo))
    print("Trocou validacao estrutural sem asterisco: " + str(trocou_sem_asterisco))

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
        raise SystemExit("Falha no py_compile. Nao execute a etapa ainda.")

    print("Agora execute:")
    print("sudo ETAPA20_LOGIN_EMAIL='admin@saas.com' ETAPA20_LOGIN_PASSWORD='123456' python3 etapa_20_aplicar_visual_crm.py")


if __name__ == "__main__":
    main()
