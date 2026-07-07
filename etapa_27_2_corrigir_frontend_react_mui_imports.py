#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 27.2 - Corrigir frontend React, imports e Material UI

Objetivo:
- Remover alias @ do frontend React.
- Remover paths do tsconfig.app.json.
- Remover alias do vite.config.ts.
- Converter imports para caminhos relativos.
- Corrigir uso de Typography com fontWeight direto.
- Substituir Grid por Box com CSS grid.
- Manter rota fallback sem caractere asterisco literal.
- Rodar npm run typecheck e npm run build.
- Nao alterar backend.
- Nao alterar banco.
- Nao alterar Docker.
- Nao substituir o legado EJS.
- Criar backup, manifesto, validacao e relatorios.
- Atualizar documentacao obrigatoria.

Como executar:
python3 etapa_27_2_corrigir_frontend_react_mui_imports.py
"""

import os
import json
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
FRONTEND_DIR = ROOT / "frontend"
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "frontend/vite.config.ts",
    "frontend/tsconfig.app.json",
    "frontend/src/app/App.tsx",
    "frontend/src/app/providers/AppThemeProvider.tsx",
    "frontend/src/routes/AppRoutes.tsx",
    "frontend/src/layouts/AppShell.tsx",
    "frontend/src/shared/components/PageHeader.tsx",
    "frontend/src/features/auth/pages/LoginPage.tsx",
    "frontend/src/features/dashboard/pages/DashboardPage.tsx",
    "frontend/src/features/crm/pages/CrmPage.tsx",
    "frontend/src/features/whatsapp/pages/WhatsappPage.tsx",
    "frontend/src/features/settings/pages/AdminPage.tsx",
    "frontend/src/features/super-admin/pages/SuperAdminPage.tsx",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

IGNORE_DIRS = [
    "node_modules",
    ".git",
    "backups",
    "reports",
    "auth_sessions",
    "__pycache__",
    "tmp_etapa_24",
    "frontend/node_modules",
    "frontend/dist"
]


def agora_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def garantir_dirs():
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


def rel(path):
    try:
        return str(Path(path).relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def ler(path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")


def gravar(path, texto):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")


def sha256(path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            bloco = f.read(1048576)
            if not bloco:
                break
            h.update(bloco)
    return h.hexdigest()


def salvar_json(path, dados):
    gravar(path, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def deve_ignorar(path):
    partes = set(path.parts)
    caminho = rel(path)
    for nome in IGNORE_DIRS:
        if nome in partes:
            return True
        if caminho == nome or caminho.startswith(nome + "/"):
            return True
    return False


def gerar_manifesto():
    itens = []
    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)
        dirs[:] = [d for d in dirs if not deve_ignorar(base_path / d)]
        for nome in files:
            p = base_path / nome
            if deve_ignorar(p):
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


def criar_backup(destino):
    destino.mkdir(parents=True, exist_ok=True)
    copiados = []
    ausentes = []
    erros = []
    for nome in BACKUP_FILES:
        origem = ROOT / nome
        destino_item = destino / nome
        if not origem.exists():
            ausentes.append(nome)
            continue
        try:
            destino_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino_item)
            copiados.append(nome)
        except Exception as exc:
            erros.append({"item": nome, "erro": str(exc)})
    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def run_cmd(cmd, cwd=None, timeout=600):
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        return {
            "cmd": cmd,
            "cwd": str(cwd or ROOT),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip()[:70000],
            "stderr": proc.stderr.strip()[:70000],
            "ok": proc.returncode == 0
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "cwd": str(cwd or ROOT),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "ok": False
        }


def vite_config():
    return """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:50010',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
});
"""


def tsconfig_app():
    return """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
"""


def app_tsx():
    return """import { AppThemeProvider } from './providers/AppThemeProvider';
import { AppRoutes } from '../routes/AppRoutes';

export function App() {
  return (
    <AppThemeProvider>
      <AppRoutes />
    </AppThemeProvider>
  );
}
"""


def theme_provider_tsx():
    return """import { ReactNode, useMemo, useState } from 'react';
import { CssBaseline, ThemeProvider } from '@mui/material';
import { createAppTheme } from '../../shared/theme/theme';
import { ColorModeContext, ColorModeName } from '../../shared/theme/ColorModeContext';

const storageKey = 'engeradios-color-mode';

function getInitialMode(): ColorModeName {
  const saved = window.localStorage.getItem(storageKey);
  if (saved === 'dark' || saved === 'light') {
    return saved;
  }
  return 'light';
}

