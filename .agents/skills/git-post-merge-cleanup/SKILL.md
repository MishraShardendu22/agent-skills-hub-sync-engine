---
name: git-post-merge-cleanup
scope: generic
description: >-
  Rules, safety constraints, and automated procedures for post-merge local Git cleanup,
  synchronizing main with GitHub, deleting stale local branches, and performing deep
  repository garbage collection (git gc, reflog expire, prune) strictly upon explicit human user request.
---

# Git Post-Merge Repository & Branch Cleanup Skill

This skill defines the official protocol and step-by-step procedures for cleaning up local development branches, pulling the latest `main` from GitHub after a Pull Request is merged, and executing deep Git repository garbage collection and maintenance.

---

## 1. Strict Permission & Trigger Boundary

> [!IMPORTANT]
> **EXPLICIT HUMAN INSTRUCTION ONLY**:
> AI agents MUST NEVER run local branch deletions, branch resets, or aggressive garbage collection automatically.
> This workflow is triggered **ONLY** when the human user explicitly instructs the agent to perform cleanup (e.g. *"clean up local branches"*, *"sync main and do git gc"*, *"I merged the PR, please clean up"*).
>
> The typical workflow is:
> 1. AI agent finishes work on a feature branch, passes pre-commit checks, commits locally, pushes branch, and opens a PR targeting `main`.
> 2. The human user reviews and merges the Pull Request on GitHub.
> 3. The human user prompts the AI agent to perform local cleanup.
> 4. The AI agent executes the safe post-merge cleanup runbook below.

---

## 2. Core Cleanup Principles

1. **Safety-First Working Tree Verification**: Never switch branches or run destructive cleanups if there are uncommitted changes or uncommitted work in progress.
2. **Main as the Source of Truth**: Always switch to `main` and pull from `origin/main` first so that the newly merged PR code and history are fully present locally before deleting the feature branch.
3. **Preserve `main` (and Protected Branches)**: Only delete feature/task branches. Never delete `main`.
4. **Remote Reference Pruning**: Prune stale remote tracking branches (`git fetch --prune origin`) to keep the remote tracking tree clean.
5. **Deep Garbage Collection**: Prune unreachable reflog entries (`git reflog expire --expire=now --all`) and optimize the local object store (`git gc --prune=now --aggressive`) to keep the `.git` directory small, fast, and healthy.
6. **Zero Stale Branches**: After cleanup, only `main` remains as the active local branch.

---

## 3. Step-by-Step Cleanup Runbook

When the human user requests post-merge cleanup, execute these exact steps in sequence:

### Step 1: Verify Working Directory State
Ensure there are no unstaged modifications or stash conflicts:
```bash
git status
```
If dirty, stop and check if there are uncommitted files that need to be preserved.

### Step 2: Switch to `main` and Pull Latest Upstream
Switch to the primary release branch and pull the merged changes from GitHub:
```bash
git switch main
git pull origin main
```

### Step 3: Prune Remote Tracking Branches
Synchronize and remove remote branch references that were deleted on GitHub after PR merge:
```bash
git fetch --prune origin
```

### Step 4: Identify & Delete Local Feature Branches
List all local branches to inspect what needs to be removed:
```bash
git branch
```
Delete all local feature branches (e.g. `<github-username>/main/<feature>`):
```bash
# Safe delete merged branches:
git branch -d <branch-name>

# If GitHub used Squash & Merge or Rebase & Merge (which changes commit hashes):
git branch -D <branch-name>
```

Or delete all local branches except `main` in one command:
```bash
git branch | grep -v "^\* main$" | grep -v "^  main$" | xargs -r git branch -D
```

### Step 4b: Prune & Remove Ephemeral Worktrees
If the merged feature branch was checked out in a dedicated worktree:
```bash
# 1. Identify worktree path
git worktree list

# 2. Safely remove the worktree directory (assert clean status first)
git worktree remove .worktrees/wt-<branch-slug>

# 3. Prune internal git worktree metadata
git worktree prune
```

### Step 5: Expire Reflogs & Run Aggressive Garbage Collection
Clean up dangling commits, unreachable objects, and optimize packfiles:
```bash
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### Step 6: Verify Final Repository State
Verify that only `main` remains and the working tree is clean:
```bash
git branch
git status
```

---

## 4. Automated Remote Branch Cleanup on PR Close (GitHub Actions)

> [!IMPORTANT]
> **MANDATORY IN EVERY REPOSITORY**: Every project repository MUST have `.github/workflows/pr-branch-cleanup.yml` deployed. This workflow is the automated counterpart to the manual local cleanup runbook above. Without it, merged feature branches accumulate on GitHub and pollute the remote branch list.

Remote feature branch deletion is automated via a GitHub Actions workflow that triggers when a PR is closed and acts only when it was merged. A branch whose PR was closed without merging keeps its work, and deleting it would close the open PRs stacked on it (GitHub retargets those only after a merge). The canonical workflow is:

```yaml
# .github/workflows/pr-branch-cleanup.yml
name: "PR Merged Remote Branch Cleanup"

