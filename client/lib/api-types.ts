export type Role =
  | "coder"
  | "verifier"
  | "faskes_admin"
  | "auditor"
  | "rule_admin"
  | "rule_approver";

export type Principal = {
  user_id: string;
  faskes_id: string;
  name: string;
  email: string;
  role: Role;
  permissions: string[];
};

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export type Code = {
  id: string;
  code_type: string;
  code: string;
  position: string | null;
  description: string | null;
};

export type ClaimListItem = {
  id: string;
  episode_no: string;
  patient_pseudonym: string;
  status: string;
  version: number;
  updated_at: string;
  code_count: number;
  open_review_count: number;
  highest_open_tier: string | null;
};

export type Job = {
  id: string;
  claim_id: string;
  claim_version: number;
  event_type: string;
  status: string;
  attempt_count: number;
  reason: string | null;
  error_message: string | null;
  created_at: string;
  processed_at: string | null;
  idempotent_replay: boolean;
};

export type RunSummary = {
  id: string;
  vector_code: string;
  rule_version: string;
  status: string;
  outcome: string | null;
  claim_version: number;
  stale: boolean;
  rerun_of_run_id: string | null;
  abstain_reason: string | null;
  tier_counts: Record<string, number>;
  started_at: string;
  finished_at: string | null;
};

export type Claim = {
  id: string;
  episode_no: string;
  patient_pseudonym: string;
  status: string;
  version: number;
  episode_start: string | null;
  episode_end: string | null;
  submitted_at: string | null;
  locked_at: string | null;
  created_at: string;
  updated_at: string;
  codes: Code[];
};

export type ClaimDetail = Claim & {
  evidence_count: number;
  quarantined_count: number;
  open_review_count: number;
  evidence_updated_after_run: boolean;
  runs: RunSummary[];
  latest_job: Job | null;
};

export type Evidence = {
  id: string;
  source_id: string;
  source_type: string;
  source_ref: string;
  kind: string;
  assertion: string;
  recorded_at: string;
  content_hash: string;
  injection_suspected: boolean;
  content_text: string | null;
};

export type Source = {
  id: string;
  source_type: string;
  system_ref: string;
  is_enabled: boolean;
  health_status: string;
  last_health_check_at: string | null;
  last_synced_at: string | null;
  freshness_sla_seconds: number;
  fresh: boolean;
  coverage: Record<string, unknown>;
};

export type QueueItem = {
  intervention_id: string;
  tier: string;
  tier_label: string;
  vector_code: string;
  claim_id: string;
  episode_no: string;
  claim_status: string;
  created_at: string;
  resolved_at: string | null;
  assessed_by_me: boolean;
  requires_assessment: boolean;
};

export type Citation = {
  evidence_item_id: string;
  evidence_hash: string;
  validation_status: string;
  role: string | null;
  quote: string | null;
  start: number | null;
  end: number | null;
  invalid_reason: string | null;
};

export type DeltaRequirement = {
  requirement_id: string;
  label: string;
  min_count: number;
};

export type DeltaObserved = {
  requirement_id: string;
  satisfied: boolean;
  supporting_evidence_ids: string[];
  out_of_window_evidence_ids: string[];
};

export type Delta = {
  check?: string;
  code?: string;
  rule_validation?: string;
  expected?: DeltaRequirement[];
  observed?: DeltaObserved[];
  missing?: string[];
  contradicting_evidence_ids?: string[];
  conflicting_codes?: string[];
  coverage_gaps?: string[];
  limitations?: string[];
  proposed_actions?: { code: string; label: string }[];
  safety_flags?: string[];
  governor_reasons?: string[];
  signal_strength?: number;
  coverage?: { sources?: unknown[]; comparisons?: unknown[] };
};

export type Recommendation = {
  finding_id: string | null;
  finding_status: string | null;
  mismatch_desc: string | null;
  abstain_reason: string | null;
  signal_strength: number | null;
  delta: Delta;
  citations: Citation[];
  policy_rule: string;
};

export type Assessment = {
  id: string;
  intervention_id: string;
  self_verdict: string;
  self_note: string | null;
  submitted_at: string;
};

export type VerdictRecord = {
  id: string;
  intervention_id: string;
  verifier_id: string;
  verdict: string;
  follow_up: string;
  rationale: string | null;
  supersedes_verdict_id: string | null;
  time_to_decision_ms: number | null;
  created_at: string;
};