export function AppThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ColorModeName>(getInitialMode);

  const value = useMemo(() => ({
    mode,
    toggleMode: () => {
      setMode((current) => {
        const next = current === 'light' ? 'dark' : 'light';
        window.localStorage.setItem(storageKey, next);
        return next;
      });
    }
  }), [mode]);

  const theme = useMemo(() => createAppTheme(mode), [mode]);

  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}
"""


def app_routes_tsx():
    return """import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../layouts/AppShell';
import { LoginPage } from '../features/auth/pages/LoginPage';
import { DashboardPage } from '../features/dashboard/pages/DashboardPage';
import { CrmPage } from '../features/crm/pages/CrmPage';
import { WhatsappPage } from '../features/whatsapp/pages/WhatsappPage';
import { AdminPage } from '../features/settings/pages/AdminPage';
import { SuperAdminPage } from '../features/super-admin/pages/SuperAdminPage';

const fallbackRoute = String.fromCharCode(42);

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/crm" element={<CrmPage />} />
        <Route path="/whatsapp" element={<WhatsappPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/super-admin" element={<SuperAdminPage />} />
      </Route>
      <Route path={fallbackRoute} element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
"""


def app_shell_tsx():
    return """import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ChatIcon from '@mui/icons-material/Chat';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import SettingsIcon from '@mui/icons-material/Settings';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import MenuIcon from '@mui/icons-material/Menu';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { useColorMode } from '../shared/theme/ColorModeContext';

const drawerWidth = 288;

const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
  { label: 'CRM Atendimento', path: '/crm', icon: <ChatIcon /> },
  { label: 'WhatsApp', path: '/whatsapp', icon: <WhatsAppIcon /> },
  { label: 'Administracao', path: '/admin', icon: <SettingsIcon /> },
  { label: 'Super Admin', path: '/super-admin', icon: <AdminPanelSettingsIcon /> }
];

export function AppShell() {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { mode, toggleMode } = useColorMode();
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));
  const [open, setOpen] = useState(false);

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2.5 }}>
        <Typography variant="h6" color="primary" sx={{ fontWeight: 900 }}>
          Engeradios CRM
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Atendimento profissional
        </Typography>
      </Box>
      <Divider />
      <List sx={{ px: 1, py: 2 }}>
        {navItems.map((item) => {
          const selected = location.pathname === item.path;
          return (
            <ListItemButton
              key={item.path}
              selected={selected}
              onClick={() => {
                navigate(item.path);
                setOpen(false);
              }}
              sx={{ borderRadius: 2, mb: 0.5 }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
      <Box sx={{ flexGrow: 1 }} />
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Frontend React base - Etapa 27
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{
          borderBottom: 1,
          borderColor: 'divider',
          width: isDesktop ? 'calc(100% - ' + drawerWidth + 'px)' : '100%',
          ml: isDesktop ? drawerWidth + 'px' : 0
        }}
      >
        <Toolbar>
          {!isDesktop && (
            <IconButton edge="start" onClick={() => setOpen(true)} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
          )}
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 800 }}>
            Plataforma SaaS
          </Typography>
          <IconButton onClick={toggleMode} color="inherit">
            {mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { lg: drawerWidth }, flexShrink: { lg: 0 } }}>
        <Drawer
          variant={isDesktop ? 'permanent' : 'temporary'}
          open={isDesktop ? true : open}
          onClose={() => setOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box'
            }
          }}
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { lg: 'calc(100% - ' + drawerWidth + 'px)' },
          minHeight: '100vh',
          pt: 10,
          px: { xs: 2, md: 4 },
          pb: 4
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}
"""


def page_header_tsx():
    return """import { Box, Typography } from '@mui/material';

interface PageHeaderProps {
  title: string;
  description: string;
}

export function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 900 }}>
        {title}
      </Typography>
      <Typography color="text.secondary" sx={{ maxWidth: 760 }}>
        {description}
      </Typography>
    </Box>
  );
}
"""


def login_page_tsx():
    return """import { Box, Button, Card, CardContent, TextField, Typography } from '@mui/material';

export function LoginPage() {
  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2 }}>
      <Card sx={{ width: '100%', maxWidth: 420 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 900 }}>
            Entrar
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            Base React criada. A integracao real de login sera feita em etapa propria.
          </Typography>
          <TextField label="E-mail" fullWidth sx={{ mb: 2 }} />
          <TextField label="Senha" type="password" fullWidth sx={{ mb: 3 }} />
          <Button variant="contained" fullWidth href="/dashboard">
            Acessar dashboard
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}
"""


def dashboard_page_tsx():
    return """import { useEffect, useState } from 'react';
