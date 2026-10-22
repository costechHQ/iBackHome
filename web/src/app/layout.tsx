import type { Metadata } from "next";
import type { ReactNode } from "react";

import { fontVariables } from "@/common/theme/fonts";

import "./globals.css";

export const metadata: Metadata = {
  title: "iBackHome",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={fontVariables}>
      <body>{children}</body>
    </html>
  );
}
