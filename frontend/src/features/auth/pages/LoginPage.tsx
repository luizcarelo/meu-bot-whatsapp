import { Box, Button, Card, CardContent, TextField, Typography } from '@mui/material';

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
