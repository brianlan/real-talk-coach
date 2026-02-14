import { useAuthContext } from "@/app/providers/auth-provider";

export function useUser() {
  const context = useAuthContext();
  return context;
}
