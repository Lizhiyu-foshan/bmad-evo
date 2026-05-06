"""
BMAD-EVO v4.0 - Data Collector
增量数据采集执行器

职责: 接收 DataCollectionSpec，根据 query 动态构建搜索 URL，
     通过 web 请求抓取实时数据，返回格式化文本。

设计原则:
  - 不写死任何数据源 URL — 所有 URL 根据 query 动态生成
  - 单源失败不影响其他源
  - 同一次分析中缓存结果避免重复请求
  - 超时保护，不阻塞整体流程
  - 结果格式化为 Markdown，直接可注入角色 prompt
"""

import json
import logging
import re
import time
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus

import requests

from .thinking_chain import DataCollectionSpec
from ..config_loader import get_config

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _build_search_url(query: str) -> str:
    return f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"


def _build_data_page_url(query: str) -> str:
    ql = query.lower()
    if any(kw in ql for kw in ["gold", "xau", "黄金", "贵金属"]):
        return "https://www.kitco.com/gold-price-today-usa/"
    if any(kw in ql for kw in ["silver", "xag", "白银"]):
        return "https://www.kitco.com/silver-price-today-usa/"
    if any(kw in ql for kw in ["crude", "oil", "wti", "brent", "原油", "油价"]):
        return "https://www.oilprice.com/oil-price-charts"
    if any(kw in ql for kw in ["copper", "铜"]):
        return "https://www.kitco.com/copper-price-today-usa/"
    if any(kw in ql for kw in ["cpi", "inflation", "通胀", "物价"]):
        return "https://tradingeconomics.com/united-states/inflation-cpi"
    if any(kw in ql for kw in ["fed", "interest rate", "fomc", "美联储", "利率"]):
        return "https://tradingeconomics.com/united-states/interest-rate"
    if any(kw in ql for kw in ["s&p", "sp500", "标普", "股市"]):
        return "https://tradingeconomics.com/united-states/stock-market"
    if any(kw in ql for kw in ["vix", "波动率", "恐慌"]):
        return "https://tradingeconomics.com/united-states/vix-volatility-index"
    if any(kw in ql for kw in ["dollar index", "dxy", "美元指数"]):
        return "https://tradingeconomics.com/united-states/currency"
    if any(kw in ql for kw in ["natural gas", "lng", "天然气"]):
        return "https://tradingeconomics.com/commodity/natural-gas"
    return ""


