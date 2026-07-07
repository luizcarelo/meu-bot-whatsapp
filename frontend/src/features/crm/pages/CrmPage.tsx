import { Card, CardContent, Typography } from '@mui/material';
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
