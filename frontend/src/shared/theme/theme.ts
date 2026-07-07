import { createTheme } from '@mui/material/styles';
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
