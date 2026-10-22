import { EvidenceGallery } from "@/features/dashboard/evidence-gallery";

type Props = { params: Promise<{ id: string }> };

// WEB-CLIENT-010
export default async function EvidencePage({ params }: Props) {
  const { id } = await params;
  return <EvidenceGallery projectId={id} />;
}
