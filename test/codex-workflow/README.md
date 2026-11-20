# Codex workflow integration test

Run `/usr/bin/python3 -B test/codex-workflow/run.py` from the repository. It requires the macOS ChatGPT desktop app and permission to bind local loopback and Unix sockets. Pass a marketplace directory as the first argument to test a distributable copy such as the Helper bundle.

The harness installs the plugin in a disposable profile and derives trust for this fixture only from the host's hook hashes. It uses the bundled app-server and desktop MCP bridge with scripted model responses and a mock desktop receiver. No real desktop service, account, or scheduler is connected.

The scenarios cover write permissions after actual compaction, dispatch rejection before delivery, protected coordinator handoff, a manual independent checkpoint when both chats were silent, and ordinary chat behavior. The handoff fixture provisions a read-only candidate before delivery and checks the installed Hook before and after the candidate reads the cutover record. The report classification helper is a test fixture. The independent monitor is not deployed and does not send notifications.
