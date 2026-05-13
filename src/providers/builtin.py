"""Built-in provider definitions.

All 44 providers from the specification.
"""

from __future__ import annotations

from .models import AuthScheme, ApiStyle, ModelDefaults, ProviderConfig

# ──────────────────────────────────────────────────────────────
# Helper: OpenAI-compatible provider (most providers use this)
# ──────────────────────────────────────────────────────────────

def _openai_compat(
    id: str,
    display_name: str,
    category: str,
    base_url: str,
    env_names: list[str] | None = None,
    summary: str = "",
    refine: str = "",
    executor: str = "",
    reasoning: str = "",
    website: str = "",
    notes: str = "",
    auth_scheme: AuthScheme = AuthScheme.BEARER,
    supports_tools: bool = False,
    supports_reasoning: bool = False,
    extra_headers: dict[str, str] | None = None,
    extra_params: dict[str, str] | None = None,
    model_aliases: dict[str, str] | None = None,
    configurable_fields: list[str] | None = None,
) -> ProviderConfig:
    return ProviderConfig(
        id=id,
        display_name=display_name,
        category=category,
        api_style=ApiStyle.OPENAI,
        base_url=base_url,
        auth_scheme=auth_scheme,
        auth_env_names=env_names or [],
        default_models=ModelDefaults(
            summary=summary,
            refine=refine,
            executor=executor,
            reasoning=reasoning,
        ),
        model_aliases=model_aliases or {},
        extra_headers=extra_headers or {},
        extra_params=extra_params or {},
        supports_tools=supports_tools,
        supports_reasoning=supports_reasoning,
        notes=notes,
        website=website,
        configurable_fields=configurable_fields or [
            "api_key", "base_url", "model_summary", "model_refine"
        ],
    )


# ──────────────────────────────────────────────────────────────
# All Built-in Providers
# ──────────────────────────────────────────────────────────────

