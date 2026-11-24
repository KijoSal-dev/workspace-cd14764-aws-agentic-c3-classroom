"""
vectrabank_architecture.py - EXERCISE STARTER (Student-Led)
==============================================================
Module 10 Exercise: Plan a Production Deployment Architecture for VectraBank

Create a deployment architecture plan for VectraBank's financial services
multi-agent system. Define runtime configuration, monitoring strategy,
cost estimates, and operational runbooks.

Same planning pattern as the demo (deployment_walkthrough.py),
with additions:
  1. FINANCIAL DOMAIN — VectraBank-specific agents and KBs
  2. OPERATIONAL RUNBOOK (NEW) — deploy, rollback, kill switch, latency
  3. COMPLIANCE REQUIREMENTS — VPC network mode, stricter thresholds
  4. COST OPTIMIZATION — model selection recommendations

Instructions:
  - Follow the demo pattern (deployment_walkthrough.py)
  - Look for TODO 1-8 below
  - Define configs as Python dicts; the provided helper handles deployment
  - Focus on WHAT to configure and WHY
"""

import json
import os
from pathlib import Path
import agentcore_cli
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


# Supporting resources are provisioned separately from the CLI runtime stack.
_RESOURCES = agentcore_cli.load_resources("lesson-10-exercise")
_ROLE_ARN = _RESOURCES["AgentCoreRoleArn"]
_GUARDRAIL_ID = _RESOURCES["GuardrailId"]
_GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "DRAFT")


# ═══════════════════════════════════════════════════════
#  VECTRABANK RUNTIME CONFIGURATION
# ═══════════════════════════════════════════════════════

# TODO 1: Define the AgentCore Runtime configuration
# Hint: Same structure as demo, but:
#   - Use networkMode "PUBLIC" and serverProtocol "HTTP" in this lab
#   - Document private subnets and security groups for a production VPC
#   - Role and guardrail IDs are discovered by the provided helper
#   - Environment variables: 3 KB IDs, state table, audit table, region, log level
VECTRABANK_RUNTIME_CONFIG = {
    "agentRuntimeName": "vectrabank-financial-services",
    "description": "Multi-agent financial services system with RAG, guardrails, and compliance",
    "roleArn": _ROLE_ARN,

    "networkConfiguration": {
        # In production: VPC mode with real subnet/security group IDs.
        # Lab uses PUBLIC mode - no VPC resources provisioned here.
        "networkMode": "PUBLIC",
    },

    "protocolConfiguration": {
        "serverProtocol": "HTTP",
    },


    "guardrailConfiguration": {
        "guardrailIdentifier": _GUARDRAIL_ID,
        "guardrailVersion": _GUARDRAIL_VERSION,
    },

    "environmentVariables": {
        "MARKET_DATA_KB_ID": "KB-MARKET-DATA-001",
        "COMPLIANCE_KB_ID": "KB-COMPLIANCE-002",
        "PRODUCTS_KB_ID": "KB-PRODUCTS-003",
        "STATE_TABLE_NAME": "vectrabank-agent-state",
        "AUDIT_TABLE_NAME": "vectrabank-audit-log",
        "AWS_REGION": os.environ.get("AWS_REGION", "us-east-1"),
        "LOG_LEVEL": "INFO",
        "ENVIRONMENT": "production",
        "ENABLE_XRAY": "true",
    },
}


# ═══════════════════════════════════════════════════════
#  AGENT DEFINITIONS
# ═══════════════════════════════════════════════════════

# TODO 2: Define 4 agents for VectraBank
# Hint: QueryRouter (Nova Lite), MarketDataRetriever (Nova Lite),
#       ComplianceRetriever (Nova Lite), FinancialAdvisor (Claude Sonnet)
#   Each needs: name, model, temperature, role, tools, estimated_tokens, requests_per_day
VECTRABANK_AGENTS = [
    {
        "name": "QueryRouter",
        "model": "amazon.nova-lite-v1:0",
        "temperature": 0.0,
        "role": "Classify incoming financial queries and route to specialist",
        "tools": ["classify_query", "check_priority"],
        "estimated_tokens_per_request": 400,
        "request_per_day": 10000,
    },
    {
        "name": "MarketDataRetriever",
        "model": "amazon.nova-lite-v1:0",
        "temperature": 0.0,
        "role": "Retrieve market data and financial reports from KB",
        "tools": ["retrieve_market_data"],
        "estimated_tokens_per_request": 600,
        "request_per_day": 6000,
    },
    {
        "name": "ComplianceRetriever",
        "model": "amazon.nova-lite-v1:0",
        "temperature": 0.0,
        "role": "Retrieve SEC/FINRA regulations and compliance guidelines from KB",
        "tools": ["retrieve_compliance_docs"],
        "estimated_tokens_per_request": 600,
        "request_per_day": 4000,
    },
    {
        "name": "FinancialAdvisor",
        "model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "temperature": 0.1,
        "role": "Synthesize retrieved data into grounded financial analysis with citations",
        "tools": [],
        "estimated_tokens_per_request": 2500,
        "request_per_day": 10000
    },
]


