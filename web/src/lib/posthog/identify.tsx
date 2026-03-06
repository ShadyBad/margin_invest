"use client";

import { useSession } from "next-auth/react";
import { useEffect } from "react";
import posthog from "posthog-js";

export function PostHogIdentify() {
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status === "authenticated" && session?.userId) {
      posthog.identify(session.userId, {
        email: session.user?.email,
      });
      if (session.user?.email) {
        posthog.alias(session.user.email);
      }
    } else if (status === "unauthenticated") {
      posthog.reset();
    }
  }, [session, status]);

  return null;
}
