import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const TITLE = "JAGA-KLAIM | AI-powered pre-claim verification copilot";
const DESCRIPTION =
  "JAGA-KLAIM membantu koder dan verifikator internal fasilitas kesehatan memeriksa konsistensi coding dengan bukti klinis dan operasional sebelum klaim diajukan, tanpa mengambil alih keputusan manusia.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  applicationName: "JAGA-KLAIM",
  openGraph: {
    type: "website",
    locale: "id_ID",
    siteName: "JAGA-KLAIM",
    title: TITLE,
    description: DESCRIPTION,
  },
};

export const viewport: Viewport = {
  themeColor: "#f8fafd",
  colorScheme: "light",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="id"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <a
          href="#konten-utama"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white"
        >
          Lompat ke konten utama
        </a>
        {children}
      </body>
    </html>
  );
}
