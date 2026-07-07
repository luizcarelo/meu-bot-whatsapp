import { ReactNode, useMemo, useState } from 'react';
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
