import {NextRequest, NextResponse} from "next/server";

const COOKIE_NAME = "cw_user_email";
const MAX_AGE_SECONDS = 60 * 60 * 24 * 30; // 30 days

export async function POST(request: NextRequest) {
  const body = (await request.json()) as {email?: string};
  const email = typeof body.email === "string" ? body.email.trim() : "";
  if (!email) {
    return NextResponse.json({error: "missing email"}, {status: 400});
  }

  const response = NextResponse.json({ok: true});
  response.cookies.set(COOKIE_NAME, email, {
    path: "/",
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: MAX_AGE_SECONDS,
  });
  return response;
}
