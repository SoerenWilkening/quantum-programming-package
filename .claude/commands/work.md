You are an orchestrator. Execute the following steps in order.

## Step 1: Find the next open issue

Run `bd ready --json` to get the next unblocked beads issue. If no issues are ready, tell the user and stop.

Extract the issue ID (e.g., `bd-42`) and title from the first result.

Tell the user: "Working on <id>: <title>"

## Step 2: Implement with worker agent

Launch the `worker` agent with this prompt:

> Implement beads issue <id>. Here is the issue data: <paste the JSON from bd ready>

Wait for the worker to finish. Note the worker's agent ID for potential resume.

Note the worker's token usage from the agent result (look for `total_tokens` in the usage metadata).

## Step 3: Review with reviewer agent

If the worker's token usage was **above 300k tokens**, launch the `reviewer` agent with this prompt:

> Review the most recent git commit.
>
> **EXTRA RIGOROUS REVIEW**: The implementation agent used a large amount of context (over 50%), which may indicate the code went through many iterations or is complex. Be extra thorough: read every changed file in full, verify all edge cases, check for leftover debug code or incomplete logic, and ensure test coverage is comprehensive.

Otherwise, launch the `reviewer` agent with the standard prompt:

> Review the most recent git commit.

Wait for the reviewer to finish.

## Step 4: Handle the verdict

Parse the reviewer's response for **PASS** or **FAIL**.

**If FAIL:**
Resume the `worker` agent (using its agent ID) with this prompt:

> The reviewer found issues with your implementation. Fix them and create a new commit.
>
> Reviewer feedback:
> <paste the full reviewer response>

After the worker finishes, go back to **Step 3** (launch reviewer again). Do this at most 3 times. If it still fails after 3 fix attempts, tell the user and stop.

**If PASS:**
Continue to Step 5.

## Step 5: Close the issue

Run `bd close <id> --reason "Implemented and reviewed" --json`

Tell the user: "Closed <id>: <title>"
