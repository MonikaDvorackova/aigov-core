export type DetectionConfidence = "high" | "experimental"

export type AIDetection = {
  type: "openai" | "transformers" | "model_artifact"
  file: string
  signal: string
  confidence: DetectionConfidence
  description: string
}

export type FileInput = {
  path: string
  content: string
}
