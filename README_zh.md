[English](README.md) | 中文

# Prompt Refiner

Claude Code 的提示词优化中间件。拦截用户提示词，读取会话上下文，在 Claude 处理之前生成更清晰、更结构化的版本。

**两种运行模式：**
- **CLI 模式** (`prf refine`)：交互式 TUI，支持 接受/编辑/原始/跳过 审阅
- **Hook 模式**（Claude Code `UserPromptSubmit`）：自动优化，通过 `decision: "block"` 阻止原始提示词，让用户选择

支持 **47 个内置 Provider**，涵盖 5 大类别：官方、国内、网关、编程专用和自定义。

## 核心工作流

```
用户输入
    |
    v
[跳过检查]         -- /no-refine、短输入、斜杠命令、问候语
    |
    v
[读取对话记录]     -- Claude Code 会话历史（.jsonl），含思考/工具调用/结果
    |
    v
[压缩上下文]       -- 启发式提取结构化字段
    |                  （任务 / 技术栈 / 已尝试 / 阻塞 / 已修改 / 约束）
    v
[优化提示词]       -- LLM 结合上下文重写输入
    |
    v
[审阅 / 注入]      -- CLI: TUI 审阅（接受/编辑/原始/跳过）
                      Hook: 阻止提示词，展示对比，用户选择后放行
```

## 快速开始

### 方式 A：Claude Code 插件（推荐）

```bash
# 第 1 步：注册 Marketplace（仅需一次）
/plugin marketplace add https://github.com/Hav1d/Claude-Code-prompt-refiner

# 第 2 步：从该 Marketplace 安装插件
/plugin install prompt-refiner
```

Claude Code 会提示你填写：
1. **Provider** — 如 `deepseek`、`openrouter`、`claude`（默认：`deepseek`）
2. **API Key** — 你的 Provider API Key（安全存储在系统密钥链中）
3. **Base URL** — 可选的自定义端点

安装后首次会话时，`SessionStart` Hook 自动引导 Python 依赖。之后 `UserPromptSubmit` Hook 会在每次提交提示词时运行，无需手动配置。

### 方式 B：CLI（独立使用）

```bash
# 安装
cd prompt-refiner
pip install -e ".[dev]"

# 首次配置（选择 Provider，输入 API Key）
prf config set

# 交互式优化提示词
prf refine

# 直接传入提示词
prf refine "修复登录 bug"

# 管道输入
echo "修复用户创建接口" | prf refine

# 连续模式
prf batch

# 查看配置
prf config show
```

> **注意**：CLI 命令是 `prf`，不是 `pr`。`pr` 与 GNU `pr` 工具冲突。

## 命令

| 命令 | 说明 |
|------|------|
| `prf refine [PROMPT]` | 优化提示词（交互式或带参数） |
| `prf batch` | 连续优化循环 |
| `prf config show` | 显示当前配置（密钥脱敏） |
| `prf config set` | 通过交互向导设置或更新 Provider |
| `prf config clear` | 移除已保存的 Provider 配置 |
| `prf providers list` | 列出全部 47 个内置 Provider |
| `prf providers show ID` | 显示 Provider 详情 |
| `prf providers search Q` | 按名称/ID/备注搜索 Provider |
| `prf clear-cache` | 清除摘要缓存 |
| `prf hook EVENT` | Claude Code Hook 入口（旧版，推荐用 `hook_entry.py`） |

### Refine 选项

| 参数 | 说明 |
|------|------|
| `--config, -c` | 配置文件路径 |
| `--no-submit, -n` | 优化后不提交给 Claude Code |
| `--dry-run, -d` | 仅展示，不执行 |
| `--output, -o` | 将最终提示词写入文件 |
| `--skip, -s` | 跳过优化 |
| `--auto, -a` | 自动接受优化结果（无 TUI） |
| `--debug` | 启用调试日志 |

## 认证

### 首次配置

```bash
prf config set
```

启动交互向导：
1. 按类别展示全部 47 个 Provider
2. 选择 Provider
3. 输入 API Key（掩码输入）
4. 可选自定义 Base URL 和模型
5. 保存到 `~/.prompt-refiner/config.json`，权限 0600

### 凭据解析链

启动时按以下顺序解析凭据（首次匹配生效）：

1. **插件 userConfig**：`CLAUDE_PLUGIN_OPTION_API_KEY` 环境变量（由 Claude Code 从密钥链设置）
2. **已保存配置**：`~/.prompt-refiner/config.json` → 活跃 Provider 的 `api_key`
3. **已保存配置**：`~/.prompt-refiner/config.json` → 活跃 Provider 的 `auth_token`
4. **环境变量**：`ANTHROPIC_API_KEY`
5. **环境变量**：`ANTHROPIC_AUTH_TOKEN`（Bearer token）
6. **回退**：`~/.claude/config.json` → `primaryApiKey`（自动检测）

