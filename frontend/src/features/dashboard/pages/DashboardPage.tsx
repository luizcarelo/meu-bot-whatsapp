import { useEffect, useState } from 'react';
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
