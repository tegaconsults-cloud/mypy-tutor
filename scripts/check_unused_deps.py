"""Check which installed packages are actually used by app code."""
import ast, os

app_files = []
for root, dirs, files in os.walk("app"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py"):
            app_files.append(os.path.join(root, f))

imports = set()
for fp in app_files:
    try:
        with open(fp, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
    except Exception:
        pass

candidates = [
    "reportlab", "openai", "PIL", "pillow", "hypothesis", "pytest",
    "git_filter_repo", "google", "pyasn1", "rsa", "cachetools", "tqdm",
    "reportlab", "multidict", "yarl", "propcache", "jiter",
]

print("Package usage in app/ directory:")
for pkg in sorted(set(candidates)):
    used = pkg in imports or pkg.lower().replace("-", "_") in imports
    status = "USED  " if used else "UNUSED"
    print(f"  {status}  {pkg}")

print()
print("All top-level imports found in app/:")
print(" ", sorted(imports))
