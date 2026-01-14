# NoxRunner 改进计划

本文档详细列出了代码审查中发现的问题及其修复方案，按优先级排序。

---

## 🔴 优先级 1：关键 Bug（必须修复）

### 1.1 CommandValidator.validate() 白名单无效问题

**文件**：`noxrunner/security/command_validator.py:95-116`

**问题描述**：
- `ALLOWED_COMMANDS` 白名单定义了68个允许的命令，但 `validate()` 方法永远返回 `True`
- 只有黑名单检查生效，白名单完全被忽略
- 这使得安全控制形同虚设

**当前代码**：
```python
def validate(self, cmd: List[str]) -> bool:
    if not cmd:
        return False
    command = cmd[0].lower()
    if command in self.BLOCKED_COMMANDS:
        return False
    # For testing, allow common commands
    # In production, this should be more restrictive
    return True  # ⚠️ 永远返回 True，白名单无效
```

**修复方案 A（严格模式 - 推荐）**：
```python
def validate(self, cmd: List[str]) -> bool:
    """
    Validate that command is safe to execute.

    Uses strict allowlist mode - only commands in ALLOWED_COMMANDS are permitted.
    """
    if not cmd:
        return False

    command = cmd[0].lower()

    # Block dangerous commands first
    if command in self.BLOCKED_COMMANDS:
        return False

    # Only allow commands in the allowlist
    return command in self.ALLOWED_COMMANDS
```

**修复方案 B（宽松模式 - 向后兼容）**：
```python
def __init__(self, strict_mode: bool = False):
    """
    Initialize validator.

    Args:
        strict_mode: If True, only allow commands in ALLOWED_COMMANDS.
                    If False, block only BLOCKED_COMMANDS (default).
    """
    self.strict_mode = strict_mode

def validate(self, cmd: List[str]) -> bool:
    if not cmd:
        return False

    command = cmd[0].lower()

    # Always block dangerous commands
    if command in self.BLOCKED_COMMANDS:
        return False

    # In strict mode, only allow whitelisted commands
    if self.strict_mode:
        return command in self.ALLOWED_COMMANDS

    # Permissive mode: allow anything not blocked
    return True
```

**推荐**：方案 A（严格模式），因为：
1. 安全性优先
2. 如果需要更多命令，可以添加到白名单
3. LocalBackend 本身就是用于测试，不需要过于宽松

**测试计划**：
```python
# tests/test_security.py
def test_validate_allowed_commands():
    validator = CommandValidator()
    assert validator.validate(["echo", "test"]) is True
    assert validator.validate(["python3", "--version"]) is True

def test_validate_blocked_commands():
    validator = CommandValidator()
    assert validator.validate(["rm", "-rf", "/"]) is False
    assert validator.validate(["sudo", "ls"]) is False

def test_validate_unknown_command():
    validator = CommandValidator()
    assert validator.validate(["unknown_command"]) is False
```

---

### 1.2 PathSanitizer 路径遍历检测不完整

**文件**：`noxrunner/security/path_sanitizer.py:56-59`

**问题描述**：
- 简单的 `..` 字符串检查可以被绕过（如 `....//`, `..././`）
- 没有处理 URL 编码的路径遍历（如 `%2e%2e`）
- 没有处理符号链接

**当前代码**：
```python
if ".." in path or path.startswith("/"):
    return workspace
```

**修复方案**：
```python
def sanitize(self, path: str, sandbox_path: Path, workspace_name: str = "workspace") -> Path:
    """
    Sanitize a path to ensure it's within the sandbox.

    Security: Prevents path traversal attacks using proper path resolution.
    """
    sandbox_resolved = sandbox_path.resolve()
    workspace = sandbox_resolved / workspace_name

    # Resolve relative paths
    if os.path.isabs(path):
        # If absolute, ensure it's within sandbox
        try:
            resolved = Path(path).resolve()
            # Check if resolved path is within sandbox using resolve()
            try:
                resolved.relative_to(sandbox_resolved)
                return resolved
            except ValueError:
                return workspace
        except (OSError, ValueError):
            return workspace
    else:
        # Relative path - resolve it first to normalize any .. or .
        try:
            # Resolve the full path to normalize traversals
            resolved = (workspace / path).resolve()

            # Now check if the normalized path is still within sandbox
            try:
                resolved.relative_to(sandbox_resolved)
                return resolved
            except ValueError:
                # Path traversal detected (normalized path escaped sandbox)
                return workspace
        except (OSError, ValueError):
            return workspace
```

