import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8001'
export const apiClient = axios.create({ baseURL: BASE })

export interface Tender {
  reference: string
  contracting_authority: string | null
  object: string | null
  tender_type: string | null
  procedure_type: string | null
  publication_date: string | null
  deadline_date: string | null
  region: string | null
  wilaya: string | null
  source_url: string | null
  scraped_at: string | null
  // Only populated for tenders that reached the award stage and were
  // successfully scraped from their PV/award notice — null means "not yet
  // available", not "zero MAD".
  montant_mad: number | null
  attributaire: string | null
}

export interface TenderList {
  items: Tender[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface QueryResponse {
  answer: string
  sources: { document_id: string; title: string; excerpt: string; relevance_score: number }[]
  confidence: number
  language: string
}

export const fetchTenders = (params: Record<string, string | number | undefined>) =>
  apiClient.get<TenderList>('/api/v1/tenders/', { params }).then((r) => r.data)

export const queryNL = (question: string, language = 'fr') =>
  apiClient.post<QueryResponse>('/api/v1/query/', { question, language }).then((r) => r.data)
