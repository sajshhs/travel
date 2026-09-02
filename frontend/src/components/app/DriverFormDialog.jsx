import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import apiClient from "@/services/apiClient";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const STATUSES = [
  { v: "online", l: "Online" }, { v: "resting", l: "Istirahat" }, { v: "offline", l: "Offline" },
];
const toDateInput = (v) => (v ? String(v).slice(0, 10) : "");
const EMPTY = { name: "", phone: "", sim_number: "", sim_expiry: "", status: "offline", rating: "", default_fee_rate: "" };

export default function DriverFormDialog({ open, onOpenChange, initial, onSaved }) {
  const editing = Boolean(initial && initial.id);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(editing ? {
      name: initial.name || "", phone: initial.phone || "", sim_number: initial.sim_number || "",
      sim_expiry: toDateInput(initial.sim_expiry), status: initial.status || "offline",
      rating: initial.rating ?? "", default_fee_rate: initial.default_fee_rate ?? "",
    } : EMPTY);
  }, [open, editing, initial]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("Nama driver wajib diisi");
      return;
    }
    setSaving(true);
    const payload = {
      name: form.name.trim(), phone: form.phone, sim_number: form.sim_number,
      sim_expiry: form.sim_expiry || null, status: form.status, rating: Number(form.rating) || 0,
      default_fee_rate: Number(form.default_fee_rate) || 0,
    };
    try {
      if (editing) await apiClient.patch(`/drivers/${initial.id}`, payload);
      else await apiClient.post("/drivers", payload);
      toast.success(editing ? "Driver diperbarui" : "Driver ditambahkan");
      onOpenChange(false);
      onSaved && onSaved();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal menyimpan driver");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg" data-testid="driver-form-dialog">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit Driver" : "Tambah Driver"}</DialogTitle>
          <DialogDescription>Data master pengemudi & masa berlaku SIM.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Nama</Label>
              <Input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Nama lengkap" data-testid="df-name" />
            </div>
            <div className="space-y-1.5">
              <Label>Telepon</Label>
              <Input value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="0812xxxx" data-testid="df-phone" />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Nomor SIM</Label>
              <Input value={form.sim_number} onChange={(e) => set("sim_number", e.target.value)} placeholder="B1-00x" data-testid="df-sim" />
            </div>
            <div className="space-y-1.5">
              <Label>SIM Berlaku s/d</Label>
              <Input type="date" value={form.sim_expiry} onChange={(e) => set("sim_expiry", e.target.value)} data-testid="df-sim-expiry" />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Status</Label>
              <Select value={form.status} onValueChange={(v) => set("status", v)}>
                <SelectTrigger data-testid="df-status"><SelectValue /></SelectTrigger>
                <SelectContent>{STATUSES.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Rating (0-5)</Label>
              <Input type="number" step="0.1" min="0" max="5" value={form.rating} onChange={(e) => set("rating", e.target.value)} placeholder="4.8" data-testid="df-rating" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Fee Default /hari (Rp) — prefill otomatis saat assign dispatch</Label>
            <Input type="number" min="0" value={form.default_fee_rate} onChange={(e) => set("default_fee_rate", e.target.value)} placeholder="mis. 150000 (kosong = tanpa prefill)" data-testid="df-default-fee" />
          </div>
        </div>
        <DialogFooter className="mt-2">
          <button className="secondary-button" onClick={() => onOpenChange(false)} data-testid="df-cancel">Batal</button>
          <button className="primary-button" disabled={saving} onClick={submit} data-testid="df-submit">
            {saving ? <Loader2 size={14} className="animate-spin" /> : null} Simpan
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
