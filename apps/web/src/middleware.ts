import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const SESSION_COOKIE = "fc_session";
const LOGIN = "/wanzhan/login";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!pathname.startsWith("/wanzhan")) {
    return NextResponse.next();
  }

  const onLogin = pathname === LOGIN || pathname.startsWith(`${LOGIN}/`);
  const hasSession = request.cookies.has(SESSION_COOKIE);

  if (onLogin) {
    if (hasSession) {
      const url = request.nextUrl.clone();
      url.pathname = "/wanzhan/matches";
      url.search = "";
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  if (!hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = LOGIN;
    url.searchParams.set("next", pathname + request.nextUrl.search);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/wanzhan/:path*"],
};