**关键改进**：
1. 使用 `Path.resolve()` 规范化路径，自动处理 `..`, `.`, 多余斜杠等
2. 在规范化后重新检查路径是否在沙盒内
3. 移除简单的字符串匹配

**测试计划**：
```python
# tests/test_security.py
def test_path_sanitizer_traversal_attempts():
    sandbox = Path("/tmp/test_sandbox")
    sanitizer = PathSanitizer()

    # 各种路径遍历尝试
    traversal_attempts = [
        "../../../etc/passwd",
        "....//....//etc/passwd",
    "..././../etc/passwd",
        "./../../etc/passwd",
        "/etc/passwd",  # 绝对路径
    ]

    for attempt in traversal_attempts:
        result = sanitizer.sanitize(attempt, sandbox)
        # 所有结果都应该是 workspace，不允许逃逸
        assert result == sandbox / "workspace", f"Failed to block: {attempt}"

def test_path_sanitizer_valid_paths():
    sandbox = Path("/tmp/test_sandbox")
    sanitizer = PathSanitizer()

    # 有效路径应该被允许
    valid_paths = [
        "file.txt",
        "subdir/file.txt",
        "subdir/deeply/nested/file.txt",
    ]

    for path in valid_paths:
        result = sanitizer.sanitize(path, sandbox)
        assert (sandbox / "workspace" / path).resolve() == result.resolve()
```

---

### 1.3 HTTPBackend 死代码问题

**文件**：`noxrunner/backend/http.py:168-176`, `noxrunner/backend/http.py:202-210`

**问题描述**：
- `touch()` 和 `upload_files()` 方法中有 `if e.status_code == 200` 检查
- `NoxRunnerHTTPError` 只在 HTTP 错误时抛出，状态码不可能是 200
- 这是死代码，永远不会执行

**当前代码**：
```python
def touch(self, session_id: str) -> bool:
    try:
        status_code, _ = self._request("POST", f"/v1/sandboxes/{session_id}/touch")
        return status_code == 200
    except NoxRunnerHTTPError as e:
        if e.status_code == 200:  # ⚠️ 永远不会执行
            return True
        raise
```

**修复方案**：
```python
def touch(self, session_id: str) -> bool:
    """Extend the TTL of a sandbox."""
    status_code, _ = self._request("POST", f"/v1/sandboxes/{session_id}/touch")
    return status_code == 200

def upload_files(self, session_id: str, files: Dict[str, Union[str, bytes]], dest: str = "/workspace") -> bool:
    """Upload files to the sandbox."""
    tar_data = self.tar_handler.create_tar(files)
    path = f"/v1/sandboxes/{session_id}/files/upload?{urllib.parse.urlencode({'dest': dest})}"
    status_code, _ = self._request(
        "POST", path, data=tar_data, content_type="application/x-tar"
    )
    return status_code == 200
```

**说明**：
- 移除不必要的 try-except 块
- 让 `_request()` 方法统一处理错误
- 如果需要特殊处理 2xx 范围内的其他状态码，可以添加相应逻辑

---

## 🟠 优先级 2：重要改进（强烈建议）

### 2.1 改进 download_workspace() 异常处理

**文件**：`noxrunner/client.py:316-317`

**问题描述**：
- 捕获所有异常并返回 `False`，掩盖了真正的错误
- 用户无法知道失败的原因（权限？磁盘满？网络错误？）

**当前代码**：
```python
except Exception:
    return False
```

