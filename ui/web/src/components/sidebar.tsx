"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Mission Control", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0h4" },
  { href: "/catalog", label: "Catalog", icon: "M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7M4 7l8-4 8 4M4 7l8 4 8-4" },
  { href: "/pipelines", label: "Pipelines", icon: "M13 10V3L4 14h7v7l9-11h-7z" },
  { href: "/query", label: "Query", icon: "M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 h-screen bg-[var(--sidebar-bg)] border-r border-[var(--border)] flex flex-col fixed left-0 top-0">
      <div className="p-5 border-b border-[var(--border)]">
        <h1 className="text-xl font-bold tracking-tight">
          <span className="text-nova-400">Nova</span>
        </h1>
        <p className="text-xs text-gray-500 mt-0.5">Data Platform</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-nova-600/20 text-nova-400"
                  : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
              }`}
            >
              <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
              </svg>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-[var(--border)]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-xs text-gray-500">All systems operational</span>
        </div>
      </div>
    </aside>
  );
}
