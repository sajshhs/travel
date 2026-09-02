import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Plus, RotateCcw, Save, Trash2 } from "lucide-react";
import apiClient from "@/services/apiClient";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LoadingState } from "@/components/shared/DataStates";
import { Field, Toggle } from "./DocLayoutEditor";

export function ConfigPanel({ canEdit }) {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => { apiClient.get("/documents/config").then((r) => setCfg(r.data)).catch(() => toast.error("Gagal memuat konfigurasi dokumen")); }, []);
  if (!cfg) return <LoadingState testId="doc-config-loading" />;
  const f = (k, v) => setCfg((c) => ({ ...c, [k]: v }));
  const bank = (i, k, v) => f("bank_accounts", cfg.bank_accounts.map((b, idx) => idx === i ? { ...b, [k]: v } : b));
  const save = async () => {
    setSaving(true);
    try {
      const r = await apiClient.patch("/documents/config", { ...cfg, tax_percent: Number(cfg.tax_percent) || 0, dp_percent: Number(cfg.dp_percent) || 0, due_days_dp: Number(cfg.due_days_dp) || 0, due_days_settlement: Number(cfg.due_days_settlement) || 0 });
      setCfg(r.data); toast.success("Konfigurasi dokumen disimpan");
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); } finally { setSaving(false); }
  };
  return (
    <div className="space-y-4" data-testid="doc-config-panel">
      <div className="flex justify-end">{canEdit ? <button className="primary-button !px-3 !py-1.5 !text-[12.5px]" onClick={save} disabled={saving} data-testid="doc-config-save">{saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Simpan</button> : null}</div>
      <fieldset disabled={!canEdit} className="grid gap-4 lg:grid-cols-2 disabled:cursor-not-allowed disabled:opacity-60">
        <div className="space-y-3 rounded-[12px] border border-[#E2E3E7] p-3">
          <p className="text-[12.5px] font-bold text-[#1C1C1E]">Pajak & DP</p>
          <Toggle label={`Kenakan ${cfg.tax_label || "PPN"} secara default`} hint="Bisa dinyalakan/dimatikan per invoice saat menerbitkan." checked={cfg.tax_enabled} onChange={(v) => f("tax_enabled", v)} testId="doc-cfg-tax" />
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Label pajak"><Input value={cfg.tax_label || ""} onChange={(e) => f("tax_label", e.target.value)} data-testid="doc-cfg-tax-label" /></Field>
            <Field label="Persen pajak (%)"><Input type="number" value={cfg.tax_percent ?? ""} onChange={(e) => f("tax_percent", e.target.value)} data-testid="doc-cfg-tax-percent" /></Field>
            <Field label="DP default (%)"><Input type="number" value={cfg.dp_percent ?? ""} onChange={(e) => f("dp_percent", e.target.value)} data-testid="doc-cfg-dp" /></Field>
            <Field label="Jatuh tempo invoice DP (hari)"><Input type="number" value={cfg.due_days_dp ?? ""} onChange={(e) => f("due_days_dp", e.target.value)} data-testid="doc-cfg-due-dp" /></Field>
            <Field label="Jatuh tempo pelunasan (hari)"><Input type="number" value={cfg.due_days_settlement ?? ""} onChange={(e) => f("due_days_settlement", e.target.value)} data-testid="doc-cfg-due-settlement" /></Field>
          </div>
          <Toggle label="Kwitansi otomatis saat pembayaran dicatat" checked={cfg.auto_receipt} onChange={(v) => f("auto_receipt", v)} testId="doc-cfg-auto-receipt" />
          <Toggle label="Status invoice ikut pembayaran otomatis" hint="Invoice jadi Sebagian/Lunas saat pembayaran masuk." checked={cfg.auto_invoice_status} onChange={(v) => f("auto_invoice_status", v)} testId="doc-cfg-auto-status" />
        </div>
        <div className="space-y-3 rounded-[12px] border border-[#E2E3E7] p-3">
          <div className="flex items-center justify-between">
            <p className="text-[12.5px] font-bold text-[#1C1C1E]">Rekening pembayaran (tercetak di invoice & konfirmasi)</p>
            <button className="secondary-button !px-2.5 !py-1 !text-[12px]" onClick={() => f("bank_accounts", [...(cfg.bank_accounts || []), { bank: "", account_no: "", account_name: "", note: "" }])} data-testid="doc-bank-add"><Plus size={13} /> Rekening</button>
          </div>
          {(cfg.bank_accounts || []).length === 0 ? <p className="text-[12px] text-[#8E8E93]">Belum ada rekening. Tambahkan agar pelanggan tahu ke mana harus transfer.</p> : null}
          {(cfg.bank_accounts || []).map((b, i) => (
            <div key={i} className="grid gap-2 rounded-[10px] bg-[#F7F8FA] p-2.5 sm:grid-cols-[1fr_1fr_1fr_1fr_auto]" data-testid={`doc-bank-${i}`}>
              <Input placeholder="Bank (BCA)" value={b.bank || ""} onChange={(e) => bank(i, "bank", e.target.value)} data-testid={`doc-bank-name-${i}`} />
              <Input placeholder="No. rekening" value={b.account_no || ""} onChange={(e) => bank(i, "account_no", e.target.value)} data-testid={`doc-bank-no-${i}`} />
              <Input placeholder="Atas nama" value={b.account_name || ""} onChange={(e) => bank(i, "account_name", e.target.value)} data-testid={`doc-bank-owner-${i}`} />
              <Input placeholder="Catatan (opsional)" value={b.note || ""} onChange={(e) => bank(i, "note", e.target.value)} />
              <button className="icon-button !h-9 !w-9" onClick={() => f("bank_accounts", cfg.bank_accounts.filter((_, idx) => idx !== i))} data-testid={`doc-bank-del-${i}`}><Trash2 size={13} /></button>
            </div>
          ))}
        </div>
        <div className="space-y-3 rounded-[12px] border border-[#E2E3E7] p-3 lg:col-span-2">
          <p className="text-[12.5px] font-bold text-[#1C1C1E]">Pesan WhatsApp saat mengirim dokumen</p>
          <p className="text-[11.5px] text-[#6B6B73]">Placeholder: {"{{customer_name}} {{driver_name}} {{doc_title}} {{doc_number}} {{amount}} {{refund_amount}} {{booking_code}} {{due_date}} {{remaining_amount}} {{vehicle_name}} {{destination}} {{start_datetime}} {{company_name}}"}</p>
          <div className="grid gap-3 lg:grid-cols-2">
            {[["wa_caption_invoice", "Invoice"], ["wa_caption_receipt", "Kwitansi"], ["wa_caption_confirmation", "Konfirmasi pemesanan"], ["wa_caption_spj", "Surat Perintah Jalan (ke driver)"], ["wa_caption_refund", "Nota Refund"]].map(([k, l]) => (
              <Field key={k} label={l}><Textarea rows={3} value={cfg[k] || ""} onChange={(e) => f(k, e.target.value)} data-testid={`doc-cfg-${k}`} /></Field>
            ))}
          </div>
        </div>
      </fieldset>
    </div>
  );
}

