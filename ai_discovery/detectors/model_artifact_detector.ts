import { basename } from "node:path"

import type { AIDetection } from "../types"

/**
 * Experimental model-weight **filename** signals only (no file reads).
 *
 * A path matches when its basename (case-insensitive):
 * - ends with `.pt`, `.pth`, `.safetensors`, or `.onnx`, or
 * - equals `pytorch_model.bin` (the only `.bin` basename matched; arbitrary `.bin` files are ignored).
 */
/** Longest first (e.g. `.safetensors` before shorter suffixes). */
const DIRECT_EXTENSIONS = [".safetensors", ".pth", ".onnx", ".pt"] as const

const KNOWN_BIN_BASENAMES = new Set(["pytorch_model.bin"])

function matchesDirectExtension(name: string): boolean {
  return DIRECT_EXTENSIONS.some((ext) => name.endsWith(ext))
}

function matchesKnownBin(name: string): boolean {
  return name.endsWith(".bin") && KNOWN_BIN_BASENAMES.has(name)
}

function matchesModelArtifactFilename(filePath: string): boolean {
  const name = basename(filePath).toLowerCase()
  if (matchesKnownBin(name)) return true
  return matchesDirectExtension(name)
}

/** Filename-only check for collectors that must not read file contents. */
export function isModelArtifactPath(filePath: string): boolean {
  return matchesModelArtifactFilename(filePath)
}

export function detectModelArtifact(filePath: string): AIDetection[] {
  if (!matchesModelArtifactFilename(filePath)) return []
  return [
    {
      type: "model_artifact",
      file: filePath,
      signal: basename(filePath),
      confidence: "experimental",
      description: "Possible model weights artifact",
    },
  ]
}
