import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PSX Investment Dashboard",
  description: "Automated analysis agents for Pakistan Stock Exchange",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
