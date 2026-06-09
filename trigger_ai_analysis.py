# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import os

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.services.ai_committee_service import AICommitteeService

async def main():
    symbol = "CDGC2601"
    print(f"🚀 Starting Deep AI Analysis for {symbol}...")
    
    service = AICommitteeService()
    result = await service.analyze_opportunity(symbol)
    
    if result.get("status") == "rejected":
        print(f"❌ Analysis REJECTED at Layer {result.get('layer')}")
        print(f"Reason: {result.get('reason')}")
        return

    print("\n" + "="*80)
    print(f"🏆 FINAL DECISION FOR {symbol}")
    print("="*80)
    decision = result.get("decision", {})
    print(f"📢 ACTION: {decision.get('decision')}")
    print(f"🎯 CONFIDENCE: {decision.get('confidence_score')}%")
    print(f"📝 RATIONALE: {decision.get('rationale_summary')}")
    print(f"⚠️ RISKS: {', '.join(decision.get('risk_warnings', []))}")
    
    reports = result.get("committee_reports", {})
    
    print("\n" + "="*80)
    print("📰 CORPORATE INTELLIGENCE (MACRO AGENT)")
    print("="*80)
    print(reports.get("macro", "No macro data"))

    print("\n" + "="*80)
    print("🤖 AI COMMITTEE DEBATE HIGHLIGHTS")
    print("="*80)
    print(reports.get("debate", "No debate data"))

if __name__ == "__main__":
    asyncio.run(main())
