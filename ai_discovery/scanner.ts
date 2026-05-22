import { detectModelArtifact } from "./detectors/model_artifact_detector"
import { detectOpenAI } from "./detectors/openai_detector"
import { detectTransformers } from "./detectors/transformers_detector"
import { formatDiscoveryReport } from "./discoveryResult"
import type { AIDetection, FileInput } from "./types"

export function scanFiles(
  files: FileInput[],
  modelArtifactPaths: string[] = []
): AIDetection[] {
  const results: AIDetection[] = []
  for (const { path: filePath, content } of files) {
    results.push(...detectOpenAI(filePath, content))
    results.push(...detectTransformers(filePath, content))
  }
  for (const filePath of modelArtifactPaths) {
    results.push(...detectModelArtifact(filePath))
  }
  return results
}

/** Debug / scripts: formats from raw detections (runs the shared structured builder internally). */
export function printDiscoveryReport(detections: AIDetection[]): void {
  console.log(formatDiscoveryReport(detections))
}

export { formatDiscoveryReport } from "./discoveryResult"
