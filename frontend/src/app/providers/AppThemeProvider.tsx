import { ReactNode, useMemo, useState } from 'react';
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
