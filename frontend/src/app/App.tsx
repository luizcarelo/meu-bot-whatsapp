import { AppThemeProvider } from './providers/AppThemeProvider';
import { AppRoutes } from '../routes/AppRoutes';

export function App() {
  return (
    <AppThemeProvider>
      <AppRoutes />
    </AppThemeProvider>
  );
}