# ═══════════════════════════════════════════════════════
#  MONITORING STRATEGY
# ═══════════════════════════════════════════════════════

# TODO 3: Define the monitoring dashboard (6 widgets)
# Hint: Total Queries, Latency P50/P99, Error Rate (2% threshold),
#       Guardrail Blocks, RAG Quality (NEW), Kill Switch Status (NEW)

# TODO 4: Define 3 alarms with thresholds
# Hint: HighErrorRate (2%), HighLatencyP99 (8s), GuardrailViolationSpike (50 blocks/5min)

# TODO 5: Define X-Ray tracing config
# Hint: 10% sampling for financial audit, annotations for query_type, agent_name, etc.
VECTRABANK_MONITORING = {
    "dashboard_name": "vectrabank-financial-services",
    "widgets": [
        {"title": "Total Queries", "type": "line", "metric": "AgentCore/Invocations",
        "period": 60, "stat": "Sum"},
        {"title": "Latency P50/P99", "type": "line",
        "metrics": [
            {"name": "AgentCore/Latency", "stat": "p50"},
            {"name": "AgentCore/Latency", "stat": "p99"},
         ], "period": 60},
        {"title": "Error Rate", "type": "number", "metric": "AgentCore/Errors",
        "period": 300, "stat": "Average", "threshold": 0.02},  # 2% for financial
        {"title": "Guardrail Blocks by Policy", "type": "stacked_bar",
        "metrics": [
            {"name": "Guardrail/PIIBlocks", "label": "PII"},
            {"name": "Guardrail/TopicBlocks", "label": "Topic"},
            {"name": "Guardrail/ContentBlocks", "label": "Content"},
        ], "period": 300},
        {"title": "RAG Retrieval Quality", "type": "line",
        "metric": "Custom/AvgRelevanceScore", "period": 300, "stat": "Average"},
        {"title": "Kill Switch Status", "type": "indicator",
        "metric": "Custom/KillSwitchActive", "period": 60},
    ],
    "alarms": [
        {
            "name": "HighErrorRate",
            "metric": "AgentCore/Errors",
            "threshold": 0.02,  # 2% — stricter for financial
            "period": 300,
            "action": "SNS → kill-switch-topic → Lambda disables runtime",
        },
        {
            "name": "HighLatencyP99",
            "metric": "AgentCore/Latency",
            "stat": "p99",
            "threshold": 8.0,  # 8 seconds
            "period": 300,
            "action": "SNS → ops-team-pager",
        },
        {
            "name": "GuardrailViolationSpike",
            "metric": "Guardrail/TotalBlocks",
            "threshold": 50,  # 50 blocks in 5 min = potential attack
            "period": 300,
            "action": "SNS → security-team + rate-limit-increase",
        },
    ],
    "xray_tracing": {
        "enabled": True,
        "sampling_rate": 0.10,  # 10% for financial (higher for audit)
        "annotations": ["query_type", "agent_name", "model_id", "customer_tier"],
    },
}


# ═══════════════════════════════════════════════════════
#  COST ESTIMATION (provided — same as demo)
# ═══════════════════════════════════════════════════════

MODEL_PRICING = {
    "amazon.nova-lite-v1:0": {"input": 0.00006, "output": 0.00024},
    "amazon.nova-pro-v1:0": {"input": 0.0008, "output": 0.0032},
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0": {"input": 0.003, "output": 0.015},
}


