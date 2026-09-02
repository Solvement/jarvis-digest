# 已掌握概念清单（known.md）

用法：把你**能向别人讲清楚**的概念打勾 `[x]`。带读时 AI 会跳过打勾的概念；日报的"前置知识"也会标出你已掌握/需补。
每次精读结束，Claude 会把你新学会的概念追加到对应分组的末尾。
格式：`- [ ] 概念名 | 别名1, 别名2`（别名用于自动匹配，可留空）

## 基础
- [ ] Transformer | self-attention, multi-head attention
- [ ] 位置编码 | positional encoding, RoPE, ALiBi
- [ ] Tokenizer | BPE, SentencePiece
- [ ] 预训练 / 微调 | pretraining, fine-tuning, SFT
- [ ] 交叉熵与语言建模目标 | next-token prediction
- [ ] 梯度下降与优化器 | Adam, AdamW, learning rate schedule
- [ ] 混合精度训练 | bf16, fp16, mixed precision
- [ ] 过拟合与正则化 | dropout, weight decay
- [ ] 评测指标 | perplexity, accuracy, F1, BLEU
- [ ] Scaling law | scaling laws, Chinchilla

## LLM 推理与后训练
- [ ] RLHF | reward model, PPO
- [ ] DPO | direct preference optimization
- [ ] GRPO | group relative policy optimization
- [ ] 蒸馏 | knowledge distillation, on-policy distillation
- [ ] 思维链 | chain-of-thought, CoT
- [ ] 推理模型 / 测试时计算 | test-time compute, reasoning model, o1-style
- [ ] 拒绝采样 | rejection sampling, best-of-N
- [ ] 过程奖励模型 | PRM, process reward model
- [ ] 指令微调数据合成 | self-instruct, synthetic data
- [ ] 幻觉 | hallucination
- [ ] 对齐与安全 | alignment, red teaming, jailbreak
- [ ] Prompt injection | prompt injection

## Agent / RAG
- [ ] ReAct | ReAct, tool use, function calling
- [ ] Agent 规划 | planning, task decomposition
- [ ] Agent 记忆 | memory, MemGPT
- [ ] 多智能体 | multi-agent
- [ ] MCP | model context protocol
- [ ] Agent 评测 | SWE-bench, agent benchmark
- [ ] RAG 基础 | retrieval-augmented generation
- [ ] 向量检索 | embedding, vector database, ANN, HNSW
- [ ] 重排序 | reranker, cross-encoder
- [ ] GraphRAG | graph RAG
- [ ] 长上下文 | long context, context window

## 多模态 / CV
- [ ] CNN 与 ResNet | convolution, ResNet
- [ ] ViT | vision transformer
- [ ] CLIP | contrastive learning, CLIP
- [ ] 视觉语言模型 | VLM, LLaVA
- [ ] Diffusion 基础 | diffusion model, DDPM, DDIM
- [ ] 潜空间扩散 | latent diffusion, VAE
- [ ] Flow matching | flow matching, rectified flow
- [ ] DiT | diffusion transformer
- [ ] 视频生成 | video generation
- [ ] 自回归图像生成 | autoregressive image generation, VQ-VAE
- [ ] 3D 表示 | NeRF, Gaussian splatting
- [ ] VLA / 具身 | vision-language-action, embodied AI
- [ ] 目标检测 / 分割 | detection, segmentation, SAM

## 训练与系统
- [ ] MoE | mixture of experts
- [ ] 线性注意力 / SSM | linear attention, Mamba, state space model, DeltaNet
- [ ] 稀疏注意力 | sparse attention
- [ ] KV cache | KV cache
- [ ] FlashAttention | flash attention
- [ ] 数据并行 / 张量并行 / 流水并行 | data parallel, tensor parallel, pipeline parallel
- [ ] ZeRO / FSDP | ZeRO, FSDP
- [ ] 量化 | quantization, GPTQ, AWQ, int4
- [ ] 投机解码 | speculative decoding
- [ ] Continuous batching / PagedAttention | vLLM, paged attention
- [ ] LoRA | LoRA, QLoRA, PEFT
- [ ] 梯度检查点 | gradient checkpointing
- [ ] 模型合并 | model merging
- [ ] 训练稳定性 | loss spike, training stability

## 我正在学 / 见过但不熟（Claude 带读时会再确认）
（自动维护，见 learning.md）
