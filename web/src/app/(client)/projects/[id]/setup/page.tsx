import { SetupTracker } from "@/features/projects/setup-tracker";

type Props = { params: Promise<{ id: string }> };

// WEB-CLIENT-003 CS-05
export default async function Page({ params }: Props) {
  const { id } = await params;
  return <SetupTracker projectId={id} />;
}
