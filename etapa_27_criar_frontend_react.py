#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 27 - Criar base do frontend React

Objetivo:
- Criar a pasta frontend com React, TypeScript, Vite e Material UI.
- Criar estrutura modular inicial por features.
- Criar AppShell responsivo com menu lateral.
- Criar tema claro e escuro com Material UI.
- Criar rotas iniciais.
- Criar cliente HTTP padronizado.
- Criar paginas placeholder para login, dashboard, CRM, WhatsApp, admin e super admin.
- Nao alterar frontend EJS legado.
- Nao alterar backend atual.
- Nao alterar banco.
- Nao alterar Docker.
- Criar backup, manifesto, validacao e relatorios.
- Atualizar documentacao obrigatoria.

Como executar:
python3 etapa_27_criar_frontend_react.py

Variaveis opcionais:
ETAPA27_NPM_INSTALL=true ou false
ETAPA27_NPM_BUILD=true ou false
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
SRC_DIR = FRONTEND_DIR / "src"
DOCS_DIR = ROOT / "docs"
REPORTS_DIR = ROOT / "reports"
BACKUPS_DIR = ROOT / "backups"

DOCS_OBRIGATORIOS = [
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md"
]

BACKUP_FILES = [
    "frontend",
    "CONTEXTO_PROJETO.md",
    "CHANGELOG.md",
    "DECISOES_TECNICAS.md",
    "PENDENCIAS.md",
    "docs/ARQUITETURA_FRONTEND_REACT.md",
    "docs/PLANO_MIGRACAO_REACT.md",
    "docs/RESUMO_ETAPA_26.md"
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
    DOCS_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)
    FRONTEND_DIR.mkdir(exist_ok=True)


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


def copiar_item(origem, destino):
    if origem.is_dir():
        if destino.exists():
            shutil.rmtree(destino)
        shutil.copytree(origem, destino, ignore=shutil.ignore_patterns("node_modules", "dist"))
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)


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
            copiar_item(origem, destino_item)
            copiados.append(nome)
        except Exception as exc:
            erros.append({"item": nome, "erro": str(exc)})
    return {
        "destino": rel(destino),
        "copiados": copiados,
        "ausentes": ausentes,
        "erros": erros
    }


def run_cmd(cmd, cwd=None, timeout=180):
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
            "stdout": proc.stdout.strip()[:50000],
            "stderr": proc.stderr.strip()[:50000],
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


def json_dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def arquivos_frontend():
    arquivos = {}

    arquivos["frontend/package.json"] = json_dump({
        "name": "engeradios-crm-frontend",
        "private": True,
        "version": "0.1.0",
        "type": "module",
        "scripts": {
            "dev": "vite --host 0.0.0.0 --port 5173",
            "build": "tsc -b && vite build",
            "preview": "vite preview --host 0.0.0.0 --port 4173",
            "typecheck": "tsc -b --pretty false"
        },
        "dependencies": {
            "@emotion/react": "latest",
            "@emotion/styled": "latest",
            "@fontsource/roboto": "latest",
            "@mui/icons-material": "latest",
            "@mui/material": "latest",
            "axios": "latest",
            "react": "latest",
            "react-dom": "latest",
            "react-router-dom": "latest"
        },
        "devDependencies": {
            "@types/react": "latest",
            "@types/react-dom": "latest",
            "@vitejs/plugin-react": "latest",
            "typescript": "latest",
            "vite": "latest"
        }
    })

    arquivos["frontend/index.html"] = """<!doctype html>
<html lang=\"pt-BR\">
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>Engeradios CRM</title>
  </head>
  <body>
    <div id=\"root\"></div>
    <script type=\"module\" src=\"/src/main.tsx\"></script>
  </body>
</html>
"""

    arquivos["frontend/vite.config.ts"] = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
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

    arquivos["frontend/tsconfig.json"] = """{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
"""

    arquivos["frontend/tsconfig.app.json"] = """{
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
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"]
}
"""

    arquivos["frontend/tsconfig.node.json"] = """{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
"""

    arquivos["frontend/.env.example"] = """VITE_API_BASE_URL=/api
VITE_APP_NAME=Engeradios CRM
"""

    arquivos["frontend/.gitignore"] = """node_modules
dist
.env
.env.local
.DS_Store
"""

    arquivos["frontend/README.md"] = """# Frontend React

Base criada na Etapa 27.

## Stack

- React
- TypeScript
- Vite
- Material UI
- React Router
- Axios

## Comandos

```bash
npm install
npm run dev
npm run build
npm run preview
```

## Observacao

Este frontend ainda nao substitui o legado EJS. A convivencia sera definida nas proximas etapas.
"""

    arquivos["frontend/src/main.tsx"] = """import React from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import { BrowserRouter } from 'react-router-dom';
import { App } from './app/App';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
"""

    arquivos["frontend/src/app/App.tsx"] = """import { AppThemeProvider } from './providers/AppThemeProvider';
import { AppRoutes } from '@/routes/AppRoutes';

export function App() {
  return (
    <AppThemeProvider>
      <AppRoutes />
    </AppThemeProvider>
  );
}
"""

    arquivos["frontend/src/app/providers/AppThemeProvider.tsx"] = """import { ReactNode, useMemo, useState } from 'react';
import { CssBaseline, ThemeProvider } from '@mui/material';
import { createAppTheme } from '@/shared/theme/theme';
import { ColorModeContext, ColorModeName } from '@/shared/theme/ColorModeContext';

const STORAGE_KEY = 'engeradios-color-mode';

function getInitialMode(): ColorModeName {
  const saved = window.localStorage.getItem(STORAGE_KEY);
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
        window.localStorage.setItem(STORAGE_KEY, next);
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

    arquivos["frontend/src/shared/theme/ColorModeContext.ts"] = """import { createContext, useContext } from 'react';

