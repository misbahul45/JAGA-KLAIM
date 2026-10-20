"use client";

import { DatabaseIcon, PencilIcon, PlusIcon } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { Field } from "@/components/shared/field";
import { OptionSelect } from "@/components/shared/option-select";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import type { Source } from "@/lib/api-types";
import { formatDateTime, formatNumber, toIsoFromLocal, toLocalInput } from "@/lib/format";

import { useAuth } from "../auth/auth-context";
import { ConfirmDialog } from "../shared/confirm-dialog";
import { STATUS_TABLES } from "../shared/labels";
import { QueryBoundary } from "../shared/query-boundary";
import { RequirePermission } from "../shared/require-permission";
import { StatusBadge } from "../shared/status-badge";

const SOURCE_TYPES = ["emr", "lis", "ris", "farmasi", "keperawatan", "manual_simulasi"].map((value) => ({
  value,
  label: value,
}));
const HEALTH_OPTIONS = Object.entries(STATUS_TABLES.health).map(([value, entry]) => ({ value, label: entry.label }));

function parseObject(text: string): { value: Record<string, unknown> | null; error: string | null } {
  if (!text.trim()) return { value: {}, error: null };
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { value: null, error: "Harus berupa objek JSON" };
    }
    return { value: parsed as Record<string, unknown>, error: null };
  } catch {
    return { value: null, error: "JSON tidak valid" };
  }
}

function CreateSourceDialog({ onDone }: { onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState("emr");
  const [ref, setRef] = useState("");
  const [hours, setHours] = useState("24");
  const [coverage, setCoverage] = useState("");
  const parsed = parseObject(coverage);
  const save = useAction(() =>
    apiFetch<Source>("/v1/evidence-sources", {
      method: "POST",
      json: {
        source_type: type,
        system_ref: ref.trim(),
        freshness_sla_seconds: Math.round(Number(hours) * 3600),
        coverage: parsed.value ?? {},
      },
    }),
  );
  const hoursValid = Number(hours) >= 1 / 60 && Number(hours) <= 8760;

  return (
    <>
      <Button
        variant="brand"
        size="sm"
        onClick={() => {
          save.reset();
          setOpen(true);
        }}
      >
        <PlusIcon aria-hidden="true" />
        Tambah sumber
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Daftarkan sumber bukti"
        description="Hanya sumber yang diizinkan faskes yang boleh dipakai sistem untuk mengambil bukti."
        confirmLabel="Daftarkan"
        pending={save.pending}
        error={save.error}
        disabled={ref.trim().length < 2 || !hoursValid || parsed.error !== null}
        onConfirm={async () => {
          const saved = await save.run();
          if (saved) {
            setOpen(false);
            setRef("");
            onDone();
          }
        }}
      >
        <div className="space-y-3">
          <Field id="src-type" label="Tipe sumber">
            <OptionSelect id="src-type" value={type} options={SOURCE_TYPES} onChange={setType} />
          </Field>
          <Field id="src-ref" label="Referensi sistem" hint="Contoh: SIMRS-EMR-01. Huruf, angka, titik, garis.">
            <Input id="src-ref" value={ref} maxLength={64} onChange={(event) => setRef(event.target.value)} />
          </Field>
          <Field id="src-sla" label="Batas kesegaran sinkronisasi (jam)" hint="Sinkronisasi lebih tua dari ini membuat pemeriksaan abstain.">
            <Input id="src-sla" type="number" min={0.02} step="any" value={hours} onChange={(event) => setHours(event.target.value)} />
          </Field>
          <Field id="src-cov" label="Catatan cakupan (JSON, opsional)" error={parsed.error}>
            <Textarea id="src-cov" rows={3} className="font-mono text-xs" value={coverage} onChange={(event) => setCoverage(event.target.value)} />
          </Field>
        </div>
      </ConfirmDialog>
    </>
  );
}

function UpdateSourceDialog({ source, onDone }: { source: Source; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [health, setHealth] = useState(source.health_status);
  const [synced, setSynced] = useState(toLocalInput(source.last_synced_at));
  const [enabled, setEnabled] = useState(source.is_enabled);
  const [hours, setHours] = useState(String(source.freshness_sla_seconds / 3600));
  const save = useAction(() =>
    apiFetch<Source>(`/v1/evidence-sources/${source.id}`, {
      method: "PATCH",
      json: {
        health_status: health,
        last_synced_at: toIsoFromLocal(synced),
        is_enabled: enabled,
        freshness_sla_seconds: Math.round(Number(hours) * 3600),
      },
    }),
  );
  const hoursValid = Number(hours) >= 1 / 60 && Number(hours) <= 8760;

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          save.reset();
          setHealth(source.health_status);
          setSynced(toLocalInput(source.last_synced_at));
          setEnabled(source.is_enabled);
          setHours(String(source.freshness_sla_seconds / 3600));
          setOpen(true);
        }}
      >
        <PencilIcon aria-hidden="true" />
        Perbarui
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={`Perbarui ${source.system_ref}`}
        description="Status ini dilaporkan operator. Pastikan sesuai kenyataan: sumber yang dinyatakan sehat dan segar akan dianggap memadai, sehingga bukti yang tidak ditemukan dapat menjadi temuan."
        confirmLabel="Simpan"
        pending={save.pending}
        error={save.error}
        disabled={!hoursValid}
        onConfirm={async () => {
          const saved = await save.run();
          if (saved) {
            setOpen(false);
            onDone();
          }
        }}
      >
        <div className="space-y-3">
          <Field id="upd-health" label="Kesehatan sumber">
            <OptionSelect id="upd-health" value={health} options={HEALTH_OPTIONS} onChange={setHealth} />
          </Field>
          <Field id="upd-sync" label="Sinkronisasi terakhir">
            <Input id="upd-sync" type="datetime-local" value={synced} onChange={(event) => setSynced(event.target.value)} />
          </Field>
          <Field id="upd-sla" label="Batas kesegaran (jam)">
            <Input id="upd-sla" type="number" min={0.02} step="any" value={hours} onChange={(event) => setHours(event.target.value)} />
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={enabled} onCheckedChange={(checked) => setEnabled(checked === true)} />
            Sumber aktif dan boleh dipakai pemeriksaan
          </label>
        </div>
      </ConfirmDialog>
    </>
  );
}

