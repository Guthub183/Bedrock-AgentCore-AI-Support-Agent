# Customer Support AI Agent — Project Reflection

## 1. Design Decision: Architectural Modularity via Model Context Protocol (MCP)

A core architectural decision in this project was delegating tool management and invocation to Amazon Bedrock AgentCore Gateway over the Model Context Protocol (MCP), rather than hardcoding Lambda SDK clients into the runtime. 

By registering `order-tracker` (via an API Gateway REST proxy) and `refund-processor` (via direct Lambda invocation) as gateway targets, the agent dynamically discovers tool schemas at runtime using `MCPClient`. This establishes clear separation of concerns: downstream Lambda schemas and API endpoints can evolve or be redeployed without requiring updates to the core agent application or system prompt. Furthermore, tool execution permissions remain encapsulated within the Bedrock Gateway IAM role, adhering to the principle of least privilege.

---

## 2. Challenges Encountered & Solutions

### Asynchronous Long-Term Memory Extraction
During cross-session testing (Test 4), the agent initially failed to recall customer attributes across separate session IDs. Investigating Bedrock AgentCore Memory revealed that entity extraction from raw conversation turns (`create_event`) occurs asynchronously via background foundation models, requiring approximately 15–30 seconds before semantic facts and user preferences populate their respective namespaces (`cs_agent/{actorId}/facts` and `cs_agent/{actorId}/preferences`).

**Solution**: We updated our evaluation workflow to incorporate a brief delay between conversation turns, and configured `MemoryHook` to resolve actor-specific namespace templates dynamically, allowing robust recall once background indexing completed.

---

## 3. Production Considerations & Future Enhancements

To deploy this customer support agent to an enterprise production environment, we would implement two key enhancements:

1. **OAuth 2.0 / OIDC Inbound Authentication**: Replace the current open authentication mode with JSON Web Token (JWT) verification integrated with Amazon Cognito. This ensures customer identity claims (`sub`, `customer_id`) are cryptographically verified and propagated directly to downstream API Gateway targets to enforce strict multi-tenant data isolation.
2. **Human-in-the-Loop Safeguards**: While order status queries are idempotent, financial operations like `initiate_refund` carry real monetary impact. In production, refunds exceeding an automated threshold (e.g., $100) should pause execution and route to a human supervisor for manual approval.
