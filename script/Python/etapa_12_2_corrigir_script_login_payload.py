#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 12.2 - Corrigir payload de login da Etapa 12

Objetivo:
- Criar backup do script etapa_12_validar_login_endpoints_autenticados.py.
- Corrigir o payload principal de login para usar email + senha.
- Manter compatibilidade com password como fallback.
- Validar sintaxe com py_compile.
- Atualizar CONTEXTO_PROJETO.md, CHANGELOG.md, DECISOES_TECNICAS.md e PENDENCIAS.md.
- Nao alterar banco.
- Nao alterar aplicacao.
- Nao executar login automaticamente.
"""

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()
BACKUPS = ROOT / "backups"

SCRIPT_ALVO = ROOT / "etapa_12_validar_login_endpoints_autenticados.py"

DOCS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def ler(path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def gravar(path, texto):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def falhar(msg):
    print("ERRO: " + msg)
    raise SystemExit(1)


def validar_sem_asterisco_indevido(texto, nome):
    if chr(42) in texto:
        falhar("Validacao bloqueou " + nome + " por conter asterisco.")


def substituir_trecho(texto, antigo, novo, descricao, relatorio):
    if antigo in texto:
        texto = texto.replace(antigo, novo, 1)
        relatorio.append(descricao)
    return texto


def atualizar_payload_login(texto):
    relatorio = []

    antigo_1 = (
        '    payload = {\n'
        '        "email": cred["email"],\n'
        '        "password": cred["senha"]\n'
        '    }\n'
        '\n'
        '    http = http_request(opener, "POST", LOGIN_PATH, payload)\n'
    )

    novo_1 = (
        '    payload = {\n'
        '        "email": cred["email"],\n'
        '        "senha": cred["senha"]\n'
        '    }\n'
        '\n'
        '    http = http_request(opener, "POST", LOGIN_PATH, payload)\n'
    )

    texto = substituir_trecho(
        texto,
        antigo_1,
        novo_1,
        "Payload principal alterado de password para senha",
        relatorio
    )

    antigo_2 = (
        '    body = (http.get("body_preview") or "").lower()\n'
        '    status_ok = http.get("status") in [200, 201, 302]\n'
        '    cookie_ok = len(resultado["cookies"]) > 0\n'
        '    body_ok = "sucesso" in body or "success" in body or "dashboard" in body or "ok" in body\n'
        '\n'
        '    resultado["ok"] = bool(status_ok and (cookie_ok or body_ok))\n'
        '\n'
        '    return resultado\n'
    )

    novo_2 = (
        '    body = (http.get("body_preview") or "").lower()\n'
        '    status_ok = http.get("status") in [200, 201, 302]\n'
        '    cookie_ok = len(resultado["cookies"]) > 0\n'
        '    body_ok = "sucesso" in body or "success" in body or "dashboard" in body or "ok" in body\n'
        '\n'
        '    resultado["ok"] = bool(status_ok and (cookie_ok or body_ok))\n'
        '\n'
        '    if not resultado["ok"]:\n'
        '        fallback_payload = {\n'
        '            "email": cred["email"],\n'
        '            "password": cred["senha"]\n'
        '        }\n'
        '        fallback_http = http_request(opener, "POST", LOGIN_PATH, fallback_payload)\n'
        '        resultado["fallback_password"] = fallback_http\n'
        '        fallback_body = (fallback_http.get("body_preview") or "").lower()\n'
        '        fallback_status_ok = fallback_http.get("status") in [200, 201, 302]\n'
        '        fallback_body_ok = "sucesso" in fallback_body or "success" in fallback_body or "dashboard" in fallback_body or "ok" in fallback_body\n'
        '        resultado["cookies"] = cookies_resumo(jar)\n'
        '        fallback_cookie_ok = len(resultado["cookies"]) > 0\n'
        '        resultado["ok"] = bool(fallback_status_ok and (fallback_cookie_ok or fallback_body_ok))\n'
        '\n'
        '    return resultado\n'
    )

    texto = substituir_trecho(
        texto,
        antigo_2,
        novo_2,
        "Fallback opcional com password adicionado",
        relatorio
    )

    if not relatorio:
        if '"senha": cred["senha"]' in texto:
            relatorio.append("Payload com senha ja estava presente")
        else:
            falhar("Nao foi possivel localizar o trecho de payload para corrigir.")

    return texto, relatorio


def atualizar_doc(nome, titulo, linhas):
    path = ROOT / nome
    texto = ler(path)

    if texto is None:
        texto = "# " + nome.replace(".md", "") + "\n"

    inicio = "<!-- ETAPA_12_2_INICIO -->"
    fim = "<!-- ETAPA_12_2_FIM -->"

    bloco_linhas = []
    bloco_linhas.append("")
    bloco_linhas.append(inicio)
    bloco_linhas.append("## " + titulo)
    bloco_linhas.append("")
    bloco_linhas.extend(linhas)
    bloco_linhas.append(fim)
    bloco_linhas.append("")

    bloco = "\n".join(bloco_linhas)

    pos_inicio = texto.find(inicio)
    pos_fim = texto.find(fim)

    if pos_inicio >= 0 and pos_fim >= pos_inicio:
        pos_fim = pos_fim + len(fim)
        novo = texto[:pos_inicio] + bloco.strip() + texto[pos_fim:]
    else:
        if not texto.endswith("\n"):
            texto += "\n"
        novo = texto + bloco

    novo = novo.replace(chr(42), "")
    validar_sem_asterisco_indevido(novo, nome)
    gravar(path, novo)


def atualizar_documentacao(relatorio):
    data = agora_iso()
    alteracoes = ", ".join(relatorio)

    atualizar_doc(
        "CONTEXTO_PROJETO.md",
        "Etapa 12.2 - Payload de login corrigido",
        [
            "Data: " + data,
            "",
            "Foi corrigido o script da Etapa 12 para usar o campo senha no payload principal de login.",
            "Foi mantido fallback opcional com password para compatibilidade.",
            "Alteracoes aplicadas: " + alteracoes + ".",
            "Nenhuma alteracao foi aplicada ao banco ou a aplicacao.",
            "A Etapa 12 deve ser reexecutada com as credenciais em variaveis de ambiente."
        ]
    )

    atualizar_doc(
        "CHANGELOG.md",
        "Etapa 12.2 - Correcao do script de login",
        [
            "Data: " + data,
            "",
            "Corrigido payload principal do script etapa_12_validar_login_endpoints_autenticados.py.",
            "Campo principal alterado para senha.",
            "Fallback com password mantido.",
            "Validada sintaxe com py_compile.",
            "Criado backup do script antes da alteracao."
        ]
    )

    atualizar_doc(
        "DECISOES_TECNICAS.md",
        "Etapa 12.2 - Decisoes tecnicas",
        [
            "Data: " + data,
            "",
            "Decidido alinhar o script ao AuthController, que espera email e senha.",
            "Decidido manter fallback com password para compatibilidade futura.",
            "Decidido nao executar login automaticamente nesta correcao.",
            "Decidido nao alterar codigo da aplicacao."
        ]
    )

    atualizar_doc(
        "PENDENCIAS.md",
        "Pendencias apos Etapa 12.2",
        [
            "Data: " + data,
            "",
            "Reexecutar a Etapa 12 com credenciais via variaveis de ambiente.",
            "Confirmar Login OK e cookie recebido no relatorio da Etapa 12.",
            "Validar fluxos reais da interface web em etapa posterior."
        ]
    )


def main():
    if not SCRIPT_ALVO.exists():
        falhar("Script alvo nao encontrado: " + str(SCRIPT_ALVO))

    texto = ler(SCRIPT_ALVO)
    if texto is None:
        falhar("Script alvo ilegivel.")

    BACKUPS.mkdir(exist_ok=True)
    backup_path = BACKUPS / ("etapa_12_2_backup_script_" + agora_stamp() + ".py")
    shutil.copy2(SCRIPT_ALVO, backup_path)

    novo_texto, relatorio = atualizar_payload_login(texto)

    if novo_texto != texto:
        gravar(SCRIPT_ALVO, novo_texto)
        print("Script corrigido.")
    else:
        print("Nenhuma alteracao necessaria no script.")

    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(SCRIPT_ALVO)],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        print(result.stderr)
        falhar("Validacao de sintaxe falhou.")

    atualizar_documentacao(relatorio)

    print("Etapa 12.2 concluida.")
    print("Backup do script: " + str(backup_path))
    print("Sintaxe validada com sucesso.")
    print("Documentacao obrigatoria atualizada.")
    print("")
    print("Agora reexecute a Etapa 12:")
    print("sudo ETAPA12_LOGIN_EMAIL='admin@saas.com' ETAPA12_LOGIN_PASSWORD='123456' python3 etapa_12_validar_login_endpoints_autenticados.py")


if __name__ == "__main__":
    main()