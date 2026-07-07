#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess

ARQUIVO = Path("etapa_24_criar_banco_teste_superadmin_tenant.py")

TRECHO_ANTIGO = '''    stdout_raw = ex.get("stdout") or ""
    try:
        resultado["json"] = json.loads(stdout_raw)
    except Exception:
        resultado["json_parse_error"] = "Nao foi possivel interpretar stdout como JSON"

    json_result = resultado.get("json") or {}
    resultado["ok"] = bool(ex.get("ok") and json_result.get("ok"))
'''

TRECHO_NOVO = '''    stdout_raw = ex.get("stdout") or ""
    try:
        resultado["json"] = json.loads(stdout_raw)
    except Exception:
        inicio = stdout_raw.find("{")
        fim = stdout_raw.rfind("}")

        if inicio >= 0 and fim >= inicio:
            trecho_json = stdout_raw[inicio:fim + 1]
            try:
                resultado["json"] = json.loads(trecho_json)
                resultado["json_extraido_de_stdout"] = True
            except Exception as exc:
                resultado["json"] = None
                resultado["json_parse_error"] = "Falha ao interpretar JSON extraido: " + str(exc)
        else:
            resultado["json"] = None
            resultado["json_parse_error"] = "Nao foi possivel localizar bloco JSON no stdout"

    json_result = resultado.get("json") or {}
    resultado["ok"] = bool(ex.get("ok") and json_result.get("ok"))
'''


def main():
    if not ARQUIVO.exists():
        raise SystemExit("Arquivo nao encontrado: " + str(ARQUIVO))

    texto = ARQUIVO.read_text(encoding="utf-8", errors="replace")

    if TRECHO_ANTIGO not in texto:
        raise SystemExit("Trecho antigo nao encontrado. Nao alterei o arquivo.")

    backup = Path("backups") / "etapa_24_antes_hotfix_parse_json_stdout.py"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(texto, encoding="utf-8")

    novo = texto.replace(TRECHO_ANTIGO, TRECHO_NOVO, 1)

    ARQUIVO.write_text(novo, encoding="utf-8")

    print("Hotfix aplicado: parser agora extrai JSON de stdout com linhas extras.")
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
        raise SystemExit("Falha no py_compile. Nao rode a Etapa 24 ainda.")


if __name__ == "__main__":
    main()
