"""
github_tools.py — Fast GitHub repository analysis tool for LangChain/LangGraph agents.
----------------------------------------------------------------------------------------
Fetches the whole repo in a single request via codeload.github.com (tarball), then
analyzes everything in memory. No cloning, no per-file API calls, no paid APIs.

Python: 3.12+
"""

from __future__ import annotations

import io
import json
import os
import re
import tarfile
import tomllib
from collections import Counter
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple

import pathspec
import requests
from pydantic import BaseModel, Field, model_validator
from langchain_core.tools import StructuredTool

# --------------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------------- #

GITHUB_API = "https://api.github.com"
CODELOAD = "https://codeload.github.com"
TIMEOUT = 20
MAX_FILE_BYTES = 1_500_000

IGNORE_SPEC = pathspec.PathSpec.from_lines(
    "gitwildmatch", [".git/", "__pycache__/", "node_modules/", "venv/", "dist/", "build/", ".idea/", ".vscode/"]
)

LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".java": "Java", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cs": "C#", ".rs": "Rust", ".swift": "Swift",
    ".kt": "Kotlin", ".html": "HTML", ".css": "CSS", ".vue": "Vue", ".json": "JSON",
    ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".md": "Markdown", ".sql": "SQL", ".sh": "Shell",
}

FRAMEWORK_SIGNATURES = {
    "FastAPI": ["fastapi"], "Flask": ["flask"], "Django": ["django"],
    "React": ['"react"', "'react'"], "Express": ['"express"', "'express'"],
    "Spring": ["springframework", "spring-boot"], "Laravel": ["laravel/framework"],
    "Vue": ['"vue"', "'vue'"], "Angular": ["@angular/core"],
}

SECRET_PATTERNS = {
    "AWS Access Key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Generic API Key": re.compile(r"(?i)(api[_-]?key)\s*[=:]\s*[\"']([A-Za-z0-9_\-]{16,})[\"']"),
    "Hardcoded Password": re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*[\"']([^\"']{4,})[\"']"),
    "Private Key Block": re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"),
    "eval() usage": re.compile(r"\beval\("),
    "exec() usage": re.compile(r"\bexec\("),
    "subprocess shell=True": re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"),
}

FASTAPI_ROUTE = re.compile(r"@(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']")
FLASK_ROUTE = re.compile(r"@(?:app|blueprint|bp)\.route\(\s*[\"']([^\"']+)[\"'](?:[^)]*methods\s*=\s*\[([^\]]*)\])?")
GITHUB_URL_RE = re.compile(r"^https://github\.com/(?P<owner>[\w.\-]+)/(?P<repo>[\w.\-]+?)(?:\.git)?/?$")

DEP_FILES = {"requirements.txt", "pyproject.toml", "package.json", "composer.json", "pom.xml", "build.gradle"}


# --------------------------------------------------------------------------------- #
# Input schema
# --------------------------------------------------------------------------------- #

class GithubToolInput(BaseModel):
    operation: Literal[
        "analyze_repo", "repository_summary", "architecture", "explain_file",
        "search_code", "dependencies", "api_routes", "statistics",
        "security_scan", "installation",
    ] = Field(..., description="Which analysis operation to run.")
    repository_url: str = Field(..., description="e.g. 'https://github.com/owner/repo'")
    branch: Optional[str] = Field(None, description="Defaults to the repo's default branch.")
    file_path: Optional[str] = Field(None, description="Required for 'explain_file'.")
    query: Annotated[Optional[str], Field(description="Required for 'search_code'.")] = None

    @model_validator(mode="after")
    def _validate(self) -> "GithubToolInput":
        if not GITHUB_URL_RE.match(self.repository_url.strip()):
            raise ValueError(f"'{self.repository_url}' is not a valid GitHub URL (expected https://github.com/<owner>/<repo>).")
        self.repository_url = self.repository_url.strip()
        if self.operation == "explain_file" and not self.file_path:
            raise ValueError("'file_path' is required for 'explain_file'.")
        if self.operation == "search_code" and not self.query:
            raise ValueError("'query' is required for 'search_code'.")
        return self