export type ColorModeName = 'light' | 'dark';

export interface ColorModeContextValue {
  mode: ColorModeName;
  toggleMode: () => void;
}

export const ColorModeContext = createContext<ColorModeContextValue>({
  mode: 'light',
  toggleMode: () => undefined
});

export function useColorMode() {
  return useContext(ColorModeContext);
}
"""

    arquivos["frontend/src/shared/theme/theme.ts"] = """import { createTheme } from '@mui/material/styles';
import { ColorModeName } from './ColorModeContext';

export function createAppTheme(mode: ColorModeName) {
  return createTheme({
    palette: {
      mode,
      primary: {
        main: '#b91c1c'
      },
      secondary: {
        main: '#2563eb'
      },
      background: {
        default: mode === 'light' ? '#f6f7fb' : '#0b1120',
        paper: mode === 'light' ? '#ffffff' : '#111827'
      }
    },
    shape: {
      borderRadius: 14
    },
    typography: {
      fontFamily: ['Roboto', 'Arial', 'sans-serif'].join(',')
    },
    components: {
      MuiButton: {
        defaultProps: {
          disableElevation: true
        },
        styleOverrides: {
          root: {
            textTransform: 'none',
            fontWeight: 700
          }
        }
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: 'none'
          }
        }
      }
    }
  });
}
"""

    arquivos["frontend/src/routes/AppRoutes.tsx"] = """import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/layouts/AppShell';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage';
import { CrmPage } from '@/features/crm/pages/CrmPage';
import { WhatsappPage } from '@/features/whatsapp/pages/WhatsappPage';
import { AdminPage } from '@/features/settings/pages/AdminPage';
import { SuperAdminPage } from '@/features/super-admin/pages/SuperAdminPage';

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
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
"""

    arquivos["frontend/src/layouts/AppShell.tsx"] = """import { useState } from 'react';
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
import { useColorMode } from '@/shared/theme/ColorModeContext';

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
        <Typography variant="h6" fontWeight={900} color="primary">
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
          <Typography variant="h6" fontWeight={800} sx={{ flexGrow: 1 }}>
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

    arquivos["frontend/src/shared/types/api.ts"] = """export interface ApiError {
  code: string;
  message: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error: ApiError | null;
}

export interface LegacyStatusResponse {
  success: boolean;
  empresaId?: number;
  connected?: boolean;
  status?: string;
  qr?: string | null;
}
"""

    arquivos["frontend/src/shared/services/httpClient.ts"] = """import axios from 'axios';

export const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  withCredentials: true,
  headers: {
    Accept: 'application/json'
  }
});

httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.localStorage.clear();
      window.sessionStorage.clear();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
"""

    arquivos["frontend/src/shared/components/PageHeader.tsx"] = """import { Box, Typography } from '@mui/material';

interface PageHeaderProps {
  title: string;
  description: string;
}

export function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h4" fontWeight={900} gutterBottom>
        {title}
      </Typography>
      <Typography color="text.secondary" sx={{ maxWidth: 760 }}>
        {description}
      </Typography>
    </Box>
  );
}
"""

    arquivos["frontend/src/features/auth/pages/LoginPage.tsx"] = """import { Box, Button, Card, CardContent, TextField, Typography } from '@mui/material';

export function LoginPage() {
  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2 }}>
      <Card sx={{ width: '100%', maxWidth: 420 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" fontWeight={900} gutterBottom>
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

    arquivos["frontend/src/features/dashboard/pages/DashboardPage.tsx"] = """import { useEffect, useState } from 'react';
