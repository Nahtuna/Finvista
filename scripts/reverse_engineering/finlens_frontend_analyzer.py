#!/usr/bin/env python3
"""
FinLens Frontend Analyzer - Reverse Engineering Tool
Phân tích cấu trúc frontend, phát hiện framework, API endpoints
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, List, Set
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class FinLensFrontendAnalyzer:
    """Tool phân tích frontend FinLens"""
    
    def __init__(self, base_url: str = "https://finlensquant.vn"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.api_endpoints = set()
        self.frameworks_detected = set()
        self.js_libraries = set()
        self.css_frameworks = set()
        
    def analyze_page(self, url: str) -> Dict:
        """Phân tích một trang cụ thể"""
        print(f"🔍 Analyzing: {url}")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'url': url,
                'status_code': response.status_code,
                'frameworks': self._detect_frameworks(soup, response.text),
                'js_libraries': self._detect_js_libraries(soup),
                'css_frameworks': self._detect_css_frameworks(soup),
                'api_endpoints': self._extract_api_endpoints(soup, response.text),
                'meta_tags': self._extract_meta_tags(soup),
                'scripts': self._extract_scripts(soup),
                'stylesheets': self._extract_stylesheets(soup)
            }
        except Exception as e:
            print(f"❌ Error analyzing {url}: {e}")
            return {'url': url, 'error': str(e)}
    
    def _detect_frameworks(self, soup, html: str) -> List[str]:
        """Phát hiện frontend framework"""
        frameworks = []
        
        # Check React
        if 'react' in html.lower() or 'reactdom' in html.lower():
            frameworks.append('React')
        if '_react' in html or '__REACT__' in html:
            frameworks.append('React (Server-side)')
            
        # Check Vue
        if 'vue' in html.lower() and 'vue.js' not in html.lower():
            frameworks.append('Vue.js')
        if '__vue__' in html or '_vnode' in html:
            frameworks.append('Vue.js (Runtime)')
            
        # Check Next.js
        if '__next' in html or '_next' in html:
            frameworks.append('Next.js')
            
        # Check Nuxt.js
        if '__nuxt' in html or '_nuxt' in html:
            frameworks.append('Nuxt.js')
            
        # Check Angular
        if 'ng-app' in html or '_ng' in html:
            frameworks.append('Angular')
            
        # Check Svelte
        if '__svelte' in html:
            frameworks.append('Svelte')
            
        return frameworks
    
    def _detect_js_libraries(self, soup) -> List[str]:
        """Phát hiện JavaScript libraries"""
        libraries = []
        
        script_tags = soup.find_all('script', src=True)
        for script in script_tags:
            src = script['src'].lower()
            
            if 'chart.js' in src or 'chartjs' in src:
                libraries.append('Chart.js')
            elif 'echarts' in src:
                libraries.append('ECharts')
            elif 'highcharts' in src:
                libraries.append('Highcharts')
            elif 'd3' in src:
                libraries.append('D3.js')
            elif 'recharts' in src:
                libraries.append('Recharts')
            elif 'plotly' in src:
                libraries.append('Plotly')
            elif 'axios' in src:
                libraries.append('Axios')
            elif 'jquery' in src:
                libraries.append('jQuery')
            elif 'lodash' in src:
                libraries.append('Lodash')
            elif 'moment' in src:
                libraries.append('Moment.js')
            elif 'dayjs' in src:
                libraries.append('Day.js')
            elif 'tailwind' in src:
                libraries.append('TailwindCSS (via CDN)')
                
        return list(set(libraries))
    
    def _detect_css_frameworks(self, soup) -> List[str]:
        """Phát hiện CSS frameworks"""
        frameworks = []
        
        link_tags = soup.find_all('link', rel='stylesheet')
        for link in link_tags:
            href = link.get('href', '').lower()
            
            if 'tailwind' in href:
                frameworks.append('TailwindCSS')
            elif 'bootstrap' in href:
                frameworks.append('Bootstrap')
            elif 'bulma' in href:
                frameworks.append('Bulma')
            elif 'material' in href:
                frameworks.append('Material UI')
                
        # Check inline classes
        all_classes = []
        for element in soup.find_all(class_=True):
            all_classes.extend(element['class'])
            
        class_string = ' '.join(all_classes)
        
        # Tailwind pattern detection
        if re.search(r'bg-[a-z]+-\d+', class_string):
            frameworks.append('TailwindCSS (Utility classes)')
            
        return list(set(frameworks))
    
    def _extract_api_endpoints(self, soup, html: str) -> List[str]:
        """Trích xuất API endpoints từ JavaScript"""
        endpoints = set()
        
        # Pattern cho API calls
        patterns = [
            r'["\']https?://[^"\']*(?:api|v1|v2)[^"\']*["\']',
            r'["\']/api/[^"\']*["\']',
            r'["\']/v[12]/[^"\']*["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.[get|post|put|delete]+\(["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                if match and ('api' in match or 'v1' in match or 'v2' in match):
                    endpoints.add(match)
        
        return list(endpoints)
    
    def _extract_meta_tags(self, soup) -> Dict:
        """Trích xuất meta tags"""
        meta = {}
        for tag in soup.find_all('meta'):
            if tag.get('name'):
                meta[tag['name']] = tag.get('content', '')
            elif tag.get('property'):
                meta[tag['property']] = tag.get('content', '')
        return meta
    
    def _extract_scripts(self, soup) -> List[str]:
        """Trích xuất script sources"""
        return [script.get('src', '') for script in soup.find_all('script', src=True)]
    
    def _extract_stylesheets(self, soup) -> List[str]:
        """Trích xuất stylesheet sources"""
        return [link.get('href', '') for link in soup.find_all('link', rel='stylesheet') if link.get('href')]
    
    def crawl_site(self, max_pages: int = 10) -> Dict:
        """Crawl và phân tích toàn bộ site"""
        print(f"🚀 Starting crawl of {self.base_url}")
        
        results = {
            'homepage': self.analyze_page(self.base_url),
            'other_pages': []
        }
        
        # Tìm các trang khác từ homepage
        try:
            homepage_soup = BeautifulSoup(results['homepage'].get('content', ''), 'html.parser')
            links = homepage_soup.find_all('a', href=True)
            
            visited = {self.base_url}
            pages_to_visit = []
            
            for link in links:
                href = link['href']
                full_url = urljoin(self.base_url, href)
                
                # Chỉ crawl internal links
                if urlparse(full_url).netloc == urlparse(self.base_url).netloc:
                    if full_url not in visited and len(pages_to_visit) < max_pages - 1:
                        pages_to_visit.append(full_url)
                        visited.add(full_url)
            
            # Crawl các trang khác
            for url in pages_to_visit[:max_pages - 1]:
                time.sleep(1)  # Rate limiting
                results['other_pages'].append(self.analyze_page(url))
                
        except Exception as e:
            print(f"❌ Error during crawl: {e}")
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Tạo báo cáo phân tích"""
        report = []
        report.append("# FinLens Frontend Analysis Report\n")
        report.append(f"**Base URL**: {self.base_url}\n")
        report.append(f"**Analysis Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Homepage analysis
        if 'homepage' in results and 'error' not in results['homepage']:
            hp = results['homepage']
            report.append("\n## Homepage Analysis\n")
            report.append(f"**Status Code**: {hp.get('status_code')}\n")
            report.append(f"**Frameworks Detected**: {', '.join(hp.get('frameworks', []))}\n")
            report.append(f"**JS Libraries**: {', '.join(hp.get('js_libraries', []))}\n")
            report.append(f"**CSS Frameworks**: {', '.join(hp.get('css_frameworks', []))}\n")
            
            if hp.get('api_endpoints'):
                report.append("\n### API Endpoints Found:\n")
                for endpoint in hp['api_endpoints']:
                    report.append(f"- `{endpoint}`\n")
        
        # Aggregate all findings
        all_frameworks = set()
        all_libraries = set()
        all_endpoints = set()
        
        for page in [results.get('homepage', {})] + results.get('other_pages', []):
            all_frameworks.update(page.get('frameworks', []))
            all_libraries.update(page.get('js_libraries', []))
            all_endpoints.update(page.get('api_endpoints', []))
        
        report.append("\n## Summary\n")
        report.append(f"**Total Frameworks**: {len(all_frameworks)}\n")
        report.append(f"**Total JS Libraries**: {len(all_libraries)}\n")
        report.append(f"**Total API Endpoints**: {len(all_endpoints)}\n")
        
        return '\n'.join(report)


def main():
    """Main function"""
    analyzer = FinLensFrontendAnalyzer()
    
    # Analyze homepage first
    print("=" * 60)
    print("FINLENS FRONTEND ANALYZER")
    print("=" * 60)
    
    results = analyzer.crawl_site(max_pages=5)
    
    # Generate and save report
    report = analyzer.generate_report(results)
    
    report_path = Path(__file__).parent.parent.parent / "docs" / "research" / "finlens_frontend_analysis_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {report_path}")
    
    # Also save raw JSON
    json_path = report_path.with_suffix('.json')
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