BUILTIN_PROVIDERS: list[ProviderConfig] = [

    # ── Custom ──────────────────────────────────────────────
    ProviderConfig(
        id="custom",
        display_name="自定义配置",
        category="custom",
        api_style=ApiStyle.OPENAI,
        base_url="",
        auth_scheme=AuthScheme.BEARER,
        auth_env_names=[],
        default_models=ModelDefaults(summary="", refine=""),
        notes="自定义 OpenAI 兼容 API，手动填写 Base URL 和模型",
        configurable_fields=[
            "api_key", "base_url", "model_summary", "model_refine",
            "api_style", "auth_scheme", "extra_headers",
        ],
    ),

    # ── Official ────────────────────────────────────────────
    ProviderConfig(
        id="claude",
        display_name="Claude Official",
        category="official",
        api_style=ApiStyle.ANTHROPIC,
        base_url="https://api.anthropic.com",
        auth_scheme=AuthScheme.X_API_KEY,
        auth_env_names=["ANTHROPIC_API_KEY"],
        default_models=ModelDefaults(
            summary="claude-haiku-4-5-20251001",
            refine="claude-haiku-4-5-20251001",
            executor="claude-sonnet-4-6",
            reasoning="claude-opus-4-7",
        ),
        model_aliases={
            "haiku": "claude-haiku-4-5-20251001",
            "sonnet": "claude-sonnet-4-6",
            "opus": "claude-opus-4-7",
        },
        supports_tools=True,
        supports_reasoning=True,
        website="https://console.anthropic.com",
        notes="Anthropic 官方 API",
    ),

    # ── 胜算云 ─────────────────────────────────────────────
    _openai_compat(
        id="shengsuan",
        display_name="胜算云",
        category="domestic",
        base_url="https://api.shengsuan.com/v1",
        env_names=["SHENGSUAN_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://shengsuan.com",
    ),

    # ── ModelScope ─────────────────────────────────────────
    _openai_compat(
        id="modelscope",
        display_name="ModelScope",
        category="domestic",
        base_url="https://api-inference.modelscope.cn/v1",
        env_names=["MODELSCOPE_API_TOKEN"],
        summary="Qwen/Qwen2.5-7B-Instruct",
        refine="Qwen/Qwen2.5-7B-Instruct",
        website="https://modelscope.cn",
        notes="魔搭社区 API",
    ),

    # ── AiHubMix ──────────────────────────────────────────
    _openai_compat(
        id="aihubmix",
        display_name="AiHubMix",
        category="domestic",
        base_url="https://aihubmix.com/v1",
        env_names=["AIHUBMIX_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://aihubmix.com",
    ),

    # ── SiliconFlow ────────────────────────────────────────
    _openai_compat(
        id="siliconflow",
        display_name="SiliconFlow",
        category="domestic",
        base_url="https://api.siliconflow.cn/v1",
        env_names=["SILICONFLOW_API_KEY"],
        summary="Qwen/Qwen2.5-7B-Instruct",
        refine="Qwen/Qwen2.5-7B-Instruct",
        reasoning="deepseek-ai/DeepSeek-R1",
        website="https://siliconflow.cn",
        supports_reasoning=True,
    ),

    # ── SiliconFlow en ─────────────────────────────────────
    _openai_compat(
        id="siliconflow-en",
        display_name="SiliconFlow en",
        category="international",
        base_url="https://api.siliconflow.com/v1",
        env_names=["SILICONFLOW_API_KEY"],
        summary="Qwen/Qwen2.5-7B-Instruct",
        refine="Qwen/Qwen2.5-7B-Instruct",
        reasoning="deepseek-ai/DeepSeek-R1",
        website="https://siliconflow.com",
        supports_reasoning=True,
    ),

    # ── DMXAPI ─────────────────────────────────────────────
    _openai_compat(
        id="dmxapi",
        display_name="DMXAPI",
        category="domestic",
        base_url="https://www.dmxapi.com/v1",
        env_names=["DMXAPI_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://dmxapi.com",
    ),

    # ── 优云智算 ───────────────────────────────────────────
    _openai_compat(
        id="youyun",
        display_name="优云智算",
        category="domestic",
        base_url="https://cloud.infini-ai.com/maas/v1",
        env_names=["YOUYUN_API_KEY"],
        summary="qwen2.5-7b-instruct",
        refine="qwen2.5-7b-instruct",
        website="https://cloud.infini-ai.com",
    ),

    # ── OpenRouter ─────────────────────────────────────────
    _openai_compat(
        id="openrouter",
        display_name="OpenRouter",
        category="international",
        base_url="https://openrouter.ai/api/v1",
        env_names=["OPENROUTER_API_KEY"],
        summary="anthropic/claude-3.5-haiku",
        refine="anthropic/claude-3.5-haiku",
        executor="anthropic/claude-sonnet-4",
        reasoning="anthropic/claude-opus-4",
        website="https://openrouter.ai",
        supports_tools=True,
        supports_reasoning=True,
        model_aliases={
            "haiku": "anthropic/claude-3.5-haiku",
            "sonnet": "anthropic/claude-sonnet-4",
            "opus": "anthropic/claude-opus-4",
        },
    ),

    # ── TheRouter ──────────────────────────────────────────
    _openai_compat(
        id="therouter",
        display_name="TheRouter",
        category="international",
        base_url="https://api.therouter.com/v1",
        env_names=["THEROUTER_API_KEY"],
        summary="claude-3-5-haiku-latest",
        refine="claude-3-5-haiku-latest",
        website="https://therouter.com",
    ),

    # ── Novita AI ──────────────────────────────────────────
    _openai_compat(
        id="novita",
        display_name="Novita AI",
        category="international",
        base_url="https://api.novita.ai/v3/openai",
        env_names=["NOVITA_API_KEY"],
        summary="meta-llama/llama-3.1-8b-instruct",
        refine="meta-llama/llama-3.1-8b-instruct",
        website="https://novita.ai",
    ),

    # ── Nvidia ─────────────────────────────────────────────
    _openai_compat(
        id="nvidia",
        display_name="Nvidia",
        category="international",
        base_url="https://integrate.api.nvidia.com/v1",
        env_names=["NVIDIA_API_KEY"],
        summary="meta/llama-3.1-8b-instruct",
        refine="meta/llama-3.1-8b-instruct",
        website="https://build.nvidia.com",
    ),

    # ── PIPILM ─────────────────────────────────────────────
    _openai_compat(
        id="pipilm",
        display_name="PIPILM",
        category="domestic",
        base_url="https://api.pipilm.com/v1",
        env_names=["PIPILM_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://pipilm.com",
    ),

    # ── DeepSeek ───────────────────────────────────────────
    _openai_compat(
        id="deepseek",
        display_name="DeepSeek",
        category="domestic",
        base_url="https://api.deepseek.com/v1",
        env_names=["DEEPSEEK_API_KEY"],
        summary="deepseek-chat",
        refine="deepseek-chat",
        reasoning="deepseek-reasoner",
        website="https://platform.deepseek.com",
        supports_reasoning=True,
        model_aliases={
            "chat": "deepseek-chat",
            "reasoner": "deepseek-reasoner",
        },
    ),

    # ── Zhipu GLM ──────────────────────────────────────────
    _openai_compat(
        id="zhipu",
        display_name="Zhipu GLM",
        category="domestic",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        env_names=["ZHIPU_API_KEY"],
        summary="glm-4-flash",
        refine="glm-4-flash",
        reasoning="glm-4-plus",
        website="https://open.bigmodel.cn",
        supports_reasoning=True,
    ),

    # ── Zhipu GLM en ───────────────────────────────────────
    _openai_compat(
        id="zhipu-en",
        display_name="Zhipu GLM en",
        category="international",
        base_url="https://open.bigmodel.com/api/paas/v4",
        env_names=["ZHIPU_API_KEY"],
        summary="glm-4-flash",
        refine="glm-4-flash",
        reasoning="glm-4-plus",
        website="https://open.bigmodel.com",
        supports_reasoning=True,
    ),

    # ── Bailian ────────────────────────────────────────────
    _openai_compat(
        id="bailian",
        display_name="Bailian",
        category="domestic",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        env_names=["DASHSCOPE_API_KEY"],
        summary="qwen-plus",
        refine="qwen-plus",
        reasoning="qwen-max",
        website="https://bailian.console.aliyun.com",
        supports_reasoning=True,
    ),

    # ── Bailian For Coding ─────────────────────────────────
    _openai_compat(
        id="bailian-coding",
        display_name="Bailian For Coding",
        category="domestic",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        env_names=["DASHSCOPE_API_KEY"],
        summary="qwen-coder-plus",
        refine="qwen-coder-plus",
        reasoning="qwen-coder-max",
        website="https://bailian.console.aliyun.com",
        supports_reasoning=True,
        notes="通义灵码专用模型",
    ),

    # ── Kimi ───────────────────────────────────────────────
    _openai_compat(
        id="kimi",
        display_name="Kimi",
        category="domestic",
        base_url="https://api.moonshot.cn/v1",
        env_names=["MOONSHOT_API_KEY"],
        summary="moonshot-v1-8k",
        refine="moonshot-v1-8k",
        website="https://platform.moonshot.cn",
    ),

    # ── Kimi For Coding ────────────────────────────────────
    _openai_compat(
        id="kimi-coding",
        display_name="Kimi For Coding",
        category="domestic",
        base_url="https://api.moonshot.cn/v1",
        env_names=["MOONSHOT_API_KEY"],
        summary="kimi-latest",
        refine="kimi-latest",
        website="https://platform.moonshot.cn",
        notes="Kimi 编程增强版",
    ),

    # ── StepFun ────────────────────────────────────────────
    _openai_compat(
        id="stepfun",
        display_name="StepFun",
        category="domestic",
        base_url="https://api.stepfun.com/v1",
        env_names=["STEPFUN_API_KEY"],
        summary="step-1-flash",
        refine="step-1-flash",
        reasoning="step-2-16k",
        website="https://platform.stepfun.com",
        supports_reasoning=True,
    ),

    # ── KAT-Coder ──────────────────────────────────────────
    _openai_compat(
        id="katcoder",
        display_name="KAT-Coder",
        category="domestic",
        base_url="https://api.katcoder.com/v1",
        env_names=["KATCODER_API_KEY"],
        summary="kat-coder-v1",
        refine="kat-coder-v1",
        website="https://katcoder.com",
    ),

    # ── Longcat ────────────────────────────────────────────
    _openai_compat(
        id="longcat",
        display_name="Longcat",
        category="domestic",
        base_url="https://api.longcat.cloud/v1",
        env_names=["LONGCAT_API_KEY"],
        summary="longcat-chat",
        refine="longcat-chat",
        website="https://longcat.cloud",
    ),

    # ── MiniMax ────────────────────────────────────────────
    _openai_compat(
        id="minimax",
        display_name="MiniMax",
        category="domestic",
        base_url="https://api.minimax.chat/v1",
        env_names=["MINIMAX_API_KEY"],
        summary="MiniMax-Text-01",
        refine="MiniMax-Text-01",
        website="https://platform.minimaxi.com",
    ),

    # ── MiniMax en ─────────────────────────────────────────
    _openai_compat(
        id="minimax-en",
        display_name="MiniMax en",
        category="international",
        base_url="https://api.minimax.chat/v1",
        env_names=["MINIMAX_API_KEY"],
        summary="MiniMax-Text-01",
        refine="MiniMax-Text-01",
        website="https://platform.minimaxi.com",
        notes="MiniMax 国际版",
    ),

    # ── DouBaoSeed ─────────────────────────────────────────
    _openai_compat(
        id="doubao",
        display_name="DouBaoSeed",
        category="domestic",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        env_names=["ARK_API_KEY"],
        summary="doubao-1.5-pro-32k",
        refine="doubao-1.5-pro-32k",
        reasoning="doubao-1.5-pro-256k",
        website="https://console.volcengine.com/ark",
        supports_reasoning=True,
    ),

    # ── BaiLing ────────────────────────────────────────────
    _openai_compat(
        id="bailing",
        display_name="BaiLing",
        category="domestic",
        base_url="https://api.bailing.ai/v1",
        env_names=["BAILING_API_KEY"],
        summary="bailing-chat",
        refine="bailing-chat",
        website="https://bailing.ai",
    ),

    # ── Xiaomi MiMo ────────────────────────────────────────
    _openai_compat(
        id="mimo",
        display_name="Xiaomi MiMo",
        category="domestic",
        base_url="https://api.mimo.xiaomi.com/v1",
        env_names=["MIMO_API_KEY"],
        summary="mimo-v2.5-pro",
        refine="mimo-v2.5-pro",
        website="https://mimo.xiaomi.com",
    ),

    # ── PackyCode ──────────────────────────────────────────
    _openai_compat(
        id="packycode",
        display_name="PackyCode",
        category="proxy",
        base_url="https://api.packycode.com/v1",
        env_names=["PACKYCODE_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://packycode.com",
    ),

    # ── Cubence ────────────────────────────────────────────
    _openai_compat(
        id="cubence",
        display_name="Cubence",
        category="proxy",
        base_url="https://api.cubence.com/v1",
        env_names=["CUBENCE_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://cubence.com",
    ),

    # ── AIGoCode ───────────────────────────────────────────
    _openai_compat(
        id="aigocode",
        display_name="AIGoCode",
        category="proxy",
        base_url="https://api.aigocode.com/v1",
        env_names=["AIGOCODE_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://aigocode.com",
    ),

    # ── RightCode ──────────────────────────────────────────
    _openai_compat(
        id="rightcode",
        display_name="RightCode",
        category="proxy",
        base_url="https://api.rightcode.ai/v1",
        env_names=["RIGHTCODE_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://rightcode.ai",
    ),

    # ── AICodeMirror ───────────────────────────────────────
    _openai_compat(
        id="aicodemirror",
        display_name="AICodeMirror",
        category="proxy",
        base_url="https://api.aicodemirror.com/v1",
        env_names=["AICODEMIRROR_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://aicodemirror.com",
    ),

    # ── AICoding ───────────────────────────────────────────
    _openai_compat(
        id="aicoding",
        display_name="AICoding",
        category="proxy",
        base_url="https://api.aicoding.com/v1",
        env_names=["AICODING_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://aicoding.com",
    ),

    # ── CrazyRouter ────────────────────────────────────────
    _openai_compat(
        id="crazyrouter",
        display_name="CrazyRouter",
        category="proxy",
        base_url="https://api.crazyrouter.com/v1",
        env_names=["CRAZYROUTER_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://crazyrouter.com",
    ),

    # ── SSAiCode ───────────────────────────────────────────
    _openai_compat(
        id="ssaicode",
        display_name="SSAiCode",
        category="proxy",
        base_url="https://api.ssaicode.com/v1",
        env_names=["SSAICODE_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://ssaicode.com",
    ),

    # ── Micu ───────────────────────────────────────────────
    _openai_compat(
        id="micu",
        display_name="Micu",
        category="proxy",
        base_url="https://api.micu.me/v1",
        env_names=["MICU_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://micu.me",
    ),

    # ── X-Code API ─────────────────────────────────────────
    _openai_compat(
        id="xcodeapi",
        display_name="X-Code API",
        category="proxy",
        base_url="https://api.x-code.dev/v1",
        env_names=["XCODE_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://x-code.dev",
    ),

    # ── CTok.ai ────────────────────────────────────────────
    _openai_compat(
        id="ctok",
        display_name="CTok.ai",
        category="proxy",
        base_url="https://api.ctok.ai/v1",
        env_names=["CTOK_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://ctok.ai",
    ),

    # ── DDSHub ─────────────────────────────────────────────
    _openai_compat(
        id="ddshub",
        display_name="DDSHub",
        category="proxy",
        base_url="https://api.ddshub.com/v1",
        env_names=["DDSHUB_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://ddshub.com",
    ),

    # ── E-FlowCode ─────────────────────────────────────────
    _openai_compat(
        id="eflowcode",
        display_name="E-FlowCode",
        category="proxy",
        base_url="https://api.eflowcode.com/v1",
        env_names=["EFLOWCODE_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://eflowcode.com",
    ),

    # ── LionCCAPI ──────────────────────────────────────────
    _openai_compat(
        id="lionccapi",
        display_name="LionCCAPI",
        category="proxy",
        base_url="https://api.lionccapi.com/v1",
        env_names=["LIONCCAPI_API_KEY"],
        summary="claude-haiku-4-5-20251001",
        refine="claude-haiku-4-5-20251001",
        website="https://lionccapi.com",
    ),

    # ── GitHub Copilot ─────────────────────────────────────
    _openai_compat(
        id="github-copilot",
        display_name="GitHub Copilot",
        category="official",
        base_url="https://api.githubcopilot.com",
        env_names=["GITHUB_TOKEN", "COPILOT_TOKEN"],
        summary="gpt-4o-mini",
        refine="gpt-4o-mini",
        executor="gpt-4o",
        website="https://github.com/features/copilot",
        notes="需要 GitHub Copilot 订阅",
        supports_tools=True,
    ),

    # ── Codex ──────────────────────────────────────────────
    _openai_compat(
        id="codex",
        display_name="Codex",
        category="official",
        base_url="https://api.openai.com/v1",
        env_names=["OPENAI_API_KEY"],
        summary="gpt-4o-mini",
        refine="gpt-4o-mini",
        executor="gpt-4o",
        reasoning="o1",
        website="https://platform.openai.com",
        supports_tools=True,
        supports_reasoning=True,
    ),

    # ── AWS Bedrock (AKSK) ─────────────────────────────────
    ProviderConfig(
        id="bedrock-aksk",
        display_name="AWS Bedrock (AKSK)",
        category="official",
        api_style=ApiStyle.BEDROCK,
        base_url="https://bedrock-runtime.{region}.amazonaws.com",
        auth_scheme=AuthScheme.AWS_SIGV4,
        auth_env_names=[
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION",
        ],
        default_models=ModelDefaults(
            summary="anthropic.claude-3-haiku-20240307-v1:0",
            refine="anthropic.claude-3-haiku-20240307-v1:0",
            executor="anthropic.claude-3-5-sonnet-20241022-v2:0",
        ),
        supports_tools=True,
        supports_reasoning=True,
        website="https://aws.amazon.com/bedrock/",
        notes="使用 AWS AKSK 认证",
        configurable_fields=[
            "access_key_id", "secret_access_key", "region",
            "model_summary", "model_refine",
        ],
    ),

    # ── AWS Bedrock (API Key) ──────────────────────────────
    ProviderConfig(
        id="bedrock-apikey",
        display_name="AWS Bedrock (API Key)",
        category="official",
        api_style=ApiStyle.BEDROCK,
        base_url="https://bedrock-runtime.{region}.amazonaws.com",
        auth_scheme=AuthScheme.CUSTOM_HEADER,
        auth_header_name="x-api-key",
        auth_env_names=[
            "AWS_BEARER_TOKEN",
            "AWS_REGION",
        ],
        default_models=ModelDefaults(
            summary="anthropic.claude-3-haiku-20240307-v1:0",
            refine="anthropic.claude-3-haiku-20240307-v1:0",
            executor="anthropic.claude-3-5-sonnet-20241022-v2:0",
        ),
        supports_tools=True,
        supports_reasoning=True,
        website="https://aws.amazon.com/bedrock/",
        notes="使用 Bearer Token 认证",
        configurable_fields=[
            "api_key", "region",
            "model_summary", "model_refine",
        ],
    ),
]


def get_builtin_provider_map() -> dict[str, ProviderConfig]:
    """Return a dict mapping provider id -> ProviderConfig."""
    return {p.id: p for p in BUILTIN_PROVIDERS}
