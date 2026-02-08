export type ModelInfo = {
  id: string;
  groq_id: string;
  name: string;
  context_window: number;
  owned_by: string;
};

export const MODELS: ModelInfo[] = [
  {
    id: "llama-3.3-70b",
    groq_id: "llama-3.3-70b-specdec",
    name: "Llama 3.3 70B",
    context_window: 8192,
    owned_by: "meta",
  },
  {
    id: "llama-3.1-8b",
    groq_id: "llama-3.1-8b-instant",
    name: "Llama 3.1 8B",
    context_window: 131072,
    owned_by: "meta",
  },
  {
    id: "llama-3.3-70b-versatile",
    groq_id: "llama-3.3-70b-versatile",
    name: "Llama 3.3 70B Versatile",
    context_window: 131072,
    owned_by: "meta",
  },
  {
    id: "mixtral-8x7b",
    groq_id: "mixtral-8x7b-32768",
    name: "Mixtral 8x7B",
    context_window: 32768,
    owned_by: "mistral",
  },
  {
    id: "gemma2-9b",
    groq_id: "gemma2-9b-it",
    name: "Gemma 2 9B",
    context_window: 8192,
    owned_by: "google",
  },
  {
    id: "deepseek-r1-70b",
    groq_id: "deepseek-r1-distill-llama-70b",
    name: "DeepSeek R1 (Distill 70B)",
    context_window: 131072,
    owned_by: "deepseek",
  },
];

const MODEL_MAP = new Map(MODELS.map((m) => [m.id, m]));

export function resolveModel(polarisId: string): ModelInfo | undefined {
  return MODEL_MAP.get(polarisId);
}
