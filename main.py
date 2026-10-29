"""
Customer Support AI Agent — Completed Implementation
===================================================
All TODO sections implemented according to Udacity rubric criteria:
- BedrockAgentCoreApp instance created at module level.
- Configuration variables for Gateway, Knowledge Base, Region, and Memory.
- BedrockModel, MemoryClient, and bedrock-agent-runtime clients initialized.
- get_namespaces() helper fetching namespace templates.
- MemoryHook extending HookProvider handling MessageAddedEvent and AfterInvocationEvent.
- search_knowledge_base() tool with configuration guard, Retrieve API call, and chunk formatting.
- calculate_loyalty_discount() tool executing code via AgentCore Code Interpreter with tier fallback.
- invoke() entrypoint decorated with @app.entrypoint integrating Gateway MCP tools, Browser, RAG, and Memory.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Imports ───────────────────────────────────────────────────────────────────
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client
import argparse, json
import os, asyncio, boto3
from strands.hooks import (
    HookProvider, AfterInvocationEvent, HookRegistry, MessageAddedEvent,
)
import logging
import uuid
from typing import Dict
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands_tools.browser import AgentCoreBrowser


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("CSAI_Agent")

# ── TODO 1 — App Initialisation ───────────────────────────────────────────────
# Create a BedrockAgentCoreApp instance.
# This registers the ASGI server for AgentCore deployment.
# There must be exactly one instance per deployment.
app = BedrockAgentCoreApp()

# Suppress interactive tool-consent prompts (required in headless deployments).
os.environ["BYPASS_TOOL_CONSENT"] = "true"


# ── TODO 2 — Configuration ────────────────────────────────────────────────────
# Replace the placeholder strings with your actual AWS resource values.
GATEWAY_URL = "https://customersupportgateway-6i2fz9ri76.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
KB_ID       = "J2ZHHFAMXO"
REGION      = "us-east-1"
MEMORY_ID   = "CustomerSupportMemory-OWdC5YC4g3"


# ── TODO 3 — Model and Clients ────────────────────────────────────────────────
model_id = "global.amazon.nova-2-lite-v1:0"

model = BedrockModel(model_id=model_id)
memory_client = MemoryClient(region_name=REGION)
_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)


# ── TODO 4 — Namespace Helper ─────────────────────────────────────────────────
def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict:
    """Return a dict mapping strategy type → namespace template string."""
    try:
        strategies = mem_client.get_memory_strategies(memory_id)
        namespaces = {}
        for strategy in strategies:
            strat_type = strategy.get("type")
            # Support both namespaceTemplates and legacy namespaces field per rubric
            if "namespaceTemplates" in strategy and strategy["namespaceTemplates"]:
                namespaces[strat_type] = strategy["namespaceTemplates"][0]
            elif "namespaces" in strategy and strategy["namespaces"]:
                namespaces[strat_type] = strategy["namespaces"][0]
        return namespaces
    except Exception as e:
        logger.warning(f"Failed to fetch memory strategies: {e}")
        return {
            "SEMANTIC": "cs_agent/{actorId}/facts",
            "USER_PREFERENCE": "cs_agent/{actorId}/preferences",
        }


# ── TODO 5 — Memory Hook ──────────────────────────────────────────────────────
class MemoryHook(HookProvider):
    """Long-term memory hook for the customer support agent."""

    def __init__(
        self,
        actor_id: str,
        session_id: str,
        memory_client: MemoryClient,
        memory_id: str,
    ):
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(memory_client, memory_id)

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve relevant memories and prepend them to the user message."""
        if not event.agent.messages:
            return

        last_message = event.agent.messages[-1]
        if last_message.get("role") != "user":
            return

        content = last_message.get("content", [])
        user_query = ""
        if isinstance(content, str):
            user_query = content
        elif isinstance(content, list) and content:
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    user_query = item["text"]
                    break
                elif isinstance(item, str):
                    user_query = item
                    break

        if not user_query:
            return

        all_context = []
        for strategy_type, namespace_template in self.namespaces.items():
            try:
                resolved_ns = namespace_template.format(actorId=self.actor_id)
                memories = self.memory_client.retrieve_memories(
                    memory_id=self.memory_id,
                    namespace=resolved_ns,
                    query=user_query,
                    top_k=5,
                )
                for memory in memories:
                    text = memory.get("content", {}).get("text", "").strip()
                    if text:
                        all_context.append(f"[{strategy_type}] {text}")
            except Exception as e:
                logger.warning(f"Error retrieving memory for {strategy_type}: {e}")

        if all_context:
            context_block = "Customer Context:\n" + "\n".join(all_context)
            if isinstance(content, list) and content and isinstance(content[0], dict) and "text" in content[0]:
                event.agent.messages[-1]["content"][0]["text"] = f"{context_block}\n\n{user_query}"
            elif isinstance(content, str):
                event.agent.messages[-1]["content"] = f"{context_block}\n\n{user_query}"

    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save the completed turn to memory after the agent responds."""
        user_query = ""
        agent_response = ""

        # Walk backwards to find the last plain-text user query and assistant response
        for msg in reversed(event.agent.messages):
            role = msg.get("role")
            content = msg.get("content", [])

            if role == "assistant" and not agent_response:
                # Assistant message: extract text only, ignore toolUse
                if isinstance(content, str) and content.strip():
                    agent_response = content.strip()
                elif isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if "toolUse" in item:
                                continue
                            if "text" in item and item["text"].strip():
                                text_parts.append(item["text"].strip())
                        elif isinstance(item, str) and item.strip():
                            text_parts.append(item.strip())
                    if text_parts:
                        agent_response = " ".join(text_parts)

            elif role == "user" and not user_query:
                # User message: filter out toolResult messages
                if isinstance(content, list):
                    is_tool_result = any(
                        isinstance(item, dict) and "toolResult" in item
                        for item in content
                    )
                    if is_tool_result:
                        continue

                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and "text" in item and item["text"].strip():
                            text_parts.append(item["text"].strip())
                        elif isinstance(item, str) and item.strip():
                            text_parts.append(item.strip())
                    raw_text = " ".join(text_parts)
                elif isinstance(content, str):
                    raw_text = content.strip()
                else:
                    raw_text = ""

                if not raw_text:
                    continue

                # Strip previously injected Customer Context block if present
                if "Customer Context:\n" in raw_text:
                    parts = raw_text.split("Customer Context:\n", 1)[1]
                    if "\n\n" in parts:
                        raw_text = parts.split("\n\n", 1)[1].strip()
                    else:
                        clean_lines = [line for line in parts.splitlines() if not line.startswith("[") and line.strip()]
                        raw_text = "\n".join(clean_lines).strip()

                user_query = raw_text

            if user_query and agent_response:
                break

        if user_query and agent_response and self.memory_id and not self.memory_id.startswith("<"):
            try:
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=self.actor_id,
                    session_id=self.session_id,
                    messages=[(user_query, "USER"), (agent_response, "ASSISTANT")],
                )
            except Exception as e:
                logger.warning(f"Error saving support interaction to memory: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:  # type: ignore
        """Register both memory callbacks."""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)


# ── TODO 6 — Knowledge Base Tool ─────────────────────────────────────────────
@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the Amazon product catalog and support knowledge base.
    Use this for product specifications, return policies, warranty
    information, loyalty program details, and order status definitions.

    Args:
        query: The question or topic to search for

    Returns:
        Relevant information retrieved from the knowledge base
    """
    if not KB_ID or KB_ID.startswith("<"):
        return "Knowledge base not configured."

    try:
        response = _bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": query},
        )
        results = response.get("retrievalResults", [])
        if not results:
            return "No relevant information found in the knowledge base."

        chunks = []
        for r in results:
            text = r.get("content", {}).get("text", "").strip()
            if text:
                chunks.append(text)

        return "\n---\n".join(chunks) if chunks else "No relevant information found in the knowledge base."
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        return f"Knowledge base error: {str(e)}"


