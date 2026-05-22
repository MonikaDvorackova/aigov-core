import type { AIDetection } from "../types"

const PATTERNS = [
  "openai",
  "OpenAI(",
  ".chat.completions",
  ".responses.create",
] as const

export function detectOpenAI(filePath: string, content: string): AIDetection[] {
  const out: AIDetection[] = []
  for (const signal of PATTERNS) {
    if (content.includes(signal)) {
      out.push({
        type: "openai",
        file: filePath,
        signal,
        confidence: "high",
        description: "OpenAI API usage (LLM inference)",
      })
    }
  }
  return out
}
