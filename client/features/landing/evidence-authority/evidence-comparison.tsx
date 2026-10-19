"use client";

import { QuoteIcon } from "lucide-react";

const ROWS = [
  {
    dot: "bg-brand",
    title: "Bukti yang dibutuhkan",
    text: "Hasil laboratorium yang mendukung diagnosis.",
  },
  {
    dot: "bg-mint",
    title: "Hasil pencarian",
    text: "Bukti tidak ditemukan pada sumber yang diizinkan.",
  },
  {
    dot: "bg-orange",
    title: "Perlu ditinjau",
    text: "Satu bukti belum ditemukan. Verifikator perlu memeriksanya.",
  },
] as const;

export function EvidenceComparison() {
  return (
    <figure className="m-0">
      <div className="rounded-2xl bg-white p-5 ring-1 ring-line sm:p-6">
        <ul className="flex flex-col gap-5">
          {ROWS.map((row, index) => (
            <li
              key={row.title}
              className="flex items-start gap-3"
            >
              <span
                aria-hidden="true"
                className={`mt-1 size-2.5 shrink-0 rounded-full ${row.dot}`}
              />

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-ink">
                    {row.title}
                  </p>

                  <span className="text-xs text-muted-foreground">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>

                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  {row.text}
                </p>
              </div>
            </li>
          ))}
        </ul>

        <div className="mt-6 flex items-start gap-3 rounded-xl bg-surface-2 p-4">
          <QuoteIcon
            className="mt-0.5 size-4 shrink-0 text-brand"
            aria-hidden="true"
          />

          <div>
            <p className="text-sm font-semibold text-ink">
              Sumber bukti
            </p>

            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              Temuan perlu dilengkapi rujukan ke sumber yang diizinkan
              dan kutipan yang relevan jika tersedia.
            </p>
          </div>
        </div>
      </div>

      <figcaption className="mt-3 text-xs leading-relaxed text-muted-foreground">
        Ilustrasi, bukan data klaim nyata. Bukti yang tidak ditemukan
        tidak otomatis berarti pelayanan tidak dilakukan.
      </figcaption>
    </figure>
  );
}