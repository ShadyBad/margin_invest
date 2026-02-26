import { SignJWT } from "jose"

const SERVICE_AUTH_SECRET = process.env.SERVICE_AUTH_SECRET || ""

export async function signServiceToken(
  userId: string,
  email?: string | null,
): Promise<string> {
  if (!SERVICE_AUTH_SECRET) {
    return ""
  }

  const secret = new TextEncoder().encode(SERVICE_AUTH_SECRET)

  return new SignJWT({ sub: userId, email: email ?? undefined })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("60s")
    .sign(secret)
}
