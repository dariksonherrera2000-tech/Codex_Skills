# PPT / Slides Diagnosis Guide

Use this reference to produce non-destructive revision suggestions for existing PPT/slides. The goal is to improve live-room effectiveness, not to redesign slides.

## Priority Levels

- `must_fix`: likely to harm credibility, decision-making, or timing in the room.
- `should_fix`: materially improves clarity or persuasion, but the talk can proceed.
- `nice_to_have`: polish or optional improvement.

## Diagnosis Checks

### Title Quality

Problem:
- Title is a topic label, such as "市场分析" or "项目进展".

Risk:
- Speaker must explain the conclusion verbally every time; audience cannot skim the story.

Suggestion:
- Rewrite as a claim: "三类客户需求正在从价格转向交付确定性".

### Evidence And Data

Problem:
- Number lacks unit, source, comparison baseline, or time window.

Risk:
- Audience may challenge credibility; speaker may overclaim.

Suggestion:
- Add source, unit, cutoff date, and baseline. If unavailable, downgrade spoken wording.

Claim status values:
- `cited_in_slides`: source or caveat appears in the PPT/slides.
- `present_without_source`: PPT/slides contain a claim or number but no source.
- `user_provided`: user supplied claim outside the PPT/slides.
- `assumed`: inferred by agent and must not be presented as fact.
- `to_verify`: needs confirmation before live use.

### Density

Problem:
- Too many bullets, charts, or unrelated messages on one page.

Risk:
- Speaker reads instead of interprets; audience misses the priority.

Suggestion:
- Choose one primary message, move secondary detail to backup/Q&A, or split page later.

### Logic Flow

Problem:
- Page transition jumps from result to solution without cause, or from feature to ask without proof.

Risk:
- Audience feels sold to instead of led.

Suggestion:
- Add transition language in the script; optionally add a bridge slide later if PPT/slides editing is allowed.

### CTA / Decision Ask

Problem:
- Ending says "thanks" without next action.

Risk:
- Meeting ends without decision, owner, or follow-up.

Suggestion:
- Add explicit ask: approve pilot, align next milestone, provide budget, schedule demo, confirm owner.

### Audience Fit

Problem:
- PPT/slides use internal jargon, technical detail, or vanity metrics for a non-technical/executive/customer audience.

Risk:
- Audience cannot map content to their decision.

Suggestion:
- Translate into business impact, customer impact, risk, cost, speed, or action.

### Visual Evidence (requires the Visual Reading Pass)

These checks are only possible after reading page images; run them for every visually read page.

Problem:
- The chart does not support the title's claim (title says "增长强劲", the line is flat or the axis is truncated to exaggerate).

Risk:
- The sharpest person in the room will attack the gap between claim and picture; credibility loss spreads to the rest of the presentation.

Suggestion:
- Align the spoken claim to what the picture actually shows, or suggest replacing/annotating the chart. In the script, pre-empt: "这张图的坐标轴是从 60 开始的,我先说明一下口径。"

Problem:
- Legend, axis labels, or table numbers unreadable at room distance; or a chart carries 6+ series when the point needs 2.

Risk:
- Audience stops listening while squinting; speaker is forced to read the slide aloud.

Suggestion:
- Script must carry the numbers verbally ("图上小字看不清没关系,关键就一个数:37%"); suggest enlarging or pruning as a `should_fix`.

Problem:
- Screenshot contains sensitive content (real customer names, internal URLs, tokens, unreleased pricing).

Risk:
- Compliance/confidentiality incident in the room or in shared recordings.

Suggestion:
- `must_fix`: blur or replace before presenting; never speak the leaked detail aloud.

### Q&A Exposure

High-risk items:
- Market size
- Financial forecast
- ROI
- Competitor comparison
- Customer logo or quote
- Security, privacy, compliance
- Implementation timeline
- Personal contribution
- Resource request
- Benchmark

For each high-risk page, prepare:
- likely question;
- defensive posture;
- source or caveat;
- fallback answer when data is missing.

## Revision Suggestion Format

```yaml
- page: 6
  issue: ROI number has no source or baseline
  live_room_risk: Customer may challenge whether the saving applies to their process
  suggested_fix: Add calculation口径 and baseline; in script, say "pilot estimate" instead of "guaranteed saving"
  priority: must_fix
  claim_status: present_without_source
```

## Weakest Link Selection

After diagnosing, name only the weakest 1-2 risks:
- A central claim without evidence.
- A page the speaker cannot explain under challenge.
- A missing decision ask.
- A time budget mismatch.
- A scanned/image-only page at a critical story moment.

Do not output a full green checklist.
