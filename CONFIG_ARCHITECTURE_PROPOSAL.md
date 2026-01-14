# 配置架构改进方案

## 原则

**库模块不直接读取环境变量，所有配置由客户端代码传递。**

## 问题

### 当前代码
```python
# ❌ 库直接读取环境变量（违反原则）
class LocalBackend:
    def exec(self, ...):
        if os.environ.get("NOXRUNNER_VERBOSE") == "1":
            print(...)
```

### 期望架构
```python
# ✅ 客户端读取配置并传递
class LocalBackend:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def exec(self, ...):
        if self.verbose:
            print(...)

# CLI 负责读取环境变量
verbose = os.environ.get("NOXRUNNER_VERBOSE") == "1"
backend = LocalBackend(verbose=verbose)
```

## 修改清单

### 1. LocalBackend 添加 verbose 参数

**文件**: `noxrunner/backend/local.py`

**修改**:
```python
def __init__(self, base_dir: str = "/tmp", verbose: bool = False):
    self.base_dir = Path(base_dir)
    self._sandboxes: Dict[str, Dict] = {}
    self.verbose = verbose  # 新增参数
    # ...

def exec(self, ...):
    # 修改前：
    # elif os.environ.get("NOXRUNNER_VERBOSE") == "1":

    # 修改后：
    elif self.verbose:
        print(...)
```

### 2. NoxRunnerClient 传递 verbose 参数

**文件**: `noxrunner/client.py`

**修改**:
```python
def __init__(
    self,
    base_url: Optional[str] = None,
    timeout: int = 30,
    local_test: bool = False,
    verbose: bool = False  # 新增参数
):
    if local_test:
        from noxrunner.backend.local import LocalBackend
        self._backend = LocalBackend(verbose=verbose)  # 传递
    else:
        from noxrunner.backend.http import HTTPSandboxBackend
        self._backend = HTTPSandboxBackend(base_url, timeout)
```

### 3. CLI 读取配置并传递

**文件**: `bin/noxrc.py`

**修改**:
```python
def get_verbose() -> bool:
    """获取 verbose 配置."""
    return os.environ.get("NOXRUNNER_VERBOSE") == "1"

def create_client(args) -> NoxRunnerClient:
    """创建客户端，传递所有配置."""
    base_url = args.base_url
    if base_url is None:
        base_url = get_base_url()

    # 读取 verbose 配置
    verbose = args.verbose or get_verbose()

    return NoxRunnerClient(
        base_url=base_url,
        timeout=args.timeout,
        local_test=args.local_test,
        verbose=verbose  # 传递给库
    )
```

### 4. SandboxBackend 基类添加 verbose

**文件**: `noxrunner/backend/base.py`

**修改**:
```python
class SandboxBackend(ABC):
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    @abstractmethod
    def exec(self, ...):
        pass
```

## 配置来源架构

```
配置来源（按优先级）:
1. 命令行参数 --verbose
2. 环境变量 NOXRUNNER_VERBOSE
3. 配置文件（未来扩展）
4. 默认值

所有配置读取都在 CLI 层完成，库只接收最终值。
```

## 测试影响

测试代码也需要更新：

```python
# 修改前
backend = LocalBackend()

# 修改后
backend = LocalBackend(verbose=False)  # 测试默认行为
backend = LocalBackend(verbose=True)   # 测试 verbose 行为
```

## 优势

1. **可测试性**: 测试时无需设置环境变量
2. **显式配置**: 所有配置在函数签名中可见
3. **灵活性**: 配置来源可以轻松扩展（文件、数据库等）
4. **解耦**: 库不依赖特定配置机制
5. **文档化**: 参数类型在签名中明确

## 未来扩展

如果需要更多配置项，按相同模式：

```python
# 库定义参数
class LocalBackend:
    def __init__(
        self,
        base_dir: str = "/tmp",
        verbose: bool = False,
        debug: bool = False,        # 新增
        timeout: int = 30,          # 新增
        max_retries: int = 3,       # 新增
    ):
        ...

# CLI 读取配置
def create_client(args):
    config = {
        'verbose': args.verbose or get_verbose(),
        'debug': args.debug or get_debug(),
        'timeout': args.timeout or get_timeout(),
        'max_retries': args.max_retries or get_max_retries(),
    }
    return NoxRunnerClient(**config)
```

## 配置文件支持（未来）

可以轻松添加配置文件支持：

```python
# CLI 层
import configparser
import json

def load_config():
    """从多个来源加载配置."""
    config = {
        'verbose': False,
        'base_url': 'http://127.0.0.1:8080',
        'timeout': 30,
    }

    # 1. 读取配置文件
    config_file = os.path.expanduser('~/.noxrunner/config.ini')
    if os.path.exists(config_file):
        parser = configparser.ConfigParser()
        parser.read(config_file)
        config.update(parser['default'])

    # 2. 读取环境变量
    if 'NOXRUNNER_VERBOSE' in os.environ:
        config['verbose'] = os.environ['NOXRUNNER_VERBOSE'] == '1'

    # 3. 命令行参数（在 argparse 中处理）

    return config
```

库层完全不需要改变！
