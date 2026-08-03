"""
Rewrite all commits where author/committer email is deploy@mypy-tutor.com
to tega.com.ng@gmail.com using git-filter-repo.

Run from the repo root:
    python scripts/rewrite_author.py
"""
import subprocess, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# Build the mailmap content
mailmap = "Sir. Tega <tega.com.ng@gmail.com> MyPy Tutor <deploy@mypy-tutor.com>\n"
mailmap_path = os.path.join(ROOT, ".mailmap_rewrite")
with open(mailmap_path, "w") as f:
    f.write(mailmap)

print("Rewriting commit history — this may take a minute...")

result = subprocess.run(
    [
        sys.executable, "-m", "git_filter_repo",
        "--mailmap", mailmap_path,
        "--force",
    ],
    capture_output=False,
)

os.unlink(mailmap_path)

if result.returncode != 0:
    print("ERROR: git-filter-repo failed")
    sys.exit(1)

print("History rewritten successfully.")
print("Verifying new author emails:")
log = subprocess.run(
    ["git", "log", "--format=%ae", "--all"],
    capture_output=True, text=True
)
emails = set(log.stdout.strip().splitlines())
print("  Author emails in history:", emails)
if "deploy@mypy-tutor.com" in emails:
    print("WARNING: deploy@mypy-tutor.com still present in some commits")
    sys.exit(1)
else:
    print("OK — deploy@mypy-tutor.com fully removed from history")
