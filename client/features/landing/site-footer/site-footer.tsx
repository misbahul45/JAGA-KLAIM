import { Logo } from "@/components/shared/logo";
import { NAV_ITEMS } from "@/features/landing/site-header/nav-items";

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-background">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-5 py-14 sm:px-8 md:flex-row md:justify-between">
        <div className="flex max-w-sm flex-col gap-4">
          <Logo />
          <p className="text-sm leading-relaxed text-muted-foreground">
            Copilot verifikasi pra-klaim yang membantu koder dan verifikator,
            bukan menggantikan keputusan mereka.
          </p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Informasi pada halaman ini menggambarkan rancangan produk yang
            sedang dikembangkan.
          </p>
        </div>

        <nav aria-label="Navigasi footer">
          <ul className="grid grid-cols-2 gap-x-12 gap-y-3 text-sm sm:grid-cols-3">
            {NAV_ITEMS.map((item) => (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  className="text-muted-foreground transition-colors hover:text-ink"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