**修复方案**：
```python
def download_workspace(
    self, session_id: str, local_dir: Union[str, Path], src: str = "/workspace"
) -> bool:
    """Download workspace from sandbox to local directory."""
    local_path = Path(local_dir)

    try:
        # Download tar archive from backend
        tar_data = self.download_files(session_id, src)

        if not tar_data or len(tar_data) == 0:
            return False

        # Use TarHandler to extract tar archive
        file_count = self._tar_handler.extract_tar(
            tar_data=tar_data,
            dest=local_path,
            sandbox_path=None,
            allow_absolute=False,
        )
        return file_count > 0
    except NoxRunnerHTTPError as e:
        # Re-raise HTTP errors with context
        raise NoxRunnerError(
            f"Failed to download workspace for session {session_id}: {e}"
        ) from e
    except (OSError, IOError) as e:
        # File system errors (permission, disk full, etc.)
        raise NoxRunnerError(
            f"Failed to extract workspace to {local_path}: {e}"
        ) from e
    except tarfile.TarError as e:
        # Tar archive errors
        raise NoxRunnerError(
            f"Failed to extract tar archive: {e}"
        ) from e
```

**说明**：
- 区分不同类型的错误
- 保留异常链（`from e`）
- 提供有用的错误信息

---

### 2.2 修复 CLI --base-url 默认值处理

**文件**：`bin/noxrc.py:439-443`, `bin/noxrc.py:62-68`

**问题描述**：
- `get_base_url()` 在 argparse 解析之前就执行
- 即使用户指定 `--base-url`，也会先读取环境变量
- 无法通过参数覆盖环境变量

**当前代码**：
```python
def get_base_url() -> Optional[str]:
    url = os.environ.get("NOXRUNNER_BASE_URL", "http://127.0.0.1:8080")
    if url == "":
        return None
    return url

parser.add_argument(
    "--base-url",
    default=get_base_url(),  # ⚠️ 在解析时就调用了
    ...
)
```

**修复方案**：
```python
def get_base_url() -> Optional[str]:
    """Get base URL from environment or default."""
    url = os.environ.get("NOXRUNNER_BASE_URL", "http://127.0.0.1:8080")
    # Return None if explicitly set to empty string (for local test)
    if url == "":
        return None
    return url

def create_client(args) -> NoxRunnerClient:
    """Create NoxRunnerClient from args."""
    # Determine base_url: command line arg takes precedence
    base_url = args.base_url
    if base_url is None:
        base_url = get_base_url()

    return NoxRunnerClient(
        base_url=base_url,
        timeout=args.timeout,
        local_test=args.local_test
    )

# 在 argparse 中使用 None 作为默认值
parser.add_argument(
    "--base-url",
    default=None,  # 改为 None
    help=f"Base URL of the NoxRunner (default: from NOXRUNNER_BASE_URL env or http://127.0.0.1:8080). Ignored if --local-test is set.",
)
```

---

### 2.3 为 TarHandler 添加 Python <3.12 的安全过滤

**文件**：`noxrunner/fileops/tar_handler.py:139-145`

**问题描述**：
- Python < 3.12 时直接调用 `tar.extract()` 没有过滤器
- 存在路径遍历和符号链接攻击风险

**当前代码**：
```python
if sys.version_info >= (3, 12):
    tar.extract(member, dest, filter="data")
else:
    tar.extract(member, dest)  # ⚠️ 不安全
```

