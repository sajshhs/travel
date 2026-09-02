import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, Eye, FileText, Loader2, Plus, Send } from "lucide-react";
import apiClient from "@/services/apiClient";
import { LoadingState, EmptyState, ErrorState } from "@/components/shared/DataStates";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import InvoiceFormDialog from "@/components/app/InvoiceFormDialog";
import { formatCurrency, formatDate } from "@/utils/formatters";
import { INVOICE_STATUS, KIND_LABEL, downloadPdf, openPdf, safeName } from "./docUtils";

const KIND_TONE = { dp: "bg-[#FFF4E5] text-[#B45309]", settlement: "bg-[#EAF2FF] text-[#0058CC]", full: "bg-[#F1F1F4] text-[#3C3C43]" };

export function InvoiceRow({ inv, onChanged, compact = false }) {
  const [busy, setBusy] = useState("");
  const st = INVOICE_STATUS[inv.status] || INVOICE_STATUS.draft;
  const sendWa = async () => {
    setBusy("wa");
    try {
      const r = await apiClient.post(`/invoices/${inv.id}/send-wa`);
      toast.success(`${inv.kind_label || "Invoice"} ${r.data?.number || ""} terkirim via WhatsApp`);
      onChanged && onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal mengirim via WhatsApp"); } finally { setBusy(""); }
  };
  const setStatus = async (status) => {
    try { await apiClient.patch(`/invoices/${inv.id}`, { status }); toast.success("Status invoice diperbarui"); onChanged && onChanged(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal mengubah status"); }
  };
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3" data-testid={`invoice-${inv.id}`}>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[12.5px] font-semibold text-[#1C1C1E]" data-testid={`invoice-number-${inv.id}`}>{inv.number}</span>
          <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${KIND_TONE[inv.kind] || KIND_TONE.full}`}>{inv.kind_label || KIND_LABEL[inv.kind] || "Invoice"}</span>
          {inv.tax_enabled ? <span className="rounded-full bg-[#F1F1F4] px-2 py-0.5 text-[10.5px] text-[#6B6B73]">{inv.tax_label} {Number(inv.tax_percent)}%</span> : null}
          {inv.sent_count ? <span className="text-[10.5px] text-[#127A36]">WA terkirim {inv.sent_count}×</span> : null}
        </div>
        {!compact ? <p className="mt-0.5 truncate text-[12px] text-[#6B6B73]">{inv.customer_name} · {inv.booking_code} · terbit {formatDate(inv.issued_at)} · jatuh tempo {formatDate(inv.due_at)}</p>
          : <p className="mt-0.5 text-[12px] text-[#6B6B73]">jatuh tempo {formatDate(inv.due_at)}</p>}
      </div>
      <span className="text-[13.5px] font-bold tabular-nums text-[#1C1C1E]" data-testid={`invoice-amount-${inv.id}`}>{formatCurrency(inv.amount_due ?? inv.amount)}</span>
      <div className="flex items-center gap-1.5">
        <Select value={inv.status} onValueChange={setStatus}>
          <SelectTrigger className="h-8 w-[125px]" data-testid={`invoice-status-${inv.id}`}><SelectValue>{st.l}</SelectValue></SelectTrigger>
          <SelectContent>{Object.entries(INVOICE_STATUS).map(([k, v]) => <SelectItem key={k} value={k}>{v.l}</SelectItem>)}</SelectContent>
        </Select>
        <button className="icon-button !h-8 !w-8" title="Lihat PDF" onClick={() => openPdf(`/invoices/${inv.id}/export?format=inline`)} data-testid={`invoice-view-${inv.id}`}><Eye size={14} /></button>
        <button className="icon-button !h-8 !w-8" title="Unduh PDF" onClick={() => downloadPdf(`/invoices/${inv.id}/export?format=pdf`, safeName(inv.number, "invoice"))} data-testid={`invoice-pdf-${inv.id}`}><Download size={14} /></button>
        <button className="secondary-button !px-2 !py-1 !text-[12px] !text-[#127A36]" disabled={busy === "wa"} onClick={sendWa} data-testid={`invoice-wa-${inv.id}`}>
          {busy === "wa" ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Kirim WA
        </button>
      </div>
    </div>
  );
}

export default function InvoicesTab() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("all");

  const load = useCallback(() => {
    setLoading(true);
    apiClient.get("/invoices").then((r) => { setRows(Array.isArray(r.data) ? r.data : []); setError(null); })
      .catch(() => setError("Gagal memuat invoice")).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  const shown = rows.filter((r) => filter === "all" || r.kind === filter);
  const addBtn = <button className="primary-button" onClick={() => setOpen(true)} data-testid="invoice-add"><Plus size={14} /> Buat Invoice</button>;

  return (
    <div className="space-y-3" data-testid="invoices-panel">
      {loading ? <LoadingState testId="invoices-loading" /> : error ? <ErrorState message={error} onRetry={load} />
        : rows.length === 0 ? <EmptyState title="Belum ada invoice" description="Terbitkan invoice DP, pelunasan, atau penuh dari booking." testId="invoices-empty" action={addBtn} /> : (
          <section className="section-card">
            <div className="section-head">
              <div className="flex items-center gap-2"><FileText size={16} className="text-[#007AFF]" /><h2>Daftar Invoice</h2></div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5" data-testid="invoice-kind-filter">
                  {[["all", "Semua"], ["dp", "DP"], ["settlement", "Pelunasan"], ["full", "Penuh"]].map(([k, l]) => (
                    <button key={k} onClick={() => setFilter(k)} data-testid={`invoice-filter-${k}`}
                      className={`rounded-full border px-3 py-1 text-[12px] font-semibold ${filter === k ? "border-[#007AFF] bg-[#EAF2FF] text-[#0058CC]" : "border-[#E2E3E7] bg-white text-[#6B6B73]"}`}>{l}</button>
                  ))}
                </div>
                {addBtn}
              </div>
            </div>
            <div className="divide-y divide-[#F2F2F5]" data-testid="invoices-list">
              {shown.map((inv) => <InvoiceRow key={inv.id} inv={inv} onChanged={load} />)}
              {shown.length === 0 ? <p className="px-4 py-6 text-center text-[12.5px] text-[#8E8E93]">Tidak ada invoice pada filter ini.</p> : null}
            </div>
          </section>
        )}
      <InvoiceFormDialog open={open} onOpenChange={setOpen} onSaved={load} />
    </div>
  );
}