import { Box, Button, Card, CardContent, Chip, Stack, Typography } from '@mui/material';
import { PageHeader } from '../../../shared/components/PageHeader';
import { httpClient } from '../../../shared/services/httpClient';
import { LegacyStatusResponse } from '../../../shared/types/api';

export function DashboardPage() {
  const [status, setStatus] = useState('CARREGANDO');

  useEffect(() => {
    let active = true;
    httpClient.get<LegacyStatusResponse>('/whatsapp/status/5')
      .then((response) => {
        if (active) {
          setStatus(response.data.status || 'DESCONECTADO');
        }
      })
      .catch(() => {
        if (active) {
          setStatus('DESCONECTADO');
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const cards = [
    { title: 'WhatsApp', value: status, text: 'Status operacional da conexao.' },
    { title: 'CRM', value: 'Pronto', text: 'Tela dedicada para atendimento.' },
    { title: 'Tema', value: 'Claro e escuro', text: 'Controlado pelo Material UI.' },
    { title: 'Frontend', value: 'React', text: 'Base criada na Etapa 27.' }
  ];

  return (
    <Box>
      <PageHeader
        title="Dashboard"
        description="Base inicial do frontend React com TypeScript, Vite e Material UI. Esta tela ainda nao substitui o legado em producao."
      />
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, 1fr)',
            lg: 'repeat(4, 1fr)'
          },
          gap: 2
        }}
      >
        {cards.map((card) => (
          <Card sx={{ height: '100%' }} key={card.title}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 700 }}>
                {card.title}
              </Typography>
              <Typography variant="h5" sx={{ mt: 1, fontWeight: 900 }}>
                {card.value}
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 1 }}>
                {card.text}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mt: 3 }}>
        <Button variant="contained" href="/crm">Abrir CRM</Button>
        <Button variant="outlined" href="/whatsapp">Gestao WhatsApp</Button>
        <Chip label="Etapa 27" color="primary" />
      </Stack>
    </Box>
  );
}
"""


def crm_page_tsx():
    return """import { Card, CardContent, Typography } from '@mui/material';
import { PageHeader } from '../../../shared/components/PageHeader';

export function CrmPage() {
  return (
    <>
      <PageHeader title="CRM Atendimento" description="Placeholder da futura tela de atendimento em React." />
      <Card>
        <CardContent>
          <Typography>
            A migracao completa do CRM sera feita em etapa futura.
          </Typography>
        </CardContent>
      </Card>
    </>
  );
}
"""


def whatsapp_page_tsx():
    return """import { Card, CardContent, Typography } from '@mui/material';
import { PageHeader } from '../../../shared/components/PageHeader';

export function WhatsappPage() {
  return (
    <>
      <PageHeader title="Gestao WhatsApp" description="Placeholder para QR Code, pairing code e status em tempo real." />
      <Card>
        <CardContent>
          <Typography>
            A gestao completa da conexao sera implementada apos a base modular.
          </Typography>
        </CardContent>
      </Card>
    </>
  );
}
"""


def admin_page_tsx():
    return """import { Card, CardContent, Typography } from '@mui/material';
import { PageHeader } from '../../../shared/components/PageHeader';

export function AdminPage() {
  return (
    <>
      <PageHeader title="Administracao" description="Placeholder para configuracoes do tenant." />
      <Card>
        <CardContent>
          <Typography>
            Usuarios, setores e configuracoes serao migrados por etapas.
          </Typography>
        </CardContent>
      </Card>
    </>
  );
}
"""


def super_admin_page_tsx():
    return """import { Card, CardContent, Typography } from '@mui/material';
import { PageHeader } from '../../../shared/components/PageHeader';

