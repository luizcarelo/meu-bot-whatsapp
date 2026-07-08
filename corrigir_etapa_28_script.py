#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import re

ARQ = Path("etapa_28_criar_backend_modular.py")

texto = ARQ.read_text(encoding="utf-8", errors="replace")

novo_repository = r'''def module_repository_js(module_name):
    return """async function getModuleInfo() {
  return {
    module: '""" + module_name + """',
    repository: 'placeholder',
    connected: false
  };
}

module.exports = {
  getModuleInfo
};
"""
'''

novo_service = r'''def module_service_js(module_name):
    label = module_name.replace("-", " ")
    return """const repository = require('./""" + module_name + """.repository');

async function getStatus() {
  const info = await repository.getModuleInfo();
  return {
    module: '""" + module_name + """',
    label: '""" + label + """',
    status: 'READY',
    info: info
  };
}

module.exports = {
  getStatus
};
"""
'''

texto2 = re.sub(
    r"def module_repository_js\(module_name\):.*?\n\ndef module_service_js\(module_name\):",
    novo_repository + "\n\ndef module_service_js(module_name):",
    texto,
    flags=re.S
)

texto3 = re.sub(
    r"def module_service_js\(module_name\):.*?\n\ndef module_controller_js\(module_name\):",
    novo_service + "\n\ndef module_controller_js(module_name):",
    texto2,
    flags=re.S
)

if texto3 == texto:
    raise SystemExit("Nenhuma alteracao aplicada. Padrao nao encontrado.")

ARQ.write_text(texto3, encoding="utf-8")

print("Patch aplicado em etapa_28_criar_backend_modular.py")