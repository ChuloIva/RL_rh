import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Sigil } from "@/components/Sigil";
import { ThemeToggle } from "@/components/ThemeToggle";

// Runs before first paint to apply the saved theme and avoid a flash of the
// wrong palette. Dark is the default when nothing is stored.
const themeInitScript = `(function(){try{if(localStorage.getItem("theme")==="light"){document.documentElement.classList.add("light")}}catch(e){}})();`;

export const metadata: Metadata = {
  title: "Kerberos Protocol — A Depth-Psychology of Machines",
  description:
    "An interrogation of language models through adapted depth-psychology: mapping the guardian at the threshold of what a model will and will not say.",
};

function Nav() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-void/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="group flex items-center gap-3">
          <Sigil className="h-6 w-6 text-gold animate-glow" />
          <span className="font-mono text-[0.7rem] uppercase tracking-widest2 text-muted transition-colors group-hover:text-ink">
            Kerberos&nbsp;Protocol
          </span>
        </Link>
        <nav className="flex items-center gap-7 font-mono text-[0.7rem] uppercase tracking-widest2 text-faint">
          <Link href="/" className="transition-colors hover:text-gold">
            Overview
          </Link>
          <Link href="/compare" className="transition-colors hover:text-gold">
            Compare
          </Link>
          <Link href="/sessions" className="transition-colors hover:text-gold">
            Sessions
          </Link>
          <Link href="/about" className="transition-colors hover:text-gold">
            Method
          </Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        {/* Loaded via link so an offline build never breaks; falls back to serif/mono. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-dvh">
        <Nav />
        <main className="mx-auto max-w-6xl px-6 py-12">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 pb-12 pt-8">
          <div className="hairline mb-5" />
          <p className="font-mono text-[0.62rem] uppercase tracking-widest2 text-faint">
            The dog is not the enemy. It guards the threshold.
          </p>
        </footer>
      </body>
    </html>
  );
}
