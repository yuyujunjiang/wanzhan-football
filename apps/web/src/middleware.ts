import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const SESSION_COOKIE = "fc_session";
const LOGIN = "/wanzhan/login";

function redirectToLogin(request: NextRequest, clearSession: boolean) {
  const url = request.nextUrl.clone();
  url.pathname = LOGIN;
  url.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  const res = NextResponse.redirect(url);
  if (clearSession) {
    res.cookies.delete(SESSION_COOKIE);
  }
  return res;
}

async function sessionIsValid(request: NextRequest): Promise<boolean> {
  const cookie = request.cookies.get(SESSION_COOKIE)?.value;
  if (!cookie) return false;

  const meUrl = new URL("/api/auth/me", request.url);
  try {
    const res = await fetch(meUrl, {
      headers: { cookie: `${SESSION_COOKIE}=${cookie}` },
      cache: "no-store",
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!pathname.startsWith("/wanzhan")) {
    return NextResponse.next();
  }

  const onLogin = pathname === LOGIN || pathname.startsWith(`${LOGIN}/`);
  const hasCookie = request.cookies.has(SESSION_COOKIE);

  if (onLogin) {
    if (hasCookie && (await sessionIsValid(request))) {
      const url = request.nextUrl.clone();
      url.pathname = "/wanzhan/matches";
      url.search = "";
      return NextResponse.redirect(url);
    }
    if (hasCookie) {
      return redirectToLogin(request, true);
    }
    return NextResponse.next();
  }

  if (!hasCookie) {
    return redirectToLogin(request, false);
  }

  if (!(await sessionIsValid(request))) {
    return redirectToLogin(request, true);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/wanzhan/:path*"],
};
