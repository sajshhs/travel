import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import apiClient from "@/services/apiClient";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import DestinationSelect from "@/components/app/DestinationSelect";

const SRC = [["manual", "Manual"], ["whatsapp", "WhatsApp"], ["website", "Website"]];
const EMPTY = { customer_name: "", phone: "", email: "", source: "manual", destination: "", trip_date: "", pax: "", value: "", message: "", assigned_to: "auto" };

export default function LeadFormDialog({ open, onOpenChange, agents, onSaved }) {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) setForm(EMPTY); }, [open]);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.customer_name.trim()) { toast.error("Nama calon customer wajib diisi"); return; }
    setSaving(true);
    try {
      await apiClient.post("/leads", {
        customer_name: form.customer_name.trim(), phone: form.phone, email: form.email,
        source: form.source, destination: form.destination, trip_date: form.trip_date || null,
        pax: Number(form.pax) || 1, value: Number(form.value) || 0, message: form.message,
        assigned_to: form.assigned_to === "auto" ? null : form.assigned_to,
      });
      toast.success("Lead ditambahkan");
      onOpenChange(false); onSaved && onSaved();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan lead"); } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg" data-testid="lead-form-dialog">
        <DialogHeader><DialogTitle>Tambah Lead</DialogTitle><DialogDescription>Buat lead manual. Bisa auto-assign ke agen.</DialogDescription></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5"><Label>Nama</Label><Input value={form.customer_name} onChange={(e) => set("customer_name", e.target.value)} placeholder="Nama / instansi" data-testid="lf-name" /></div>
            <div className="space-y-1.5"><Label>Sumber</Label>
              <Select value={form.source} onValueChange={(v) => set("source", v)}>
                <SelectTrigger data-testid="lf-source"><SelectValue /></SelectTrigger>
                <SelectContent>{SRC.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
              </Select></div>
            <div className="space-y-1.5"><Label>Telepon</Label><Input value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="0812xxxx" data-testid="lf-phone" /></div>
            <div className="space-y-1.5"><Label>Email</Label><Input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} data-testid="lf-email" /></div>
            <div className="space-y-1.5"><Label>Destinasi (master)</Label><DestinationSelect value={form.destination} onChange={(v) => set("destination", v)} testId="lf-dest" optionsPath="/leads/destination-options" /></div>
            <div className="space-y-1.5"><Label>Tanggal trip</Label><Input type="date" value={form.trip_date} onChange={(e) => set("trip_date", e.target.value)} data-testid="lf-date" /></div>
            <div className="space-y-1.5"><Label>Pax</Label><Input type="number" min="1" value={form.pax} onChange={(e) => set("pax", e.target.value)} data-testid="lf-pax" /></div>
            <div className="space-y-1.5"><Label>Nilai (Rp)</Label><Input type="number" value={form.value} onChange={(e) => set("value", e.target.value)} data-testid="lf-value" /></div>
          </div>
          <div className="space-y-1.5"><Label>Ditugaskan</Label>
            <Select value={form.assigned_to} onValueChange={(v) => set("assigned_to", v)}>
              <SelectTrigger data-testid="lf-assign"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="auto">Otomatis (round-robin)</SelectItem>{(agents || []).map((a) => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}</SelectContent>
            </Select></div>
          <div className="space-y-1.5"><Label>Pesan</Label><Textarea value={form.message} onChange={(e) => set("message", e.target.value)} rows={2} data-testid="lf-message" /></div>
        </div>
        <DialogFooter className="mt-2">
          <button className="secondary-button" onClick={() => onOpenChange(false)} data-testid="lf-cancel">Batal</button>
          <button className="primary-button" disabled={saving} onClick={submit} data-testid="lf-submit">{saving ? <Loader2 size={14} className="animate-spin" /> : null} Simpan</button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
