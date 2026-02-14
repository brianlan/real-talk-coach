import NextAuth from "next-auth"
import GitHub from "next-auth/providers/github"

const authConfig = {
  providers: [
    GitHub({
      clientId: process.env.GITHUB_ID,
      clientSecret: process.env.GITHUB_SECRET,
    }),
  ],
}

const { handlers } = NextAuth(authConfig)

export const GET = handlers.GET
export const POST = handlers.POST
