---
description: Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit or optimize an existing skill, run evals to test a skill, or optimize a skill's description for better triggering accuracy.
---

# Skill Creator

A workflow for creating new skills and iteratively improving them.

## Core Loop

1. Decide what the skill should do and roughly how
2. Write a draft of the skill
3. Create test prompts and run them with the skill active
4. Evaluate the results qualitatively (and quantitatively if possible)
5. Rewrite the skill based on feedback
6. Repeat until satisfied
7. Package the final skill

Your job is to figure out where the user is in this process and help them progress.

---

## Step 1: Capture Intent

Start by understanding what the user wants. The current conversation might already contain a workflow to capture (e.g., "turn this into a skill"). If so, extract from conversation history first.

Questions to answer:
1. What should this skill enable the AI to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases? (Skills with objectively verifiable outputs benefit from test cases; subjective outputs often don't need them.)

## Step 2: Interview and Research

Proactively ask about edge cases, input/output formats, example files, success criteria, and dependencies. Wait to write test prompts until this part is ironed out.

## Step 3: Write the SKILL.md

Fill in these components:

- **name**: Skill identifier
- **description**: When to trigger, what it does. This is the primary triggering mechanism — include both what the skill does AND specific contexts for when to use it. Make descriptions a little "pushy" to combat undertriggering. E.g., instead of "How to build a dashboard", write "How to build a dashboard. Use this skill whenever the user mentions dashboards, data visualization, or wants to display any kind of data."
- **the rest of the skill body**

### Skill Anatomy

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) — Always in context (~100 words)
2. **SKILL.md body** — In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** — As needed (unlimited, scripts can execute without loading)

Key patterns:
- Keep SKILL.md under 500 lines; if approaching this limit, add hierarchy with clear pointers
- Reference files clearly from SKILL.md with guidance on when to read them
- For large reference files (>300 lines), include a table of contents

### Writing Patterns

Prefer using the imperative form in instructions.

**Defining output formats:**
```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**Examples pattern:**
```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

### Writing Style

Explain to the model **why** things are important instead of heavy-handed MUSTs. Use theory of mind. Start by writing a draft, then look at it with fresh eyes and improve.

If you find yourself writing ALWAYS or NEVER in all caps, or using super rigid structures, that's a yellow flag — reframe and explain the reasoning so the model understands why the thing is important.

## Step 4: Test Cases

After writing the skill draft, come up with 2-3 realistic test prompts — the kind of thing a real user would actually say. Share with the user for confirmation.

Save test cases to `evals/evals.json`:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

## Step 5: Run Test Cases

For each test case, read the skill's SKILL.md, then follow its instructions to accomplish the test prompt. Do them one at a time.

Organize results in `<skill-name>-workspace/` as sibling to the skill directory:
```
<skill-name>-workspace/
├── iteration-1/
│   ├── eval-0/
│   │   └── outputs/
│   └── eval-1/
│       └── outputs/
└── iteration-2/
    └── ...
```

For each test case, present the prompt and the output directly. If the output is a file, save it and tell the user where it is. Ask for feedback: "How does this look? Anything you'd change?"

## Step 6: Improve the Skill

Based on feedback:

1. **Generalize from the feedback.** The skill will be used across many different prompts. Don't overfit to test examples. Rather than fiddly changes or oppressively constrictive MUSTs, try different metaphors or patterns.

2. **Keep the prompt lean.** Remove things that aren't pulling their weight. Read transcripts — if the skill makes the model waste time on unproductive steps, remove those parts.

3. **Explain the why.** Explain reasoning behind instructions so the model understands importance. This is more effective than rigid ALL CAPS rules.

4. **Look for repeated work.** If test cases all independently wrote similar helper scripts, bundle that script into `scripts/` directory.

### Iteration Loop

After improving:
1. Apply improvements to the skill
2. Rerun all test cases into a new `iteration-<N+1>/` directory
3. Present results and ask for feedback
4. Read feedback, improve again, repeat

Keep going until:
- The user says they're happy
- All feedback is empty (everything looks good)
- You're not making meaningful progress

---

## Description Optimization

The description field is the primary triggering mechanism. After creating or improving a skill, offer to optimize the description.

### Generate trigger eval queries

Create 20 eval queries — a mix of should-trigger and should-not-trigger:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

Queries must be realistic. Not abstract requests, but concrete and specific with detail (file paths, personal context, column names, URLs).

**Bad:** `"Format this data"`, `"Extract text from PDF"`
**Good:** `"ok so my boss just sent me this xlsx file called 'Q4 sales final FINAL v2.xlsx' and she wants me to add a column that shows the profit margin as a percentage"`

For **should-trigger** queries (8-10): different phrasings of same intent, cases where user doesn't name the skill explicitly but clearly needs it.

For **should-not-trigger** queries (8-10): near-misses that share keywords but need something different. Don't make them obviously irrelevant.

### Review with user

Present the eval set for review. Let user edit queries, toggle should-trigger, add/remove entries.

### Apply the result

Update the skill's SKILL.md frontmatter description. Show user before/after.

---

## Packaging

When the skill is finalized, ensure:
1. SKILL.md has proper YAML frontmatter (name, description)
2. All referenced scripts/resources exist
3. Directory structure is clean
4. Present the final skill directory path to the user for installation
