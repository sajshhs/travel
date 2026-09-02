import { toast } from "sonner";
import apiClient from "@/services/apiClient";

export async function fetchPdfBlobUrl(url) {
  const res = await apiClient.get(url, { responseType: "blob" });
  return window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
}

export async function downloadPdf(url, filename) {
  try {
    const blobUrl = await fetchPdfBlobUrl(url);
    const a = document.createElement("a");
    a.href = blobUrl; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    window.URL.revokeObjectURL(blobUrl);
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Gagal mengunduh PDF");
  }
}

export async function openPdf(url) {
  try {
    const blobUrl = await fetchPdfBlobUrl(url);
    window.open(blobUrl, "_blank", "noopener");
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Gagal membuka PDF");
  }
}

export const INVOICE_STATUS = {
  draft: { l: "Draft", tone: "neutral" },
  sent: { l: "Terkirim", tone: "info" },
  partial: { l: "Sebagian", tone: "warning" },
  paid: { l: "Lunas", tone: "success" },
  void: { l: "Batal", tone: "danger" },
};

export const KIND_LABEL = { dp: "Invoice DP", settlement: "Invoice Pelunasan", full: "Invoice Penuh" };

export function safeName(number, fallback) {
  return `${(number || fallback).replace(/\//g, "-")}.pdf`;
}
