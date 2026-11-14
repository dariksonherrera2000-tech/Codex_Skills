# Natural Speech Guide

Use this reference when the user wants the speaking script to sound natural, colloquial, and less AI-like. This guide adapts the Chinese-first "说人话" stance from [MrGeDiao/shuorenhua](https://github.com/MrGeDiao/shuorenhua) to live presentation scripts: protect information first, then reduce template feel, performance tone, and register drift.

## Core Stance

1. Protect information before style. Lock numbers,口径, dates, names, source caveats, commitments, decisions, responsibilities, and exact asks before rewriting.
2. Match the room. A board update can be concise and formal; a customer proposal can be consultative; a promotion defense can use "我" for accountability. Natural does not always mean casual.
3. Fix patterns, not just words. Do not do mechanical synonym replacement. Rewrite the posture of the sentence.
4. Keep professional terms when they carry meaning. Do not remove domain language just because it sounds formal.
5. Make the speaker specific. A script should sound like this presenter talking to this audience, not like a generic model explaining a slide.
6. Reread for drift. After making language more natural, check that facts, obligations, risk boundaries, and source status did not change.

## Protected Spans For Presentation Scripts

Do not casually rewrite:
- metric values, units, baselines, dates, periods, percentages, and currency;
- source labels, caveats, sample sizes, and "to verify" notes;
- product names, customer names, team names, role names, legal/compliance wording;
- decisions requested from the audience;
- implementation commitments, owner names, deadlines, and resource asks;
- quoted customer/user language;
- terms from the slides that the audience expects to hear.

If a protected item makes the sentence stiff, keep the item and rewrite the surrounding language.

## Script Naturalness Pass

Run this pass after the first page-by-page draft:

1. Mark protected spans.
2. Choose intensity:
   - `minimal`: high-stakes executive, legal, compliance, finance, or technical pages. Only remove obvious template phrasing.
   - `standard`: default for most reports, proposals, and defenses. Rewrite stiff phrasing while preserving structure.
   - `strong`: only when the script is obviously generic, slogan-heavy, or user explicitly says "别像 AI / 说人话".
3. Remove or rewrite AI-ish patterns.
4. Remove repeated page-level openings. Count spoken uses of `这一页` / `本页` / `这页`; more than 3 total is a rewrite signal unless the words are pointing at a visual or summarizing a compressed version.
5. Read the script aloud mentally. If it sounds like a written memo, shorten it.
6. Run factual reread: no numbers, responsibilities, caveats, or ask changed.

## AI-ish Patterns To Remove

### Formula openers

Avoid overusing:
- "先说结论"
- "本页主要想表达"
- "这一页讲的是"
- "这页展示了"
- "接下来我将从三个方面"
- "值得注意的是"
- "综上所述"

Use direct spoken variants:
- "先把话说简单一点：..."
- "只看一个点：..."
- "这里别急着看细节，先看趋势。"
- "所以今天要定的，其实是..."
- "刚才说的是现象，真正卡住的是..."
- "如果我是客户，我会先问..."

### Over-polished transitions

Weak:
- "基于上述分析，我们可以得出..."
- "在这样的背景下，方案应运而生。"
- "这不仅是一次效率提升，更是组织能力的升级。"

Better:
- "问题看清楚以后，方案就很直接了。"
- "所以我们没有先做大而全，而是先把这个环节打穿。"
- "这句话不要把它听成口号，它对应的是后面两个动作。"

### Fake authority

Weak:
- "行业专家普遍认为..."
- "大量研究表明..."
- "市场已经充分证明..."

Better:
- If source exists: "这里引用的是第 6 页这组试点数据..."
- If source is missing: "这句话现在缺来源。上台时建议降级成工作判断，不要说成行业共识。"

### Consultant filler

Trim:
- "赋能", "抓手", "闭环", "沉淀", "拉齐认知", "形成合力"
- "关键举措", "重要路径", "能力升级", "持续深化"

Replace with actual action:
- "让销售能当天看到状态"
- "把审批从三步减到一步"
- "每周五前由项目负责人同步风险"

### Three-part stiffness

Do not force every point into exactly three parts. If the slide has two real points, say two. If it has four implementation steps, keep four. Natural pacing matters more than a neat triad.

### Emotional overacting

Avoid:
- "我非常激动地向大家汇报"
- "这对我们意义重大"
- "这是一个里程碑式的时刻"

Use grounded emotion:
- "这里我会讲得慢一点，因为它直接关系到今天要不要批资源。"
- "这个结果不错，但我更想说清楚它的边界。"

## Presentation-specific Register

Executive report:
- Natural = short, direct, decision-aware.
- Good: "只需要您看两个数：进度提前了，但风险也前移了。"
- Bad: "本页从多个维度充分展现了项目推进的阶段性成果。"

Customer proposal:
- Natural = customer-first, low bragging.
- Good: "如果用贵团队现在的流程来算，先试点这一个环节最稳。"
- Bad: "我们的平台将全面赋能贵司数字化转型。"

Promotion defense:
- Natural = accountable, not self-mythologizing.
- Good: "这件事里，我真正做对的是先砍掉了两个低价值方向。"
- Bad: "这充分体现了我在复杂业务场景下的综合领导力。"

Technical talk:
- Natural = precise and candid.
- Good: "这个方案快，但不是免费午餐。代价是缓存失效会更难排查。"
- Bad: "该架构以创新方式实现了性能与稳定性的双重提升。"

Training:
- Natural = patient, concrete.
- Good: "这里先别记概念，看这个例子就够了。"
- Bad: "接下来我们将深入探讨这一能力的底层逻辑。"

## Output Requirements

In the final `自然度回读` section, include:
- `已保护的信息`: numbers, sources, responsibilities, names, and exact asks preserved;
- `已压掉的 AI 味`: 1-3 pattern families removed, such as formula opener, fake authority, consultant filler, over-polished transition;
- `已减少的机械开头`: repeated page-level openings removed, especially "这一页讲", "本页主要", and "这页展示";
- `仍需人工确认的口吻`: any page where the speaker's personal style, risk appetite, or audience relationship could change wording.

Keep this section short. It is a confidence check, not a lecture.
