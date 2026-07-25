#!/usr/bin/env python3
"""
FinLens JS Bundle Analyzer - Extract API endpoints from JavaScript bundles
Phân tích các file JavaScript đã bundle để tìm API endpoints
"""

import requests
import re
import json
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Set
from pathlib import Path
import time


class FinLensJSBundleAnalyzer:
    """Tool phân tích JavaScript bundles để tìm API endpoints"""
    
    def __init__(self, base_url: str = "https://finlensquant.vn"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.js_bundles = []
        self.api_endpoints = set()
        self.websocket_endpoints = set()
        
    def fetch_page_and_extract_bundles(self, url: str) -> List[str]:
        """Fetch trang và extract JavaScript bundles"""
        print(f"📄 Fetching: {url}")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            scripts = [script.get('src', '') for script in soup.find_all('script', src=True)]
            
            # Filter for JS bundles (exclude external CDNs)
            bundles = []
            for script in scripts:
                if any(pattern in script for pattern in ['/_next/static', '/static', '/assets', '/js']):
                    full_url = urljoin(self.base_url, script)
                    bundles.append(full_url)
                    
            return bundles
            
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return []
    
    def analyze_js_bundle(self, bundle_url: str) -> Dict:
        """Phân tích một JS bundle để tìm API endpoints"""
        print(f"🔍 Analyzing bundle: {bundle_url}")
        
        try:
            response = self.session.get(bundle_url, timeout=15)
            response.raise_for_status()
            
            js_content = response.text
            
            # Patterns để tìm API endpoints
            patterns = {
                'api_calls': [
                    r'["\']https?://[^"\']*(?:api|v1|v2)[^"\']*["\']',
                    r'["\']/api/[^"\']*["\']',
                    r'["\']/v[12]/[^"\']*["\']',
                    r'["\']/graphql["\']',
                ],
                'fetch_calls': [
                    r'fetch\(["\']([^"\']+)["\']',
                    r'fetch\(`([^`]+)`\)',
                ],
                'axios_calls': [
                    r'axios\.[get|post|put|delete|patch]+\(["\']([^"\']+)["\']',
                    r'axios\(["\']([^"\']+)["\']',
                ],
                'websocket_urls': [
                    r'["\']wss?://[^"\']*["\']',
                    r'new WebSocket\(["\']([^"\']+)["\']',
                ],
                'base_urls': [
                    r'BASE_URL["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    r'API_URL["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    r'NEXT_PUBLIC_API["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                ]
            }
            
            findings = {
                'bundle_url': bundle_url,
                'size': len(js_content),
                'api_endpoints': set(),
                'websocket_endpoints': set(),
                'base_urls': set(),
                'fetch_patterns': set(),
                'axios_patterns': set()
            }
            
            # Extract patterns
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    matches = re.findall(pattern, js_content, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0] if match[0] else match[1] if len(match) > 1 else match[0]
                        
                        if match:
                            if category == 'websocket_urls':
                                findings['websocket_endpoints'].add(match)
                            elif category == 'base_urls':
                                findings['base_urls'].add(match)
                            elif category in ['fetch_calls', 'axios_calls']:
                                findings['fetch_patterns'].add(match)
                            else:
                                # Filter for API-like URLs
                                if any(api_keyword in match.lower() for api_keyword in ['api', 'v1', 'v2', 'graphql']):
                                    findings['api_endpoints'].add(match)
            
            return findings
            
        except Exception as e:
            print(f"❌ Error analyzing bundle {bundle_url}: {e}")
            return {'bundle_url': bundle_url, 'error': str(e)}
    
    def analyze_all_bundles(self, max_bundles: int = 20) -> Dict:
        """Phân tích tất cả JS bundles"""
        print("🚀 Starting JS bundle analysis...")
        
        results = {
            'bundles_analyzed': [],
            'all_api_endpoints': set(),
            'all_websocket_endpoints': set(),
            'all_base_urls': set(),
            'summary': {}
        }
        
        # Get bundles from homepage
        bundles = self.fetch_page_and_extract_bundles(self.base_url)
        
        print(f"📦 Found {len(bundles)} JS bundles")
        
        # Analyze each bundle
        for i, bundle_url in enumerate(bundles[:max_bundles]):
            time.sleep(0.5)  # Rate limiting
            findings = self.analyze_js_bundle(bundle_url)
            results['bundles_analyzed'].append(findings)
            
            # Aggregate findings
            if 'error' not in findings:
                results['all_api_endpoints'].update(findings.get('api_endpoints', set()))
                results['all_websocket_endpoints'].update(findings.get('websocket_endpoints', set()))
                results['all_base_urls'].update(findings.get('base_urls', set()))
        
        # Convert sets to lists for JSON serialization
        results['all_api_endpoints'] = list(results['all_api_endpoints'])
        results['all_websocket_endpoints'] = list(results['all_websocket_endpoints'])
        results['all_base_urls'] = list(results['all_base_urls'])
        
        # Summary
        results['summary'] = {
            'total_bundles': len(bundles),
            'analyzed_bundles': len(results['bundles_analyzed']),
            'unique_api_endpoints': len(results['all_api_endpoints']),
            'unique_websocket_endpoints': len(results['all_websocket_endpoints']),
            'unique_base_urls': len(results['all_base_urls'])
        }
        
        return results
    
    def categorize_endpoints(self, endpoints: List[str]) -> Dict[str, List[str]]:
        """Phân loại endpoints theo chức năng"""
        categories = {
            'authentication': [],
            'cw_data': [],
            'market_data': [],
            'user_data': [],
            'portfolio': [],
            'subscription': [],
            'other': []
        }
        
        for endpoint in endpoints:
            endpoint_lower = endpoint.lower()
            
            if any(keyword in endpoint_lower for keyword in ['auth', 'login', 'register', 'token', 'logout']):
                categories['authentication'].append(endpoint)
            elif any(keyword in endpoint_lower for keyword in ['cw', 'warrant', 'option']):
                categories['cw_data'].append(endpoint)
            elif any(keyword in endpoint_lower for keyword in ['market', 'stock', 'price', 'index']):
                categories['market_data'].append(endpoint)
            elif any(keyword in endpoint_lower for keyword in ['user', 'profile', 'account']):
                categories['user_data'].append(endpoint)
            elif any(keyword in endpoint_lower for keyword in ['portfolio', 'position', 'holding']):
                categories['portfolio'].append(endpoint)
            elif any(keyword in endpoint_lower for keyword in ['sub', 'plan', 'payment', 'upgrade']):
                categories['subscription'].append(endpoint)
            else:
                categories['other'].append(endpoint)
        
        return categories
    
    def generate_report(self, results: Dict) -> str:
        """Tạo báo cáo phân tích"""
        report = []
        report.append("# FinLens JS Bundle Analysis Report\n")
        report.append(f"**Analysis Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Summary
        summary = results.get('summary', {})
        report.append("## Summary\n")
        report.append(f"- **Total Bundles Found**: {summary.get('total_bundles', 0)}\n")
        report.append(f"- **Bundles Analyzed**: {summary.get('analyzed_bundles', 0)}\n")
        report.append(f"- **Unique API Endpoints**: {summary.get('unique_api_endpoints', 0)}\n")
        report.append(f"- **Unique WebSocket Endpoints**: {summary.get('unique_websocket_endpoints', 0)}\n")
        report.append(f"- **Unique Base URLs**: {summary.get('unique_base_urls', 0)}\n")
        
        # Base URLs
        if results.get('all_base_urls'):
            report.append("\n## Base URLs Found\n")
            for base_url in results['all_base_urls']:
                report.append(f"- `{base_url}`\n")
        
        # WebSocket Endpoints
        if results.get('all_websocket_endpoints'):
            report.append("\n## WebSocket Endpoints\n")
            for ws_url in results['all_websocket_endpoints']:
                report.append(f"- `{ws_url}`\n")
        
        # API Endpoints - Categorized
        if results.get('all_api_endpoints'):
            categorized = self.categorize_endpoints(results['all_api_endpoints'])
            
            report.append("\n## API Endpoints by Category\n")
            
            for category, endpoints in categorized.items():
                if endpoints:
                    report.append(f"### {category.title()}\n")
                    for endpoint in endpoints:
                        report.append(f"- `{endpoint}`\n")
                    report.append("\n")
        
        # Detailed Bundle Analysis
        report.append("## Detailed Bundle Analysis\n")
        for bundle in results.get('bundles_analyzed', [])[:10]:  # Limit to first 10
            if 'error' not in bundle:
                report.append(f"### {bundle['bundle_url']}\n")
                report.append(f"- **Size**: {bundle['size']:,} bytes\n")
                if bundle.get('api_endpoints'):
                    report.append(f"- **API Endpoints**: {len(bundle['api_endpoints'])}\n")
                if bundle.get('websocket_endpoints'):
                    report.append(f"- **WebSocket Endpoints**: {len(bundle['websocket_endpoints'])}\n")
                report.append("\n")
        
        return '\n'.join(report)


def main():
    """Main function"""
    analyzer = FinLensJSBundleAnalyzer()
    
    print("=" * 60)
    print("FINLENS JS BUNDLE ANALYZER")
    print("=" * 60)
    
    results = analyzer.analyze_all_bundles(max_bundles=30)
    
    # Generate report
    report = analyzer.generate_report(results)
    
    report_path = Path(__file__).parent.parent.parent / "docs" / "research" / "finlens_js_analysis_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {report_path}")
    
    # Save raw data
    json_path = report_path.with_suffix('.json')
    # Convert sets to lists for JSON serialization
    for bundle in results.get('bundles_analyzed', []):
        for key in bundle:
            if isinstance(bundle[key], set):
                bundle[key] = list(bundle[key])
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Raw data saved to: {json_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(report)


if __name__ == "__main__":
    main()
