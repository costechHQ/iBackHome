import { redirect } from "next/navigation";

type Props = { params: Promise<{ id: string }> };

// The contractor's project opens on its milestones (the only project tab built so far).
export default async function ContractorProjectPage({ params }: Props) {
  const { id } = await params;
  redirect(`/c/projects/${id}/milestones`);
}
