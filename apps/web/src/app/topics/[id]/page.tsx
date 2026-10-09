import { TopicDetail } from "@/components/pages/topics";
export const metadata = { title: "Topic Intelligence" };
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <TopicDetail id={id} />;
}