class DataCollector:
    """增量数据采集执行器 — 所有 URL 根据 query 动态生成"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(_DEFAULT_HEADERS)
        self._cache: Dict[str, str] = {}
        cfg = get_config()
        tc_cfg = cfg.get("analysis", {}).get("thinking_chain", {})
        dc_cfg = tc_cfg.get("data_collection", {})
        self.timeout = dc_cfg.get("request_timeout", 30)
        self.max_retries = dc_cfg.get("max_retries", 2)
        self.enabled = dc_cfg.get("enabled", True)

    def execute(self, spec: DataCollectionSpec) -> str:
        if not self.enabled:
            return "[数据采集已禁用]"

        if not spec.queries:
            return "[无额外数据采集需求]"

        results: List[str] = []
        results.append(f"### 实时采集数据（来源: {', '.join(spec.sources[:3])}）\n")
        results.append(f"*采集时间: {time.strftime('%Y-%m-%d %H:%M UTC')}*\n")

        success_count = 0
        fail_count = 0

        for query in spec.queries:
            cache_key = query.lower().strip()
            if cache_key in self._cache:
                results.append(self._cache[cache_key])
                success_count += 1
                continue

            raw = None

            for attempt in range(self.max_retries):
                try:
                    raw = self._fetch_query(query)
                    if raw:
                        break
                except Exception as e:
                    logger.warning(
                        f"Data collection attempt {attempt + 1} failed for '{query}': {e}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(1)

            if raw:
                formatted = self._format_result(query, raw)
                results.append(formatted)
                self._cache[cache_key] = formatted
                success_count += 1
            else:
                results.append(f"**{query}**: [采集失败，请角色基于已有数据进行分析]")
                fail_count += 1

        results.append(
            f"\n*采集统计: {success_count} 项成功, {fail_count} 项失败*"
        )

        return "\n".join(results)

    def _fetch_query(self, query: str) -> Optional[str]:
        data_url = _build_data_page_url(query)
        if data_url:
            html = self._call_url(data_url)
            if html:
                extracted = self._extract_numeric_data(html, query)
                if extracted:
                    return extracted

        return self._fetch_via_search(query)

    def _fetch_via_search(self, query: str) -> Optional[str]:
        search_url = _build_search_url(query + " price today" if "price" not in query.lower() else query)
        html = self._call_url(search_url)
        if not html:
            return None
        return self._extract_search_results(html, query)

    def _call_url(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except requests.Timeout:
            logger.warning(f"Timeout fetching {url}")
            return None
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None

    def _extract_numeric_data(self, html: str, query: str) -> Optional[str]:
        ql = query.lower()
        numbers = re.findall(r'[\d,]+\.?\d*', html)
        results = []

        if any(kw in ql for kw in ["gold", "xau", "黄金"]):
            for n in numbers:
                val = float(n.replace(",", ""))
                if 1000 < val < 10000:
                    results.append(f"Gold spot: ${val:,.2f}/oz")
                    break
        elif any(kw in ql for kw in ["silver", "xag", "白银"]):
            for n in numbers:
                val = float(n.replace(",", ""))
                if 20 < val < 150:
                    results.append(f"Silver spot: ${val:,.2f}/oz")
                    break
        elif any(kw in ql for kw in ["oil", "crude", "wti", "brent", "原油"]):
            for n in numbers:
                val = float(n.replace(",", ""))
                if 50 < val < 200:
                    results.append(f"Crude oil: ${val:,.2f}/bbl")
                    break
        elif any(kw in ql for kw in ["copper", "铜"]):
            for n in numbers:
                val = float(n.replace(",", ""))
                if 3 < val < 10:
                    results.append(f"Copper: ${val:,.2f}/lb")
                    break
        elif any(kw in ql for kw in ["natural gas", "lng", "天然气"]):
            for n in numbers:
                val = float(n.replace(",", ""))
                if 1 < val < 20:
                    results.append(f"Natural gas: ${val:,.2f}")
                    break
        elif any(kw in ql for kw in ["cpi", "inflation", "通胀"]):
            pct_nums = re.findall(r'([\d]+\.?\d*)\s*(?:percent|%)', html)
            if pct_nums:
                results.append(f"CPI (latest): {pct_nums[0]}% YoY")
        elif any(kw in ql for kw in ["fed", "interest rate", "利率"]):
            pct_nums = re.findall(r'([\d]+\.?\d*)\s*(?:percent|%)', html)
            if pct_nums:
                results.append(f"Fed Funds Rate: {pct_nums[0]}%")
        elif any(kw in ql for kw in ["s&p", "sp500", "标普"]):
            m = re.search(r'([\d,]+\.?\d*)', html[html.find("S&P"):html.find("S&P")+100] if "S&P" in html else "")
            if m:
                results.append(f"S&P 500: {m.group(1)}")
        elif any(kw in ql for kw in ["vix", "波动率"]):
            pct_nums = re.findall(r'([\d]+\.?\d*)', html)
            for n in pct_nums:
                val = float(n)
                if 10 < val < 50:
                    results.append(f"VIX: {val}")
                    break

        return "; ".join(results) if results else None

    def _extract_search_results(self, html: str, query: str) -> Optional[str]:
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        if not snippets:
            snippets = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)

        if not snippets:
            headlines = re.findall(r'<h[23][^>]*>([^<]+)</h[23]>', html)
            snippets = headlines

        cleaned = []
        for s in snippets[:5]:
            text = re.sub(r'<[^>]+>', '', s).strip()
            if text:
                cleaned.append(text)

        if not cleaned:
            return None

        lines = [f"搜索结果 ({query}):"]
        for i, s in enumerate(cleaned, 1):
            lines.append(f"  {i}. {s}")
        return "\n".join(lines)

    def _format_result(self, query: str, raw: str) -> str:
        return f"**{query}**: {raw}"

    def clear_cache(self):
        self._cache.clear()
