"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/admin/skills", label: "Skills" },
  { href: "/admin/scenarios", label: "Scenarios" },
  { href: "/admin/sessions", label: "Sessions" },
  { href: "/admin/audit-log", label: "Audit Log" },
];

export function AdminNav() {
  const pathname = usePathname();

  return (
    <nav
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 12,
        alignItems: "center",
        padding: "12px 0",
      }}
      aria-label="Admin navigation"
    >
      <div style={{ fontWeight: 700, fontSize: 16 }}>Admin</div>
      {navItems.map((item) => {
        const active = pathname?.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            style={{
              padding: "8px 12px",
              borderRadius: 10,
              border: active ? "1px solid #2f2a24" : "1px solid #d9d3cb",
              background: active ? "#2f2a24" : "#f7f3ec",
              color: active ? "#f7f3ec" : "#2f2a24",
              textDecoration: "none",
              fontWeight: 600,
            }}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
