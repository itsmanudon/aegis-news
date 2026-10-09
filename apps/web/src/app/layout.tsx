import type { Metadata } from "next";
import localFont from "next/font/local";
import { Providers } from "@/components/providers";
import { Shell } from "@/components/shell";
import "./globals.css";
const editorial = localFont({
  src: [
    {
      path: "./fonts/SourceSerif4Variable-Roman.woff2",
      weight: "200 900",
      style: "normal",
    },
  ],
  variable: "--font-editorial",
  display: "swap",
  fallback: ["Georgia"],
  adjustFontFallback: "Times New Roman",
});
const editorialItalic = localFont({
  src: "./fonts/SourceSerif4Variable-Italic.woff2",
  weight: "200 900",
  style: "italic",
  variable: "--font-editorial-italic",
  display: "swap",
  preload: false,
  fallback: ["Georgia"],
  adjustFontFallback: "Times New Roman",
});
const interfaceFont = localFont({
  src: "./fonts/InterVariable.woff2",
  weight: "100 900",
  variable: "--font-interface",
  display: "swap",
  fallback: ["Arial"],
});
export const metadata: Metadata = {
  title: {
    default: "Discover · Aegis News",
    template: "%s · AegisNews",
  },
  description:
    "Discover source reporting, explore intelligence, and inspect the evidence.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${editorial.variable} ${editorialItalic.variable} ${interfaceFont.variable}`}
    >
      <body>
        <Providers>
          <Shell>{children}</Shell>
        </Providers>
      </body>
    </html>
  );
}
