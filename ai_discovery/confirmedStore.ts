export type ConfirmedAISystem = {
  id: string
  source: "discovery"
  detectionType: "openai" | "transformers" | "model_artifact"
  file: string
  createdAt: string
}

export type ConfirmSystemInput = {
  detectionType: "openai" | "transformers" | "model_artifact"
  file: string
}

export type AddConfirmedResult = {
  record: ConfirmedAISystem
  /** False when this detectionType + file was already stored. */
  created: boolean
}

const systems: ConfirmedAISystem[] = []

function newId(): string {
  return `cas_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`
}

/** Exported so tooling/tests can align with UI; same rules as dashboard `candidatePathNormalize`. */
export function normalizeCandidatePath(file: string): string {
  return file
    .trim()
    .replace(/\\/g, "/")
    .replace(/\/+/g, "/")
    .toLowerCase()
}

function normalizeFile(file: string): string {
  return normalizeCandidatePath(file)
}

export function addConfirmedSystem(input: ConfirmSystemInput): AddConfirmedResult {
  const file = normalizeFile(input.file)
  const existing = systems.find(
    (s) => s.detectionType === input.detectionType && s.file === file
  )
  if (existing) {
    return { record: existing, created: false }
  }
  const row: ConfirmedAISystem = {
    id: newId(),
    source: "discovery",
    detectionType: input.detectionType,
    file,
    createdAt: new Date().toISOString(),
  }
  systems.push(row)
  return { record: row, created: true }
}

export function listConfirmedSystems(): ConfirmedAISystem[] {
  return [...systems]
}
