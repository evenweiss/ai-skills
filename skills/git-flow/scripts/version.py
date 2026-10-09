#!/usr/bin/env python3
"""Calculate company Git Flow versions from live remote refs; never write Git state."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def version(text):
    return tuple(map(int, text.split("."))) if VERSION.fullmatch(text) else None


def render(parts):
    return ".".join(map(str, parts))


def calculate(args):
    if args.production not in ("main", "master"):
        raise ValueError("production must be main or master")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", args.remote):
        raise ValueError("invalid remote name")

    repo = Path(args.repo).resolve()
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ValueError("repo must be the repository root")

    refs = git(repo, "ls-remote", "--heads", "--tags", args.remote).splitlines()
    live = {}
    for line in refs:
        sha, ref = line.split("\t", 1)
        live[ref] = sha

    production_ref = f"refs/heads/{args.production}"
    production_sha = live.get(production_ref)
    if not production_sha:
        raise ValueError(f"remote {production_ref} is missing")
    tracking_ref = f"refs/remotes/{args.remote}/{args.production}"
    if git(repo, "rev-parse", "--verify", tracking_ref) != production_sha:
        raise ValueError("local remote-tracking production branch is stale; fetch and retry")

    merged_tags = set(git(repo, "tag", "--merged", tracking_ref).splitlines())
    local_tags = dict(
        line.split("\t", 1)
        for line in git(repo, "for-each-ref", "--format=%(refname)%09%(objectname)", "refs/tags").splitlines()
    )
    reachable = []
    for ref, sha in live.items():
        if not ref.startswith("refs/tags/") or ref.endswith("^{}"):
            continue
        name = ref.removeprefix("refs/tags/")
        parsed = version(name)
        if parsed is None:
            continue
        if local_tags.get(ref) != sha:
            raise ValueError(f"local tag {name} differs from remote; fetch and retry")
        if name in merged_tags:
            reachable.append((parsed, name))
    if not reachable:
        raise ValueError("no X.Y.Z tag reachable from remote production branch")

    tag_number, tag_name = max(reachable)
    result = {
        "status": "ok",
        "mode": args.mode,
        "production": args.production,
        "production_sha": production_sha,
        "base_tag": tag_name,
    }
    hotfixes = []
    for ref in live:
        if ref.startswith("refs/heads/hotfix/"):
            name = ref.removeprefix("refs/heads/hotfix/")
            parsed = version(name)
            if parsed is not None:
                hotfixes.append((parsed, name))

    if args.mode == "create-hotfix":
        highest_hotfix = max(hotfixes) if hotfixes else None
        result["highest_remote_hotfix"] = highest_hotfix[1] if highest_hotfix else None
        base = max(tag_number, highest_hotfix[0]) if highest_hotfix else tag_number
        candidate = render((base[0], base[1], base[2] + 1))
        result["candidate"] = f"hotfix/{candidate}"
        if highest_hotfix and highest_hotfix[0] > tag_number and highest_hotfix[0][:2] != tag_number[:2]:
            result["status"] = "needs_review"
            result["reason"] = "highest hotfix uses a newer version line than the production tag"
        if f"refs/heads/hotfix/{candidate}" in live:
            raise ValueError("candidate hotfix branch already exists on remote")
    elif args.mode == "finish-feature":
        result["candidate"] = render((tag_number[0], tag_number[1] + 1, 0))
    elif args.mode == "finish-hotfix":
        result["candidate"] = render((tag_number[0], tag_number[1], tag_number[2] + 1))
    else:
        if not args.branch or not args.branch.startswith("release/"):
            raise ValueError("release mode requires --branch release/X.Y.Z")
        target = args.branch.removeprefix("release/")
        parsed = version(target)
        if parsed is None or parsed <= tag_number:
            raise ValueError("release version must be X.Y.Z and higher than production tag")
        result["candidate"] = target

    if args.mode == "create-release":
        if f"refs/heads/{args.branch}" in live:
            raise ValueError("candidate release branch already exists on remote")

    if args.mode.startswith("finish-") or args.mode == "create-release":
        candidate = result["candidate"]
        if f"refs/tags/{candidate}" in live:
            raise ValueError(f"remote tag {candidate} already exists")
        other = [
            f"{kind}/{candidate}" for kind in ("hotfix", "release")
            if f"refs/heads/{kind}/{candidate}" in live and f"{kind}/{candidate}" != args.branch
        ]
        if other:
            result["status"] = "needs_review"
            result["reason"] = "candidate version has another remote branch: " + ", ".join(other)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("create-hotfix", "create-release", "finish-feature", "finish-hotfix", "finish-release"))
    parser.add_argument("--repo", default=".")
    parser.add_argument("--remote", required=True)
    parser.add_argument("--production", required=True)
    parser.add_argument("--branch", help="source branch; required for release modes")
    args = parser.parse_args()
    try:
        print(json.dumps(calculate(args), ensure_ascii=False, separators=(",", ":")))
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