export function SourcesView() {
  const { can } = useAuth();
  const sources = useApi<Source[]>("/v1/evidence-sources");
  const manage = can("source:manage");

  return (
    <RequirePermission permission="source:read">
      <div className="space-y-6">
        <PageHeader
          title="Sumber bukti"
          description="Sumber yang diizinkan faskes untuk pengambilan bukti. Kesehatan dan kesegaran menentukan apakah bukti tidak ditemukan boleh dianggap selisih, atau pemeriksaan harus abstain."
          actions={manage ? <CreateSourceDialog onDone={sources.reload} /> : null}
        />
        <Alert variant="info">
          <AlertTitle>Status dilaporkan operator</AlertTitle>
          <AlertDescription>
            Belum ada konektor otomatis ke sistem faskes. Kesehatan dan waktu sinkronisasi diperbarui secara
            manual oleh admin faskes. Sumber yang tidak sehat, tidak aktif, atau melewati batas kesegaran
            membuat pemeriksaan abstain (T0), bukan menyimpulkan pelayanan tidak terjadi.
          </AlertDescription>
        </Alert>
        <QueryBoundary state={sources} rows={4}>
          {(items) =>
            items.length === 0 ? (
              <EmptyState
                icon={DatabaseIcon}
                title="Belum ada sumber bukti"
                description="Tanpa sumber aktif, semua pemeriksaan berakhir abstain karena cakupan bukti tidak memadai."
              />
            ) : (
              <div className="overflow-x-auto rounded-3xl border border-line bg-white">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Sumber</TableHead>
                      <TableHead>Aktif</TableHead>
                      <TableHead>Kesehatan</TableHead>
                      <TableHead>Pemeriksaan kesehatan</TableHead>
                      <TableHead>Sinkronisasi terakhir</TableHead>
                      <TableHead>Kesegaran</TableHead>
                      {manage ? <TableHead className="text-right">Aksi</TableHead> : null}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map((source) => (
                      <TableRow key={source.id}>
                        <TableCell>
                          <p className="font-medium text-ink">{source.system_ref}</p>
                          <p className="text-xs text-muted-foreground">{source.source_type}</p>
                        </TableCell>
                        <TableCell>{source.is_enabled ? "Ya" : <Badge variant="neutral">Nonaktif</Badge>}</TableCell>
                        <TableCell>
                          <StatusBadge kind="health" value={source.health_status} />
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{formatDateTime(source.last_health_check_at)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{formatDateTime(source.last_synced_at)}</TableCell>
                        <TableCell>
                          <Badge variant={source.fresh ? "success" : "warning"}>
                            {source.fresh ? "Segar" : "Melewati batas"}
                          </Badge>
                          <span className="ml-1.5 text-xs text-muted-foreground">
                            ≤ {formatNumber(source.freshness_sla_seconds / 3600, 1)} jam
                          </span>
                        </TableCell>
                        {manage ? (
                          <TableCell className="text-right">
                            <UpdateSourceDialog source={source} onDone={sources.reload} />
                          </TableCell>
                        ) : null}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )
          }
        </QueryBoundary>
      </div>
    </RequirePermission>
  );
}
