import asyncio
import json
import time
import os
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

# Ensure main.py can be imported
sys.path.insert(0, r"C:\Users\ksaty\OneDrive\Desktop\Project Al Support Agent\starter")
import main

test_scenarios = [
    {
        "id": "Test 1 — Order Tracking",
        "description": "Checks order ORD-001 status, carrier, tracking number, and delivery date via Gateway order-tracker tool.",
        "payload": {
            "prompt": "Can you track order ORD-001?",
            "customer_id": "CUST-123",
            "session_id": "t1"
        },
        "expected": "shipping status, tracking number TRK987654321, carrier UPS, estimated delivery"
    },
    {
        "id": "Test 2 — Refund Processing",
        "description": "Initiates a return and refund for Kindle Paperwhite (ORD-002) via Gateway refund-processor tool.",
        "payload": {
            "prompt": "I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.",
            "customer_id": "CUST-123",
            "session_id": "t2"
        },
        "expected": "refund ID, APPROVED status, 3-5 business days message"
    },
    {
        "id": "Test 3 — Knowledge Base (RAG)",
        "description": "Retrieves Platinum loyalty tier benefits from Bedrock Knowledge Base.",
        "payload": {
            "prompt": "What are the benefits of the Platinum loyalty tier?",
            "customer_id": "CUST-123",
            "session_id": "t3"
        },
        "expected": "free same-day shipping, 15% discount, priority support"
    },
    {
        "id": "Test 4A — Memory (Introduce Preference)",
        "description": "Session A: Customer introduces name Jane and preference for concise responses.",
        "payload": {
            "prompt": "Hi, I am Jane. I prefer concise responses.",
            "customer_id": "CUST-123",
            "session_id": "s-A"
        },
        "expected": "Acknowledges customer name Jane and communication preference"
    },
    {
        "id": "Test 4B — Memory Recall Across Sessions",
        "description": "Session B: Tests recall of Jane's name and communication preference from AgentCore Memory.",
        "payload": {
            "prompt": "Do you remember my name and communication preference?",
            "customer_id": "CUST-123",
            "session_id": "s-B"
        },
        "expected": "Recalls Jane and preference for concise responses across sessions"
    },
    {
        "id": "Test 5 — Loyalty Discount Calculation",
        "description": "Calculates exact loyalty discount using Code Interpreter sandbox for Gold tier with 4250 points on $150 order.",
        "payload": {
            "prompt": "I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.",
            "customer_id": "CUST-123",
            "session_id": "t5"
        },
        "expected": "points redeemed, tier discount 10%, final total, remaining points"
    },
    {
        "id": "Test 6 — Browser Tool",
        "description": "Navigates to external website via Browser tool and extracts page title.",
        "payload": {
            "prompt": "Go to https://www.amazon.com and tell me the page title.",
            "customer_id": "CUST-123",
            "session_id": "t6"
        },
        "expected": "Page title retrieved from live Amazon.com"
    }
]

async def run_tests():
    print("=" * 70)
    print("STARTING UDACITY AI SUPPORT AGENT RUBRIC TESTS")
    print("=" * 70)
    
    results = []
    
    for i, test in enumerate(test_scenarios, 1):
        print(f"\n[{i}/{len(test_scenarios)}] Running: {test['id']}")
        print(f"Prompt: {test['payload']['prompt']}")
        print("-" * 50)
        
        start_time = time.time()
        try:
            response = await main.invoke(test['payload'])
            duration = time.time() - start_time
            print(f"Response ({duration:.1f}s):\n{response}\n")
            results.append({
                "test": test,
                "response": response,
                "duration": duration,
                "status": "PASS"
            })
        except Exception as e:
            duration = time.time() - start_time
            print(f"ERROR ({duration:.1f}s): {e}\n")
            results.append({
                "test": test,
                "response": str(e),
                "duration": duration,
                "status": "FAIL"
            })
            
        # If between Test 4A and 4B, wait a short moment for memory extraction
        if test["id"] == "Test 4A — Memory (Introduce Preference)":
            print("\nWaiting 20 seconds for AgentCore memory background extraction...\n")
            time.sleep(20)
            
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED!")
    print("=" * 70)
    
    # Save results to a file
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print("Results saved to test_results.json")

if __name__ == "__main__":
    asyncio.run(run_tests())