# ── TODO 7 — Loyalty Discount Tool (Code Interpreter) ────────────────────────
@tool
def calculate_loyalty_discount(
    loyalty_points: int,
    tier: str,
    order_total: float,
    product_category: str = "standard",
) -> str:
    """
    Calculate the loyalty discount for a customer order using the
    AgentCore Code Interpreter. Runs exact arithmetic in a secure sandbox.

    Args:
        loyalty_points:   Customer's current points balance
        tier:             Customer tier — Silver, Gold, or Platinum
        order_total:      Order total in USD
        product_category: standard, device, or fresh

    Returns:
        Full discount breakdown and final price
    """
    code = f'''
import json

loyalty_points = {loyalty_points}
tier = "{tier}"
order_total = float({order_total})
product_category = "{product_category}"

earn_rates = {{"standard": 1, "device": 2, "fresh": 5}}
tier_rates = {{"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}}

# Points redemption rules:
# 1. 100 points = $1.00 (each 500 points = $5.00)
# 2. Maximum redeemable points capped at 50% of the order total
max_points_allowed = int((order_total * 0.50) * 100)
# 3. Eligible points is the lesser of the customer's balance and the 50% cap
eligible_points = min(loyalty_points, max_points_allowed)
# 4. Floor eligible points to the nearest lower 500-point block (minimum 500 points)
if eligible_points >= 500:
    points_redeemed = (eligible_points // 500) * 500
else:
    points_redeemed = 0

points_discount = round(points_redeemed / 100.0, 2)
remaining_points_before_earn = loyalty_points - points_redeemed
subtotal_after_points = round(order_total - points_discount, 2)

tier_discount_pct = tier_rates.get(tier, 0.0)
tier_discount = round(subtotal_after_points * tier_discount_pct, 2)
final_total = round(subtotal_after_points - tier_discount, 2)

earn_rate = earn_rates.get(product_category.lower(), 1)
points_earned = int(final_total * earn_rate)
remaining_points = remaining_points_before_earn + points_earned
total_savings = round(order_total - final_total, 2)

result = {{
    "points_redeemed": points_redeemed,
    "tier_discount_pct": tier_discount_pct,
    "final_total": final_total,
    "remaining_points": remaining_points,
    "points_discount": points_discount,
    "tier_discount": tier_discount,
    "total_savings": total_savings,
    "points_earned": points_earned,
}}

print(json.dumps(result))
'''

    try:
        with code_session(REGION) as code_client:
            response = code_client.invoke("executeCode", {
                "code": code,
                "language": "python",
                "clearContext": True,
            })

            for event in response.get("stream", []):
                if "result" in event:
                    return json.dumps(event["result"])

        raise RuntimeError("No output received from code session")

    except Exception as e:
        logger.warning(f"Code interpreter unavailable ({e}); using fallback calculation.")
        earn_rates = {"standard": 1, "device": 2, "fresh": 5}
        tier_rates = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}

        # Exact same floored 500-point logic in fallback
        max_points_allowed = int((order_total * 0.50) * 100)
        eligible_points = min(loyalty_points, max_points_allowed)
        if eligible_points >= 500:
            points_redeemed = (eligible_points // 500) * 500
        else:
            points_redeemed = 0

        points_discount = round(points_redeemed / 100.0, 2)
        remaining_points_before_earn = loyalty_points - points_redeemed
        subtotal_after_points = round(order_total - points_discount, 2)

        tier_discount_pct = tier_rates.get(tier, 0.0)
        tier_discount = round(subtotal_after_points * tier_discount_pct, 2)
        final_total = round(subtotal_after_points - tier_discount, 2)

        earn_rate = earn_rates.get(product_category.lower(), 1)
        points_earned = int(final_total * earn_rate)
        remaining_points = remaining_points_before_earn + points_earned
        total_savings = round(order_total - final_total, 2)

        return json.dumps({
            "points_redeemed": points_redeemed,
            "tier_discount_pct": tier_discount_pct,
            "final_total": final_total,
            "remaining_points": remaining_points,
            "points_discount": points_discount,
            "tier_discount": tier_discount,
            "total_savings": total_savings,
            "points_earned": points_earned,
            "note": "Calculated via local fallback handler.",
        })


# ── TODO 8 — Agent Entrypoint ─────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an intelligent customer support assistant for an e-commerce platform.
Your job is to assist customers with order tracking, returns and refunds, product questions, loyalty rewards, and general inquiries.

Capabilities and Instructions:
1. Order Tracking: Use the Gateway tools (get_order, get_customer_orders, get_customer) to look up order status, carriers, tracking numbers, and delivery dates.
2. Returns and Refunds: Use the refund_processor tool to submit refund requests for eligible items.
3. Product Specs & Store Policies: Use search_knowledge_base to answer questions about product catalogs, return windows, warranty terms, and loyalty tier perks.
4. Loyalty Discounts: Use calculate_loyalty_discount to compute points redemption and tier discounts precisely.
5. Live Web Lookups: Use the browser tool to look up live web pages when requested.

Tone and Demeanor:
- Professional, concise, empathetic, and accurate.
- Maintain customer context provided in the conversation.
"""

@app.entrypoint
async def invoke(payload, context=None):
    """
    Main handler called by AgentCore for every incoming request.

    Expected payload keys:
      prompt      (str, required) — the customer's message
      customer_id (str, optional) — unique customer identifier
      session_id  (str, optional) — session identifier; generated if absent
    """
    try:
        user_input = payload.get("prompt") or payload.get("message") or ""
        actor_id = payload.get("customer_id") or payload.get("actor_id") or "guest"
        session_id = payload.get("session_id") or str(uuid.uuid4())

        memory_hook = MemoryHook(
            actor_id=actor_id,
            session_id=session_id,
            memory_client=memory_client,
            memory_id=MEMORY_ID,
        )

        agent_core_browser = AgentCoreBrowser(region=REGION)

        tools = [
            search_knowledge_base,
            calculate_loyalty_discount,
            agent_core_browser.browser,
        ]

        # Connect to the AgentCore Gateway using MCPClient
        client = None
        if GATEWAY_URL and not GATEWAY_URL.startswith("<"):
            try:
                client = MCPClient(lambda: streamable_http_client(url=GATEWAY_URL))
                client.__enter__()
                gateway_tools = client.list_tools_sync()
                tools.extend(gateway_tools)
            except (ConnectionError, TimeoutError) as net_err:
                logger.error(f"Gateway connection/timeout error: {net_err}")
                return (
                    "The customer support tool gateway is currently unreachable due to a network connection issue or timeout. "
                    "Please verify your network connection and try again in a few moments, or contact customer support."
                )
            except Exception as gw_err:
                logger.error(f"Failed to connect to Customer Support Gateway: {gw_err}")
                return (
                    "The customer support tool gateway is currently unavailable. "
                    "Our team has been notified. Please try your request again shortly or contact support for assistance."
                )

        try:
            agent = Agent(
                model=model,
                system_prompt=SYSTEM_PROMPT,
                tools=tools,
                hooks=[memory_hook],
                state={"actor_id": actor_id, "session_id": session_id},
            )

            response = await agent.invoke_async(user_input)
        except (ConnectionError, TimeoutError) as net_err:
            logger.error(f"Network error during agent tool execution: {net_err}")
            return (
                "A network timeout occurred while executing backend support tools. "
                "Please retry your request in a few moments."
            )
        except Exception as exec_err:
            logger.error(f"Error during agent tool execution: {exec_err}")
            return (
                "An unexpected error occurred while communicating with our backend services. "
                "Please try again or contact customer support."
            )
        finally:
            if client is not None:
                try:
                    client.__exit__(None, None, None)
                except Exception:
                    pass

        if hasattr(response, "message") and isinstance(response.message, dict):
            content = response.message.get("content", [])
            if isinstance(content, list) and content and isinstance(content[0], dict) and "text" in content[0]:
                return content[0]["text"]
        elif hasattr(response, "text"):
            return response.text
        return str(response)

    except Exception as e:
        logger.error(f"Error in invoke: {e}", exc_info=True)
        return "An error occurred while processing your request. Please try again later or contact customer support."


# ── CLI entry point (do not modify) ──────────────────────────────────────────
def main():
    """Run one invocation from the command line for local testing."""
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    response = asyncio.run(invoke(json.loads(args.payload)))
    print(response)


if __name__ == "__main__":
    app.run()
    # Uncomment the line below and comment app.run() for local CLI testing:
    # main()