### 优雅降级

如果没有 API Key：
- **CLI 模式**：跳过 LLM 优化，仅应用前缀/后缀
- **Hook 模式**：直接放行，不做修改（空 stdout）
- **不会崩溃，不会报错** — 工具始终可用，只是没有优化功能

### 管理凭据

```bash
prf config set     # 设置或更新 Provider + API Key
prf config show    # 显示配置（密钥脱敏：********abcd）
prf config clear   # 移除已保存的 Provider 配置
```

## 配置

**插件模式**：凭据来自 `userConfig`（安装时设置，存储在密钥链中）。`SessionStart` Hook 从这些值生成运行时配置，无需手动配置文件。

**CLI 模式**：配置按优先级从低到高加载：

1. **内置默认值**（`src/config.py`）
2. **用户配置**：`~/.prompt-refiner/config.json`（通过 `prf config set`）
3. **项目配置**：`./prompt-config.json`（从 `prompt-config.example.json` 复制）
4. **显式路径**：`--config` 参数
5. **环境变量**：`REFINE_MODEL`、`ANTHROPIC_API_KEY` 等

`prompt-config.example.json` 仅作为 CLI 和手动 Hook 模式的配置模板。

### 多 Provider 配置格式

```json
{
  "active_provider": "deepseek",
  "providers": {
    "deepseek": {
      "api_key": "sk-...",
      "base_url": "https://api.deepseek.com/v1",
      "models": {
        "refine": "deepseek-chat",
        "summary": "deepseek-chat"
      }
    },
    "openrouter": {
      "api_key": "sk-or-...",
      "base_url": "https://openrouter.ai/api/v1",
      "models": {
        "refine": "anthropic/claude-3.5-haiku",
        "summary": "anthropic/claude-3.5-haiku"
      }
    }
  },
  "prefix": "优先使用可用的 skills、MCP 工具和插件。",
  "suffix": "完成修改后，将关键更新记录到 memory。",
  "auto_refine": false,
  "history_lines": 50,
  "debug_mode": false
}
```

### 关键设置

| 设置项 | 默认值 | 说明 |
|--------|--------|------|
| `active_provider` | `""` | 当前活跃的 Provider ID |
| `providers` | `{}` | Provider 配置（密钥、URL、模型） |
| `auto_refine` | `false` | 跳过 TUI 审阅，自动接受优化结果 |
| `auto_refine_min_length` | `20` | 触发自动优化的最小字符数 |
| `history_lines` | `50` | 读取的对话记录条目数 |
| `max_summary_tokens` | `300` | 上下文摘要 LLM 调用的最大 token 数 |
| `max_refined_tokens` | `800` | 优化 LLM 调用的最大 token 数 |
| `prefix` | `""` | 每个最终提示词前添加的文本 |
| `suffix` | `""` | 每个最终提示词后追加的文本 |
| `cache_ttl` | `300` | 摘要缓存有效期（秒） |
| `skip_commands` | `["/no-refine", "/nr", "/skip"]` | 跳过优化的命令 |
| `ignore_patterns` | `["^\\s*$", "^/[a-z]+"]` | 跳过优化的正则模式 |
| `debug_mode` | `false` | 启用调试日志 |

### 环境变量

| 变量 | 映射到 | 说明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | `api_key` | LLM 调用的 API Key |
| `ANTHROPIC_AUTH_TOKEN` | `auth_token` | 网关/代理的 Bearer token |
| `ANTHROPIC_BASE_URL` | `api_base_url` | 自定义 API 端点 |
| `REFINE_MODEL` | `refine_model` | 覆盖优化模型 |
| `SUMMARY_MODEL` | `summary_model` | 覆盖摘要模型 |
| `PROMPT_REFINE_PROVIDER` | `active_provider` | 覆盖活跃 Provider |
| `PROMPT_REFINE_DEBUG` | `debug_mode` | 启用调试模式（`1`/`true`/`yes`） |

## Claude Code 集成（Hooks）

### 插件模式（推荐）

```bash
# 注册 Marketplace（仅需一次）
/plugin marketplace add https://github.com/Hav1d/Claude-Code-prompt-refiner

# 安装插件
/plugin install prompt-refiner
```

插件会自动：
- 注册 `SessionStart` Hook 引导 Python 依赖（每次会话运行，依赖已是最新时快速退出）
- 注册 `UserPromptSubmit` Hook 进行提示词优化
- 从 `userConfig` 读取凭据（安全存储在系统密钥链中）

无需手动配置 Hook。

### 手动 Hook 配置（高级）

