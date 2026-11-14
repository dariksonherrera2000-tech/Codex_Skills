# Presentation Script Coach（汇报逐字稿与提词辅助 Skill）

![Codex Skill](https://img.shields.io/badge/Codex%20Skill-presentation--script--coach-111827)
![Language](https://img.shields.io/badge/Language-%E4%B8%AD%E6%96%87-blue)
![Input](https://img.shields.io/badge/Input-PPTX%20%7C%20PDF%20%7C%20HTML%20%7C%20Brief-green)
![Output](https://img.shields.io/badge/Output-Script%20%7C%20Q%26A%20%7C%20Teleprompter-purple)
![Safety](https://img.shields.io/badge/Safety-Non--destructive-orange)

> 标签：`Codex Skill` · `PPT` · `Slides` · `汇报逐字稿` · `Speaker Notes` · `Teleprompter` · `提词器` · `Q&A`

把已有 PPT、PDF、HTML slides 或 `presentation-report-preflight` 策略简报，转成一份能直接彩排的中文汇报方案：按页逐字稿、自然口播、转场话术、时间分配、追问攻防、改稿建议，以及确认稿后的提词器/备注辅助文件。

它不负责重做 PPT，也不会默认修改源文件。它回答的是：**这份 PPT/slides 在这个场合里，应该怎么讲，才能更稳地达成目标？**

---

## 核心能力

| 能力 | 说明 |
| --- | --- |
| **按页逐字稿** | 每页都有讲述目的、建议时长、逐字稿、转场句、压缩版和追问方向。 |
| **需求确认门** | 交互模式下先给需求确认卡，确认场景、听众、目标、时长和口吻后再生成完整逐页稿。 |
| **自然口语化** | 借鉴“说人话”的表达原则，去掉 AI 式套话，保留事实、数字、口径和责任边界。 |
| **看图讲解** | 对图表、截图、流程图、图片页做视觉阅读，不把图片页简单跳过。 |
| **场景定制** | 根据汇报对象、行业、时长、身份和目标调整语气与打法。 |
| **PPT/slides 诊断** | 给出非破坏式改稿建议：标题、证据、来源、信息密度、CTA、追问风险。 |
| **Q&A 攻防** | 针对高风险页准备追问、回答方向和需要补充的材料。 |
| **时间校验** | 用脚本检查逐字稿朗读时长，避免“标 15 分钟，实际讲 25 分钟”。 |
| **汇报辅助** | 用户确认稿件后，可生成 HTML 提词器版或 PPTX 备注版派生文件。 |

---

## 适用场景

- 销售提案、客户汇报、咨询交付
- 融资路演、产品发布、战略汇报
- 晋升答辩、季度/年度复盘、项目复盘
- 技术分享、培训授课、内部同步
- 已有 PPT/slides 不想重做，但需要“讲得更像真人、更有现场感”

---

## 安装

本仓库根目录就是一个标准 skill。推荐使用开源 [`skills` CLI](https://github.com/vercel-labs/skills) 安装：

```bash
# 安装到当前项目
npx skills add archlizheng/presentation-script-coach

# 安装到用户级，全局可用
npx skills add archlizheng/presentation-script-coach -g

# 只安装给指定 agent
npx skills add archlizheng/presentation-script-coach -a codex
npx skills add archlizheng/presentation-script-coach -a claude-code
```

也可以手动克隆后放到 Codex skills 目录：

```bash
git clone https://github.com/archlizheng/presentation-script-coach.git
cp -R presentation-script-coach ~/.codex/skills/presentation-script-coach
```

---

## 快速使用

在 Codex 中可以这样触发：

```text
用 $presentation-script-coach 读取这份 PPT，按 15 分钟客户汇报生成中文逐字稿和 Q&A。
```

```text
用 $presentation-script-coach 帮我把这个 HTML slides 做成自然一点的路演口播稿，别太像 AI。
```

```text
用 $presentation-script-coach 根据这份 PDF，给我按页讲稿、转场句和 5 分钟压缩版。
```

默认情况下，skill 会先输出一张需求确认卡，不会立刻写完整逐页稿。你确认或修正后，它再生成正式稿。如果你想跳过确认，可以直接说“直接给 / 别问 / 先出稿”。

生成稿件后，skill 会在末尾询问下一步是否生成辅助文件。稿件确认后，也可以这样请求：

```text
这版逐字稿没问题。请生成 HTML 提词器版。
```

```text
这版逐字稿确认。请把逐字稿写入 PPTX 每页备注里。
```

---

## 输入与输出

### 支持输入

| 输入 | 处理方式 |
| --- | --- |
| `.pptx` | 抽取标题、正文、表格、图片提示、speaker notes，并可渲染页面图片辅助理解。 |
| `.pdf` | 按页抽取文本和表格；扫描页或图片页会标记为需要 OCR/人工复核。 |
| `.html` | 按 `section`、`.slide`、`[data-slide]`、标题层级等方式切页。 |
| 策略简报 | 可读取 `presentation-report-preflight` 产出的策略、目标、时长和证据计划。 |

### 默认输出

- `presentation-speaking-brief.md`：给人读的汇报策略、逐页讲稿、Q&A 和彩排清单。
- `presentation-speaking-brief.contract.json`：机器可读交接契约，供后续提词器/备注注入使用。

完整稿交付后会附带“下一步汇报辅助”选择：HTML 提词器版、PPTX 备注版、PDF/通用提词卡，或暂不生成辅助文件。

输出结构包括：

1. 汇报策略摘要
2. PPT/slides 诊断与改稿建议
3. Timing Brief
4. Page-by-page Verbatim Script
5. Q&A / 追问攻防
6. 彩排自检
7. Speaking Handoff Contract 摘要
8. 下一步汇报辅助选择

---

## 提词器与备注辅助

辅助文件只会在用户确认逐字稿后生成，且默认不覆盖源文件。完整逐字稿交付后，skill 必须询问是否继续生成对应辅助文件，避免只产出 JSON 契约后就结束。

### HTML 提词器版

```bash
python scripts/build_presentation_assist.py html \
  --source /absolute/path/to/input.html \
  --contract /absolute/path/to/presentation-speaking-brief.contract.json \
  --out /absolute/path/to/input.teleprompter.html
```

特性：

- 主屏幕不显示逐字稿。
- 按 `T` 打开独立提词器弹窗，可拖到另一块屏幕。
- 翻页时自动同步对应页讲稿。
- Reveal.js 页面优先使用官方 API/events。
- 普通 HTML slides 使用 `section`、`.slide`、`[data-slide]`、hash 和 active/present class 做通用同步。
- 弹窗被浏览器拦截时，可回退到隐藏侧边面板。

### PPTX 备注版

```bash
python scripts/build_presentation_assist.py pptx \
  --source /absolute/path/to/input.pptx \
  --contract /absolute/path/to/presentation-speaking-brief.contract.json \
  --out /absolute/path/to/input.with-notes.pptx
```

特性：

- 把对应页面逐字稿写入对应 PPTX 页面备注。
- 保留已有备注。
- 使用 `PRESENTATION SCRIPT COACH START/END` 托管块，重复运行时只替换托管块。
- 注入前校验页数、页 ID、标题 hash、内容 hash，避免讲稿错写到错误页面。

### PDF 或策略简报

PDF 和策略简报不能直接注入提词器或 PPTX 备注。skill 会生成可打印提词卡：

```bash
python scripts/build_presentation_assist.py cards \
  --contract /absolute/path/to/presentation-speaking-brief.contract.json \
  --out /absolute/path/to/cue-cards.md
```

---

## 目录结构

```text
presentation-script-coach/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── build_presentation_assist.py
│   ├── check_timing.py
│   ├── extract_slides_context.py
│   └── render_page_images.py
└── references/
    ├── delivery-playbooks.md
    ├── example-speaking-brief.md
    ├── natural-speech-guide.md
    ├── script-writing-guide.md
    ├── slides-diagnosis-guide.md
    └── speaking-brief.schema.json
```

---

## 依赖说明

脚本采用 Python，并在文件头声明 PEP 723 inline dependencies。常见依赖包括：

- `python-pptx`：抽取和写入 PPTX speaker notes。
- `pdfplumber` / `pypdf`：抽取 PDF 页面文本与表格。
- `lxml`：解析 HTML slides。
- `PyMuPDF` / LibreOffice / Playwright：在可用时渲染页面图片，辅助理解图表和截图。

如果当前 Python 环境缺少依赖，可优先使用 `uv run` 运行脚本。

---

## 验证

发布前可运行：

```bash
python /Users/ethan/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python -m py_compile scripts/*.py
python -m json.tool references/speaking-brief.schema.json >/dev/null
```

建议额外检查是否还有旧口径残留：

```bash
rg -n '<old-term-regex>' .
```

---

## 设计原则

1. **先确认，再写完整稿**：交互模式下先输出需求确认卡；只有用户确认、修正，或明确要求跳过时，才生成完整逐页稿。
2. **先讲法，后辅助**：先产出逐字稿与策略，用户确认后才生成提词器或备注版文件。
3. **派生文件，不改源文件**：HTML 输出 `*.teleprompter.html`，PPTX 输出 `*.with-notes.pptx`。
4. **准确映射页面**：辅助生成前重新抽取源文件并校验页面身份，尽量避免错页注入。
5. **不编造事实**：来源不明的数字、案例和行业判断会标记为待确认。
6. **像人说话**：减少模板感、口号感和 AI 味，避免每页都用“这一页讲 / 本页主要 / 这页展示”开头。

---

## 与 presentation-report-preflight 的关系

`presentation-report-preflight` 负责在制作 PPT/slides 前规划策略、标题链和内容蓝图。

`presentation-script-coach` 面向已有 PPT/slides：读取现有文件，生成这场汇报的讲法、逐字稿、Q&A 和辅助文件。

两者可以串联，也可以独立使用。

---

## 注意事项

- 不直接重做或美化 PPT/slides。
- 不把扫描页或图片页假装成已理解内容。
- 不编造客户案例、数据来源、行业事实或承诺。
- 不默认覆盖源文件。
- 如果用户确认稿件后又重排、删页或替换文件，辅助生成会要求重新确认映射。

---

## License

本仓库暂未声明开源许可证。公开使用、复制或二次分发前，请先与作者确认授权范围。
