---
name: github-publish
description: Review a Git worktree, prepare an accurate commit message and body from the actual diff, commit the intended changes, and push them to GitHub. Use when the user asks to submit, commit, push, or publish project changes to GitHub; do not use for pull request creation or release publishing unless separately requested.
---

# GitHub Publish

Turn the intended local changes into one reviewable Git commit and push it to the repository's configured GitHub remote.

## Establish scope

- Read repository instructions and inspect `git status --short`, the current branch, configured remotes, and relevant diffs before staging anything.
- Preserve unrelated user changes. Stage explicit paths that belong to the request. Use `git add --all` only when the user clearly wants every current change included and the complete diff has been reviewed.
- Never discard, overwrite, stash, or rewrite existing work merely to make the tree clean.
- If the directory is not a Git repository, or no GitHub remote exists, prepare the repository locally and ask for the missing repository URL or repository-creation choice only when it is actually needed.

## Protect credentials

Before committing, inspect staged file names and the staged diff for credentials or private material. Pay special attention to `.env`, private keys, tokens, credential files, generated diagnostics, and local data directories.

- Do not stage a secret. Add the local file to `.gitignore` when that matches the project, and commit a sanitized `.example` file when useful.
- Do not print or repeat suspected secret values in commentary, commit messages, or final responses.
- If a secret is already tracked or appears in history, stop before pushing and explain that removing the file from the new commit does not revoke or erase the exposed credential.

## Validate the staged result

- Run `git diff --check` and inspect `git diff --cached --stat`, `git diff --cached --name-status`, and the complete staged diff.
- Run the smallest meaningful tests, formatter, type check, or build supported by the affected project. Do not claim a check passed unless it ran successfully.
- Confirm the staged diff contains the requested result and no accidental files. If nothing is staged, do not create an empty commit unless the user explicitly requests one.

## Write the commit message

Follow an established repository convention when one exists. Otherwise use:

```text
<type>(<optional scope>): <concise outcome>

- <meaningful behavior or implementation change>
- <second material change, when needed>

Validation:
- <command and result>
```

Choose `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, or `build` from the actual diff. Keep the subject specific and under 72 characters. Describe the final behavior and motivation; do not narrate the work session, exaggerate scope, list routine file-by-file edits, or add attribution trailers unless the user asks.

Write the message to a temporary file and use `git commit --file <path>` so multiline text and shell characters are preserved safely.

## Commit and push

- A request to “提交并推送”, “上传到 GitHub”, or equivalent authorizes the ordinary commit and push for the stated scope. A request to review, draft, or prepare stops before the commit or push.
- Commit only after validation. Push the current branch to the configured GitHub remote; set its upstream when missing.
- Never force-push, delete a branch or tag, amend an existing commit, bypass hooks, or change remote history unless the user explicitly requests that exact operation and its implications have been checked.
- Do not create a pull request, tag, release, or repository unless requested.
- If authentication, branch protection, conflicts, or hook failures block the push, preserve the local commit and report the exact next action without weakening protections.

## Report

Return the commit subject, short commit hash, branch and remote, pushed status, and validation performed. Mention any intended files left uncommitted. Link the GitHub commit only when its URL can be derived reliably from the configured remote.
