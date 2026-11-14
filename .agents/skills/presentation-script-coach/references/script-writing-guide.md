# Script Writing Guide

Use this reference when writing verbatim scripts, transitions, compressed versions, and rehearsal language.

## Principles

1. Spoken first: write short sentences that can be read aloud without losing breath.
2. One page, one job: each page script should advance one decision, proof point, lesson, or transition.
3. Claim then explain: open each page with the conclusion, then support it.
4. Signpost changes: tell the audience when you move from problem to evidence, evidence to plan, or plan to ask.
5. Mark uncertainty: if a number lacks a source or baseline, use conservative wording.
6. Make silence useful: include brief pauses for important claims, chart reading, or decision asks.
7. Do not narrate every bullet. Explain the meaning behind the slide.
8. Make the script sound like someone speaking in the room. Avoid formula openers, slogan endings, fake authority, and consultant filler; use `natural-speech-guide.md` for the final pass.
9. Vary page openings. Do not let every page start with "这一页讲...", "本页主要...", or "这页展示..."; those phrases are labels, not speech.

## Page Script Pattern

Use this pattern unless the page type calls for a different structure:

```markdown
- 本页目的：<one sentence>
- 建议时长：<duration>
- 逐字稿：
  "先把结论放前面：...
  这里先别急着看全部细节，重点看...
  对我们来说，这意味着...
  下面我接着讲..."
- 转场句："接下来我们看为什么会发生。"
- 压缩版："如果时间有限，只讲..."
- 必须保留：<data, caveat, CTA, source, customer wording>
- 可能追问：<question>
- 回答方向：<answer stance>
```

## 看图话术 (Chart / Diagram Walkthrough)

Use this pattern for any page whose core evidence is a chart, diagram, screenshot, or photo that was visually read. Never say "这页展示了我们的数据" — that is narrating the slide's existence, not its meaning.

Three beats, in order:

1. Orient — tell the audience what they are looking at, in one sentence: "左边这张是过去四个季度的付费留存,右边是同期的客单价。"
2. Point — direct their eyes to the one place that matters: "别的先不用看,重点看三月这个拐点。" Use the visual emphasis you observed (the biggest number, the highlighted bar, the reddest cell).
3. Land — say the takeaway the visual is arguing, then bridge to the implication: "掉下来的不是新客,是老客续费。这就是为什么下一页我们要先修续费流程。"

Rules:
- One chart, one takeaway. If the chart argues two things, pick the one this page's job needs; move the other to Q&A.
- Do not read out every data point or legend entry. The audience can see; your job is selection and meaning.
- Numbers read only from the image (`read_from_image`): speak them at the precision you actually saw. If the label was small or blurry, use magnitude wording ("大概在三成左右") and flag it for verification instead of inventing precision.
- Architecture/flow diagrams: walk one path through the diagram ("一个请求进来,先到网关,再到风控,真正的耗时在第三步"), not module-by-module inventory.
- Screenshots: say what the audience should notice is possible ("大家看,这一步用户已经不需要填表了"), not the UI inventory.
- Leave a beat of silence after Point — the audience needs a second to actually look.

## Anti-mechanical Page Openers

Page-by-page structure is for the document; the spoken script should not sound like a form being filled out.

Avoid repeated spoken openings:
- "这一页讲的是..."
- "本页主要想表达..."
- "这页展示了..."
- "接下来我将介绍..."

Use these alternatives instead:
- Conclusion first: "结论先放前面：..."
- Audience concern first: "如果我是客户，我会先问一个问题：..."
- Continuation from previous page: "刚才说的是现象，真正卡住的是..."
- Data or visual focus: "先看左边这条线，三月以后开始变了。"
- Decision focus: "今天需要您拍板的，其实是这件事。"
- Risk focus: "这里我会说得保守一点，因为这个数字还缺口径。"

Frequency rule: in the full spoken script, `这一页` / `本页` / `这页` should appear no more than 3 times total unless they are needed for visual pointing or compressed summaries. If several adjacent page scripts use the same opener shape, rewrite before delivery.

## Transition Consistency Check

After drafting all pages, read only the transition sentences in sequence. If three or more use the same shape ("接下来我们看..."), vary the mechanism: a question ("那问题出在哪?"), a contrast ("这是好消息,坏消息在下一页"), a callback ("还记得第 2 页那个缺口吗"), or a plain handoff ("先说到这,下面是资源的事").

## Tone Controls

Executive:
- Lead with conclusion and implication.
- Cut background unless it changes a decision.
- Prefer grounded directness: "只需要看两个数..." / "今天需要您定的是...".

Customer / sales:
- Use customer language and pain.
- Avoid internal jargon.
- Prefer consultative wording: "如果按贵团队现在的流程来算..." / "先试点这个环节最稳...".

Investor:
- Keep pace fast.
- Tie every detail to market, traction, defensibility, or capital plan.
- Separate evidence from hypothesis: "已经验证的是..." vs "还没验证、但我们正在看的假设是...".

Promotion defense:
- Make personal contribution visible.
- Link work to next-level competency.
- Sound accountable without self-mythologizing: "这件事里，我真正做对的是..." / "下次我会保留这个做法...".

Technical:
- Be precise and honest.
- Define terms before acronyms.
- Say the tradeoff plainly: "这个方案快，但代价是..." / "这里还没解决的是...".

Training:
- Use patient sequencing.
- Add practice prompts.
- Use simple teaching language: "这里先别记概念，看例子..." / "我们停一下，自己判断一次...".

## Transitions

Use transitions to prevent page-by-page fragmentation.

Common transition intents:
- Problem to evidence: "这个问题不是感觉，我们看一组数据。"
- Evidence to cause: "数看完了，接下来要解释为什么。"
- Cause to solution: "根因在这里，方案就不能只补表面。"
- Solution to proof: "方案讲完不算，还是要看验证结果。"
- Proof to ask: "有了这个结果，今天要大家确认的是..."
- Detail to summary: "如果只记一句，就是..."

## Compressed Versions

Every page should have a compressed version for time cuts:
- Keep the title claim.
- Keep one proof point or one caveat.
- Skip examples unless the page is a case page.
- Say where details can be answered in Q&A.

Example:
```markdown
压缩版："只讲结论：试点把处理时间从 3 天降到 2 小时。口径我放在页脚，详细过程如果大家关心，我在 Q&A 展开。"
```

## Evidence Language

When source is present:
- "根据页面中的数据..."
- "按这个统计口径..."
- "和去年同期 / 目标 / 试点前相比..."

When source is missing:
- "当前材料里有一个关键数字，但来源还需要补齐。现场建议把它说成'当前材料显示'，不要说成行业结论。"

When claim is assumed:
- "这里先作为工作假设，不作为已验证结论。"

When page is image-only:
- "这张图片页需要人工确认内容后再写最终逐字稿。基于前后页，它大概率承担的是...，但不要直接照此上场。"

## Opening And Closing

Opening must answer:
- why this topic matters now;
- what the audience will get;
- what decision or action is expected.

Closing must include:
- one remembered sentence;
- decision request or next step;
- Q&A invitation.

Avoid ending with only "谢谢".
