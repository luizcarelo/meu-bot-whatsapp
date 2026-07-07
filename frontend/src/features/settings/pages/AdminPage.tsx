import { Card, CardContent, Typography } from '@mui/material';
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
