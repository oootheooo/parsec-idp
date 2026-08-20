export type Workspace = {
  id: string;
  name: string;
  slug: string;
  role: string;
};
export type User = {
  id: string;
  email: string;
  display_name: string;
  workspaces: Workspace[];
};
export type ListResponse<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};
export type ProcessorVersion = {
  id: string;
  processor_id: string;
  version_number: number;
  state: "draft" | "published";
  schema_json: Record<string, unknown>;
  instructions: string;
  validation_config: Record<string, unknown>[];
  review_config: Record<string, unknown>;
  extraction_config: Record<string, unknown>;
};
export type Processor = {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  status: string;
  latest_version_id: string | null;
  updated_at: string;
  versions?: ProcessorVersion[];
  draft_version_id?: string;
};
export type DocumentEvent = {
  id: string;
  to_status: string;
  message: string | null;
  created_at: string;
};
export type ProcessingMode = "smart" | "native" | "visual" | "docling";
export type VisualReader = "ocr" | "vision";
export type ProcessingPageRoute = {
  page_number: number;
  route: string;
  reader?: string | null;
  reasons: string[];
};
export type DocumentItem = {
  id: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  status: string;
  selected_processor_id: string | null;
  page_count: number | null;
  error_message_safe: string | null;
  processing_mode: ProcessingMode;
  visual_reader: VisualReader;
  processing_route: Record<string, unknown> & {
    route?: string;
    visual_reader?: VisualReader;
    pages?: ProcessingPageRoute[];
  };
  created_at: string;
  updated_at: string;
  events?: DocumentEvent[];
  latest_extraction_id?: string | null;
  original_url?: string;
};
export type Evidence = {
  page_number: number | null;
  bbox: { x0: number; y0: number; x1: number; y1: number } | null;
  source_text: string | null;
  evidence_strength: number;
};
export type ExtractionField = {
  id: string;
  json_path: string;
  field_label: string;
  value_json: unknown;
  effective_value: unknown;
  confidence: number;
  confidence_level: string;
  validation_state: string;
  review_state: string;
  evidence: Evidence[];
};
export type Extraction = {
  id: string;
  data: Record<string, unknown>;
  effective_data: Record<string, unknown>;
  fields: ExtractionField[];
  validations: {
    id: string;
    passed: boolean;
    message: string;
    severity: string;
  }[];
  validation_summary: { failed: number; passed: number };
  review_summary: { reviewed: number; total: number };
};
