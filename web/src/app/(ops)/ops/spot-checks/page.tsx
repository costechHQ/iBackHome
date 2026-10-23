import { environmentName } from "@/common/layout/shell-data";
import { SpotChecks } from "@/features/ops-console/spot-checks";

type Props = { searchParams: Promise<{ project?: string }> };

// WEB-OPS-007 (?project= picks the project, from a project's "Book one")
export default async function SpotChecksPage({ searchParams }: Props) {
  const { project } = await searchParams;
  return <SpotChecks environment={environmentName()} initialProject={project ?? null} />;
}
