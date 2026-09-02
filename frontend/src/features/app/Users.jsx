import { useState } from "react";
import { toast } from "sonner";
import { UserCog, Plus, Loader2 } from "lucide-react";
import apiClient from "@/services/apiClient";
import { useResource } from "@/hooks/useResource";
import DataTable from "@/components/shared/DataTable";
import { LoadingState, EmptyState, ErrorState } from "@/components/shared/DataStates";
import { StatusPill } from "@/components/shared/StatusPill";
import { formatDate } from "@/utils/formatters";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ROLE_LABEL = { owner: "Pemilik", ops_admin: "Admin Operasional", driver: "Driver" };

export default function Users() {
  const { data, loading, error, reload } = useResource("/users");
  const rows = Array.isArray(data) ? data : [];
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "ops_admin", phone: "" });
  const [saving, setSaving] = useState(false);

  const columns = [
    { key: "name", label: "Nama", render: (r) => <span className="font-semibold text-[#1C1C1E]">{r.name}</span> },
    { key: "email", label: "Email", mono: true },
    { key: "role", label: "Peran", render: (r) => ROLE_LABEL[r.role] || r.role },
    { key: "phone", label: "Telepon", mono: true },
    { key: "status", label: "Status", render: (r) => <StatusPill value={r.status} tone={r.status === "active" ? "success" : "neutral"} /> },
    { key: "created_at", label: "Dibuat", render: (r) => formatDate(r.created_at) },
  ];

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await apiClient.post("/users", form);
      toast.success("User berhasil dibuat");
      setOpen(false);
      setForm({ name: "", email: "", password: "", role: "ops_admin", phone: "" });
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Gagal membuat user");
    } finally {
      setSaving(false);
    }
  };

  const AddButton = (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button className="primary-button" data-testid="users-add-button"><Plus size={15} /> Tambah User</button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Tambah User Baru</DialogTitle>
          <DialogDescription>Buat akun baru dan tetapkan perannya (RBAC).</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="u-name">Nama</Label>
            <Input id="u-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required data-testid="users-name-input" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="u-email">Email</Label>
            <Input id="u-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required data-testid="users-email-input" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="u-password">Kata Sandi</Label>
            <Input id="u-password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={6} data-testid="users-password-input" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="u-phone">Telepon</Label>
            <Input id="u-phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="users-phone-input" />
          </div>
          <div className="space-y-1.5">
            <Label>Peran</Label>
            <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
              <SelectTrigger data-testid="users-role-select"><SelectValue placeholder="Pilih peran" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="owner">Pemilik</SelectItem>
                <SelectItem value="ops_admin">Admin Operasional</SelectItem>
                <SelectItem value="driver">Driver</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <button type="submit" className="primary-button" disabled={saving} data-testid="users-submit-button">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Simpan
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );

  if (loading) return <LoadingState testId="users-loading" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  if (rows.length === 0) {
    return (
      <div data-testid="users-page">
        <EmptyState title="Belum ada user" description="Tambahkan akun pengguna baru." action={AddButton} testId="users-empty" />
      </div>
    );
  }

  return (
    <div data-testid="users-page">
      <DataTable
        title="Daftar User"
        icon={UserCog}
        actions={AddButton}
        columns={columns}
        rows={rows}
        footer={`${rows.length} user terdaftar`}
        testId="users-table"
      />
    </div>
  );
}
