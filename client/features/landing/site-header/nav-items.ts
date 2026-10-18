export const NAV_ITEMS = [
  { id: "masalah", label: "Masalah" },
  { id: "cara-kerja", label: "Cara Kerja" },
  { id: "risiko", label: "Risiko" },
  { id: "bukti", label: "Bukti" },
  { id: "tata-kelola", label: "Tata Kelola" },
  { id: "faq", label: "FAQ" },
] as const;

export type NavItemId = (typeof NAV_ITEMS)[number]["id"];
