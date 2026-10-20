"use client";

import { FilePenLine, FileSearch, House, KeyRound, ListChecks, Moon, Search, ShieldCheck, Stamp, Sun } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useRef, useState } from "react";
import { Logo } from "@/components/logo";
import { TransitionLink } from "@/components/transition-link";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview", icon: House },
  { href: "/projects", label: "Project quality", icon: FileSearch },
  { href: "/retire", label: "Retire credits", icon: Stamp },
  { href: "/verify", label: "Verify", icon: ShieldCheck },
  { href: "/auditor", label: "Auditor", icon: KeyRound },
  { href: "/assess", label: "Assess", icon: FilePenLine },
  { href: "/review", label: "Review", icon: ListChecks },
];

/** Item size + gap on the rail; the active highlight slides by this step. */
const STEP = 58;

function useActiveIndex() {
  const pathname = usePathname();
  return NAV.findIndex((item) => (item.href === "/" ? pathname === "/" : pathname.startsWith(item.href)));
}

const railButton =
  "group relative z-10 grid size-12 shrink-0 place-items-center rounded-2xl text-rail-foreground transition-colors duration-300 hover:bg-rail-hover hover:text-white aria-[current=page]:text-rail-active-foreground aria-[current=page]:hover:bg-transparent aria-[current=page]:hover:text-rail-active-foreground [&_svg]:size-5";

function Tooltip({ children }: { children: React.ReactNode }) {
  return (
    <span
      role="tooltip"
      className="pointer-events-none absolute top-1/2 left-full z-20 ml-4 -translate-x-1 -translate-y-1/2 rounded-lg bg-foreground px-2.5 py-1.5 text-xs font-semibold whitespace-nowrap text-background opacity-0 shadow-lg transition-[opacity,transform] duration-200 group-hover:translate-x-0 group-hover:opacity-100 group-focus-visible:translate-x-0 group-focus-visible:opacity-100"
    >
      {children}
    </span>
  );
}

function RailThemeToggle({ className, tooltip = true }: { className?: string; tooltip?: boolean }) {
  const { resolvedTheme, setTheme } = useTheme();
  return (
    <button
      type="button"
      aria-label="Toggle dark mode"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      className={cn(railButton, "cursor-pointer", className)}
    >
      <Sun aria-hidden className="hidden dark:block" />
      <Moon aria-hidden className="dark:hidden" />
      {tooltip && <Tooltip>Light / dark</Tooltip>}
    </button>
  );
}

/** Floating icon rail on the left (desktop) and a bottom bar on phones. */
export function SideRail() {
  const active = useActiveIndex();

  return (
    <>
      {/* Desktop rail */}
      <aside
        aria-label="Main navigation"
        className="animate-fade fixed top-4 bottom-4 left-4 z-40 hidden w-[72px] flex-col items-center rounded-[26px] bg-rail py-4 shadow-[0_20px_50px_-24px_rgba(8,20,15,0.65)] ring-1 ring-white/5 transition-colors duration-300 md:flex"
      >
        <TransitionLink
          href="/"
          aria-label="OnceSealed home"
          className="mb-6 grid size-12 place-items-center rounded-2xl text-[#9fe0c2] hover:text-white"
        >
          <Logo className="size-7" />
        </TransitionLink>

        <nav className="relative flex flex-col gap-2.5">
          {active >= 0 && (
            <span
              aria-hidden
              className="absolute top-0 left-0 size-12 rounded-2xl bg-rail-active shadow-[0_6px_16px_-8px_rgba(0,0,0,0.5)] transition-[transform,background-color] duration-500 ease-[cubic-bezier(.2,.7,.2,1)]"
              style={{ transform: `translateY(${active * STEP}px)` }}
            />
          )}
          {NAV.map((item, i) => (
            <TransitionLink
              key={item.href}
              href={item.href}
              aria-label={item.label}
              aria-current={i === active ? "page" : undefined}
              className={railButton}
            >
              <item.icon aria-hidden />
              <Tooltip>{item.label}</Tooltip>
            </TransitionLink>
          ))}
        </nav>

        <div className="mt-auto flex flex-col items-center gap-2.5">
          <span aria-hidden className="mb-1 h-px w-8 bg-white/10" />
          <RailThemeToggle />
        </div>
      </aside>

      {/* Phone bottom bar */}
      <nav
        aria-label="Main navigation"
        className="fixed inset-x-3 bottom-3 z-40 flex items-center justify-between rounded-[22px] bg-rail px-2 py-2 shadow-[0_16px_40px_-20px_rgba(8,20,15,0.7)] md:hidden"
      >
        {NAV.map((item, i) => (
          <TransitionLink
            key={item.href}
            href={item.href}
            aria-label={item.label}
            aria-current={i === active ? "page" : undefined}
            className={cn(railButton, "aria-[current=page]:bg-rail-active")}
          >
            <item.icon aria-hidden />
          </TransitionLink>
        ))}
        <RailThemeToggle tooltip={false} />
      </nav>
    </>
  );
}

/** Lookup box: retirement number or serial → /verify. Ctrl/⌘ K focuses it. */
function LookupSearch() {
  const router = useRouter();
  const ref = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        ref.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <form
      role="search"
      className="relative w-full max-w-[380px]"
      onSubmit={(e) => {
        e.preventDefault();
        const q = value.trim().replace(/^#/, "");
        if (!q) return;
        router.push(`/verify?q=${encodeURIComponent(q)}`);
        setValue("");
        ref.current?.blur();
      }}
    >
      <label htmlFor="lookup" className="sr-only">
        Look up a retirement number or serial
      </label>
      <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3.5 z-10 size-4 -translate-y-1/2 text-muted-foreground" />
      <input
        ref={ref}
        id="lookup"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        autoComplete="off"
        placeholder="Look up retirement # or serial…"
        className="min-h-11 w-full rounded-2xl border border-white/50 bg-card/70 pr-16 pl-10 text-sm text-foreground shadow-[0_8px_24px_-16px_rgba(10,30,22,0.5)] backdrop-blur-md transition-[background-color,border-color,box-shadow] duration-300 placeholder:text-muted-foreground focus:bg-card dark:border-white/10"
      />
      <kbd className="pointer-events-none absolute top-1/2 right-3 z-10 -translate-y-1/2 rounded-md border border-border bg-secondary px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
        Ctrl K
      </kbd>
    </form>
  );
}

export function TopBar() {
  return (
    <div className="animate-fade mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-x-6 gap-y-3 px-6 pt-5 md:px-8">
      <div className="flex items-center gap-3 md:hidden">
        <Logo className="size-7 text-primary" />
        <span className="text-[17px] font-bold">OnceSealed</span>
      </div>
      <LookupSearch />
      <div className="flex flex-wrap items-center gap-2">
        <Badge
          className="bg-card/70 backdrop-blur-md"
          title="Prototype: Ethereum Sepolia testnet · simulated serials · fictional buyers · no real credits retired"
        >
          Prototype · simulated serials
        </Badge>
        <Badge className="bg-card/70 backdrop-blur-md">
          <span aria-hidden className="size-2 rounded-full bg-warn" />
          Sepolia testnet
        </Badge>
      </div>
    </div>
  );
}
