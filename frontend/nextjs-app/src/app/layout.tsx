import "./globals.css";
import { ClientShell } from "@/components/ClientShell";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        suppressHydrationWarning
        style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#f8fafc" }}
      >
        <ClientShell>{children}</ClientShell>
      </body>
    </html>
  );
}
