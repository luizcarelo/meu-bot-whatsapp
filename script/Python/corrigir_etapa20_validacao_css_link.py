#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

ARQUIVO = Path("etapa_20_aplicar_visual_crm.py")

NOVA_FUNCAO_LINK = '''def bloco_link_css():
    return '/css/style.css'
'''


def trocar_funcao(texto, nome_funcao, novo_conteudo):
    inicio = texto.find("def " + nome_funcao + "():")
    if inicio < 0:
        raise SystemExit("Funcao nao encontrada: " + nome_funcao)

    proximo = texto.find("\\ndef ", inicio + 1)
    if proximo < 0:
        raise SystemExit("Fim da funcao nao encontrado: " + nome_funcao)

    return texto[:inicio] + novo_conteudo + texto[proximo + 1:]


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    novo = trocar_funcao(texto, "bloco_link_css", NOVA_FUNCAO_LINK)

    linha_antiga = '    validar_sem_asterisco(novo, "views/crm.ejs")'
    linha_nova = (
        '    validar_sem_asterisco(bloco_link_css(), "link css crm")\\n'
        '    validar_sem_asterisco(bloco_visual_crm(), "bloco visual crm")'
    )

    if linha_antiga not in novo:
        raise SystemExit("Linha de validacao antiga nao encontrada.")

    novo = novo.replace(linha_antiga, linha_nova, 1)

    backup = Path("backups") / "etapa_20_validacao_css_link_backup.py"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(texto, encoding="utf-8")

    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Correcao aplicada.")
    print("Backup criado em: " + str(backup))
    print("Agora execute:")
    print("sudo ETAPA20_LOGIN_EMAIL='admin@saas.com' ETAPA20_LOGIN_PASSWORD='123456' python3 etapa_20_aplicar_visual_crm.py")


if __name__ == "__main__":
    main()
