# Udacity Nanodegree Project Resubmission Notes

This document provides a direct mapping between each required rubric item and the exact code implementation, test artifact, and evidence file included in this resubmission package.

---

### 1. Deploy an AI Agent to a Cloud Runtime
- **Rubric Requirement:** Provide visible evidence of an `agentcore invoke` command and the agent's response without errors.
- **Code Implementation:**
  - `main.py` initializes `BedrockAgentCoreApp()` at module level (line 53).
  - Main handler `invoke()` decorated with `@app.entrypoint` (line 425).
  - Main module entrypoint configured with `app.run()` (line 527).
- **Proof & Evidence Files:**
  - **`agentcore_invoke_evidence.txt`**: Full terminal session showing `agentcore dev --port 8080` startup and `agentcore invoke --dev '{"prompt": "Can you track order ORD-001?", "customer_id": "CUST-123", "session_id": "cli-test-1"}'` returning order status `SHIPPED`, carrier `UPS`, tracking number `TRK987654321`.
  - **`TEST_RESULTS.md` (Section 1)**: Formatted walkthrough of CLI invocation.

---

### 2. Integrate External Tools Using the Model Context Protocol
- **Rubric Requirement:** Catch connection, timeout, and tool-execution exceptions near the Gateway call; return a concise, user-friendly message identifying the failed operation and suggesting safe next steps without crashing or exposing secrets. Demonstrate successful execution of Target 1 (order-tracker) and Target 2 (refund-processor).
- **Code Implementation:**
  - `main.py` lines 454–500: Wraps Gateway `MCPClient` initialization and tool discovery in dedicated `try/except (ConnectionError, TimeoutError, Exception)` blocks.
  - Catches runtime execution timeouts and returns concise user-facing error guidance without exposing credentials or stack traces.
- **Proof & Evidence Files:**
  - **`gateway_error_handling_evidence.txt`**:
    1. Controlled failure test with unreachable Gateway URL demonstrating safe user response: *"The customer support tool gateway is currently unavailable. Our team has been notified. Please try your request again shortly or contact support for assistance."*
    2. Verified execution logs for Target 1 (`order-tracker___get_order`) and Target 2 (`refund-processor___initiate_refund`).
  - **`test1_order_tracking.txt`**: Target 1 output log.
  - **`test2_refund_processing.txt`**: Target 2 output log.
  - **`TEST_RESULTS.md` (Sections 2, 3, 4)**.

---

### 3. Execute Computational Tasks via a Sandboxed Code Interpreter
- **Rubric Requirement:** Enforce 500-point redemption flooring after capping redemption at 50% of the order total. Test point balances below, at, and above 500-point boundaries, and orders exceeding 50% cap. Both sandbox code string and fallback path must implement this exact logic.
- **Code Implementation:**
  - `main.py` lines 286–405 (`calculate_loyalty_discount`):
    1. `max_points_allowed = int((order_total * 0.50) * 100)` (50% order total cap).
    2. `eligible_points = min(loyalty_points, max_points_allowed)`.
    3. `points_redeemed = (eligible_points // 500) * 500 if eligible_points >= 500 else 0`.
    4. Exact same logic replicated in both Code Interpreter sandbox and fallback function.
    5. Returns dict with `points_redeemed`, `tier_discount_pct`, `final_total`, `remaining_points`.
- **Proof & Evidence Files:**
  - **`loyalty_boundary_test_evidence.txt`**: 8 comprehensive boundary test cases run via Code Interpreter sandbox in `us-east-1`:
    - Below boundary (450 pts, 499 pts) -> 0 pts redeemed.
    - At boundary (500 pts) -> 500 pts redeemed.
    - Above boundary (550 pts, 1499 pts) -> 500 pts, 1000 pts redeemed.
    - 50% cap exact ($50 order, 4000 pts) -> 2500 pts redeemed (50% exact).
    - 50% cap floored ($55 order, 4000 pts) -> 2500 pts redeemed (floored from 2750).
    - Sub-500 order cap ($8 order, 5000 pts) -> 0 pts redeemed (cap is 400 pts).
  - **`test5_loyalty_discount.txt`**: Test 5 output log.
  - **`TEST_RESULTS.md` (Section 7)**.

---

### 4. Implement Cross-Session Agent Memory with Retrieval and Persistence
- **Rubric Requirement:** Persist only the latest plain-text customer query and corresponding assistant answer. Filter out `toolResult` blocks, tool calls, and previously injected `Customer Context:\n...` strings so tool results are never saved as user input.
- **Code Implementation:**
  - `main.py` lines 163–239 (`save_support_interaction`):
    1. Filters user messages to ignore any message containing `toolResult`.
    2. Strips prepended `Customer Context:\n...` header from the genuine user prompt.
    3. Filters assistant messages to ignore `toolUse` blocks and extract plain assistant response.
    4. Calls `memory_client.create_event(..., messages=[(user_query, "USER"), (agent_response, "ASSISTANT")])`.
- **Proof & Evidence Files:**
  - **`memory_persistence_evidence.txt`**: Verified unit test proving `toolResult` and `Customer Context` are stripped before calling `create_event`.
  - **`test4_long_term_memory.txt`**: Live cross-session evaluation logs demonstrating Session A ingestion and Session B recall across distinct sessions.
  - **`TEST_RESULTS.md` (Section 6)**.

---

### 5. Submission Package Contents (`submission.zip`)
- `main.py` — Complete implementation (0 placeholders, all TODOs implemented).
- `REFLECTION.md` — 325-word written reflection covering design decisions, challenges, and production considerations.
- `TEST_RESULTS.md` — Comprehensive test report covering all 6 test scenarios + rubric evidence.
- `RESUBMISSION_NOTES.md` — This mapping document.
- `agentcore_invoke_evidence.txt` — Proof of `agentcore invoke` execution.
- `gateway_error_handling_evidence.txt` — Proof of Gateway error surfacing and Target 1 & 2 logs.
- `loyalty_boundary_test_evidence.txt` — Proof of 8 loyalty discount boundary tests.
- `memory_persistence_evidence.txt` — Proof of clean memory event persistence.
- `cloudwatch_alarm.png` — CloudWatch alarm screenshot.
- `test1_order_tracking.txt` through `test6_browser_tool.txt` — Individual scenario output logs.
- `test_results.json` — Raw test execution JSON data.
- `product_catalog.txt`, `pyproject.toml`, `README.md`, `.bedrock_agentcore.yaml`.
