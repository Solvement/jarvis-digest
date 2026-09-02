# Jarvis · AI 每日情报 + 论文带读

每天中午 12:00（纽约）自动抓取 GitHub Trending / Hugging Face Daily Papers / arXiv，按你的兴趣画像用 LLM 打分筛出 15–20 条，生成中文速览日报（Markdown + 网页），并提供一个"只讲你不会的部分"的对话式精读 skill，把笔记沉淀成 Obsidian 知识库。

```
采集 300–500 条 → 去重/硬过滤 → LLM 打分 → 核心方向 14 条 + 全领域热点 4 条 → 中文速览 + 示意图
                                                                    ↓
                                            你每天 10 分钟：标「想读」 → 每周 1–2 篇在 Claude 里精读 → notes/
```

## 目录

| 路径 | 作用 |
|---|---|
| `jarvis/` | 流水线代码（采集 → 打分 → 速览 → 输出） |
| `config.yml` | 所有可调参数：源、阈值、条数、模型 |
| `profile/interests.md` | 兴趣画像（LLM 打分时原样读取）— **写得越具体，筛得越准** |
| `profile/known.md` | 已掌握概念勾选清单 — 带读时跳过、日报标注前置 |
| `profile/learning.md` | 讲过但没完全懂的概念（自动维护） |
| `digests/YYYY-MM-DD.md` | 日报（Obsidian 打开整个仓库即可） |
| `docs/` | 网页仪表盘（GitHub Pages），数据在 `docs/data/` |
| `notes/` | 精读笔记 / 概念卡片（Claude 自动写入） |
| `.claude/skills/deep-read/` | 对话式带读 skill |
| `.github/workflows/daily.yml` | 每天自动运行并提交 |

## 部署（一次性，约 10 分钟）

1. **建仓库**：在 GitHub 新建公开仓库 `jarvis`，把本目录推上去：
   ```bash
   git init && git add . && git commit -m "init jarvis"
   git branch -M main
   git remote add origin https://github.com/Solvement/jarvis-digest.git
   git push -u origin main
   ```
2. **放 API key**：仓库 Settings → Secrets and variables → Actions → New repository secret，名字 `OPENAI_API_KEY`。
3. **允许 Actions 写仓库**：Settings → Actions → General → Workflow permissions → 选 **Read and write permissions**。
4. **开 GitHub Pages**：Settings → Pages → Source 选 *Deploy from a branch*，Branch `main`，folder `/docs`。几分钟后网页在 `https://Solvement.github.io/jarvis-digest/`。
5. **手动跑第一次**：Actions → daily-digest → Run workflow。跑完仓库里会多出 `digests/今天.md` 和 `docs/data/今天.json`。
6. 把 `config.yml` 里 `site.repo` 改成真实仓库地址。

## 本地运行

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...          # Windows PowerShell: $env:OPENAI_API_KEY="sk-..."
python -m jarvis run                  # 今天
python -m jarvis run --date 2026-09-01
python -m jarvis run --fixtures --no-llm   # 不联网、不花钱，用测试数据跑通
```

本地预览网页：`cd docs && python -m http.server 8000` 然后打开 http://localhost:8000

## 每天怎么用

1. 中午打开网页（或 Obsidian 里的 `digests/`），10 分钟扫一遍。"今日必读"是核心分最高的一条。
2. 值得深入的点 **☆ 想读**，攒进右侧精读队列；看过的点 **标为已读**。
3. 每周挑 1–2 篇，点 **复制精读指令给 Claude**，粘到 Claude Code / Cowork（在仓库目录下打开），Claude 会：
   - 读 `profile/known.md`，只问你"不会"的前置概念
   - 逐节带读、提问检验、扮演审稿人
   - 把笔记写进 `notes/`，把新学会的概念同步回 `known.md`
4. 隔一段时间回头看 `profile/known.md` 的增长——那就是你的进度条。

## 调参

- 觉得筛得太宽/太窄：改 `profile/interests.md` 的措辞，或 `config.yml → ranking`。
- 想换模型：`config.yml → llm`，或在 Actions 里设 `JARVIS_SCORE_MODEL` / `JARVIS_DIGEST_MODEL` 环境变量。
- 成本：打分用 nano、速览用 mini，每天约 10–15 万 token 输入，**每月 $3–6**。

## 致谢 / 参考

采集思路参考 [agents-radar](https://github.com/duanyytop/agents-radar)，兴趣打分参考 [ArxivDigest](https://github.com/AutoLLM/ArxivDigest)，笔记结构参考 [DeepPaperNote](https://github.com/917Dhj/DeepPaperNote)，"只讲缺口"的带读机制参考 RPKT（arXiv 2508.11892）。