# --------------------------------------------------------------------------------- #
# Fetch: one metadata call + one tarball download, everything else is in-memory
# --------------------------------------------------------------------------------- #

class RepoData:
    """In-memory snapshot of a repo: metadata + {path: text_content}."""
    def __init__(self, meta: dict, files: Dict[str, str]):
        self.meta = meta
        self.files = files  # text files only, binaries skipped
        self.paths = list(files.keys())


def _session() -> requests.Session:
    s = requests.Session()
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "github-analysis-tool"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    s.headers.update(headers)
    return s


def _load_repo(session: requests.Session, owner: str, repo: str, branch: Optional[str]) -> RepoData:
    meta_resp = session.get(f"{GITHUB_API}/repos/{owner}/{repo}", timeout=TIMEOUT)
    if meta_resp.status_code == 404:
        raise RuntimeError(f"Repository '{owner}/{repo}' not found.")
    if not meta_resp.ok:
        raise RuntimeError(f"GitHub API error {meta_resp.status_code}: {meta_resp.text[:200]}")
    meta = meta_resp.json()
    resolved_branch = branch or meta["default_branch"]

    tar_resp = session.get(f"{CODELOAD}/{owner}/{repo}/tar.gz/{resolved_branch}", timeout=TIMEOUT)
    if not tar_resp.ok:
        raise RuntimeError(f"Could not download branch '{resolved_branch}' for '{owner}/{repo}' ({tar_resp.status_code}).")

    files: Dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(tar_resp.content), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.size > MAX_FILE_BYTES:
                continue
            # tarball root is "<repo>-<branch>/..." — strip it
            rel_path = member.name.split("/", 1)[1] if "/" in member.name else member.name
            if not rel_path or IGNORE_SPEC.match_file(rel_path):
                continue
            raw = tar.extractfile(member).read()
            if b"\x00" in raw[:1024]:
                continue  # binary
            files[rel_path] = raw.decode("utf-8", errors="replace")

    meta["_resolved_branch"] = resolved_branch
    return RepoData(meta, files)


# --------------------------------------------------------------------------------- #
# Analysis (pure functions over RepoData, no I/O)
# --------------------------------------------------------------------------------- #

def _dependencies(repo: RepoData) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if "requirements.txt" in repo.files:
        out["requirements_txt"] = [l.strip() for l in repo.files["requirements.txt"].splitlines() if l.strip() and not l.startswith("#")]
    if "pyproject.toml" in repo.files:
        try:
            data = tomllib.loads(repo.files["pyproject.toml"])
        except tomllib.TOMLDecodeError:
            data = {}
        out["pyproject_toml"] = {
            "project_dependencies": data.get("project", {}).get("dependencies", []),
            "poetry_dependencies": list(data.get("tool", {}).get("poetry", {}).get("dependencies", {}).keys()),
        }
    if "package.json" in repo.files:
        try:
            data = json.loads(repo.files["package.json"])
        except json.JSONDecodeError:
            data = {}
        out["package_json"] = {"dependencies": list(data.get("dependencies", {}).keys()),
                                "devDependencies": list(data.get("devDependencies", {}).keys())}
    for f, key in [("composer.json", "composer_json"), ("pom.xml", "pom_xml"), ("build.gradle", "build_gradle")]:
        if f in repo.files:
            out[key] = {"present": True}
    return out


def _frameworks(repo: RepoData) -> List[str]:
    combined = "\n".join(repo.files[f].lower() for f in DEP_FILES if f in repo.files)
    detected = [fw for fw, sigs in FRAMEWORK_SIGNATURES.items() if any(s.lower() in combined for s in sigs)]
    if "manage.py" in repo.files and "Django" not in detected:
        detected.append("Django")
    return sorted(set(detected))


