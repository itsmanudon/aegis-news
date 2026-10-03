import { DocumentDetail } from "@/components/pages/document-detail";
export const metadata = { title: "Document detail" };
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DocumentDetail id={id} />;
}
