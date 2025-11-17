"""Default provider/model templates used to bootstrap configs."""

DEFAULT_PROVIDER_MODELS = {
    "bailian": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "timeout": 60,
        "max_retries": 3,
        "default_model": "qwen-plus",
        "models": [
            {
                "name": "通用对话",
                "code": "qwen-plus",
                "tags": ["general", "zh"],
                "description": "适合中文助理、问答与总结任务",
            },
            {
                "name": "写作助手",
                "code": "qwen-turbo",
                "tags": ["writing"],
                "description": "取向文案/长文生成",
            },
            {
                "name": "长文本专家",
                "code": "qwen-max-longcontext",
                "tags": ["analysis", "long-form"],
                "description": "支持更长上下文的分析模型",
            },
        ],
    },
    "ollama": {
        "api_base": "http://127.0.0.1:11434",
        "timeout": 120,
        "max_retries": 3,
        "default_model": "qwen2.5-coder",
        "models": [
            {
                "name": "本地代码助手",
                "code": "qwen2.5-coder",
                "tags": ["coding", "zh"],
                "description": "擅长本地离线代码补全与调试",
            },
            {
                "name": "Mini 速答",
                "code": "qwen2.5-mini",
                "tags": ["quick", "general"],
                "description": "轻量模型，适合快速问答",
            },
        ],
    },
}
