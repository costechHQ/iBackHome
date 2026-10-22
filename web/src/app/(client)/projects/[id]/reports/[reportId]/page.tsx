import { ReportViewer } from "@/features/reports/reports";

type Props = { params: Promise<{ id: string; reportId: string }> };

// WEB-CLIENT-018 (report viewer)
export default async function ReportPage({ params }: Props) {
  const { id, reportId } = await params;
  return <ReportViewer projectId={id} reportId={reportId} />;
}
