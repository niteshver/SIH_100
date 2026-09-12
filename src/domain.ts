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

// Live data is intentionally empty until an officer publishes a tender or a bidder submits an application.
// Keeping this collection empty prevents demo records from being presented as real procurement activity.
export const DEMO_TENDERS: Tender[] = []
export const DEMO_BIDS: Bid[] = []
export const DEMO_ACTIVITY: Activity[] = []

export const demoServices = {
  tender: { list: async (): Promise<ServiceResult<Tender[]>> => ({ data: DEMO_TENDERS, source: 'demo', requiresReview: true }) },
  bid: { list: async (): Promise<ServiceResult<Bid[]>> => ({ data: DEMO_BIDS, source: 'demo', requiresReview: true }) },
  notification: { list: async (): Promise<ServiceResult<Activity[]>> => ({ data: DEMO_ACTIVITY, source: 'demo', requiresReview: true }) },
}
