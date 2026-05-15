import "@copilotkit/react-ui/styles.css"
import "./globals.css"

export const metadata = {
  title: "JARVIS v2 — Cognitive Runtime",
  description: "Proactive personal AI with world-state awareness",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta name="theme-color" content="#050b14" />
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body>{children}</body>
    </html>
  )
}
