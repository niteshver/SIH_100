export type UserRole = 'OFFICER' | 'BIDDER'
export type Workspace = 'overview' | 'tenders' | 'bids' | 'documents' | 'audit'
export type Status = 'OPEN' | 'IN_REVIEW' | 'VERIFIED' | 'REQUIRES_REVIEW' | 'DRAFT'

export type Tender = {
  id: string
  title: string
  department: string
  deadline: string
  budget: string
  status: Status
  bids: number
  requirements: string[]
}

export type Bid = {
  id: string
  bidder: string
  tender: string
  submitted: string
  score: number
  risk: 'LOW' | 'MEDIUM' | 'HIGH'
  status: Status
}

export type Activity = {
  id: string
  label: string
  detail: string
  time: string
  tone: 'blue' | 'green' | 'amber'
}

export type ServiceResult<T> = {
  data: T
  source: 'demo' | 'api'
  requiresReview: boolean
}

export interface TenderService {
  list(): Promise<ServiceResult<Tender[]>>
  create(input: Partial<Tender>): Promise<ServiceResult<Tender>>
}

export interface BidService {
  list(tenderId?: string): Promise<ServiceResult<Bid[]>>
}

export interface DocumentService {
  upload(file: File, scope: 'tender' | 'bid'): Promise<ServiceResult<{ name: string; size: number; hash?: string }>>
}

export interface VerificationService {
  verify(type: string, value: string): Promise<ServiceResult<{ status: Status; reference?: string }>>
}

export interface AnalysisService {
  analyze(tenderId: string, bidId?: string): Promise<ServiceResult<{ score: number; risk: Bid['risk']; explanation: string }>>
}

export interface NotificationService {
  list(): Promise<ServiceResult<Activity[]>>
}

export interface AuditService {
  record(event: string, metadata?: Record<string, string>): Promise<void>
}

export const DEMO_TENDERS: Tender[] = [
  { id: 'TND-2026-001', title: 'Construction of Community Health Centre', department: 'Department of Health & Family Welfare', deadline: '18 Mar 2026', budget: '₹2.4 Cr', status: 'OPEN', bids: 24, requirements: ['5+ years experience', 'GST registration', '₹1 Cr turnover'] },
  { id: 'TND-2026-002', title: 'Smart Classroom Equipment & Installation', department: 'Department of School Education', deadline: '24 Mar 2026', budget: '₹86 L', status: 'OPEN', bids: 11, requirements: ['OEM authorization', 'Make in India declaration', '3+ years experience'] },
  { id: 'TND-2025-119', title: 'District E-Governance Network Upgrade', department: 'Department of Information Technology', deadline: 'Closed 04 Mar 2026', budget: '₹5.8 Cr', status: 'IN_REVIEW', bids: 37, requirements: ['ISO certification', '₹3 Cr turnover', 'Technical proposal'] },
]

export const DEMO_BIDS: Bid[] = [
  { id: 'BID-260318-0842', bidder: 'Aarav Infrastructure Pvt. Ltd.', tender: 'Community Health Centre', submitted: 'Today, 09:42', score: 94, risk: 'LOW', status: 'VERIFIED' },
  { id: 'BID-260317-0718', bidder: 'Nexora Build Systems', tender: 'Community Health Centre', submitted: 'Yesterday, 17:18', score: 81, risk: 'MEDIUM', status: 'REQUIRES_REVIEW' },
  { id: 'BID-260316-0431', bidder: 'Pragati Civil Works', tender: 'E-Governance Network Upgrade', submitted: '16 Mar, 12:06', score: 76, risk: 'MEDIUM', status: 'IN_REVIEW' },
]

export const DEMO_ACTIVITY: Activity[] = [
  { id: '1', label: 'Bid evidence verified', detail: 'Aarav Infrastructure · BID-260318-0842', time: '12 min ago', tone: 'green' },
  { id: '2', label: 'New tender published', detail: 'Smart Classroom Equipment & Installation', time: '48 min ago', tone: 'blue' },
  { id: '3', label: 'Manual review required', detail: 'Nexora Build Systems · GST mismatch', time: '1 hr ago', tone: 'amber' },
]

export const demoServices = {
  tender: { list: async (): Promise<ServiceResult<Tender[]>> => ({ data: DEMO_TENDERS, source: 'demo', requiresReview: true }) },
  bid: { list: async (): Promise<ServiceResult<Bid[]>> => ({ data: DEMO_BIDS, source: 'demo', requiresReview: true }) },
  notification: { list: async (): Promise<ServiceResult<Activity[]>> => ({ data: DEMO_ACTIVITY, source: 'demo', requiresReview: true }) },
}