如果需要手动控制，将以下内容添加到项目的 `.claude/settings.json`：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python -X utf8 -m src.hook_entry UserPromptSubmit --config prompt-config.json",
            "timeout": 30000
          }
        ]
      }
    ]
  }
}
```

`-X utf8` 参数在 Windows 上是必需的，用于正确处理中文/Unicode。

### Hook 工作原理

**两步阻止流程（Windows 兼容）：**

1. 用户提交提示词 → Hook 读取会话记录 → LLM 优化
2. 如果优化结果与原文不同 → 保存到临时文件 → 返回 `decision: "block"` 阻止提示词
3. Claude Code 展示原文 vs 优化版的对比，用户选择：
   - `a` = 接受优化版
   - `e` = 编辑优化版
   - `o` = 使用原文
4. 用户重新提交选择 → Hook 返回对应的 `additionalContext`
5. Claude 处理最终提示词（不会把选择字母当成提示词）

### Hook vs CLI 模式

| 方面 | CLI 模式 | Hook 模式 |
|------|----------|-----------|
| TUI 审阅 | 有（接受/编辑/原始/跳过） | **阻止式审阅**（对比展示 + 选择） |
| 输出 | 提交给 Claude Code 或管道 | `additionalContext` + `decision: "block"` |
| 用户看到 | Rich 终端 diff + 选择 | Claude 展示两个版本，用户输入 a/e/o |
| 凭据缺失 | 运行向导（交互式） | 静默放行 |
| stdin 读取 | `typer.prompt()` | 逐字符读取 + `raw_decode`（避免 EOF 阻塞） |

## 支持的 Provider（47 个）

### 官方

| Provider | ID | 默认模型 |
|----------|-----|----------|
| Claude Official | `claude` | claude-haiku-4-5-20251001 |
| GitHub Copilot | `github-copilot` | gpt-4o-mini |
| Codex | `codex` | gpt-4o-mini |
| AWS Bedrock (AKSK) | `bedrock-aksk` | anthropic.claude-3-5-haiku |
| AWS Bedrock (API Key) | `bedrock-apikey` | anthropic.claude-3-5-haiku |

### 国内

| Provider | ID | 默认模型 |
|----------|-----|----------|
| ModelScope | `modelscope` | Qwen/Qwen3-235B-A22B |
| SiliconFlow | `siliconflow` | Qwen/Qwen3-235B-A22B |
| DMXAPI | `dmxapi` | claude-haiku-4-5-20251001 |
| 优云智算 | `youyun` | qwen2.5-72b-instruct |
| 胜算云 | `shengsuan` | claude-haiku-4-5-20251001 |
| Zhipu GLM | `zhipu` | glm-4-flash |
| 百炼 | `bailian` | qwen-plus |
| 百炼编程版 | `bailian-coding` | qwen-code-latest |
| Kimi | `kimi` | moonshot-v1-8k |
| Kimi 编程版 | `kimi-coding` | kimi-latest |
| StepFun | `stepfun` | step-1-flash |
| KAT-Coder | `katcoder` | kat-coder-pro |
| Longcat | `longcat` | longcat-coder |
| MiniMax | `minimax` | MiniMax-Text-01 |
| 豆包 | `doubao` | doubao-1.5-pro |
| 百灵 | `bailing` | bailing-coder |
| 小米 MiMo | `mimo` | mimo-v2.5-pro |

### 网关

| Provider | ID | 默认模型 |
|----------|-----|----------|
| AiHubMix | `aihubmix` | claude-haiku-4-5-20251001 |
| OpenRouter | `openrouter` | anthropic/claude-3.5-haiku |
| TheRouter | `therouter` | claude-3-5-haiku-latest |
| Novita AI | `novita` | meta-llama/llama-3.1-8b-instruct |
| DeepSeek | `deepseek` | deepseek-chat |
| + 3 个 | | |

### 编程专用

| Provider | ID | 默认模型 |
|----------|-----|----------|
| PackyCode | `packycode` | claude-haiku-4-5-20251001 |
| Cubence | `cubence` | claude-haiku-4-5-20251001 |
| + 11 个 | | |

### 自定义

| Provider | ID | 说明 |
|----------|-----|------|
| 自定义配置 | `custom` | 任何 OpenAI 兼容 API，手动配置 |

使用 `prf providers list` 查看全部 47 个 Provider，或 `prf providers search <关键词>` 过滤。

## 项目结构

```
prompt-refiner/
├── .claude-plugin/
│   ├── plugin.json           # 插件清单（userConfig、元数据）
│   └── marketplace.json      # 市场列表（自引用）
├── hooks/
│   └── hooks.json            # 插件 Hooks（SessionStart + UserPromptSubmit）
├── scripts/
│   ├── ensure-deps.sh        # SessionStart：venv + 依赖引导（Unix）
│   ├── ensure-deps.cmd       # SessionStart：venv + 依赖引导（Windows）
│   ├── run-hook.sh           # UserPromptSubmit：env → config → hook（Unix）
│   └── run-hook.cmd          # UserPromptSubmit：env → config → hook（Windows）
├── skills/
│   └── refine/SKILL.md       # Claude 技能定义
├── bin/
│   └── prf                   # CLI 包装脚本（使用插件 venv 或系统 prf）
├── src/
│   ├── __init__.py
│   ├── app.py                # CLI 入口（Typer），所有命令
│   ├── config.py             # Pydantic 配置，分层加载，旧版迁移
│   ├── credentials.py        # 凭据解析链
│   ├── models.py             # 数据模型：UserChoice, RefineResult, SessionContext
│   ├── refiner.py            # 核心优化：启发式 + LLM，should_refine 检查
│   ├── llm.py                # LLM 调用，使用 Provider 适配层
│   ├── summarizer.py         # 上下文压缩（启发式提取）
│   ├── transcript_reader.py  # Claude Code .jsonl 对话记录解析
│   ├── ui.py                 # Rich TUI：diff 展示，接受/编辑/原始/跳过
│   ├── executor.py           # 提交到 claude CLI，写入文件
│   ├── cache.py              # 文件级摘要缓存
│   ├── logger.py             # 结构化 JSONL 日志
│   ├── hook_integration.py   # Hook 逻辑：handle_hook，两步阻止流程
│   ├── hook_entry.py         # Hook __main__：stdin 读取，参数解析
│   ├── hook_terminal.py      # CONIN$/CONOUT$ 终端绕过（Windows）
│   ├── setup_wizard.py       # Provider 选择 + API Key 向导
│   └── providers/
│       ├── __init__.py       # 公开 API 重导出
│       ├── models.py         # ProviderConfig, ApiStyle, AuthScheme
│       ├── builtin.py        # 47 个内置 Provider 定义
│       ├── registry.py       # Provider 注册表（单例）
│       └── adapters.py       # 统一适配器：OPENAI/ANTHROPIC/BEDROCK/CUSTOM
├── tests/                    # 测试套件
├── examples/                 # Hook payload 示例
├── docs/                     # 扩展文档
├── .claude/
│   ├── settings.json         # Claude Code Hook 配置（本地开发）
│   └── settings.local.json.example
├── requirements.txt          # Python 依赖（插件引导使用）
├── prompt-config.json        # 项目级配置模板
├── prompt-config.example.json # 分发用配置模板
├── pyproject.toml            # 构建配置，入口点
├── install.sh                # 安装脚本
└── README.md
```

## 扩展：添加新 Provider

### 通过配置（推荐）

```json
{
  "active_provider": "custom",
  "providers": {
    "custom": {
      "api_key": "your-key",
      "base_url": "https://your-provider.com/v1",
      "models": {
        "refine": "your-model",
        "summary": "your-model"
      }
    }
  }
}
```

### 通过代码

```python
from src.providers import get_registry, ProviderConfig, ApiStyle, AuthScheme, ModelDefaults

