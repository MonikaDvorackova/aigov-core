import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"

import { isModelArtifactPath } from "./detectors/model_artifact_detector"
import type { FileInput } from "./types"

const SKIP_DIR = new Set([
  "node_modules",
  ".git",
  ".next",
  "dist",
  "build",
  ".turbo",
  "__pycache__",
  ".venv",
  "venv",
  "target",
])

const EXT_OK = new Set([
  ".ts",
  ".tsx",
  ".js",
  ".jsx",
  ".mjs",
  ".cjs",
  ".py",
  ".rs",
  ".go",
  ".java",
  ".kt",
])

export type CollectedPaths = {
  textPaths: string[]
  modelArtifactPaths: string[]
}

/**
 * Walk `rootDir` and collect text files to read and model-artifact paths
 * (`isModelArtifactPath`: `.pt`/`.pth`/`.safetensors`/`.onnx` or `pytorch_model.bin` only).
 */
export function collectFilesForScan(rootDir: string): CollectedPaths {
  const textPaths: string[] = []
  const modelArtifactPaths: string[] = []

  function walk(dir: string): void {
    let names: string[]
    try {
      names = readdirSync(dir)
    } catch {
      return
    }
    for (const name of names) {
      const full = join(dir, name)
      let st
      try {
        st = statSync(full)
      } catch {
        continue
      }
      if (st.isDirectory()) {
        if (SKIP_DIR.has(name)) continue
        walk(full)
      } else if (st.isFile()) {
        if (isModelArtifactPath(full)) {
          modelArtifactPaths.push(full)
          continue
        }
        const dot = name.lastIndexOf(".")
        const ext = dot >= 0 ? name.slice(dot) : ""
        if (EXT_OK.has(ext)) textPaths.push(full)
      }
    }
  }

  walk(rootDir)
  return { textPaths, modelArtifactPaths }
}

export function loadTextFileInputs(
  absolutePaths: string[],
  relRoot: string
): FileInput[] {
  const inputs: FileInput[] = []
  for (const abs of absolutePaths) {
    try {
      const content = readFileSync(abs, "utf8")
      inputs.push({
        path: relative(relRoot, abs) || abs,
        content,
      })
    } catch {
      // skip unreadable
    }
  }
  return inputs
}

export function toRelativePaths(
  absolutePaths: string[],
  relRoot: string
): string[] {
  return absolutePaths.map((p) => relative(relRoot, p) || p)
}
