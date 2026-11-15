import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'REXO · Your care, understood', description: 'A synthetic patient safety demo. Understand your visit, ask questions, and make your voice heard.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
