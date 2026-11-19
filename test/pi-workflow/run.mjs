import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtemp, mkdir, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const piPackage = process.argv[2];
if (!piPackage) throw new Error("Usage: node test/pi-workflow/run.mjs /path/to/node_modules/@earendil-works/pi-coding-agent");

const { RpcClient } = await import(pathToFileURL(resolve(piPackage, "dist/index.js")));
const cliPath = resolve(piPackage, "dist/bundle/cli.js");
const plugin = fileURLToPath(new URL("../../plugins/ai-development-workflow", import.meta.url));
const provider = fileURLToPath(new URL("./provider.ts", import.meta.url));
const fixture = await mkdtemp(join(tmpdir(), "pi-ai-workflow-"));
const agentDir = join(fixture, "agent");
const cwd = join(fixture, "project");
const requestsPath = join(fixture, "requests.jsonl");
const record = join(fixture, "coordination record.md");
const reminder = "上下文刚压缩";
const markerType = "ai-development-workflow-compaction";
const env = { PI_CODING_AGENT_DIR: agentDir, PI_WORKFLOW_TEST_REQUESTS: requestsPath };

let client;
async function open(sessionFile, envOverrides = {}) {
  await client?.stop();
  const args = ["--offline", "--extension", provider];
  if (sessionFile) args.push("--session", sessionFile);
  client = new RpcClient({
    cliPath, cwd, env: { ...env, ...envOverrides }, args, provider: "workflow-fixture", model: "workflow-fixture",
  });
  await client.start();
  return client.getState();
}

async function requests() {
  return (await readFile(requestsPath, "utf8")).trim().split("\n").filter(Boolean).map(JSON.parse);
}

function reminderCount(messages) {
  return JSON.stringify(messages).split(reminder).length - 1;
}

async function seed() {
  for (let i = 0; i < 3; i++) {
    await client.promptAndWait(`Fixture turn ${i}\n${"Example history preserved by Pi. ".repeat(90)}`);
  }
}

async function compactionMarkers(sessionFile) {
  return (await readFile(sessionFile, "utf8")).trim().split("\n")
    .map(JSON.parse).filter((entry) => entry.type === "custom" && entry.customType === markerType);
}

try {
  await mkdir(agentDir);
  await mkdir(cwd);
  await writeFile(join(agentDir, "settings.json"), JSON.stringify({
    compaction: { enabled: true, keepRecentTokens: 250, reserveTokens: 1000 },
  }));
  await writeFile(record, "This record belongs to the test only.\n");
  await writeFile(requestsPath, "");
  execFileSync(process.execPath, [cliPath, "install", plugin], { cwd, env: { ...process.env, ...env } });

  const original = await open();
  const commands = await client.getCommands();
  const skill = commands.find((command) => command.name === "skill:ai-development-workflow");
  assert.equal(skill?.sourceInfo.path, join(plugin, "skills", "ai-development-workflow", "SKILL.md"));
  assert.equal(await client.prompt(`/ai-workflow-register fixture-task "${record}"`), "handled");
  assert.equal((await requests()).length, 0);
  await seed();
  assert.equal(reminderCount((await requests()).at(-1)), 0);

  await client.compact();
  const markers = await compactionMarkers(original.sessionFile);
  assert.equal(markers.length, 1);
  const [pending] = markers;
  assert.equal(pending.data.sessionId, original.sessionId);
  assert.equal(pending.data.handled, false);
  assert.equal(JSON.stringify(pending).includes(record), false);

  const nodeOnly = join(fixture, "node-only");
  await mkdir(nodeOnly);
  await symlink(process.execPath, join(nodeOnly, "node"));
  await open(original.sessionFile, { PATH: nodeOnly });
  const fallback = await client.promptAndWait("Continue with Python temporarily unavailable");
  assert.ok(fallback.some((event) => event.type === "extension_ui_request" && /手动续接/.test(event.message)));
  assert.equal(reminderCount((await requests()).at(-1)), 0);
  assert.equal((await compactionMarkers(original.sessionFile)).at(-1).data.handled, false);

  const resumed = await open(original.sessionFile);
  assert.equal(resumed.sessionId, original.sessionId);
  const beforeResume = (await requests()).length;
  await client.promptAndWait("Continue original after restart");
  const resumedRequests = (await requests()).slice(beforeResume);
  assert.equal(resumedRequests.length, 1);
  assert.equal(reminderCount(resumedRequests[0]), 1);
  assert.match(JSON.stringify(resumedRequests[0]), /coordination record\.md/);
  assert.match(JSON.stringify(resumedRequests[0].find((message) => reminderCount(message))), /Fixture reply and repeated compaction summary/);
  assert.equal(reminderCount(await client.getMessages()), 0);
  assert.equal((await compactionMarkers(original.sessionFile)).at(-1).data.handled, true);

  await open(original.sessionFile);
  await client.promptAndWait("Continue once more");
  assert.equal(reminderCount((await requests()).at(-1)), 0);

  await seed();
  const beforeOverflow = (await requests()).length;
  const overflowEvents = await client.promptAndWait("force fixture overflow");
  assert.ok(overflowEvents.some((event) => event.type === "compaction_end" && event.reason === "overflow" && event.willRetry));
  const overflowRequests = (await requests()).slice(beforeOverflow);
  assert.equal(overflowRequests.length, 3, "Initial request, compaction summary, and same-run retry");
  assert.deepEqual(overflowRequests.map(reminderCount), [0, 0, 1], JSON.stringify({
    markers: (await compactionMarkers(original.sessionFile)).map((entry) => entry.data),
    summaries: overflowRequests.map((messages) => messages.map((message) => JSON.stringify(message))
      .filter((message) => message.includes("conversation history before this point"))),
  }));
  const overflowMarker = (await compactionMarkers(original.sessionFile)).at(-1).data;
  assert.equal(overflowMarker.handled, true);
  assert.notEqual(overflowMarker.compactionId, pending.data.compactionId);

  await seed();
  await client.compact();
  const lastPending = (await compactionMarkers(original.sessionFile)).at(-1).data;
  assert.equal(lastPending.handled, false);
  await client.clone();
  const fork = await client.getState();
  assert.notEqual(fork.sessionId, original.sessionId);
  assert.equal((await compactionMarkers(fork.sessionFile)).at(-1).data.sessionId, original.sessionId);
  await client.promptAndWait("Continue the fork");
  assert.equal(reminderCount((await requests()).at(-1)), 0);

  await client.switchSession(original.sessionFile);
  assert.equal(await client.prompt("/ai-workflow-unregister fixture-task"), "handled");
  await client.promptAndWait("Continue after revoking the original registration");
  assert.equal(reminderCount((await requests()).at(-1)), 0);
  assert.equal((await compactionMarkers(original.sessionFile)).at(-1).data.handled, true);
  console.log("Pi package loading, opt-in, compaction, resume, deduplication, overflow retry, fork isolation, revocation, and helper failure passed.");
} catch (error) {
  if (client?.getStderr()) console.error(client.getStderr());
  throw error;
} finally {
  await client?.stop();
  await rm(fixture, { recursive: true, force: true });
}
