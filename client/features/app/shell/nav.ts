import {
  ChartColumnIcon,
  ClipboardCheckIcon,
  DatabaseIcon,
  FileTextIcon,
  GitPullRequestArrowIcon,
  LayoutDashboardIcon,
  ScaleIcon,
  ScrollTextIcon,
  ShieldCheckIcon,
  UsersIcon,
  type LucideIcon,
} from "lucide-react";

export type NavGroup = "kerja" | "pantau" | "tata-kelola" | "administrasi";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  permission: string;
  group: NavGroup;
};

export const GROUP_LABELS: Record<NavGroup, string> = {
  kerja: "Alur kerja",
  pantau: "Pemantauan",
  "tata-kelola": "Tata kelola",
  administrasi: "Administrasi",
};

export const GROUP_ORDER: NavGroup[] = ["kerja", "pantau", "tata-kelola", "administrasi"];

export const NAV_ITEMS: NavItem[] = [
  { href: "/dasbor", label: "Dasbor", icon: LayoutDashboardIcon, permission: "claim:read", group: "kerja" },
  { href: "/klaim", label: "Klaim", icon: FileTextIcon, permission: "claim:read", group: "kerja" },
  { href: "/tinjauan", label: "Antrean tinjauan", icon: ClipboardCheckIcon, permission: "review:read", group: "kerja" },
  { href: "/sumber-bukti", label: "Sumber bukti", icon: DatabaseIcon, permission: "source:read", group: "kerja" },
  { href: "/metrik", label: "Metrik mutu", icon: ChartColumnIcon, permission: "metrics:read", group: "pantau" },
  { href: "/audit", label: "Log audit", icon: ScrollTextIcon, permission: "audit:read", group: "pantau" },
  { href: "/aturan", label: "Aturan bukti", icon: ScaleIcon, permission: "rule:read", group: "tata-kelola" },
  { href: "/kebijakan", label: "Kebijakan tier", icon: ShieldCheckIcon, permission: "rule:read", group: "tata-kelola" },
  { href: "/usulan-aturan", label: "Usulan pembaruan", icon: GitPullRequestArrowIcon, permission: "rule:read", group: "tata-kelola" },
  { href: "/pengguna", label: "Pengguna", icon: UsersIcon, permission: "user:manage", group: "administrasi" },
];

export function visibleNav(can: (permission: string) => boolean): NavItem[] {
  return NAV_ITEMS.filter((item) => can(item.permission));
}

export function defaultRoute(permissions: readonly string[]): string {
  const granted = new Set(permissions);
  const first = NAV_ITEMS.find((item) => granted.has(item.permission));
  return first ? first.href : "/akun";
}

export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
