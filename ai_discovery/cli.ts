import { join } from "node:path"

import { formatDiscoveryReportFromResult } from "./discoveryResult"
import { runDiscovery } from "./runDiscovery"

/** Repo root when running compiled output from `ai_discovery/dist/cli.js`. */
function defaultRoot(): string {
  return join(__dirname, "..", "..")
}

const args = process.argv.slice(2)
const root = args[0] ? join(process.cwd(), args[0]) : defaultRoot()
const result = runDiscovery(root)
console.log(formatDiscoveryReportFromResult(result))
