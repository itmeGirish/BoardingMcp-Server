# SKILL: draft-benchmark

Use when: user asks to run draft pipeline benchmarks, fill Draft_test.xlsx, compare with ChatGPT-5.4, or analyze draft errors.

## Instructions for Claude

When this skill is invoked, follow these steps ONE BY ONE:

### Step 1: Run Pipeline on Each Scenario (Fill "Draft Agent" Column C)

For each of the 10 scenarios in `docs/Draft_test.xlsx` column B:

1. Read the scenario text from the Excel file using openpyxl
2. Run the drafting pipeline:
   ```python
   import asyncio, openpyxl, sys, time
   from pathlib import Path
   sys.path.insert(0, str(Path("c:/Girish/Fundamental_Projects/ActionAi/Agent_steer_backend/BoardingMcp-Server")))
   from app.agents.drafting_agents.drafting_graph import get_drafting_graph

   graph = get_drafting_graph()
   result = await graph.ainvoke({"user_request": scenario_text})
   ```
3. Extract draft text from result:
   - Try `result["final_draft"]["draft_artifacts"][0]["text"]` first
   - Fallback to `result["draft"]["draft_artifacts"][0]["text"]`
4. Write the draft text into column C of that row
5. Save Excel after each scenario
6. Print: scenario number, word count, time taken
7. Move to next scenario

Do this ONE scenario at a time. Do NOT batch. Save after each one.

### Step 2: Error Analysis + Compare (Fill Columns E and F)

After all 10 drafts are filled, for each scenario:

1. Read column C (Draft Agent) and column D (ChatGPT-5.4) from the Excel
2. Run error analysis on BOTH drafts using `research/run_draft_benchmark.py --compare` OR manually check:

**Error Categories to Check:**

| Category | Severity | What to Look For |
|----------|----------|------------------|
| Fabrication | CRITICAL (-2.0) | Invented AIR/SCC/ILR citations, fake annexures for documents not in input, invented events/dates |
| Wrong Statute | CRITICAL (-2.0) | Indian Evidence Act 1872 (repealed→BSA 2023), CrPC 1973 (repealed→BNSS 2023), IPC (repealed→BNS 2023), phantom S.27A SRA |
| Missing Section | HIGH (-1.0) | No verification clause, no prayer, no jurisdiction, no cause of action, no valuation, no court fee |
| Legal Error | HIGH/MEDIUM (-1.0/-0.5) | Limitation anchored to notice date, pendente lite cites S.34 CPC (should be Order XX Rule 11), facts-law section mixing, "and/or" usage |
| Placeholder Excess | MEDIUM (-0.5) | More than 15 `{{PLACEHOLDER}}` in one draft |
| Structural | MEDIUM/LOW (-0.5/-0.25) | Missing paragraph numbers, non-continuous numbering, no continuous numbering through document |

**Scoring:** Start at 10.0, deduct per severity above. Min 0, max 10.

3. Write into column E ("Compare"):
   ```
   Winner: [pipeline/chatgpt] ([score diff])
   Pipeline: [score]/10 ([word_count]w, [placeholder_count] placeholders)
   ChatGPT: [score]/10 ([word_count]w, [placeholder_count] placeholders)
   ```

4. Write into column F ("Improvements") — list every pipeline error:
   ```
   [CRITICAL] Fabricated citation: AIR 2019 SC 456
   [HIGH] Missing: cause of action section
   [MEDIUM] Pendente lite cites S.34 CPC instead of Order XX Rule 11
   [MISSING] Sections present in ChatGPT but not pipeline: schedule of property
   ```

5. Save Excel after each scenario comparison

### Step 3: Print Summary

After all 10 are compared, print:
- Average score: Pipeline vs ChatGPT
- Win count: Pipeline X | ChatGPT Y
- Top 3 error categories hurting pipeline (by frequency)
- Which scenarios pipeline loses worst on

## Key Files

- Excel: `docs/Draft_test.xlsx` (columns: s.no, Civil Draft Scenarios, Draft Agent, Chatgpt-5.4, Compare, Improvements)
- Pipeline: `app/agents/drafting_agents/drafting_graph.py` → `get_drafting_graph()`
- Runner script: `research/run_draft_benchmark.py` (--draft or --compare mode)
- Reports saved to: `research/output/`

## Running Via Script (Alternative)

```bash
# Fill Draft Agent column
agent_steer/Scripts/python.exe research/run_draft_benchmark.py --draft

# Compare + fill Compare and Improvements columns
agent_steer/Scripts/python.exe research/run_draft_benchmark.py --compare
```
