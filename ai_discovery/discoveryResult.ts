import { dirname } from "node:path"

import type { AIDetection } from "./types"

export type DiscoveryGroupedSummary = {
  highConfidence: {
    openai: { files: string[] }
  }
  experimental: {
    transformers: { files: string[] }
    /** See `detectors/model_artifact_detector.ts` for filename rules (not arbitrary `.bin`). */
    modelArtifacts: { files: string[] }
  }
}

export type DiscoveryNote = {
  code: "combined_local_inference"
  message: string
  folders: string[]
}

export type DiscoveryResponse = {
  detections: AIDetection[]
  groupedSummary: DiscoveryGroupedSummary
  notes: DiscoveryNote[]
}

function uniqueSortedFiles(
  detections: AIDetection[],
  type: AIDetection["type"]
): string[] {
  const set = new Set<string>()
  for (const d of detections) {
    if (d.type === type) set.add(d.file)
  }
  return [...set].sort()
}

export function combinedLocalInferenceFolders(
  detections: AIDetection[]
): string[] {
  const tDirs = new Set(
    detections
      .filter((d) => d.type === "transformers")
      .map((d) => dirname(d.file))
  )
  const mDirs = new Set(
    detections
      .filter((d) => d.type === "model_artifact")
      .map((d) => dirname(d.file))
  )
  const both = [...tDirs].filter((dir) => mDirs.has(dir))
  return both.sort()
}

export function buildDiscoveryResult(detections: AIDetection[]): DiscoveryResponse {
  const folders = combinedLocalInferenceFolders(detections)
  const notes: DiscoveryNote[] = []
  if (folders.length > 0) {
    notes.push({
      code: "combined_local_inference",
      message: "Possible local model inference (combined signals)",
      folders,
    })
  }

  return {
    detections,
    groupedSummary: {
      highConfidence: {
        openai: { files: uniqueSortedFiles(detections, "openai") },
      },
      experimental: {
        transformers: { files: uniqueSortedFiles(detections, "transformers") },
        modelArtifacts: { files: uniqueSortedFiles(detections, "model_artifact") },
      },
    },
    notes,
  }
}

/**
 * Plain-text report from an already-built structured result (CLI path — no second grouping pass).
 * Not used by the HTTP API; the API returns JSON (`DiscoveryResponse`).
 */
export function formatDiscoveryReportFromResult(result: DiscoveryResponse): string {
  const { groupedSummary, notes } = result
  const o = groupedSummary.highConfidence.openai.files
  const t = groupedSummary.experimental.transformers.files
  const m = groupedSummary.experimental.modelArtifacts.files

  const lines: string[] = ["Detected AI usage:", ""]

  lines.push("High confidence:")
  lines.push("- OpenAI usage")
  if (o.length === 0) {
    lines.push("  (none)")
  } else {
    for (const f of o) {
      lines.push(`  - ${f}`)
    }
  }

  lines.push("")
  lines.push("Experimental:")
  lines.push("- Transformers usage")
  if (t.length === 0) {
    lines.push("  (none)")
  } else {
    for (const f of t) {
      lines.push(`  - ${f}`)
    }
  }

  lines.push("- Model artifacts")
  if (m.length === 0) {
    lines.push("  (none)")
  } else {
    for (const f of m) {
      lines.push(`  - ${f}`)
    }
  }

  for (const n of notes) {
    lines.push("")
    lines.push(`${n.message}:`)
    for (const folder of n.folders) {
      lines.push(`  - ${folder}`)
    }
  }

  return lines.join("\n")
}

/** Presentation helper: builds structured result, then formats (handy when you only have raw detections). */
export function formatDiscoveryReport(detections: AIDetection[]): string {
  return formatDiscoveryReportFromResult(buildDiscoveryResult(detections))
}
