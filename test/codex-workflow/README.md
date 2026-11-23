# Codex workflow integration test

Run `/usr/bin/python3 -B test/codex-workflow/run.py` from the repository. It requires the macOS ChatGPT desktop app and permission to bind local loopback and Unix sockets. Pass a marketplace directory as the first argument to test a distributable copy such as the Helper bundle.

The harness installs the plugin in a disposable profile and derives trust for this fixture only from the host's hook hashes. It uses the bundled app-server and desktop MCP bridge with scripted model responses and a mock desktop receiver. No real desktop service, account, or scheduler is connected.

The scenarios cover write permissions after actual compaction, dispatch rejection before delivery, protected coordinator handoff, a manual independent checkpoint when both chats were silent, and ordinary chat behavior. The handoff fixture provisions a read-only candidate before delivery and checks the installed Hook before and after the candidate reads the cutover record. The report classification helper is a test fixture. The independent monitor is not deployed and does not send notifications.

The last case enables code mode in the bundled app-server. A protected coordinator calls the mock desktop through JavaScript. The receiver must get the valid packet exactly once. A packet missing its reporting instructions must return the dispatch Hook's denial and reach the receiver zero times.

## Skill behavior exercises

Use an isolated coordinator, an executor and synthetic task data for these exercises. Give the agents the skill and scenario inputs, then inspect their replies and the recorded actions.

- **Stop work.** Tell the coordinator to revoke authorization while work is in progress. Run once with the approved dispatch route active, then with it withdrawn and a separately authorized stop-notification route available. Check the route actually used, delivery receipt, and the executor's stop evidence separately. If no approved route is available, the status should say that stopping remains unconfirmed.
- **Blocker cleared.** Use the original three reporting events (`completed`, `stopped`, `blocked`). First the executor is waiting for a test package, then the package becomes available. Check that the executor reports the material change once and names the work that can continue. Repeating an unchanged waiting state should produce no duplicate report.
