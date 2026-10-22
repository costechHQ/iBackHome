import { ReportsList } from "@/features/reports/reports";

type Props = { params: Promise<{ id: string }> };

// WEB-CLIENT-018 (list)
export default async function ReportsPage({ params }: Props) {
  const { id } = await params;
  return <ReportsList projectId={id} />;
}
