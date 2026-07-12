# Team workflow: humans + coding agents, divide and conquer

Four actors work this repo in parallel — Hari, Milind, and coding agents
(Claude Code, Antigravity). We hit three working-tree/branch collisions on
Jul 11 alone. These rules exist so that never happens again.

## The rules

1. **Nobody commits to `main` directly.** Every change — human or agent —
   goes branch → PR → review → merge. Docs typos included; small PRs are
   cheap, mystery commits are not.
2. **One task = one branch = one PR.** Branch naming:
   `task/<id>-<slug>` for tracked tasks (e.g. `task/03-fail-closed-pipeline`),
   `chore/…` or `fix/…` for untracked small things. Keep PRs reviewable in
   under ten minutes.
3. **Claim before you code.** The shared task list is the backlog. Set
   yourself as `owner` before starting (agents: `TaskUpdate owner`) so two
   actors never build the same thing twice — we built EWMA closure twice on
   Jul 11; once was enough.
4. **Agents never share a working tree.** Each coding agent works in its own
   git worktree (`git worktree add ../kaaval-<task> task/<id>-<slug>`) or its
   own clone. The main checkout at `kaaval-assurance/` belongs to whoever is
   running the dev servers. Uncommitted state in a shared tree is invisible
   to everyone else — if you must leave the tree dirty, push a `wip/…`
   snapshot branch instead (see PR #3).
5. **The PR body states what was verified**, not just what changed: test
   count, tsc/build status, and — for anything demo-visible — how it was
   exercised in the browser. Same evidence discipline as the product.
6. **Cross-review.** An agent's PR is reviewed by a human (or at minimum a
   different agent than the author). Merge is a human decision during
   hackathon week.
7. **Secrets never touch a branch.** `.env` stays gitignored; keys never
   appear in PR bodies, commit messages, or artifacts.

## Current open PRs

- **#2** `feat/agentic-chain-and-demo-upgrades` — support domain,
  double-failure path, Fireworks kimi fix, agent chain. Needs Hari review.
- **#3** `wip/tree-snapshot-grounding-polish` — snapshot of the shared
  tree's uncommitted state: grounding rules (recommend merge) + agent-module
  deletion (needs an explicit decision, do not merge silently).

## Suggested (needs team agreement, not enabled)

Branch protection on `main` (require one approving review). Enabling it
mid-hackathon changes Hari's current push-to-main flow — agree first, then
one of the admins flips it in repo settings.
