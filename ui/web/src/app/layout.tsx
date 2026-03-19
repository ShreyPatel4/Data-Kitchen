import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/sidebar";

export const metadata: Metadata = {
  title: "Nova - Data Platform",
  description: "AI-driven data platform — connect sources, model data, ship dashboards in one day",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 ml-60 p-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
