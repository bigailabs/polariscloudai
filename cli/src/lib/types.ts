// API response types for Polaris Cloud

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  demo_mode: boolean;
  database: string;
  auth_enabled: boolean;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string | null;
  tier: string;
  compute_minutes_used: number;
  compute_minutes_limit: number;
  storage_bytes_used: number;
  storage_bytes_limit: number;
  created_at: string;
  auth_provider: string | null;
  avatar_url: string | null;
}

export interface ApiKey {
  id: string;
  user_id: string;
  name: string;
  description: string;
  key?: string;
  key_prefix?: string;
  created_at: string;
  last_used: string | null;
  request_count?: number;
  is_active?: boolean;
}

export interface TemplateParameter {
  name: string;
  label: string;
  type: string;
  required: boolean;
  default?: any;
  placeholder?: string;
  options?: { value: string; label: string }[];
  description?: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  parameters: TemplateParameter[];
  default_port: number;
  estimated_deploy_time: string;
  access_type: string;
  features: string[];
  color: string;
}

export interface Deployment {
  id: string;
  user_id: string;
  template_id: string;
  name: string;
  status: string;
  provider: string;
  provider_instance_id?: string;
  machine_type?: string;
  host?: string;
  port?: number;
  access_url?: string;
  config?: Record<string, any>;
  error_message?: string;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
}

export interface UsageRecord {
  id: string;
  provider: string;
  machine_type: string;
  started_at: string;
  ended_at?: string;
  minutes: number;
  cost_usd: string;
  billing_month: string;
}

export interface StorageVolume {
  id: string;
  provider: string;
  bucket_name: string;
  path: string;
  size_bytes: number;
  created_at: string;
}

export interface UsageAnalytics {
  total_requests: number;
  this_month: number;
  last_month: number;
  daily_data: { date: string; requests: number }[];
  key_usage: { id: string; name: string; total_requests: number; last_used: string | null }[];
}

export interface DashboardStats {
  tier: string;
  compute_minutes_used: number;
  compute_minutes_limit: number;
  storage_bytes_used: number;
  storage_bytes_limit: number;
  active_deployments: number;
  total_deployments: number;
  api_keys_count: number;
}

export interface PolarisConfig {
  apiUrl: string;
  defaultFormat: "table" | "json";
  noColor: boolean;
}
