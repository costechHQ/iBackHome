import { EvidenceGallery } from "@/features/dashboard/evidence-gallery";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<{ milestone?: string }> };

// WEB-CLIENT-010 (?milestone= opens it filtered to that milestone)
export default async function EvidencePage({ params, searchParams }: Props) {
  const { id } = await params;
  const { milestone } = await searchParams;
  return <EvidenceGallery projectId={id} initialMilestone={milestone ?? ""} />;
}