on:
  pull_request:
    types: [closed]

permissions:
  contents: read

jobs:
  cleanup-merged-branch:
    name: "Delete Merged Remote Branch"
    if: >
      github.event.pull_request.merged == true &&
      github.event.pull_request.head.repo.full_name == github.repository &&
      github.event.pull_request.head.ref != 'main' &&
      github.event.pull_request.head.ref != 'master'
    runs-on: ubuntu-24.04
    permissions:
      contents: write
      pull-requests: read
    steps:
      - name: "Delete Remote Feature Branch"
        uses: actions/github-script@<full-commit-sha> # vX.Y.Z (current major, pinned by SHA)
        with:
          script: |
            const pr = context.payload.pull_request;
            const { owner, repo } = context.repo;
            const headRef = pr.head.ref;
            const keep = (why) => core.info(`Keeping branch ${headRef}: ${why}.`);

            // The job's if says the same; the script must hold on its own.
            if (pr.merged !== true) return keep('the pull request was closed without merging');
            if (pr.head.repo?.full_name !== `${owner}/${repo}`) return keep('it is not in this repository');
            const defaultBranch = context.payload.repository?.default_branch;
            if (headRef === defaultBranch || ['main', 'master'].includes(headRef) || /^Frozen-/i.test(headRef)) {
              return keep('it is a long-lived branch');
            }

            let branch;
            try {
              ({ data: branch } = await github.rest.repos.getBranch({ owner, repo, branch: headRef }));
            } catch (error) {
              if (error.status === 404) return core.info(`Branch ${headRef} is already gone.`);
              throw error;
            }
            if (branch.protected) return keep('it is protected');
            let rules = [];
            try {
              rules = await github.paginate(github.rest.repos.getBranchRules, { owner, repo, branch: headRef, per_page: 100 });
            } catch (error) {
              // Rulesets need GitHub Pro in a private repository, so none applies.
              // Any other refusal leaves the rules unknown and the branch kept.
              if (error.status !== 403 || !/upgrade to github pro/i.test(error.message)) throw error;
            }
            if (rules.some((rule) => rule.type === 'deletion')) return keep('a ruleset restricts its deletion');
            if (branch.commit.sha !== pr.head.sha) return keep(`it moved to ${branch.commit.sha} after the merge of ${pr.head.sha}`);
            const open = await github.paginate(github.rest.pulls.list, { owner, repo, state: 'open', head: `${owner}:${headRef}`, per_page: 100 });
            if (open.length > 0) return keep(`open pull request #${open[0].number} comes from it`);

            try {
              await github.rest.git.deleteRef({ owner, repo, ref: `heads/${headRef}` });
              core.info(`Deleted branch ${headRef}.`);
            } catch (error) {
              if (error.status === 422 || error.status === 404) {
                core.info(`Branch ${headRef} was already deleted.`);
              } else {
                core.setFailed(`Failed to delete branch ${headRef}: ${error.message}`);
              }
            }
```

**Safety guarantees baked into the workflow:**
- Deletes only the head branch of a **merged** PR; a PR closed without merging keeps its branch.
- Only runs on branches from the same repo (not forks).
- Never deletes the default branch, `main`, `master` or a `Frozen-*` branch (add the repository's own long-lived patterns to that check).
- Keeps a branch that branch protection or a ruleset keeps from deletion, a branch that gained commits after the merge, and a branch another open PR comes from.
- Silently skips if the branch was already deleted.
- GitHub's own "Automatically delete head branches" setting (on in this repository) deletes a merged PR's head branch whatever the workflow keeps, unless protection or a ruleset stops it; a private repository without GitHub Pro has neither, so never merge a PR whose head is a long-lived branch such as `Frozen-*`.
- In this repository `tests/pr_branch_cleanup_test.mjs` runs the script against each of these cases.

**Relationship to local cleanup (Sections 2–3 above):**
- This workflow handles the **remote** branch only.
- The human user still triggers the local cleanup runbook (Sections 1–3) after merging.
- Together they ensure zero stale branches both locally and on GitHub.