**修复方案**：
```python
def _is_safe_member(self, member, dest: Path) -> bool:
    """Check if a tar member is safe to extract."""
    # Check for absolute paths
    if member.name.startswith("/"):
        return False

    # Check for path traversal
    if ".." in member.name.split("/"):
        return False

    # Check if the extracted path would be outside destination
    target_path = dest / member.name
    try:
        target_path.resolve().relative_to(dest.resolve())
    except ValueError:
        return False

    # For symlinks, check the link target
    if member.issym():
        if ".." in member.linkname.split("/"):
            return False
        # Don't allow absolute symlinks
        if member.linkname.startswith("/"):
            return False

    return True

def extract_tar(
    self,
    tar_data: bytes,
    dest: Path,
    sandbox_path: Optional[Path] = None,
    allow_absolute: bool = False,
) -> int:
    """Extract a tar archive to a directory."""
    if not tar_data or len(tar_data) == 0:
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    file_count = 0

    tar_buffer = io.BytesIO(tar_data)
    with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
        for member in tar.getmembers():
            # Skip directories (they will be created automatically)
            if member.isdir():
                continue

            # Security check for all Python versions
            if not allow_absolute and not self._is_safe_member(member, dest):
                continue

            # Additional sandbox check if provided
            if sandbox_path:
                target_path = dest / member.name
                try:
                    target_path.resolve().relative_to(sandbox_path.resolve())
                except ValueError:
                    continue
            else:
                # Ensure target is within dest
                target_path = dest / member.name
                try:
                    target_path.resolve().relative_to(dest.resolve())
                except ValueError:
                    continue

            # Create parent directories
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Extract with appropriate filter
            if sys.version_info >= (3, 12):
                tar.extract(member, dest, filter="data")
            else:
                # Manual security checks already done above
                tar.extract(member, dest)
            file_count += 1

    return file_count
```

---

## 🟡 优先级 3：增强功能（建议添加）

### 3.1 为 LocalBackend 添加 TTL 自动清理

**文件**：`noxrunner/backend/local.py`

**问题描述**：
- 沙盒有过期时间，但从未自动清理
- 可能导致磁盘空间泄漏

**修复方案**：
```python
def __init__(self, base_dir: str = "/tmp"):
    self.base_dir = Path(base_dir)
    self._sandboxes: Dict[str, Dict] = {}
    self.validator = CommandValidator()
    self.sanitizer = PathSanitizer()
    self.tar_handler = TarHandler()
    self._print_warning(...)

    # Auto-cleanup expired sandboxes on initialization
    self._cleanup_expired()

def _cleanup_expired(self):
    """Remove expired sandbox directories."""
    now = datetime.now(timezone.utc)
    expired_sessions = []

    for session_id, info in self._sandboxes.items():
        if info["expires_at"] < now:
            expired_sessions.append(session_id)

    for session_id in expired_sessions:
        try:
            self.delete_sandbox(session_id)
        except Exception:
            pass  # Best effort cleanup

    # Also scan for orphaned sandbox directories
    if self.base_dir.exists():
        for sandbox_dir in self.base_dir.glob("noxrunner_sandbox_*"):
            # Check if it's tracked
            session_id = sandbox_dir.name.replace("noxrunner_sandbox_", "")
            if session_id not in self._sandboxes:
                # Orphaned directory, remove it
                try:
                    shutil.rmtree(sandbox_dir)
                except Exception:
                    pass

def touch(self, session_id: str) -> bool:
    """Extend the TTL of a sandbox."""
    if session_id not in self._sandboxes:
        self.create_sandbox(session_id)
        return True

    sandbox = self._sandboxes[session_id]
    ttl = sandbox.get("ttl_seconds", 900)
    sandbox["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    # Trigger cleanup
    self._cleanup_expired()

    return True
```

---

### 3.2 优化 LocalBackend 警告输出

**文件**：`noxrunner/backend/local.py`

**问题描述**：
- 每次 `exec()` 都打印警告
- 用户可能因警告过多而忽略真正的问题

**修复方案**：
```python
def __init__(self, base_dir: str = "/tmp"):
    # ... 现有代码 ...
    self._warning_shown = False  # 添加标志
    self._print_warning(...)

def _print_warning_once(self, message: str, critical: Optional[str] = None):
    """Print warning only once per session."""
    if self._warning_shown:
        return

    self._warning_shown = True
    self._print_warning(message, critical)

def exec(self, ...):
    """Execute a command in the sandbox."""
    # 只打印一次警告
    self._print_warning_once(
        f"Local sandbox mode active. Executing: {' '.join(cmd)}",
    )

    # ... 其余代码 ...
```

或者使用环境变量控制：
```python
def exec(self, ...):
    if os.environ.get("NOXRUNNER_QUIET") != "1":
        self._print_warning(...)
```

---

### 3.3 改进 wait_for_pod_ready() 健康检查

