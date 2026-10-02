import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "AegisNews · Foundation",
  description: "Secure Multimodal News Intelligence Platform foundation",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