export function SuperAdminPage() {
  return (
    <>
      <PageHeader title="Super Admin" description="Placeholder para gestao SaaS master." />
      <Card>
        <CardContent>
          <Typography>
            A gestao de tenants sera migrada em etapa futura.
          </Typography>
        </CardContent>
      </Card>
    </>
  );
}
"""


def arquivos_corrigidos():
    return {
        "frontend/vite.config.ts": vite_config(),
        "frontend/tsconfig.app.json": tsconfig_app(),
        "frontend/src/app/App.tsx": app_tsx(),
        "frontend/src/app/providers/AppThemeProvider.tsx": theme_provider_tsx(),
        "frontend/src/routes/AppRoutes.tsx": app_routes_tsx(),
        "frontend/src/layouts/AppShell.tsx": app_shell_tsx(),
        "frontend/src/shared/components/PageHeader.tsx": page_header_tsx(),
        "frontend/src/features/auth/pages/LoginPage.tsx": login_page_tsx(),
        "frontend/src/features/dashboard/pages/DashboardPage.tsx": dashboard_page_tsx(),
        "frontend/src/features/crm/pages/CrmPage.tsx": crm_page_tsx(),
        "frontend/src/features/whatsapp/pages/WhatsappPage.tsx": whatsapp_page_tsx(),
        "frontend/src/features/settings/pages/AdminPage.tsx": admin_page_tsx(),
        "frontend/src/features/super-admin/pages/SuperAdminPage.tsx": super_admin_page_tsx()
    }


def aplicar_correcoes():
    alteracoes = []
    for nome, texto in arquivos_corrigidos().items():
        antes = sha256(nome)
        atual = ler(nome)
        alterado = atual != texto
        if alterado:
            gravar(nome, texto)
        depois = sha256(nome)
        alteracoes.append({
            "arquivo": nome,
            "alterado": alterado,
            "sha256_antes": antes,
            "sha256_depois": depois,
            "tamanho": len(texto)
        })
    return alteracoes


def validar_sem_asterisco(nome, texto):
    achados = []
    for idx, linha in enumerate(texto.splitlines(), start=1):
        if chr(42) in linha:
            achados.append({"arquivo": nome, "linha": idx, "texto": linha[:300]})
    return achados


def validar_estrutura():
    arquivos = list(arquivos_corrigidos().keys()) + [
        "frontend/package.json",
        "frontend/src/main.tsx",
        "frontend/src/shared/services/httpClient.ts",
        "frontend/src/shared/theme/theme.ts"
    ]
    itens = []
    erros = []
    for nome in arquivos:
        texto = ler(nome)
        existe = texto is not None
        ast = validar_sem_asterisco(nome, texto or "")
        item = {
            "arquivo": nome,
            "existe": existe,
            "sha256": sha256(nome),
            "sem_asterisco": len(ast) == 0,
            "asteriscos": ast[:10],
            "ok": existe and len(ast) == 0
        }
        itens.append(item)
        if not item["ok"]:
            erros.append(item)
    tudo = "\n".join((ler(nome) or "") for nome in arquivos if ler(nome) is not None)
    checks = {
        "sem_alias_arroba": "@/" not in tudo,
        "sem_baseUrl": "baseUrl" not in (ler("frontend/tsconfig.app.json") or ""),
        "sem_paths": "paths" not in (ler("frontend/tsconfig.app.json") or ""),
        "sem_import_path_node": "node:path" not in (ler("frontend/vite.config.ts") or ""),
        "sem_grid_item": "Grid" not in (ler("frontend/src/features/dashboard/pages/DashboardPage.tsx") or ""),
        "sem_fontWeight_prop": " fontWeight=" not in tudo,
        "sem_path_asterisco_literal": 'path="*"' not in (ler("frontend/src/routes/AppRoutes.tsx") or ""),
        "fallback_com_from_char_code": "String.fromCharCode(42)" in (ler("frontend/src/routes/AppRoutes.tsx") or "")
    }
    ok = len(erros) == 0 and all(checks.values())
    return {"arquivos": itens, "checks": checks, "erros": erros, "ok": ok}


def executar_build():
    return {
        "node_version": run_cmd(["node", "--version"], timeout=30),
        "npm_version": run_cmd(["npm", "--version"], timeout=30),
        "typecheck": run_cmd(["npm", "run", "typecheck"], cwd=FRONTEND_DIR, timeout=600),
        "build": run_cmd(["npm", "run", "build"], cwd=FRONTEND_DIR, timeout=600)
    }


def build_ok(builds):
    return bool(builds["typecheck"].get("ok") and builds["build"].get("ok"))


def atualizar_doc_obrigatorio(nome, titulo, linhas):
    atual = ler(nome)
    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"
    ini = "<!-- ETAPA_27_2_INICIO -->"
    fim = "<!-- ETAPA_27_2_FIM -->"
    bloco = []
    bloco.append("")
    bloco.append(ini)
    bloco.append("## " + titulo)
    bloco.append("")
    bloco.extend(linhas)
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
            atual += "\n"
        novo = atual + novo_bloco
    gravar(nome, novo)


def atualizar_documentacao(relatorio):
    data = relatorio["gerado_em"]
    atualizar_doc_obrigatorio("CONTEXTO_PROJETO.md", "Etapa 27.2 - Frontend React corrigido", [
        "Data: " + data,
        "",
        "Removido alias @ e paths do TypeScript para simplificar a base React.",
        "Convertidos imports para caminhos relativos.",
        "Corrigido uso do Material UI para compatibilidade de tipos.",
        "Substituido Grid por Box com CSS grid no dashboard.",
        "Build OK: " + str(relatorio["build_ok"]) + "."
    ])
    atualizar_doc_obrigatorio("CHANGELOG.md", "Etapa 27.2 - Correcao React Material UI", [
        "Data: " + data,
        "",
        "Removido alias @ do Vite e do TypeScript.",
        "Ajustados imports do frontend para caminhos relativos.",
        "Corrigidas propriedades de Typography usando sx.",
        "Removido Grid item do dashboard.",
        "Executado typecheck e build."
    ])
    atualizar_doc_obrigatorio("DECISOES_TECNICAS.md", "Etapa 27.2 - Decisao imports relativos", [
        "Data: " + data,
        "",
        "Decidido remover path alias para evitar asteriscos em arquivos de configuracao.",
        "Decidido usar imports relativos nesta fase inicial.",
        "Decidido usar Box com CSS grid em vez de Grid item para evitar incompatibilidade de tipos com Material UI instalado."
    ])
    atualizar_doc_obrigatorio("PENDENCIAS.md", "Pendencias apos Etapa 27.2", [
        "Data: " + data,
        "",
        "Validar visualmente o frontend com npm run dev.",
        "Etapa 28: criar backend modular em paralelo.",
        "Etapa 29: padronizar respostas reais de API.",
        "Etapa 30: migrar login real para React."
    ])
    return DOCS_OBRIGATORIOS


def gerar_relatorio_md(relatorio):
    linhas = []
    linhas.append("# Etapa 27.2 - Corrigir frontend React MUI e imports")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivos alterados: " + str(sum(1 for x in relatorio["alteracoes"] if x["alterado"])))
    linhas.append("- Validacao estrutura OK: " + str(relatorio["validacao"]["ok"]))
    linhas.append("- Typecheck OK: " + str(relatorio["builds"]["typecheck"].get("ok")))
    linhas.append("- Build OK: " + str(relatorio["builds"]["build"].get("ok")))
    linhas.append("- Runtime geral OK: " + str(relatorio["ok"]))
    linhas.append("")
    linhas.append("## Checks")
    linhas.append("")
    for chave, valor in relatorio["validacao"]["checks"].items():
        linhas.append("- " + chave + ": " + str(valor))
    linhas.append("")
    linhas.append("## Alteracoes")
    linhas.append("")
    for item in relatorio["alteracoes"]:
        linhas.append("- " + item["arquivo"] + " alterado: " + str(item["alterado"]))
    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()
    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_27_2_frontend_react_mui_imports_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_27_2_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    alteracoes = aplicar_correcoes()
    validacao = validar_estrutura()
    builds = executar_build()
    ok_build = build_ok(builds)

    relatorio_base = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "alteracoes": alteracoes,
        "validacao": validacao,
        "builds": builds,
        "build_ok": ok_build,
        "ok": bool(validacao["ok"] and ok_build)
    }
    docs = atualizar_documentacao(relatorio_base)
    relatorio_base["docs_obrigatorios"] = docs

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_27_2_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)
    relatorio_base["manifesto_depois"] = rel(manifesto_depois_path)

    json_path = REPORTS_DIR / "etapa_27_2_corrigir_frontend_react_mui_imports.json"
    md_path = REPORTS_DIR / "etapa_27_2_corrigir_frontend_react_mui_imports.md"
    salvar_json(json_path, relatorio_base)
    gravar(md_path, gerar_relatorio_md(relatorio_base))

    print("Etapa 27.2 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Validacao estrutura OK: " + str(validacao["ok"]))
    print("Typecheck OK: " + str(builds["typecheck"].get("ok")))
    print("Build OK: " + str(builds["build"].get("ok")))
    print("Runtime geral OK: " + str(relatorio_base["ok"]))

    if not relatorio_base["ok"]:
        print("")
        print("Aviso: Etapa 27.2 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
