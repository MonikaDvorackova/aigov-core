import { createGovAIClient } from "../../../typescript-sdk/dist/index.js";

const baseUrl = process.env.GOVAI_AUDIT_BASE_URL ?? "http://127.0.0.1:8088";
const apiKey = process.env.GOVAI_API_KEY;
const runId = process.env.GOVAI_RUN_ID ?? "demo-run";

const client = createGovAIClient({ baseUrl, apiKey });

console.log("health", await client.health());
console.log("ready", await client.ready());
console.log("summary", await client.getComplianceSummary(runId));
console.log("export", await client.exportAudit(runId));
