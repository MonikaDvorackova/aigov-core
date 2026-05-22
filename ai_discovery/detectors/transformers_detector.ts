import type { AIDetection } from "../types"

const PATTERNS = [
  "transformers",
  "pipeline(",
  "AutoModel",
  "AutoTokenizer",
] as const

export function detectTransformers(
  filePath: string,
  content: string
): AIDetection[] {
  const out: AIDetection[] = []
  for (const signal of PATTERNS) {
    if (content.includes(signal)) {
      out.push({
        type: "transformers",
        file: filePath,
        signal,
        confidence: "experimental",
        description: "Transformers usage (local model)",
      })
    }
  }
  return out
}
