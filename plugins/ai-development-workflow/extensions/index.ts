import { isAbsolute, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  getAgentDir,
  getLatestCompactionEntry,
  type ExtensionAPI,
  type ExtensionContext,
} from "@earendil-works/pi-coding-agent";

const script = fileURLToPath(new URL(
  "../skills/ai-development-workflow/scripts/codex_compact.py",
  import.meta.url,
));
const compactionStateType = "ai-development-workflow-compaction";

interface CompactionState {
  sessionId: string;
  compactionId: string;
  handled: boolean;
}

function compactionState(ctx: ExtensionContext, sessionId: string, compactionId: string) {
  // Count delivery anywhere in the same session, even after navigating its tree.
  const entries = ctx.sessionManager.getEntries();
  for (let index = entries.length - 1; index >= 0; index--) {
    const entry = entries[index];
    if (entry.type !== "custom" || entry.customType !== compactionStateType) continue;
    const data = entry.data as Partial<CompactionState> | undefined;
    if (data?.sessionId === sessionId && data.compactionId === compactionId && typeof data.handled === "boolean") {
      return data.handled;
    }
  }
  return undefined;
}

function activeCompaction(ctx: ExtensionContext) {
  return getLatestCompactionEntry(ctx.sessionManager.getBranch());
}

export default function (pi: ExtensionAPI) {
  async function run(action: "register" | "unregister" | "context", sessionId: string, ...args: string[]) {
    const result = await pi.exec(
      "python3",
      ["-B", script, "--host", "pi", "--config-dir", resolve(getAgentDir()), action, sessionId, ...args],
      { timeout: 5000, maxBuffer: 1024 * 1024 },
    );
    if (result.code !== 0) throw new Error(result.stderr.trim() || `python3 exited with status ${result.code}`);
    return result.stdout.trim();
  }

  async function readReminder(ctx: ExtensionContext, sessionId: string) {
    try {
      return await run("context", sessionId);
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      const message = `无法读取压缩续接登记。请按最新协调记录手动续接。\n${detail}`;
      if (ctx.hasUI) ctx.ui.notify(message, "warning");
      else console.warn(message);
      return undefined;
    }
  }

  pi.registerCommand("ai-workflow-register", {
    description: "登记当前会话负责统筹的任务与协调记录",
    handler: async (args, ctx) => {
      const match = /^(\S+)\s+(.+)$/s.exec(args.trim());
      const record = match?.[2].replace(/^(["'])(.+)\1$/s, "$2");
      if (!match || !record || !isAbsolute(record)) {
        ctx.ui.notify("用法 /ai-workflow-register <任务ID> <协调记录绝对路径>", "error");
        return;
      }
      await run("register", ctx.sessionManager.getSessionId(), match[1], record);
      ctx.ui.notify("已登记当前会话的任务。", "info");
    },
  });

  pi.registerCommand("ai-workflow-unregister", {
    description: "撤销当前会话的统筹任务登记",
    handler: async (args, ctx) => {
      const task = args.trim();
      if (!/^\S+$/.test(task)) {
        ctx.ui.notify("用法 /ai-workflow-unregister <任务ID>", "error");
        return;
      }
      await run("unregister", ctx.sessionManager.getSessionId(), task);
      ctx.ui.notify("已撤销当前会话的任务登记。", "info");
    },
  });

  pi.on("session_compact", async (_event, ctx) => {
    // Pi 1.5 can report an older entry when two compactions produce the same summary.
    const compaction = activeCompaction(ctx);
    const sessionId = ctx.sessionManager.getSessionId();
    if (!compaction || compactionState(ctx, sessionId, compaction.id) !== undefined) return;

    const reminder = await readReminder(ctx, sessionId);
    if (!reminder || ctx.sessionManager.getSessionId() !== sessionId) return;
    if (activeCompaction(ctx)?.id !== compaction.id || compactionState(ctx, sessionId, compaction.id) !== undefined) return;

    pi.appendEntry<CompactionState>(compactionStateType, { sessionId, compactionId: compaction.id, handled: false });
  });

  pi.on("context", async (event, ctx) => {
    if (!event.messages.some((message) => message.role === "compactionSummary")) return;
    const compaction = activeCompaction(ctx);
    const sessionId = ctx.sessionManager.getSessionId();
    if (!compaction || compactionState(ctx, sessionId, compaction.id) !== false) return;

    const summary = event.messages.find((message) =>
      message.role === "compactionSummary" && message.timestamp === Date.parse(compaction.timestamp),
    );
    if (summary?.role !== "compactionSummary") return;

    // A resumed session reads the live registration so revoked records cannot leak from the marker.
    const reminder = await readReminder(ctx, sessionId);
    if (reminder === undefined || ctx.signal?.aborted || ctx.sessionManager.getSessionId() !== sessionId) return;
    if (activeCompaction(ctx)?.id !== compaction.id || compactionState(ctx, sessionId, compaction.id) !== false) return;

    pi.appendEntry<CompactionState>(compactionStateType, { sessionId, compactionId: compaction.id, handled: true });
    if (!reminder) return;

    // Enrich the existing summary for this model request without adding a message or changing history.
    return {
      messages: event.messages.map((message) => message === summary
        ? { ...summary, summary: `${summary.summary}\n\n${reminder}` }
        : message),
    };
  });
}
