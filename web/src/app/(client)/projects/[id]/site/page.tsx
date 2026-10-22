import { SiteEditor } from "@/features/projects/site-editor";

type Props = { params: Promise<{ id: string }> };

// WEB-CLIENT-004
export default async function Page({ params }: Props) {
  const { id } = await params;
  return <SiteEditor projectId={id} />;
}
