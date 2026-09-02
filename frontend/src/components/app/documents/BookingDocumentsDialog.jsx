import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { ClipboardCheck, Download, Eye, FileText, Loader2, Plus, Receipt, Route, Send } from "lucide-react";
import apiClient from "@/services/apiClient";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { LoadingState } from "@/components/shared/DataStates";
import InvoiceFormDialog from "@/components/app/InvoiceFormDialog";
import { formatCurrency } from "@/utils/formatters";
import { InvoiceRow } from "./InvoicesTab";
import { ReceiptRow } from "./ReceiptsTab";
import { RefundNoteRow } from "./RefundNotesTab";
import { RotateCcw } from "lucide-react";
import { downloadPdf, openPdf, safeName } from "./docUtils";

function BookingDocCard({ kind, icon: Icon, title, desc, bookingId, existing, onChanged, disabled, disabledNote }) {
  const [busy, setBusy] = useState(false);
  const base = `/documents/booking/${bookingId}/${kind}`;
  const sendWa = async () => {
    setBusy(true);
    try {
      const r = await apiClient.post(`${base}/send-wa`);
      toast.success(`${title} ${r.data?.number || ""} terkirim via WhatsApp`);
      onChanged && onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || `Gagal mengirim ${title}`); } finally { setBusy(false); }
  };
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-[12px] border border-[#E2E3E7] px-4 py-3" data-testid={`bdoc-${kind}`}>
      <div className="flex min-w-0 items-start gap-3">
        <Icon size={18} className="mt-0.5 flex-shrink-0 text-[#007AFF]" />
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-[#1C1C1E]">{title}{existing ? <span className="ml-2 font-mono text-[11.5px] font-normal text-[#6B6B73]" data-testid={`bdoc-number-${kind}`}>{existing.number}</span> : null}</p>
          <p className="text-[11.5px] text-[#6B6B73]">{disabled ? disabledNote : desc}{existing?.sent_count ? ` · WA terkirim ${existing.sent_count}×` : ""}</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        <button className="icon-button !h-8 !w-8" title="Lihat PDF" disabled={disabled} onClick={() => openPdf(`${base}/pdf?inline=true`).then(onChanged)} data-testid={`bdoc-view-${kind}`}><Eye size={14} /></button>
        <button className="icon-button !h-8 !w-8" title="Unduh PDF" disabled={disabled} onClick={() => downloadPdf(`${base}/pdf`, safeName(existing?.number, kind)).then(onChanged)} data-testid={`bdoc-pdf-${kind}`}><Download size={14} /></button>
        <button className="secondary-button !px-2 !py-1 !text-[12px] !text-[#127A36]" disabled={busy || disabled} onClick={sendWa} data-testid={`bdoc-wa-${kind}`}>
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Kirim WA
        </button>
      </div>
    </div>
  );
}