function RuleCard({ rule, meta, canEdit, onSaved }) {
  const [d, setD] = useState({ pattern: rule.pattern, prefix: rule.prefix, width: rule.width, reset: rule.reset, start: rule.start });
  const [preview, setPreview] = useState(rule.preview);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { setD({ pattern: rule.pattern, prefix: rule.prefix, width: rule.width, reset: rule.reset, start: rule.start }); setPreview(rule.preview); }, [rule]);
  useEffect(() => {
    const t = setTimeout(() => {
      apiClient.post(`/documents/numbering/${rule.key}/preview`, { ...d, width: Number(d.width) || 4, start: Number(d.start) || 1 })
        .then((r) => { setPreview(r.data.preview); setErr(""); }).catch((e) => setErr(e?.response?.data?.detail || "Pola tidak valid"));
    }, 350);
    return () => clearTimeout(t);
  }, [d, rule.key]);
  const save = async () => {
    setSaving(true);
    try { await apiClient.put(`/documents/numbering/${rule.key}`, { ...d, width: Number(d.width) || 4, start: Number(d.start) || 1 }); toast.success("Aturan penomoran disimpan"); onSaved(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); } finally { setSaving(false); }
  };
  const reset = async () => { try { await apiClient.delete(`/documents/numbering/${rule.key}`); toast.success("Dikembalikan ke bawaan"); onSaved(); } catch (e) { toast.error("Gagal mereset"); } };
  return (
    <div className="space-y-3 rounded-[12px] border border-[#E2E3E7] p-3" data-testid={`numbering-${rule.key}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><p className="text-[12.5px] font-bold text-[#1C1C1E]">{rule.label}{rule.overridden ? <span className="ml-2 rounded-full bg-[#EAF2FF] px-2 py-0.5 text-[10.5px] font-semibold text-[#0058CC]">disesuaikan</span> : null}</p>{rule.desc ? <p className="text-[11px] text-[#6B6B73]">{rule.desc}</p> : null}</div>
        <div className="text-right"><p className="text-[10.5px] uppercase text-[#8E8E93]">Nomor berikutnya</p><p className={`font-mono text-[13px] font-bold ${err ? "text-[#A8221A]" : "text-[#1C1C1E]"}`} data-testid={`numbering-preview-${rule.key}`}>{err || preview}</p></div>
      </div>
      <fieldset disabled={!canEdit} className="grid gap-2 sm:grid-cols-[2fr_1fr_1fr_1fr_1fr] disabled:opacity-60">
        <Field label="Pola"><Input className="font-mono" value={d.pattern || ""} onChange={(e) => setD((x) => ({ ...x, pattern: e.target.value }))} data-testid={`numbering-pattern-${rule.key}`} /></Field>
        <Field label="Awalan"><Input value={d.prefix || ""} onChange={(e) => setD((x) => ({ ...x, prefix: e.target.value }))} data-testid={`numbering-prefix-${rule.key}`} /></Field>
        <Field label="Digit"><Input type="number" min={1} max={8} value={d.width ?? 4} onChange={(e) => setD((x) => ({ ...x, width: e.target.value }))} data-testid={`numbering-width-${rule.key}`} /></Field>
        <Field label="Reset urut"><Select value={d.reset} onValueChange={(v) => setD((x) => ({ ...x, reset: v }))}><SelectTrigger data-testid={`numbering-reset-${rule.key}`}><SelectValue /></SelectTrigger><SelectContent>{meta.reset_options.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}</SelectContent></Select></Field>
        <Field label="Mulai dari"><Input type="number" min={1} value={d.start ?? 1} onChange={(e) => setD((x) => ({ ...x, start: e.target.value }))} data-testid={`numbering-start-${rule.key}`} /></Field>
      </fieldset>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {[...meta.global_tokens, ...meta.context_tokens.filter((t) => rule.tokens.includes(t.token))].map((t) => (
            <button key={t.token} type="button" disabled={!canEdit} title={`${t.desc} — contoh ${t.example}`} onClick={() => setD((x) => ({ ...x, pattern: `${x.pattern || ""}{${t.token}}` }))} className="rounded-full border border-[#E2E3E7] bg-white px-2 py-0.5 font-mono text-[10.5px] text-[#3C3C43] hover:border-[#B9D5FF]" data-testid={`numbering-token-${rule.key}-${t.token}`}>{`{${t.token}}`}</button>
          ))}
        </div>
        {canEdit ? <div className="flex gap-2"><button className="secondary-button !px-2.5 !py-1 !text-[12px]" onClick={reset} data-testid={`numbering-reset-btn-${rule.key}`}><RotateCcw size={13} /> Bawaan</button><button className="primary-button !px-3 !py-1.5 !text-[12.5px]" disabled={saving || Boolean(err)} onClick={save} data-testid={`numbering-save-${rule.key}`}>{saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Simpan</button></div> : null}
      </div>
    </div>
  );
}

export function NumberingPanel({ canEdit }) {
  const [meta, setMeta] = useState(null);
  const load = useCallback(() => { apiClient.get("/documents/numbering").then((r) => setMeta(r.data)).catch(() => toast.error("Gagal memuat aturan penomoran")); }, []);
  useEffect(() => { load(); }, [load]);
  if (!meta) return <LoadingState testId="numbering-loading" />;
  return (
    <div className="space-y-3" data-testid="numbering-panel">
      <p className="text-[12.5px] text-[#6B6B73]">Nomor yang sudah terbit tidak berubah — aturan hanya berlaku untuk nomor berikutnya. Klik token untuk menambahkannya ke pola.</p>
      {meta.data.map((r) => <RuleCard key={r.key} rule={r} meta={meta} canEdit={canEdit} onSaved={load} />)}
    </div>
  );
}