import { Box, Button, Card, CardContent, Chip, Grid, Stack, Typography } from '@mui/material';
import { PageHeader } from '@/shared/components/PageHeader';
import { httpClient } from '@/shared/services/httpClient';
import { LegacyStatusResponse } from '@/shared/types/api';

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
      <Grid container spacing={2}>
        {cards.map((card) => (
          <Grid item xs={12} sm={6} lg={3} key={card.title}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography color="text.secondary" variant="body2" fontWeight={700}>
                  {card.title}
                </Typography>
                <Typography variant="h5" fontWeight={900} sx={{ mt: 1 }}>
                  {card.value}
                </Typography>
                <Typography color="text.secondary" sx={{ mt: 1 }}>
                  {card.text}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mt: 3 }}>
        <Button variant="contained" href="/crm">Abrir CRM</Button>
        <Button variant="outlined" href="/whatsapp">Gestao WhatsApp</Button>
        <Chip label="Etapa 27" color="primary" />
      </Stack>
    </Box>
  );
}
"""

    arquivos["frontend/src/features/crm/pages/CrmPage.tsx"] = """import { Card, CardContent, Typography } from '@mui/material';
import { PageHeader } from '@/shared/components/PageHeader';

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

    arquivos["frontend/src/features/whatsapp/pages/WhatsappPage.tsx"] = """import { Card, CardContent, Typography } from '@mui/material';
import { PageHeader } from '@/shared/components/PageHeader';

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

    arquivos["frontend/src/features/settings/pages/AdminPage.tsx"] = """import { Card, CardContent, Typography } from '@mui/material';
import { PageHeader } from '@/shared/components/PageHeader';

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

    arquivos["frontend/src/features/super-admin/pages/SuperAdminPage.tsx"] = """import { Card, CardContent, Typography } from '@mui/material';
import { PageHeader } from '@/shared/components/PageHeader';

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

    arquivos["frontend/src/vite-env.d.ts"] = """/// <reference types="vite/client" />
