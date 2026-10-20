"use client";

import { PlusIcon, Trash2Icon } from "lucide-react";
import { useRef } from "react";

import { OptionSelect } from "@/components/shared/option-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { CODE_TYPE_LABELS } from "../shared/labels";

export type CodeDraft = {
  key: string;
  code_type: string;
  code: string;
  position: string;
  description: string;
};

type CodesEditorProps = {
  codes: CodeDraft[];
  onChange: (codes: CodeDraft[]) => void;
};

const TYPE_OPTIONS = Object.entries(CODE_TYPE_LABELS).map(([value, label]) => ({ value, label }));

export function draftsFrom(
  codes: { code_type: string; code: string; position: string | null; description: string | null }[],
): CodeDraft[] {
  return codes.map((code, index) => ({
    key: `k${index}`,
    code_type: code.code_type,
    code: code.code,
    position: code.position ?? "",
    description: code.description ?? "",
  }));
}

export function CodesEditor({ codes, onChange }: CodesEditorProps) {
  const counter = useRef(codes.length + 100);

  const update = (key: string, patch: Partial<CodeDraft>) =>
    onChange(codes.map((code) => (code.key === key ? { ...code, ...patch } : code)));

  const add = () => {
    counter.current += 1;
    onChange([
      ...codes,
      { key: `k${counter.current}`, code_type: "procedure", code: "", position: "", description: "" },
    ]);
  };

  return (
    <div className="space-y-3">
      {codes.map((code, index) => (
        <div key={code.key} className="grid gap-2 rounded-2xl border border-line bg-surface p-3 sm:grid-cols-12">
          <div className="sm:col-span-3">
            <OptionSelect
              ariaLabel={`Jenis kode ${index + 1}`}
              value={code.code_type}
              options={TYPE_OPTIONS}
              onChange={(value) => update(code.key, { code_type: value })}
            />
          </div>
          <div className="sm:col-span-3">
            <Input
              aria-label={`Kode ${index + 1}`}
              placeholder="Kode"
              value={code.code}
              maxLength={32}
              onChange={(event) => update(code.key, { code: event.target.value })}
            />
          </div>
          <div className="sm:col-span-2">
            <Input
              aria-label={`Posisi kode ${index + 1}`}
              placeholder="Posisi (opsional)"
              value={code.position}
              maxLength={32}
              onChange={(event) => update(code.key, { position: event.target.value })}
            />
          </div>
          <div className="sm:col-span-3">
            <Input
              aria-label={`Deskripsi kode ${index + 1}`}
              placeholder="Deskripsi (opsional)"
              value={code.description}
              maxLength={500}
              onChange={(event) => update(code.key, { description: event.target.value })}
            />
          </div>
          <div className="flex sm:col-span-1 sm:justify-end">
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Hapus kode ${index + 1}`}
              disabled={codes.length <= 1}
              onClick={() => onChange(codes.filter((item) => item.key !== code.key))}
            >
              <Trash2Icon aria-hidden="true" />
            </Button>
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={add}>
        <PlusIcon aria-hidden="true" />
        Tambah kode
      </Button>
    </div>
  );
}