registry = get_registry()
registry.register(ProviderConfig(
    id="my-provider",
    display_name="My Provider",
    category="custom",
    api_style=ApiStyle.OPENAI,
    base_url="https://my-provider.com/v1",
    auth_scheme=AuthScheme.BEARER,
    default_models=ModelDefaults(refine="my-model"),
))
```

### API 样式

| 样式 | 使用者 | 端点格式 |
|------|--------|----------|
| `OPENAI` | 大多数 Provider | `{base}/chat/completions` |
| `ANTHROPIC` | Claude Official | `{base}/v1/messages` |
| `BEDROCK` | AWS Bedrock | `{base}/model/{model}/invoke` |
| `CUSTOM` | 自定义 Provider | 可配置 |

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行全部测试
pytest

# 带覆盖率运行
pytest --cov=src --cov-report=term-missing

# 运行特定测试文件
pytest tests/test_refiner.py -v
```

## 已知限制

1. **Hook 模式使用两步阻止流程**：由于 Claude Code 子进程无法在 Windows 上访问 CONIN$ 进行交互式终端输入，Hook 使用 `decision: "block"` 阻止提示词，展示对比后让用户选择。

2. **stdin EOF 处理**：Claude Code 在管道传输 JSON 后可能不会关闭 stdin。`hook_entry.py` 使用逐字符读取 + `json.JSONDecoder.raw_decode()` 来检测完整 JSON，避免 EOF 阻塞。

3. **Windows 编码**：Hook 命令中需要 `-X utf8` Python 参数，以在 Windows 上正确处理中文/Unicode。

4. **模型质量影响效果**：弱模型可能会回答问题而不是重写提示词。优化器包含对话式响应拒绝作为安全网，但优质模型效果更好。

## 许可证

MIT
