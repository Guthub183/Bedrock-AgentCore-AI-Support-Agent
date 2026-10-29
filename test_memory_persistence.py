import main
from unittest.mock import MagicMock

hook = main.MemoryHook('CUST-123', 's-test', MagicMock(), 'test-mem')

# Test: Messages with tool use, tool results, and prepended customer context
mock_event = MagicMock()
mock_agent = MagicMock()
mock_agent.messages = [
    {
        'role': 'user',
        'content': [{'text': "Customer Context:\n[SEMANTIC] The user's name is Jane.\n\nCan you track order ORD-001?"}]
    },
    {
        'role': 'assistant',
        'content': [{'toolUse': {'toolUseId': 'tool-1', 'name': 'order-tracker___get_order', 'input': {'order_id': 'ORD-001'}}}]
    },
    {
        'role': 'user',
        'content': [{'toolResult': {'toolUseId': 'tool-1', 'content': [{'text': '{"status": "SHIPPED"}'}]}}]
    },
    {
        'role': 'assistant',
        'content': [{'text': 'Your order ORD-001 is currently SHIPPED.'}]
    }
]
mock_event.agent = mock_agent

# Call save_support_interaction
hook.save_support_interaction(mock_event)

# Verify create_event arguments
assert hook.memory_client.create_event.called, "create_event was not called!"
call_args = hook.memory_client.create_event.call_args

print("create_event was called with kwargs:")
print("actor_id:", call_args.kwargs['actor_id'])
print("session_id:", call_args.kwargs['session_id'])
print("memory_id:", call_args.kwargs['memory_id'])

persisted_messages = call_args.kwargs['messages']
user_saved, user_role = persisted_messages[0]
asst_saved, asst_role = persisted_messages[1]

print("\nExtracted User Query:", repr(user_saved))
print("Extracted Assistant Response:", repr(asst_saved))

assert user_saved == "Can you track order ORD-001?", f"Failed! Got: {user_saved}"
assert asst_saved == "Your order ORD-001 is currently SHIPPED.", f"Failed! Got: {asst_saved}"
assert user_role == "USER", f"Expected USER role, got: {user_role}"
assert asst_role == "ASSISTANT", f"Expected ASSISTANT role, got: {asst_role}"
assert "toolResult" not in user_saved
assert "Customer Context" not in user_saved

print("\nUNIT TEST VERIFICATION: 100% PASSED!")
print("Tool results were successfully filtered out.")
print("Injected customer context was successfully stripped.")
print("Only pure customer query and pure assistant response are persisted.")
