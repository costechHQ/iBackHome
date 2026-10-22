import { SiteMap } from "@/features/dashboard/site-map";

type Props = { params: Promise<{ id: string }> };

// WEB-CLIENT-012
export default async function SiteMapPage({ params }: Props) {
  const { id } = await params;
  return <SiteMap projectId={id} />;
}
