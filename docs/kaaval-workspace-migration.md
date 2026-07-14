# Kaaval workspace migration: `amdHackathon` to `kaaval-ai`

## Recommendation

Rename and reorganize the workspace, but **do not rename the active parent directory in place during the current Codex/Git session**.

The hackathon is now one historical milestone inside a broader product. The durable workspace name should match the GitHub organization and brand:

```text
/Users/milanjali/kaaval-ai/
```

Prefer `kaaval-ai` over `kavaalai`: it matches `github.com/kaaval-ai`, is easier to parse, and avoids a second spelling convention.

## Proposed layout

```text
kaaval-ai/
├── kaaval-assurance/        # runtime model-call assurance gateway
├── nanocanary/              # behavioral qualification and drift evidence
├── kaaval-cli/              # thin installation/control client; current kaaval repo
├── research-notes/          # canonical research, strategy, validation and IP notes
├── website/                 # kaaval.ai static/marketing site
├── incubating/
│   ├── substrate/           # governed memory research/product candidate
│   ├── shadowdeploy/        # deployment-gate candidate when code is present
│   └── router/              # future routing research; not the current wedge
└── archive/
    └── amd-act-ii-2026/     # final video, deck, cover and immutable submission record
```

Each existing Git repository remains an independent repository with its current remote. This is a filesystem/workspace migration, not a monorepo conversion.

## Why not rename in place now

- The current Codex workspace root is `/Users/milanjali/amdHackathon/kaaval-assurance`; moving its parent can invalidate the active task and tool permissions.
- The parent contains five independent Git repositories plus the website and submission assets.
- Submission/deck scripts contain absolute `/Users/milanjali/amdHackathon/...` paths.
- The final video checksum file contains an absolute old path.
- IDE workspaces, shell aliases, automation, secrets files, and external task state may contain additional absolute references outside the scanned repositories.
- The current Kaaval Assurance worktree contains an existing tracked deletion and untracked submission-generation files; migration should preserve them byte-for-byte.

## Known in-workspace absolute references

At the time of this plan, the scan found these path-bound files:

- `kaaval-assurance/scripts/update_adapt_slide.mjs`
- `kaaval-assurance/scripts/update_market_slide.mjs`
- `kaaval-assurance/scripts/inspect_market_slide.mjs`
- `kaaval-assurance/scripts/run_submission_deck.mjs`
- `submission/Kaaval-Assurance-Track-3-Final.mp4.sha256`

Replace script constants with paths derived from the repository root as part of the migration. Regenerate the checksum manifest with a relative filename rather than editing only its path text.

## Safe migration sequence

1. Freeze writes across all Kaaval repositories.
2. Record `git status --short --branch`, `HEAD`, remotes, and ignored/untracked file inventories for every repository.
3. Back up secret-bearing `.env` files separately; never commit them as part of the move.
4. Create `/Users/milanjali/kaaval-ai` and copy repositories and assets while preserving `.git` directories and file metadata.
5. Compare source and destination file inventories and checksums for non-generated assets.
6. Update absolute path references and regenerate path-bearing checksum manifests.
7. Run the full test/build suite in each destination repository.
8. Verify every repository still points to its original remote and that local branches/dirty state match the pre-move inventory.
9. Open the new parent as a fresh Codex/IDE workspace and update automations, shell aliases, and local documentation.
10. Keep `/Users/milanjali/amdHackathon` read-only for a short verification window, then archive or remove it only after explicit approval.

## Migration acceptance gates

- All repositories have identical `HEAD`, branches, remotes, and intentional dirty state before and after migration.
- Kaaval Assurance tests and Flight Deck build pass from the new location.
- NanoCanary tests and `doctor` pass from the new location.
- The public submission assets retain their verified hashes.
- No maintained source file references `/Users/milanjali/amdHackathon`.
- `kaaval.ai`, GitHub repositories, container images, and deployment systems are unaffected; local filesystem paths are not part of their public identity.

## Decision

**Yes, graduate the workspace from `amdHackathon` to `kaaval-ai`; do it as a verified copy-and-cutover migration after the active submission workspace is frozen, not as an in-place rename.**