**文件**：`noxrunner/backend/http.py:232-247`

**问题描述**：
- 硬编码使用 `echo ready` 命令
- 如果沙盒没有 `echo` 命令会误判

**修复方案**：
```python
def wait_for_pod_ready(self, session_id: str, timeout: int = 30, interval: int = 2) -> bool:
    """Wait for sandbox to be ready."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # Try multiple health check strategies
            strategies = [
                # Strategy 1: Check if we can run any command
                (["sh", "-c", "exit 0"], lambda r: r.get("exitCode") == 0),
                # Strategy 2: Check workspace directory exists
                (["sh", "-c", "test -d /workspace"], lambda r: r.get("exitCode") == 0),
                # Strategy 3: Simple echo (fallback)
                (["echo", "ready"], lambda r: "ready" in r.get("stdout", "")),
            ]

            for cmd, check in strategies:
                try:
                    result = self.exec(session_id, cmd, timeout_seconds=5)
                    if check(result):
                        return True
                except NoxRunnerHTTPError:
                    continue
                except Exception:
                    continue

        except NoxRunnerHTTPError:
            # Sandbox might not be ready yet
            pass
        except Exception:
            pass

        time.sleep(interval)

    return False
```

---

## 🧪 测试增强

### 添加安全测试套件

**新文件**：`tests/test_security_hardening.py`

```python
"""Security hardening tests."""

import pytest
from noxrunner.security.command_validator import CommandValidator
from noxrunner.security.path_sanitizer import PathSanitizer
from pathlib import Path

class TestCommandValidator:
    """Test command validation security."""

    def test_blocked_commands(self):
        """Test that dangerous commands are blocked."""
        validator = CommandValidator()
        blocked = ["rm", "sudo", "chmod", "killall"]
        for cmd in blocked:
            assert validator.validate([cmd, "test"]) is False

    def test_allowlist_enforcement(self):
        """Test that only allowed commands pass (in strict mode)."""
        validator = CommandValidator()
        # After fix: should enforce allowlist
        assert validator.validate(["python3", "--version"]) is True
        assert validator.validate(["unknown_cmd"]) is False

class TestPathSanitizer:
    """Test path sanitization security."""

    def test_path_traversal_variants(self):
        """Test various path traversal attempts."""
        sandbox = Path("/tmp/sandbox")
        sanitizer = PathSanitizer()

        traversals = [
            "../../../etc/passwd",
            "....//....//etc/passwd",
            "..././../etc/passwd",
            "./../../etc/passwd",
            "%2e%2e/%2e%2e/etc/passwd",  # URL encoded (if applicable)
        ]

        for attempt in traversals:
            result = sanitizer.sanitize(attempt, sandbox)
            assert "etc/passwd" not in str(result), f"Failed to block: {attempt}"

    def test_symlink_protection(self):
        """Test that symlinks don't escape sandbox."""
        # This would require more complex test setup
        pass
```

---

## 📊 实施优先级总结

| 优先级 | 问题 | 工作量 | 风险 |
|--------|------|--------|------|
| 🔴 P0 | CommandValidator 白名单 | 低 | 低 |
| 🔴 P0 | PathSanitizer 路径遍历 | 低 | 低 |
| 🔴 P0 | HTTPBackend 死代码 | 低 | 低 |
| 🟠 P1 | download_workspace 异常 | 低 | 低 |
| 🟠 P1 | CLI --base-url 处理 | 低 | 低 |
| 🟠 P1 | TarHandler 安全过滤 | 中 | 低 |
| 🟡 P2 | TTL 自动清理 | 中 | 中 |
| 🟡 P2 | LocalBackend 警告优化 | 低 | 低 |
| 🟡 P2 | wait_for_pod_ready 改进 | 中 | 低 |
| 🟢 P3 | 安全测试套件 | 中 | 低 |

**预计总工作量**：2-3 天

**建议实施顺序**：
1. 先修复所有 P0 问题（1-2 小时）
2. 修复 P1 问题（2-3 小时）
3. 添加测试（1-2 小时）
4. 实施 P2 增强功能（4-6 小时）