def _api_routes(repo: RepoData) -> List[Dict[str, str]]:
    routes = []
    for path, content in repo.files.items():
        if not path.endswith(".py"):
            continue
        for method, route in FASTAPI_ROUTE.findall(content):
            routes.append({"framework": "FastAPI", "method": method.upper(), "path": route, "file": path})
        for route, methods in FLASK_ROUTE.findall(content):
            routes.append({"framework": "Flask", "method": methods.replace("'", "").replace('"', "").strip() or "GET", "path": route, "file": path})
    return routes


def _statistics(repo: RepoData) -> Dict[str, Any]:
    folders = {"/".join(p.split("/")[:-1]) for p in repo.paths if "/" in p}
    lang_files, lang_loc, total_loc = Counter(), Counter(), 0
    largest = None
    for path, content in repo.files.items():
        ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        lang = LANGUAGES.get(ext, "Other")
        loc = content.count("\n") + 1
        lang_files[lang] += 1
        lang_loc[lang] += loc
        total_loc += loc
        size = len(content.encode("utf-8"))
        if largest is None or size > largest["size_bytes"]:
            largest = {"file": path, "size_bytes": size}
    breakdown = [{"language": l, "files": lang_files[l], "loc": lang_loc[l]}
                 for l in sorted(lang_files, key=lambda l: lang_loc[l], reverse=True)]
    return {"total_files": len(repo.paths), "total_folders": len(folders),
            "total_lines_of_code": total_loc, "largest_file": largest, "language_breakdown": breakdown}


def _security_scan(repo: RepoData) -> List[Dict[str, Any]]:
    findings = []
    for path, content in repo.files.items():
        for i, line in enumerate(content.splitlines(), 1):
            for issue, pattern in SECRET_PATTERNS.items():
                if pattern.search(line):
                    findings.append({"issue": issue, "file": path, "line": i,
                                      "snippet": pattern.sub("***REDACTED***", line).strip()[:200]})
    return findings


def _search_code(repo: RepoData, query: str) -> List[Dict[str, Any]]:
    needle, results = query.lower(), []
    for path, content in repo.files.items():
        for i, line in enumerate(content.splitlines(), 1):
            if needle in line.lower():
                results.append({"file": path, "line": i, "snippet": line.strip()[:200]})
                if len(results) >= 50:
                    return results
    return results


def _tree(repo: RepoData) -> Dict[str, Any]:
    root: Dict[str, Any] = {}
    for path in repo.paths:
        node = root
        parts = path.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = None

    def to_list(node: dict, name: str) -> Dict[str, Any]:
        children = [{"type": "file", "name": k} if v is None else to_list(v, k) for k, v in node.items()]
        return {"type": "directory", "name": name, "children": children}

    return to_list(root, "/")


def _installation(repo: RepoData, deps: Dict[str, Any], frameworks: List[str]) -> Dict[str, Any]:
    steps, managers = [], []
    if "requirements_txt" in deps:
        steps.append("pip install -r requirements.txt"); managers.append("pip")
    if "pyproject_toml" in deps:
        if deps["pyproject_toml"].get("poetry_dependencies"):
            steps.append("poetry install"); managers.append("poetry")
        else:
            steps.append("pip install ."); managers.append("pip")
    if "package_json" in deps:
        if "yarn.lock" in repo.files:
            steps.append("yarn install"); managers.append("yarn")
        else:
            steps.append("npm install"); managers.append("npm")
    if "composer_json" in deps:
        steps.append("composer install"); managers.append("composer")
    if "pom_xml" in deps:
        steps.append("mvn install"); managers.append("maven")
    if "build_gradle" in deps:
        steps.append("./gradlew build"); managers.append("gradle")
    if not steps:
        steps.append("No recognized dependency manifest found.")
    return {"detected_package_managers": sorted(set(managers)), "detected_frameworks": frameworks, "steps": steps}


# --------------------------------------------------------------------------------- #
# Operation dispatch — all operate on the same pre-fetched RepoData
# --------------------------------------------------------------------------------- #

