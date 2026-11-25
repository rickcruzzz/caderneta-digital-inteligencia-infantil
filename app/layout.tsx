import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Caderneta Digital",
  description: "Inteligência de dados, monitoramento e continuidade do cuidado infantil.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
