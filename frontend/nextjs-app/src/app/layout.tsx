export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#f8fafc" }}>
        <header style={{ background: "#0f172a", color: "white", padding: "1rem 2rem" }}>
          <h1 style={{ margin: 0, fontSize: "1.25rem" }}>RFP Response Accelerator</h1>
          <p style={{ margin: "0.25rem 0 0", opacity: 0.8, fontSize: "0.875rem" }}>
            AI reuses institutional knowledge safely
          </p>
        </header>
        <main style={{ maxWidth: 1200, margin: "0 auto", padding: "2rem" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