def _dispatch(op: str, repo: RepoData, file_path: Optional[str], query: Optional[str]) -> Dict[str, Any]:
    m = repo.meta

    if op == "repository_summary":
        deps = _dependencies(repo)
        return {"full_name": m.get("full_name"), "description": m.get("description"),
                "stars": m.get("stargazers_count"), "forks": m.get("forks_count"),
                "primary_language": m.get("language"), "license": (m.get("license") or {}).get("name"),
                "branch": m["_resolved_branch"], "frameworks": _frameworks(repo),
                "dependency_manifests": list(deps.keys()), "total_files": len(repo.paths)}

    if op == "architecture":
        entry_points = [f for f in ("main.py", "app.py", "manage.py", "index.js", "server.js", "index.ts") if f in repo.files]
        return {"branch": m["_resolved_branch"], "frameworks": _frameworks(repo),
                "entry_points": entry_points, "directory_tree": _tree(repo)}

    if op == "explain_file":
        if file_path not in repo.files:
            raise RuntimeError(f"File '{file_path}' was not found, is binary, or exceeds the size limit.")
        content = repo.files[file_path]
        ext = "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        return {"file": file_path, "language": LANGUAGES.get(ext, "Other"),
                "lines_of_code": content.count("\n") + 1, "content": content}

    if op == "search_code":
        results = _search_code(repo, query)
        return {"query": query, "match_count": len(results), "matches": results}

    if op == "dependencies":
        return _dependencies(repo)

    if op == "api_routes":
        routes = _api_routes(repo)
        return {"route_count": len(routes), "routes": routes}

    if op == "statistics":
        return _statistics(repo)

    if op == "security_scan":
        findings = _security_scan(repo)
        return {"issue_count": len(findings), "findings": findings}

    if op == "installation":
        deps = _dependencies(repo)
        return _installation(repo, deps, _frameworks(repo))

    if op == "analyze_repo":
        deps = _dependencies(repo)
        frameworks = _frameworks(repo)
        return {"full_name": m.get("full_name"), "description": m.get("description"),
                "stars": m.get("stargazers_count"), "branch": m["_resolved_branch"],
                "frameworks": frameworks, "dependencies": deps, "statistics": _statistics(repo),
                "api_routes": _api_routes(repo), "security_findings": _security_scan(repo),
                "installation": _installation(repo, deps, frameworks), "directory_tree": _tree(repo)}

    raise RuntimeError(f"Unsupported operation '{op}'.")


def _run_github_tool(
    operation: str, repository_url: str, branch: Optional[str] = None,
    file_path: Optional[str] = None, query: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch a public GitHub repo once (tarball) and run the requested analysis in memory."""
    try:
        match = GITHUB_URL_RE.match(repository_url)
        owner, repo_name = match.group("owner"), match.group("repo")
        session = _session()
        repo = _load_repo(session, owner, repo_name, branch)
        data = _dispatch(operation, repo, file_path, query)
        return {"success": True, "operation": operation, "data": data}
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}
    except requests.RequestException as exc:
        return {"success": False, "error": f"Network error contacting GitHub: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"Unexpected error during '{operation}': {exc}"}


# --------------------------------------------------------------------------------- #
# StructuredTool
# --------------------------------------------------------------------------------- #

github_tool = StructuredTool.from_function(
    func=_run_github_tool,
    name="github_tool",
    description=(
        "Analyzes a public GitHub repository in a single fast pass (tarball download, no cloning). "
        "operation: 'analyze_repo' (full report), 'repository_summary', 'architecture' (tree + frameworks), "
        "'explain_file' (needs file_path), 'search_code' (needs query), 'dependencies', 'api_routes' "
        "(FastAPI/Flask), 'statistics' (LOC, languages), 'security_scan' (secrets, eval/exec, shell=True), "
        "'installation'. Returns a structured dict with a 'success' flag."
    ),
    args_schema=GithubToolInput,
    return_direct=False,
    handle_tool_error=True,
)