export default function BookingDocumentsDialog({ open, onOpenChange, booking, onChanged }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [invOpen, setInvOpen] = useState(null); // kind
  const [rcpBusy, setRcpBusy] = useState("");

  const load = useCallback(() => {
    if (!booking?.id) return;
    setLoading(true);
    apiClient.get(`/documents/booking/${booking.id}`).then((r) => setData(r.data))
      .catch((e) => toast.error(e?.response?.data?.detail || "Gagal memuat dokumen booking")).finally(() => setLoading(false));
  }, [booking]);
  useEffect(() => { if (open) load(); }, [open, load]);

  const changed = () => { load(); onChanged && onChanged(); };
  const b = data?.booking || booking || {};
  const sug = data?.suggest || {};
  const paid = Number(b.paid_amount || 0);
  const total = Number(b.total_amount || 0);
  const paymentsWithoutReceipt = (data?.payments || []).filter((p) => p.type !== "refund" && Number(p.amount) > 0 && !(data?.receipts || []).some((r) => r.payment_id === p.id));
  const makeReceipt = async (paymentId) => {
    setRcpBusy(paymentId);
    try { await apiClient.post("/documents/receipts", { payment_id: paymentId }); toast.success("Kwitansi diterbitkan"); changed(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal menerbitkan kwitansi"); } finally { setRcpBusy(""); }
  };
  const bdoc = (kind) => (data?.booking_docs || []).find((d) => d.kind === kind);
  const isCancelled = b.status === "cancelled";
  const canRefundNote = isCancelled && Number(b.refund_amount || 0) > 0;
  const makeRefundNote = async () => {
    setRcpBusy("refund");
    try { await apiClient.post("/documents/refund-notes", { booking_id: b.id }); toast.success("Nota refund diterbitkan"); changed(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal menerbitkan nota refund"); } finally { setRcpBusy(""); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl" data-testid="booking-documents-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><FileText size={17} className="text-[#007AFF]" /> Dokumen · {b.code}</DialogTitle>
          <DialogDescription>{b.customer_name} · total {formatCurrency(total)} · terbayar {formatCurrency(paid)} · sisa {formatCurrency(Math.max(total - paid, 0))}</DialogDescription>
        </DialogHeader>
        {loading && !data ? <LoadingState testId="bdocs-loading" /> : (
          <div className="space-y-5">
            {isCancelled ? (
              <section className="space-y-2" data-testid="bdoc-refund-section">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-[13px] font-bold text-[#A8221A]">Pembatalan & Nota Refund</h3>
                  {canRefundNote && !data?.refund_note ? (
                    <button className="secondary-button !px-2.5 !py-1 !text-[12px]" disabled={rcpBusy === "refund"} onClick={makeRefundNote} data-testid="bdoc-make-refund-note">
                      {rcpBusy === "refund" ? <Loader2 size={13} className="animate-spin" /> : <RotateCcw size={13} />} Terbitkan Nota Refund
                    </button>
                  ) : null}
                </div>
                <div className="rounded-[12px] border border-[#F0C4C0] bg-[#FFF8F7]">
                  <p className="px-4 pt-3 text-[12px] text-[#6B6B73]">Denda {formatCurrency(b.cancellation_fee || 0)} · Refund {formatCurrency(b.refund_amount || 0)}{b.cancellation_reason ? ` · ${b.cancellation_reason}` : ""}</p>
                  {data?.refund_note ? <RefundNoteRow note={data.refund_note} onChanged={changed} compact />
                    : <p className="px-4 pb-3 pt-1 text-[12px] text-[#8E8E93]">{canRefundNote ? "Nota refund belum diterbitkan." : "Dibatalkan tanpa pengembalian dana — tidak ada nota refund."}</p>}
                </div>
              </section>
            ) : null}
            <section className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-[13px] font-bold text-[#1C1C1E]">Invoice</h3>
                {!isCancelled ? (
                <div className="flex flex-wrap gap-1.5">
                  <button className="secondary-button !px-2.5 !py-1 !text-[12px]" onClick={() => setInvOpen("dp")} data-testid="bdoc-new-invoice-dp"><Plus size={13} /> Invoice DP {sug.dp_percent ? `(${sug.dp_percent}% ≈ ${formatCurrency(sug.dp_amount)})` : ""}</button>
                  <button className="secondary-button !px-2.5 !py-1 !text-[12px]" disabled={sug.remaining <= 0} onClick={() => setInvOpen("settlement")} data-testid="bdoc-new-invoice-settlement"><Plus size={13} /> Invoice Pelunasan {sug.remaining > 0 ? `(${formatCurrency(sug.remaining)})` : "(lunas)"}</button>
                  <button className="secondary-button !px-2.5 !py-1 !text-[12px]" onClick={() => setInvOpen("full")} data-testid="bdoc-new-invoice-full"><Plus size={13} /> Invoice Penuh</button>
                </div>
                ) : null}
              </div>
              <div className="divide-y divide-[#F2F2F5] rounded-[12px] border border-[#E2E3E7]" data-testid="bdoc-invoices">
                {(data?.invoices || []).length === 0 ? <p className="px-4 py-4 text-center text-[12.5px] text-[#8E8E93]">Belum ada invoice untuk booking ini.</p>
                  : data.invoices.map((inv) => <InvoiceRow key={inv.id} inv={inv} onChanged={changed} compact />)}
              </div>
            </section>

            <section className="space-y-2">
              <h3 className="text-[13px] font-bold text-[#1C1C1E]">Kwitansi pembayaran</h3>
              <div className="divide-y divide-[#F2F2F5] rounded-[12px] border border-[#E2E3E7]" data-testid="bdoc-receipts">
                {(data?.receipts || []).length === 0 && paymentsWithoutReceipt.length === 0 ? <p className="px-4 py-4 text-center text-[12.5px] text-[#8E8E93]">Belum ada pembayaran tercatat.</p> : null}
                {(data?.receipts || []).map((r) => <ReceiptRow key={r.id} rcp={r} onChanged={changed} compact />)}
                {paymentsWithoutReceipt.map((p) => (
                  <div key={p.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3" data-testid={`bdoc-payment-${p.id}`}>
                    <div className="text-[12.5px] text-[#6B6B73]">Pembayaran {p.type === "dp" ? "DP" : "pelunasan"} · {p.method} · <span className="font-semibold text-[#1C1C1E]">{formatCurrency(p.amount)}</span> — belum ada kwitansi</div>
                    <button className="secondary-button !px-2.5 !py-1 !text-[12px]" disabled={rcpBusy === p.id} onClick={() => makeReceipt(p.id)} data-testid={`bdoc-make-receipt-${p.id}`}>
                      {rcpBusy === p.id ? <Loader2 size={13} className="animate-spin" /> : <Receipt size={13} />} Terbitkan Kwitansi
                    </button>
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-2">
              <h3 className="text-[13px] font-bold text-[#1C1C1E]">Dokumen perjalanan</h3>
              <BookingDocCard kind="confirmation" icon={ClipboardCheck} title="Konfirmasi Pemesanan" desc="Ringkasan jadwal, armada, driver & pembayaran untuk pelanggan." bookingId={b.id} existing={bdoc("confirmation")} onChanged={load} disabled={isCancelled} disabledNote="Booking dibatalkan — konfirmasi tidak berlaku." />
              <BookingDocCard kind="spj" icon={Route} title="Surat Perintah Jalan (SPJ)" desc="Surat tugas untuk driver — dikirim ke WhatsApp driver." bookingId={b.id} existing={bdoc("spj")} onChanged={load}
                disabled={!b.driver_id || isCancelled} disabledNote={isCancelled ? "Booking dibatalkan — SPJ tidak berlaku." : "Booking belum punya driver — tetapkan driver dulu."} />
            </section>
          </div>
        )}
        <InvoiceFormDialog open={Boolean(invOpen)} onOpenChange={(v) => !v && setInvOpen(null)} booking={b} defaultKind={invOpen || "full"} onSaved={changed} />
      </DialogContent>
    </Dialog>
  );
}
