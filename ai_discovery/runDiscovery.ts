import { resolve } from "node:path"

import {
  collectFilesForScan,
  loadTextFileInputs,
  toRelativePaths,
} from "./filesystemCollect"
import { buildDiscoveryResult } from "./discoveryResult"
import { scanFiles } from "./scanner"
import type { DiscoveryResponse } from "./discoveryResult"

/**
 * Run a full filesystem scan under `absoluteRoot` (must already be resolved and safe).
 * Text files are read for OpenAI / Transformers signals. Model artifacts are detected from
 * filenames only: `.pt`, `.pth`, `.safetensors`, `.onnx`, or basename `pytorch_model.bin`
 * (arbitrary `.bin` files are not treated as model artifacts).
 */
export function runDiscovery(absoluteRoot: string): DiscoveryResponse {
  const root = resolve(absoluteRoot)
  const { textPaths, modelArtifactPaths } = collectFilesForScan(root)
  const inputs = loadTextFileInputs(textPaths, root)
  const modelRel = toRelativePaths(modelArtifactPaths, root)
  const detections = scanFiles(inputs, modelRel)
  return buildDiscoveryResult(detections)
}
