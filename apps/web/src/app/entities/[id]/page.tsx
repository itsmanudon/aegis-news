import { EntityDetail } from "@/components/pages/entities";
export const metadata = { title: "Entity detail" };
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <EntityDetail id={id} />;
}
