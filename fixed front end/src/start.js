import { createStart } from "@tanstack/react-start";
import { authMiddleware, base44RequestMiddleware } from "@/lib/auth-middleware";

// Every server function and server route gets `context.getBase44()`, acting as the visitor.
// Base44's error capture (src/lib/error-capture*.js) needs Cloudflare Workers, so it is off on Vercel.
export const startInstance = createStart(() => ({
  requestMiddleware: [base44RequestMiddleware],
  functionMiddleware: [authMiddleware],
}));
