import { appendFileSync } from "node:fs";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const cost = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };

export default function (pi: ExtensionAPI) {
  let overflowed = false;
  pi.registerProvider("workflow-fixture", {
    api: "workflow-fixture",
    apiKey: "fixture",
    baseUrl: "https://fixture.invalid",
    models: [{
      id: "workflow-fixture",
      name: "Workflow fixture",
      reasoning: false,
      input: ["text"],
      cost,
      contextWindow: 16000,
      maxTokens: 1000,
    }],
    streamSimple(model, context) {
      const log = process.env.PI_WORKFLOW_TEST_REQUESTS;
      if (!log) throw new Error("Missing fixture request log path");
      appendFileSync(log, `${JSON.stringify(context.messages)}\n`);

      const last = context.messages.at(-1);
      const forceOverflow = last?.role === "user" && (
        last.content === "force fixture overflow" ||
        Array.isArray(last.content) && last.content.some((block) =>
          block.type === "text" && block.text === "force fixture overflow")
      );
      const overflow = forceOverflow && !overflowed;
      if (overflow) overflowed = true;

      const stream = createAssistantMessageEventStream();
      const message = {
        role: "assistant" as const,
        api: model.api,
        provider: model.provider,
        model: model.id,
        content: [{ type: "text" as const, text: "Fixture reply and repeated compaction summary." }],
        usage: { ...cost, totalTokens: 201, input: 200, output: 1, cost: { ...cost, total: 0 } },
        timestamp: Date.now(),
      };
      if (overflow) {
        stream.push({ type: "error", reason: "error", error: {
          ...message, content: [], stopReason: "error", errorMessage: "context length exceeded",
        } });
      } else {
        stream.push({ type: "done", reason: "stop", message: { ...message, stopReason: "stop" } });
      }
      return stream;
    },
  });
}