export type InterventionDetail = {
  id: string;
  tier: string;
  tier_label: string;
  vector_code: string;
  created_at: string;
  resolved_at: string | null;
  stale: boolean;
  evidence_updated_after_run: boolean;
  claim: {
    id: string;
    episode_no: string;
    patient_pseudonym: string;
    status: string;
    version: number;
    codes: Code[];
  };
  run: {
    id: string;
    status: string;
    outcome: string | null;
    claim_version: number;
    rule_version_id: string;
    rule_version: string;
    rule_validation_status: string;
    policy_version: string;
    model_name: string;
    model_version: string;
    prompt_version: string;
    correlation_id: string;
    started_at: string;
  };
  evidence: Evidence[];
  gate: { required: boolean; revealed: boolean; own_assessment: Assessment | null };
  recommendation: Recommendation | null;
  verdicts: VerdictRecord[];
};

export type Step = {
  seq: number;
  step_type: string;
  tool_name: string | null;
  status: string;
  source_id: string | null;
  result_ref: Record<string, unknown> | null;
  latency_ms: number | null;
  error_message: string | null;
};

export type RunFinding = {
  id: string;
  status: string;
  claim_code: string | null;
  tier: string | null;
  intervention_id: string | null;
  revealed: boolean;
  mismatch_desc: string | null;
  signal_strength: number | null;
  delta: Delta | null;
  citations: Citation[];
};

export type RunDetail = {
  id: string;
  claim_id: string;
  claim_version: number;
  vector_code: string;
  status: string;
  outcome: string | null;
  stale: boolean;
  trigger: string;
  rerun_of_run_id: string | null;
  correlation_id: string;
  rule_version: string;
  policy_version: string;
  model_name: string;
  model_version: string;
  prompt_version: string;
  abstain_reason: string | null;
  coverage: { sources?: Record<string, unknown>[]; comparisons?: { code: string; gaps: string[]; quarantined: number }[] };
  validation_errors: Record<string, unknown> | null;
  tier_counts: Record<string, number>;
  started_at: string;
  finished_at: string | null;
  steps: Step[];
  findings: RunFinding[];
};

export type Metric = {
  code: string;
  label: string;
  definition: string;
  unit: string;
  target: string | null;
  status: "ok" | "no_data" | "not_measured";
  value: number | null;
  numerator: number | null;
  denominator: number | null;
  sample_size: number;
  note: string | null;
  breakdown: Record<string, unknown>;
  window_start: string;
  window_end: string;
};

export type Dashboard = {
  claims_by_status: Record<string, number>;
  jobs_by_status: Record<string, number>;
  open_review_by_tier: Record<string, number>;
  run_outcomes_30d: Record<string, number>;
  sources: {
    id: string;
    source_type: string;
    system_ref: string;
    health_status: string;
    is_enabled: boolean;
    last_synced_at: string | null;
  }[];
  generated_at: string;
};

export type AuditEntry = {
  id: string;
  seq: number;
  created_at: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  actor_type: string;
  actor_id: string | null;
  payload: Record<string, unknown>;
  prev_hash: string | null;
  record_hash: string;
};

export type ChainVerification = {
  valid: boolean;
  checked: number;
  first_invalid_seq: number | null;
  reason: string | null;
};

export type RuleVersionBrief = {
  id: string;
  version: string;
  status: string;
  validation_status: string;
  created_by: string | null;
  approved_by: string | null;
  submitted_at: string | null;
  approved_at: string | null;
  activated_at: string | null;
  retired_at: string | null;
};

export type RuleSet = {
  id: string;
  name: string;
  description: string | null;
  vector: { id: string; code: string; name: string; description: string | null; is_active: boolean };
  active_version_id: string | null;
  versions: RuleVersionBrief[];
};

export type RuleVersion = RuleVersionBrief & {
  rule_set_id: string;
  rule_set_name: string;
  vector_code: string;
  expected_rules: { id: string; code_pattern: string; spec: Record<string, unknown>; is_active: boolean }[];
};

export type PolicyRule = {
  id: string;
  code: string;
  tier: string;
  priority: number;
  condition: Record<string, unknown>;
  is_active: boolean;
};

export type PolicyVersion = {
  id: string;
  version: string;
  status: string;
  config_hash: string;
  created_by: string | null;
  approved_by: string | null;
  approved_at: string | null;
  activated_at: string | null;
  rules: PolicyRule[];
};

export type EvaluationSummary = {
  engine?: string;
  validation_set?: string;
  overall?: Record<string, number | null>;
};

export type RuleUpdate = {
  id: string;
  status: string;
  basis_verdict_ids: string[];
  base_rule_version_id: string;
  result_rule_version_id: string | null;
  proposed_by: string | null;
  decided_by: string | null;
  proposed_change: Record<string, unknown>;
  evaluation: {
    regression_count?: number;
    improvement_count?: number;
    regressions?: string[];
    improvements?: string[];
    changed_cases?: { id: string; from: string; to: string; expected: string }[];
    vector?: string;
    baseline?: EvaluationSummary;
    candidate?: EvaluationSummary;
  } | null;
  created_at: string;
  evaluated_at: string | null;
  decided_at: string | null;
};
