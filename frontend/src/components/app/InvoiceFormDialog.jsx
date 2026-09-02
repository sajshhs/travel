import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, FileText } from "lucide-react";
import apiClient from "@/services/apiClient";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatCurrency } from "@/utils/formatters";

const KINDS = [
  { v: "dp", l: "Invoice DP (uang muka)", d: "Menagih persentase/nominal DP untuk mengunci jadwal & unit." },
  { v: "settlement", l: "Invoice Pelunasan", d: "Menagih sisa tagihan setelah pembayaran yang sudah masuk." },
  { v: "full", l: "Invoice Penuh", d: "Menagih seluruh total booking sekaligus (tanpa DP)." },
];

export default function InvoiceFormDialog({ open, onOpenChange, onSaved, booking: presetBooking = null, defaultKind = "full" }) {
  const [bookings, setBookings] = useState([]);
  const [bookingId, setBookingId] = useState("");
  const [kind, setKind] = useState(defaultKind);
  const [dpPercent, setDpPercent] = useState("");
  const [amount, setAmount] = useState("");
  const [taxEnabled, setTaxEnabled] = useState(false);
  const [cfg, setCfg] = useState({ tax_percent: 11, tax_label: "PPN", dp_percent: 30 });
  const [dueAt, setDueAt] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setKind(defaultKind); setAmount(""); setDueAt(""); setNotes(""); setDpPercent("");
    apiClient.get("/documents/config").then((r) => {
      setCfg(r.data || {}); setTaxEnabled(Boolean(r.data?.tax_enabled)); setDpPercent(String(r.data?.dp_percent ?? 30));
    }).catch(() => {});
    if (presetBooking) { setBookings([presetBooking]); setBookingId(presetBooking.id); return; }
    setBookingId("");
    apiClient.get("/bookings").then((r) => setBookings((Array.isArray(r.data) ? r.data : []).filter((b) => b.status !== "cancelled"))).catch(() => setBookings([]));
  }, [open, presetBooking, defaultKind]);

  const b = bookings.find((x) => x.id === bookingId);
  const total = Number(b?.total_amount || 0);
  const paid = Number(b?.paid_amount || 0);
  const tax = taxEnabled ? Math.round(total * Number(cfg.tax_percent || 0) / 100) : 0;
  const grand = total + tax;
  const dpPct = Number(dpPercent || cfg.dp_percent || 0);
  const autoAmount = kind === "dp" ? Math.round(grand * dpPct / 100) : kind === "settlement" ? Math.max(grand - paid, 0) : grand;
  const finalAmount = amount ? Number(amount) : autoAmount;

  const submit = async () => {
    if (!bookingId) { toast.error("Pilih booking terlebih dahulu"); return; }
    setSaving(true);
    try {
      const r = await apiClient.post("/invoices", {
        booking_id: bookingId, kind, amount: amount ? Number(amount) : null,
        dp_percent: kind === "dp" ? dpPct : null, tax_enabled: taxEnabled, due_at: dueAt || null, notes,
      });
      toast.success(`${r.data?.kind_label || "Invoice"} ${r.data?.number || ""} dibuat`);
      onOpenChange(false);
      onSaved && onSaved(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal membuat invoice");
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg" data-testid="invoice-form-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><FileText size={17} className="text-[#007AFF]" /> Buat Invoice</DialogTitle>
          <DialogDescription>Nomor otomatis mengikuti aturan penomoran. Pajak bisa dinyalakan per invoice.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          {!presetBooking ? (
            <div className="space-y-1.5">
              <Label>Booking</Label>
              <Select value={bookingId} onValueChange={setBookingId}>
                <SelectTrigger data-testid="inv-booking"><SelectValue placeholder="Pilih booking" /></SelectTrigger>
                <SelectContent>
                  {bookings.map((x) => <SelectItem key={x.id} value={x.id}>{x.code} · {x.customer_name} · {formatCurrency(x.total_amount)}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="rounded-[10px] bg-[#F7F8FA] px-3 py-2 text-[12.5px]" data-testid="inv-booking-preset">
              <span className="font-semibold text-[#1C1C1E]">{presetBooking.code}</span> · {presetBooking.customer_name} · total {formatCurrency(total)} · terbayar {formatCurrency(paid)}
            </div>
          )}
          <div className="space-y-1.5">
            <Label>Jenis invoice</Label>
            <div className="grid gap-2 sm:grid-cols-3">
              {KINDS.map((k) => (
                <button type="button" key={k.v} onClick={() => setKind(k.v)} data-testid={`inv-kind-${k.v}`}
                  className={`rounded-[10px] border px-3 py-2 text-left transition-colors ${kind === k.v ? "border-[#007AFF] bg-[#EAF2FF]" : "border-[#E2E3E7] bg-white hover:border-[#B9D5FF]"}`}>
                  <span className="block text-[12.5px] font-semibold text-[#1C1C1E]">{k.l}</span>
                  <span className="block text-[11px] leading-snug text-[#6B6B73]">{k.d}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {kind === "dp" ? (
              <div className="space-y-1.5">
                <Label>Persen DP (%)</Label>
                <Input type="number" value={dpPercent} onChange={(e) => setDpPercent(e.target.value)} data-testid="inv-dp-percent" />
              </div>
            ) : null}
            <div className="space-y-1.5">
              <Label>Nominal tagihan (Rp) — kosong = otomatis</Label>
              <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder={String(autoAmount)} data-testid="inv-amount" />
            </div>
            <div className="space-y-1.5">
              <Label>Jatuh tempo</Label>
              <Input type="date" value={dueAt} onChange={(e) => setDueAt(e.target.value)} data-testid="inv-due" />
            </div>
          </div>
          <div className="flex items-center justify-between rounded-[10px] border border-[#E2E3E7] px-3 py-2">
            <div>
              <p className="text-[12.5px] font-semibold text-[#1C1C1E]">Kenakan {cfg.tax_label || "PPN"} {Number(cfg.tax_percent || 0)}%</p>
              <p className="text-[11px] text-[#6B6B73]">Pajak dihitung dari total booking. Default mengikuti Pengaturan Dokumen.</p>
            </div>
            <Switch checked={taxEnabled} onCheckedChange={setTaxEnabled} data-testid="inv-tax-toggle" />
          </div>
          {b ? (
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 rounded-[10px] bg-[#F7F8FA] px-3 py-2 text-[12px] text-[#6B6B73]" data-testid="inv-summary">
              <span>Total booking</span><span className="text-right tabular-nums text-[#1C1C1E]">{formatCurrency(total)}</span>
              {taxEnabled ? <><span>{cfg.tax_label} {Number(cfg.tax_percent)}%</span><span className="text-right tabular-nums text-[#1C1C1E]">{formatCurrency(tax)}</span></> : null}
              {kind === "settlement" ? <><span>Sudah dibayar</span><span className="text-right tabular-nums text-[#1B7F3B]">- {formatCurrency(paid)}</span></> : null}
              <span className="font-semibold text-[#1C1C1E]">Yang ditagihkan</span>
              <span className="text-right text-[13px] font-bold tabular-nums text-[#1C1C1E]" data-testid="inv-final-amount">{formatCurrency(finalAmount)}</span>
            </div>
          ) : null}
          <div className="space-y-1.5">
            <Label>Catatan (tercetak di invoice)</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="mis. Harga sudah termasuk driver & BBM…" data-testid="inv-notes" />
          </div>
        </div>
        <DialogFooter className="mt-2">
          <button className="secondary-button" onClick={() => onOpenChange(false)} data-testid="inv-cancel">Batal</button>
          <button className="primary-button" disabled={saving} onClick={submit} data-testid="inv-submit">{saving ? <Loader2 size={14} className="animate-spin" /> : null} Terbitkan Invoice</button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