def estimate_monthly_costs(agents: list, days: int = 30) -> dict:
    """Estimate monthly costs for VectraBank."""
    costs = {}
    total = 0

    for agent in agents:
        model = agent["model"]
        pricing = MODEL_PRICING.get(model, {"input": 0.001, "output": 0.005})
        tokens = agent["estimated_tokens_per_request"]
        daily_requests = agent["requests_per_day"]

        input_tokens = tokens * 0.6
        output_tokens = tokens * 0.4
        daily_cost = ((input_tokens / 1000) * pricing["input"] +
                      (output_tokens / 1000) * pricing["output"]) * daily_requests
        monthly_cost = daily_cost * days

        costs[agent["name"]] = {
            "model": model, "daily_requests": daily_requests,
            "monthly_cost": round(monthly_cost, 2),
        }
        total += monthly_cost

    # TODO 6: Add infrastructure costs
    # Hint: DynamoDB (2 tables), Knowledge Bases (3 KBs), CloudWatch + X-Ray, VPC
    # Add each as costs["name"] = {"monthly_cost": estimated_cost}
    # Infrastructure costs
    infra = {
        "DynamoDB (2 tables)": 50.0,
        "Knowledge Bases (3 KBs)": 30.0,
        "CloudWatch + X-Ray": 25.0,
        "VPC/Networking": 10.0,
    }
    for name, cost in infra.items():
        costs[name] = {"monthly_cost": cost}
        total += cost
    
    costs["TOTAL"] = {"monthly_cost": round(total, 2)}
    return costs


# ═══════════════════════════════════════════════════════
#  OPERATIONAL RUNBOOK (NEW — not in demo)
# ═══════════════════════════════════════════════════════

# TODO 7: Define 4 operational runbook procedures
# Hint: Each is a dict with "name", "steps" (list of strings), and procedure-specific fields
#   1. Deploy a New Version — test, update guardrail, deploy runtime, smoke test, monitor
#   2. Rollback — identify previous version, update runtime, verify, post-mortem
#   3. Kill Switch Triggered — acknowledge, check audit log, investigate, fix, re-enable
#   4. Latency Investigation — X-Ray map, per-agent latency, identify bottleneck, scale
OPERATIONAL_RUNBOOK = {
    "deploy_new_version": {
        "title": "Deploy a New Version",
        "steps": [
            "1. Run full test suite: python -m pytest tests/ -v --cov",
            "2. Update guardrail if policies changed: aws bedrock create-guardrail-version ...",
            "3. Deploy the updated configuration: python vectrabank_architecture.py (uses AgentCore CLI)",
            "4. Run smoke test against production: python smoke_test.py --count 20",
            "5. Monitor dashboard for 15 minutes — verify error rate < 2%",
            "6. If error rate > 2%, execute rollback procedure immediately",
        ],
    },
    "rollback": {
        "title": "Rollback to Previous Version",
        "steps": [
            "1. Identify previous stable runtime version from deployment log",
            "2. Restore the previous application and configuration, then redeploy through AgentCore CLI",
            "3. Revert guardrail version if changed: reference previous guardrailVersion",
            "4. Run smoke test to verify rollback: python smoke_test.py --count 10",
            "5. Post-mortem: investigate why new version failed, create incident ticket",
        ],
    },
    "kill_switch_triggered": {
        "title": "Kill Switch Triggered — Agent Disabled",
        "steps": [
            "1. Acknowledge alarm in CloudWatch — note trigger time and error details",
            "2. Check audit log for root cause: query type, guardrail policy, error pattern",
            "3. If adversarial attack: enable stricter rate limiting, investigate source IPs",
            "4. If agent malfunction: review recent deployment changes, check model availability",
            "5. Deploy the fix through AgentCore CLI; after verification, restore the access disabled by the kill switch",
            "6. Monitor for 30 minutes post-recovery — verify kill switch doesn't re-trigger",
        ],
    },
    "latency_investigation": {
        "title": "Investigate Latency Spike (P99 > 8s)",
        "steps": [
            "1. Open X-Ray service map — identify which agent/model is the bottleneck",
            "2. Check per-agent latency: Router (<200ms), Retrievers (<1s), Advisor (<3s)",
            "3. If Retriever slow: check KB indexing status, vector store health",
            "4. If Advisor slow: check model throttling, consider model fallback to Nova Pro",
            "5. If Router slow: check for DynamoDB throttling on state table",
            "6. Scale if needed: increase DynamoDB capacity, add retry backoff for throttling",
        ],
    },
}


# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════

def deploy_to_agentcore() -> str:
    """Provided infrastructure; student architecture TODOs remain above."""
    required = ("networkConfiguration", "protocolConfiguration", "environmentVariables")
    if any(key not in VECTRABANK_RUNTIME_CONFIG for key in required) or len(VECTRABANK_AGENTS) != 4:
        raise ValueError("Complete the runtime configuration and four agent definitions before deployment.")
    resources = agentcore_cli.load_resources("lesson-10-exercise")
    config = {**VECTRABANK_RUNTIME_CONFIG,
              "roleArn": resources["AgentCoreRoleArn"],
              "guardrailConfiguration": {
                  "guardrailIdentifier": resources["GuardrailId"],
                  "guardrailVersion": os.environ.get("GUARDRAIL_VERSION", "DRAFT")}}
    return agentcore_cli.deploy(config)


