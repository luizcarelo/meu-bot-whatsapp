import { Card, CardContent, Typography } from '@mui/material';
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
