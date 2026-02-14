import NextAuth from "next-auth"
import GitHub from "next-auth/providers/github"

const authConfig = {
  providers: [GitHub],
}

const { handlers } = NextAuth(authConfig)

export const GET = handlers.GET
export const POST = handlers.POST
