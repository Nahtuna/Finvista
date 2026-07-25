#!/usr/bin/env python3
"""
FinLens Network Interceptor - HTTP & WebSocket Analysis
Intercept và phân tích network traffic để tìm API endpoints
"""

import asyncio
import json
import websockets
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
from typing import Dict, List, Set
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs


class FinLensNetworkInterceptor:
    """Tool intercept network traffic từ FinLens"""
    
    def __init__(self, base_url: str = "https://finlensquant.vn"):
        self.base_url = base_url
        self.captured_requests = []
        self.captured_responses = []
        self.api_endpoints = set()
        self.websocket_messages = []
        
    def setup_selenium_with_network_logging(self):
        """Setup Selenium với network logging"""
        chrome_options = Options()
        
        # Enable performance logging
        caps = DesiredCapabilities.CHROME
        caps['goog:loggingPrefs'] = {'performance': 'ALL'}
        
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        chrome_options.add_argument('--headless')  # Run headless
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=chrome_options, desired_capabilities=caps)
        return driver
    
    def extract_network_logs(self, driver) -> List[Dict]:
        """Extract network logs từ Chrome DevTools"""
        logs = driver.get_log('performance')
        network_data = []
        
        for entry in logs:
            try:
                log_json = json.loads(entry['message'])['message']
                
                if log_json['method'] == 'Network.requestWillBeSent':
                    request_data = {
                        'url': log_json['params']['request']['url'],
                        'method': log_json['params']['request']['method'],
                        'headers': log_json['params']['request']['headers'],
                        'post_data': log_json['params']['request'].get('postData'),
                        'timestamp': log_json['params']['timestamp']
                    }
                    network_data.append(request_data)
                    
                elif log_json['method'] == 'Network.responseReceived':
                    response_data = {
                        'url': log_json['params']['response']['url'],
                        'status': log_json['params']['response']['status'],
                        'headers': log_json['params']['response']['headers'],
                        'mime_type': log_json['params']['response']['mimeType'],
                        'timestamp': log_json['params']['timestamp']
                    }
                    network_data.append(response_data)
                    
            except (KeyError, json.JSONDecodeError) as e:
                continue
                
        return network_data
    
    def analyze_network_traffic(self, driver, wait_time: int = 30):
        """Phân tích network traffic trong thời gian chờ"""
        print(f"🕵️ Analyzing network traffic for {wait_time} seconds...")
        
        start_time = time.time()
        all_network_data = []
        
        while time.time() - start_time < wait_time:
            time.sleep(2)
            logs = self.extract_network_logs(driver)
            all_network_data.extend(logs)
            
        return all_network_data
    
    def filter_api_endpoints(self, network_data: List[Dict]) -> Dict:
        """Lọc API endpoints từ network data"""
        api_requests = {}
        
        for entry in network_data:
            url = entry.get('url', '')
            
            # Filter cho API endpoints
            if any(pattern in url.lower() for pattern in ['api', 'v1', 'v2', 'graphql', 'ws', 'wss']):
                parsed_url = urlparse(url)
                path = parsed_url.path
                
                if path not in api_requests:
                    api_requests[path] = {
                        'full_url': url,
                        'method': entry.get('method', 'GET'),
                        'count': 1,
                        'sample_request': entry
                    }
                else:
                    api_requests[path]['count'] += 1
                    
        return api_requests
    
    def crawl_and_intercept(self, max_pages: int = 3) -> Dict:
        """Crawl và intercept network traffic"""
        print("🚀 Starting network interception...")
        
        driver = self.setup_selenium_with_network_logging()
        results = {
            'api_endpoints': {},
            'network_logs': [],
            'pages_analyzed': []
        }
        
        try:
            # Visit homepage
            print(f"📍 Visiting: {self.base_url}")
            driver.get(self.base_url)
            
            # Wait for page load
            time.sleep(5)
            
            # Analyze homepage
            homepage_logs = self.analyze_network_traffic(driver, wait_time=15)
            homepage_apis = self.filter_api_endpoints(homepage_logs)
            
            results['api_endpoints']['homepage'] = homepage_apis
            results['network_logs'].extend(homepage_logs)
            results['pages_analyzed'].append(self.base_url)
            
            # Try to find and visit other pages
            try:
                # Look for navigation links
                nav_links = driver.find_elements(By.CSS_SELECTOR, 'a[href]')
                visited_urls = {self.base_url}
                
                for link in nav_links[:max_pages]:
                    try:
                        href = link.get_attribute('href')
                        if href and self.base_url in href and href not in visited_urls:
                            print(f"📍 Visiting: {href}")
                            driver.get(href)
                            time.sleep(3)
                            
                            page_logs = self.analyze_network_traffic(driver, wait_time=10)
                            page_apis = self.filter_api_endpoints(page_logs)
                            
                            results['api_endpoints'][href] = page_apis
                            results['network_logs'].extend(page_logs)
                            results['pages_analyzed'].append(href)
                            visited_urls.add(href)
                            
                    except Exception as e:
                        print(f"❌ Error visiting link: {e}")
                        continue
                        
            except Exception as e:
                print(f"❌ Error finding navigation links: {e}")
                
        finally:
            driver.quit()
            
        return results
    
    async def analyze_websocket(self, ws_url: str = "wss://finlensquant.vn/ws"):
        """Phân tích WebSocket connection"""
        print(f"🔌 Connecting to WebSocket: {ws_url}")
        
        messages = []
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("✅ WebSocket connected")
                
                # Listen for messages
                timeout = 30
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        messages.append({
                            'direction': 'server_to_client',
                            'timestamp': time.time(),
                            'data': message
                        })
                        print(f"📨 Received: {message[:100]}...")
                        
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        try:
                            await websocket.ping()
                        except:
                            break
                            
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            
        return messages
    
    def generate_report(self, results: Dict) -> str:
        """Tạo báo cáo phân tích network"""
        report = []
        report.append("# FinLens Network Analysis Report\n")
        report.append(f"**Analysis Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # API Endpoints Summary
        report.append("## API Endpoints Discovered\n")
        
        all_apis = {}
        for page, apis in results.get('api_endpoints', {}).items():
            for path, data in apis.items():
                if path not in all_apis:
                    all_apis[path] = data
                else:
                    all_apis[path]['count'] += data['count']
        
        if all_apis:
            for path, data in sorted(all_apis.items(), key=lambda x: x[1]['count'], reverse=True):
                report.append(f"### `{data['method']} {path}`\n")
                report.append(f"- **Count**: {data['count']}\n")
                report.append(f"- **Full URL**: `{data['full_url']}`\n")
                report.append("\n")
        else:
            report.append("No API endpoints discovered in network traffic.\n")
            report.append("This might indicate:\n")
            report.append("- APIs are loaded after user authentication\n")
            report.append("- APIs are called via WebSocket only\n")
            report.append("- APIs use dynamic endpoints\n")
        
        # Pages Analyzed
        report.append("## Pages Analyzed\n")
        for page in results.get('pages_analyzed', []):
            report.append(f"- {page}\n")
        
        return '\n'.join(report)


async def main():
    """Main function"""
    interceptor = FinLensNetworkInterceptor()
    
    print("=" * 60)
    print("FINLENS NETWORK INTERCEPTOR")
    print("=" * 60)
    
    # HTTP/HTTPS Analysis
    results = interceptor.crawl_and_intercept(max_pages=3)
    
    # Generate report
    report = interceptor.generate_report(results)
    
    report_path = Path(__file__).parent.parent.parent / "docs" / "research" / "finlens_network_analysis_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Network report saved to: {report_path}")
    
    # Save raw data
    json_path = report_path.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Raw network data saved to: {json_path}")
    
    # WebSocket Analysis (optional - requires authentication)
    print("\n" + "=" * 60)
    print("WEBSOCKET ANALYSIS")
    print("=" * 60)
    print("Note: WebSocket analysis requires authentication.")
    print("Skipping for now - can be run separately with valid credentials.")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
