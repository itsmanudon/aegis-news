import { MultimediaFeed } from "@/components/multimedia";
import { PageHeading } from "@/components/ui/console";
export default function Page() {
  return (
    <>
      <PageHeading
        title="Multimedia news"
        description="Provider articles, publisher image references and refreshable YouTube metadata."
      />
      <MultimediaFeed />
    </>
  );
}
