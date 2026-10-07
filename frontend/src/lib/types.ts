export type Resolved = { field: string; value: string | number; source: string };
export type Option = { id: string; title: string; merchant_name: string; city: string; total: number; unit_price: number; rating: number | null; reviews: number | null; perks?: string; best?: boolean; verified?: boolean };
export type Msg = {
  id?: number | string; role: "user" | "agent"; content: string; ts: number;
  options?: Option[]; browsed?: { domain: string; status: string; note: string }[]; resolved?: Resolved[]; needs?: string | null;
  failed?: boolean; fresh?: boolean;
};
export type ChatContext = {
  kind?: string; city?: string; budget?: number; guests?: number; units?: number; merchant?: string; currency?: string;
  dates?: { text: string; start?: string; end?: string | null }; last_selected?: { title?: string; merchant?: string };
};
export type Conversation = { id: string; title: string; updated: number };