"""

    return arquivos


def aplicar_frontend():
    arquivos = arquivos_frontend()
    resultados = []
    for nome, texto in arquivos.items():
        antes = sha256(nome)
        gravar(nome, texto)
        depois = sha256(nome)
        resultados.append({
            "arquivo": nome,
            "alterado": antes != depois,
            "sha256_antes": antes,
            "sha256_depois": depois,
            "tamanho": len(texto)
        })
    return resultados


def atualizar_doc_obrigatorio(nome, titulo, linhas):
    atual = ler(nome)
    if atual is None:
        atual = "# " + nome.replace(".md", "") + "\n"
    ini = "<!-- ETAPA_27_INICIO -->"
    fim = "<!-- ETAPA_27_FIM -->"
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


def atualizar_documentacao():
    data = agora_iso()
    atualizar_doc_obrigatorio("CONTEXTO_PROJETO.md", "Etapa 27 - Base frontend React", [
        "Data: " + data,
        "",
        "Criada a base do frontend em frontend/ com React, TypeScript, Vite e Material UI.",
        "Criada estrutura modular inicial por app, routes, layouts, shared e features.",
        "Criado AppShell responsivo com Drawer, AppBar e tema claro/escuro.",
        "O frontend legado EJS nao foi substituido nesta etapa."
    ])
    atualizar_doc_obrigatorio("CHANGELOG.md", "Etapa 27 - Criacao do frontend React", [
        "Data: " + data,
        "",
        "Adicionada pasta frontend com base React.",
        "Adicionados arquivos de Vite, TypeScript, Material UI e rotas iniciais.",
        "Adicionados placeholders para login, dashboard, CRM, WhatsApp, admin e super admin.",
        "Nenhuma rota legada foi removida."
    ])
    atualizar_doc_obrigatorio("DECISOES_TECNICAS.md", "Etapa 27 - Decisoes do frontend React", [
        "Data: " + data,
        "",
        "Decidido criar o frontend novo em pasta isolada frontend/.",
        "Decidido usar Material UI com Emotion e ThemeProvider.",
        "Decidido usar Vite com proxy /api para o backend atual em desenvolvimento.",
        "Decidido manter coexistencia com o legado ate migracoes futuras."
    ])
    atualizar_doc_obrigatorio("PENDENCIAS.md", "Pendencias apos Etapa 27", [
        "Data: " + data,
        "",
        "Validar npm install e npm run build no frontend.",
        "Etapa 28: criar backend modular em paralelo.",
        "Etapa 29: padronizar respostas de API.",
        "Etapa 30: migrar login e sessao para o frontend React.",
        "Etapa 31: migrar dashboard definitivo."
    ])
    return DOCS_OBRIGATORIOS


def validar_sem_asterisco(nome, texto):
    achados = []
    for idx, linha in enumerate(texto.splitlines(), start=1):
        if chr(42) in linha:
            achados.append({"arquivo": nome, "linha": idx, "texto": linha[:300]})
    return achados


def validar_estrutura():
    obrigatorios = [
        "frontend/package.json",
        "frontend/index.html",
        "frontend/vite.config.ts",
        "frontend/tsconfig.json",
        "frontend/tsconfig.app.json",
        "frontend/src/main.tsx",
        "frontend/src/app/App.tsx",
        "frontend/src/layouts/AppShell.tsx",
        "frontend/src/routes/AppRoutes.tsx",
        "frontend/src/shared/theme/theme.ts",
        "frontend/src/shared/services/httpClient.ts",
        "frontend/src/features/dashboard/pages/DashboardPage.tsx",
        "frontend/src/features/whatsapp/pages/WhatsappPage.tsx",
        "frontend/src/features/crm/pages/CrmPage.tsx"
    ]
    itens = []
    erros = []
    for nome in obrigatorios:
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
    pkg = None
    try:
        pkg = json.loads(ler("frontend/package.json") or "{}")
    except Exception:
        pkg = {}
    deps = pkg.get("dependencies", {})
    dev_deps = pkg.get("devDependencies", {})
    checks = {
        "tem_react": "react" in deps,
        "tem_react_dom": "react-dom" in deps,
        "tem_mui": "@mui/material" in deps,
        "tem_emotion": "@emotion/react" in deps and "@emotion/styled" in deps,
        "tem_vite": "vite" in dev_deps,
        "tem_typescript": "typescript" in dev_deps,
        "tem_router": "react-router-dom" in deps,
        "tem_axios": "axios" in deps
    }
    ok = len(erros) == 0 and all(checks.values())
    return {"arquivos": itens, "checks": checks, "erros": erros, "ok": ok}


def npm_flags():
    install = os.environ.get("ETAPA27_NPM_INSTALL", "true").strip().lower()
    build = os.environ.get("ETAPA27_NPM_BUILD", "true").strip().lower()
    return {
        "install": install not in ["false", "0", "nao", "não", "no"],
        "build": build not in ["false", "0", "nao", "não", "no"]
    }


def executar_npm():
    flags = npm_flags()
    resultado = {
        "node_version": run_cmd(["node", "--version"], timeout=30),
        "npm_version": run_cmd(["npm", "--version"], timeout=30),
        "install_executado": flags["install"],
        "build_executado": False,
        "install": None,
        "build": None,
        "ok": True
    }
    if flags["install"]:
        resultado["install"] = run_cmd(["npm", "install"], cwd=FRONTEND_DIR, timeout=600)
        resultado["ok"] = resultado["ok"] and resultado["install"].get("ok", False)
    if flags["build"]:
        resultado["build_executado"] = True
        resultado["build"] = run_cmd(["npm", "run", "build"], cwd=FRONTEND_DIR, timeout=600)
        resultado["ok"] = resultado["ok"] and resultado["build"].get("ok", False)
    return resultado


def gerar_relatorio_md(relatorio):
    linhas = []
    linhas.append("# Etapa 27 - Criar base do frontend React")
    linhas.append("")
    linhas.append("Data: " + relatorio["gerado_em"])
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("- Backup criado em: " + relatorio["backup"]["destino"])
    linhas.append("- Manifesto antes: " + relatorio["manifesto_antes"])
    linhas.append("- Manifesto depois: " + relatorio["manifesto_depois"])
    linhas.append("- Arquivos frontend gravados: " + str(len(relatorio["frontend_arquivos"])))
    linhas.append("- Validacao estrutura OK: " + str(relatorio["validacao"]["ok"]))
    linhas.append("- npm install executado: " + str(relatorio["npm"]["install_executado"]))
    linhas.append("- npm build executado: " + str(relatorio["npm"]["build_executado"]))
    linhas.append("- npm OK: " + str(relatorio["npm"]["ok"]))
    linhas.append("- Documentacao obrigatoria atualizada: " + str(len(relatorio["docs_obrigatorios"])))
    linhas.append("")
    linhas.append("## Checks")
    linhas.append("")
    for chave, valor in relatorio["validacao"]["checks"].items():
        linhas.append("- " + chave + ": " + str(valor))
    linhas.append("")
    linhas.append("## Arquivos principais")
    linhas.append("")
    for item in relatorio["frontend_arquivos"][:40]:
        linhas.append("- " + item["arquivo"] + " alterado: " + str(item["alterado"]))
    linhas.append("")
    linhas.append("## Proxima etapa sugerida")
    linhas.append("")
    linhas.append("Etapa 28 - Criar backend modular em paralelo.")
    return "\n".join(linhas) + "\n"


def main():
    garantir_dirs()
    stamp = agora_stamp()
    backup_dir = BACKUPS_DIR / ("etapa_27_frontend_react_base_" + stamp)

    manifesto_antes = gerar_manifesto()
    manifesto_antes_path = REPORTS_DIR / "etapa_27_manifesto_antes.json"
    salvar_json(manifesto_antes_path, manifesto_antes)

    backup = criar_backup(backup_dir)
    frontend_arquivos = aplicar_frontend()
    docs_obrigatorios = atualizar_documentacao()
    validacao = validar_estrutura()
    npm = executar_npm()

    manifesto_depois = gerar_manifesto()
    manifesto_depois_path = REPORTS_DIR / "etapa_27_manifesto_depois.json"
    salvar_json(manifesto_depois_path, manifesto_depois)

    relatorio = {
        "gerado_em": agora_iso(),
        "raiz": str(ROOT),
        "backup": backup,
        "manifesto_antes": rel(manifesto_antes_path),
        "manifesto_depois": rel(manifesto_depois_path),
        "frontend_arquivos": frontend_arquivos,
        "docs_obrigatorios": docs_obrigatorios,
        "validacao": validacao,
        "npm": npm
    }

    json_path = REPORTS_DIR / "etapa_27_criar_frontend_react.json"
    md_path = REPORTS_DIR / "etapa_27_criar_frontend_react.md"
    salvar_json(json_path, relatorio)
    gravar(md_path, gerar_relatorio_md(relatorio))

    print("Etapa 27 concluida.")
    print("Backup: " + backup["destino"])
    print("Manifesto antes: " + rel(manifesto_antes_path))
    print("Manifesto depois: " + rel(manifesto_depois_path))
    print("Relatorio JSON: " + rel(json_path))
    print("Relatorio Markdown: " + rel(md_path))
    print("Arquivos frontend gravados: " + str(len(frontend_arquivos)))
    print("Validacao estrutura OK: " + str(validacao["ok"]))
    print("npm install executado: " + str(npm["install_executado"]))
    print("npm build executado: " + str(npm["build_executado"]))
    print("npm OK: " + str(npm["ok"]))
    print("Documentacao obrigatoria atualizada: " + str(len(docs_obrigatorios)))

    if not validacao["ok"] or not npm["ok"]:
        print("")
        print("Aviso: Etapa 27 nao validou completamente. Consulte o relatorio.")


if __name__ == "__main__":
    main()
