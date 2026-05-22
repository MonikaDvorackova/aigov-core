export type {
  AIDetection,
  DetectionConfidence,
  FileInput,
} from "./types"
export type {
  DiscoveryGroupedSummary,
  DiscoveryNote,
  DiscoveryResponse,
} from "./discoveryResult"
export {
  buildDiscoveryResult,
  combinedLocalInferenceFolders,
  formatDiscoveryReport,
  formatDiscoveryReportFromResult,
} from "./discoveryResult"
export {
  collectFilesForScan,
  loadTextFileInputs,
  toRelativePaths,
} from "./filesystemCollect"
export { runDiscovery } from "./runDiscovery"
export { printDiscoveryReport, scanFiles } from "./scanner"
export type {
  AddConfirmedResult,
  ConfirmSystemInput,
  ConfirmedAISystem,
} from "./confirmedStore"
export {
  addConfirmedSystem,
  listConfirmedSystems,
  normalizeCandidatePath,
} from "./confirmedStore"
