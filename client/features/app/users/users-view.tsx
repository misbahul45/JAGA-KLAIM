"use client";

import { KeyRoundIcon, PlusIcon, UsersIcon } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { Field } from "@/components/shared/field";
import { OptionSelect } from "@/components/shared/option-select";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAction } from "@/hooks/use-action";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import type { Role } from "@/lib/api-types";

import { useAuth } from "../auth/auth-context";
import { ConfirmDialog } from "../shared/confirm-dialog";
import { ROLE_LABELS, labelOf } from "../shared/labels";
import { QueryBoundary } from "../shared/query-boundary";
import { RequirePermission } from "../shared/require-permission";

type UserRow = { id: string; name: string; email: string; role: Role; is_active: boolean };

const ASSIGNABLE = ["coder", "verifier", "faskes_admin", "auditor"].map((value) => ({
  value,
  label: labelOf(ROLE_LABELS, value),
}));

function CreateUserDialog({ onDone }: { onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("coder");
  const [password, setPassword] = useState("");
  const save = useAction(() =>
    apiFetch<UserRow>("/v1/users", { method: "POST", json: { name: name.trim(), email: email.trim(), role, password } }),
  );
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
        Tambah pengguna
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Tambah pengguna faskes"
        description="Pengguna hanya dapat mengakses data faskes Anda. Peran tata kelola aturan tidak dapat diberikan dari sini."
        confirmLabel="Buat akun"
        pending={save.pending}
        error={save.error}
        disabled={!name.trim() || !email.trim() || password.length < 12}
        onConfirm={async () => {
          const saved = await save.run();
          if (saved) {
            setOpen(false);
            setName("");
            setEmail("");
            setPassword("");
            onDone();
          }
        }}
      >
        <div className="space-y-3">
          <Field id="usr-name" label="Nama">
            <Input id="usr-name" value={name} maxLength={120} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field id="usr-email" label="Email">
            <Input id="usr-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </Field>
          <Field id="usr-role" label="Peran">
            <OptionSelect id="usr-role" value={role} options={ASSIGNABLE} onChange={setRole} />
          </Field>
          <Field id="usr-pass" label="Kata sandi awal" hint="Minimal 12 karakter. Sampaikan lewat kanal aman dan minta pengguna menggantinya.">
            <Input id="usr-pass" type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </Field>
        </div>
      </ConfirmDialog>
    </>
  );
}

function ResetPasswordDialog({ user }: { user: UserRow }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const save = useAction(() =>
    apiFetch<{ message: string }>(`/v1/users/${user.id}/password`, { method: "POST", json: { new_password: password } }),
  );
  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          save.reset();
          setDone(false);
          setPassword("");
          setOpen(true);
        }}
      >
        <KeyRoundIcon aria-hidden="true" />
        Atur ulang sandi
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={`Atur ulang kata sandi ${user.name}`}
        description="Semua sesi aktif pengguna ini diakhiri. Tindakan tercatat pada audit trail."
        confirmLabel={done ? "Selesai" : "Atur ulang"}
        pending={save.pending}
        error={save.error}
        disabled={password.length < 12}
        onConfirm={async () => {
          if (done) {
            setOpen(false);
            return;
          }
          const saved = await save.run();
          if (saved) setDone(true);
        }}
      >
        {done ? (
          <p className="text-sm text-ink">Kata sandi diatur ulang dan semua sesi pengguna diakhiri.</p>
        ) : (
          <Field id="rst-pass" label="Kata sandi baru" hint="Minimal 12 karakter.">
            <Input id="rst-pass" type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </Field>
        )}
      </ConfirmDialog>
    </>
  );
}

function RoleSelect({ user, onDone, self }: { user: UserRow; onDone: () => void; self: boolean }) {
  const change = useAction((role: string) =>
    apiFetch<UserRow>(`/v1/users/${user.id}`, { method: "PATCH", json: { role } }),
  );
  return (
    <div className="w-44">
      <OptionSelect
        ariaLabel={`Peran ${user.name}`}
        value={user.role}
        options={ASSIGNABLE}
        disabled={change.pending}
        onChange={async (value) => {
          if (value === user.role) return;
          const saved = await change.run(value);
          if (saved) onDone();
        }}
      />
      {self ? <p className="mt-1 text-[0.7rem] text-muted-foreground">Akun Anda</p> : null}
      {change.error ? <p className="mt-1 text-xs text-destructive">Peran gagal diubah</p> : null}
    </div>
  );
}

function ActiveToggle({ user, onDone, self }: { user: UserRow; onDone: () => void; self: boolean }) {
  const toggle = useAction(() =>
    apiFetch<UserRow>(`/v1/users/${user.id}`, { method: "PATCH", json: { is_active: !user.is_active } }),
  );
  return (
    <div className="flex items-center gap-2">
      <Badge variant={user.is_active ? "success" : "neutral"}>{user.is_active ? "Aktif" : "Nonaktif"}</Badge>
      <Button
        variant="ghost"
        size="sm"
        disabled={toggle.pending || self}
        title={self ? "Anda tidak dapat menonaktifkan akun sendiri" : undefined}
        onClick={async () => {
          const saved = await toggle.run();
          if (saved) onDone();
        }}
      >
        {user.is_active ? "Nonaktifkan" : "Aktifkan"}
      </Button>
    </div>
  );
}

export function UsersView() {
  const { principal } = useAuth();
  const users = useApi<UserRow[]>("/v1/users");
  return (
    <RequirePermission permission="user:manage">
      <div className="space-y-6">
        <PageHeader
          title="Pengguna"
          description="Kelola akun pada faskes Anda. Peran menentukan izin di server, bukan hanya menu yang tampak."
          actions={<CreateUserDialog onDone={users.reload} />}
        />
        <QueryBoundary state={users} rows={4}>
          {(items) =>
            items.length === 0 ? (
              <EmptyState icon={UsersIcon} title="Belum ada pengguna" />
            ) : (
              <div className="overflow-x-auto rounded-3xl border border-line bg-white">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nama</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Peran</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Kata sandi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map((user) => {
                      const self = user.id === principal.user_id;
                      return (
                        <TableRow key={user.id}>
                          <TableCell className="font-medium">{user.name}</TableCell>
                          <TableCell className="text-xs">{user.email}</TableCell>
                          <TableCell>
                            <RoleSelect user={user} self={self} onDone={users.reload} />
                          </TableCell>
                          <TableCell>
                            <ActiveToggle user={user} self={self} onDone={users.reload} />
                          </TableCell>
                          <TableCell className="text-right">
                            {self ? <span className="text-xs text-muted-foreground">Gunakan halaman Akun</span> : <ResetPasswordDialog user={user} />}
                          </TableCell>
                        </TableRow>
                      );
                    })}
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
