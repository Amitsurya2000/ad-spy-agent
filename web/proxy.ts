import { NextRequest, NextResponse } from "next/server";

// Lightweight shared-password gate: this dashboard triggers real scrape jobs
// and spends Gemini quota, so a bare public Vercel URL shouldn't be left
// wide open. Standard browser Basic Auth prompt - no login page needed.
// Set DASHBOARD_PASSWORD to enable; leave unset to disable (e.g. local dev).
export function proxy(req: NextRequest) {
  const password = process.env.DASHBOARD_PASSWORD;
  if (!password) {
    return NextResponse.next();
  }

  const authHeader = req.headers.get("authorization");
  if (authHeader?.startsWith("Basic ")) {
    try {
      const decoded = atob(authHeader.slice(6));
      const suppliedPassword = decoded.slice(decoded.indexOf(":") + 1);
      if (suppliedPassword === password) {
        return NextResponse.next();
      }
    } catch {
      // fall through to the 401 below
    }
  }

  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Ad Spy Agent"' },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