def main():
    print("=" * 70)
    print("  VectraBank Deployment Architecture — Module 10 Exercise")
    print("  Runtime Config + Monitoring + Cost + Operational Runbook")
    print("=" * 70)

    # ── Runtime Configuration ──
    print(f"\n{'━' * 70}")
    print("  1. AgentCore Runtime Configuration")
    print(f"{'━' * 70}")
    cfg = VECTRABANK_RUNTIME_CONFIG
    print(f"  Runtime:  {cfg['agentRuntimeName']}")
    print(f"  Network:  {cfg['networkConfiguration']['networkMode']}")
    print(f"  Note:     Production deploys use VPC mode with private subnets")
    print(f"  Protocol: {cfg['protocolConfiguration']['serverProtocol']}")
    print(f"  Guardrail: {cfg['guardrailConfiguration']['guardrailIdentifier']} "
          f"v{cfg['guardrailConfiguration']['guardrailVersion']}")
    print(f"  Environment Variables:")
    for key, val in cfg["environmentVariables"].items():
        print(f"    {key}: {val}")
    
    print(f"\n{'━' * 70}")
    print("  2. Agent Definitions (4 agents)")
    print(f"{'━' * 70}")
    for agent in VECTRABANK_AGENTS:
        print(f"\n  {agent['name']}:")
        print(f"    Model:       {agent['model']}")
        print(f"    Temperature: {agent['temperature']}")
        print(f"    Role:        {agent['role']}")
        print(f"    Daily reqs:  {agent['requests_per_day']:,}")
    
    print(f"\n{'━' * 70}")
    print("  3. Monitoring Strategy")
    print(f"{'━' * 70}")
    mon = VECTRABANK_MONITORING
    print(f"\n  Dashboard: {mon['dashboard_name']} ({len(mon['widgets'])} widgets)")
    for w in mon["widgets"]:
        print(f"    [{w['type']:12s}] {w['title']}")
    print(f"\n  Alarms ({len(mon['alarms'])}):")
    for a in mon["alarms"]:
        print(f"    {a['name']}: threshold={a['threshold']}, period={a['period']}s")
        print(f"      -> {a['action']}")
    print(f"\n  X-Ray: sampling={mon['xray_tracing']['sampling_rate']*100:.0f}%, "
          f"annotations={', '.join(mon['xray_tracing']['annotations'])}")
    
    print(f"\n{'━' * 70}")
    print("  4. Monthly Cost Estimation (10,000 requests/day)")
    print(f"{'━' * 70}")
    costs = estimate_monthly_costs(VECTRABANK_AGENTS)
    print(f"\n  {'Component':<25s} {'Model':<40s} {'Monthly':>10s}")
    print(f"  {'─' * 75}")
    for name, data in costs.items():
        if name == "TOTAL":
            print(f"  {'─' * 75}")
        model = data.get("model", "—")
        cost = data["monthly_cost"]
        print(f"  {name:<25s} {model:<40s} ${cost:>9.2f}")

    print(f"\n{'━' * 70}")
    print("  5. Operational Runbook (4 procedures)")
    print(f"{'━' * 70}")
    for key, runbook in OPERATIONAL_RUNBOOK.items():
        print(f"\n  {runbook['title']}")
        for step in runbook["steps"]:
            print(f"    {step}")
    
    print(f"\n{'━' * 70}")
    print("  6. Deploy to AgentCore Runtime (AgentCore CLI)")
    print(f"{'━' * 70}")
    print(f"\n  Role ARN:    {_ROLE_ARN}")
    print(f"  Guardrail:   {_GUARDRAIL_ID} (v{_GUARDRAIL_VERSION})")
    print()
    runtime_arn = deploy_to_agentcore()    

    print(f"\n{'━' * 70}")
    print(f"\n  Key Takeaways:")
    print(f"{'━' * 70}")
    print(f"  1. VPC NETWORK MODE — financial services agents stay internal")
    print(f"  2. MULTI-MODEL COST OPTIMIZATION — Lite for routing/retrieval, Sonnet for synthesis")
    print(f"  3. STRICTER THRESHOLDS — 2% error rate for financial compliance")
    print(f"  4. OPERATIONAL RUNBOOK — deploy, rollback, kill switch, latency procedures (NEW)")
    print(f"  5. AUDIT TRAIL — X-Ray at 10% sampling + full guardrail audit log\n")

    deploy_to_agentcore()


if __name__ == "__main__":
    main()
