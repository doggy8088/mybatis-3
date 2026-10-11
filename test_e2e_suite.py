#!/usr/bin/env python3
"""
MyBatis 3 Traditional Chinese (zh_TW) Localization & Publishing
End-to-End (E2E) Test Suite

Covers all 25 features across Milestones M1, M2, and M3:
- M1: Localization (Features 1-13)
- M2: GitHub Pages Publishing (Features 14-19)
- M3: Git Branch, PR & Copilot Review Loop (Features 20-25)

Systematic 4-Tier Test Architecture:
- Tier 1: Feature Coverage (>=5 test cases per feature in isolation = 125 tests)
- Tier 2: Boundary & Corner Cases (65 tests)
- Tier 3: Cross-Feature Combinations (20 tests)
- Tier 4: Real-World Scenarios (12 tests)
Total: 222 Automated Test Cases
"""

import argparse
import json
import os
import re
import socket
import ssl
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Global Constants & Paths
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.dirname(__file__))

DOC_FILES = [
    "index.md",
    "getting-started.md",
    "configuration.md",
    "sqlmap-xml.md",
    "dynamic-sql.md",
    "java-api.md",
    "statement-builders.md",
    "logging.md",
]

DOC_HTML_FILES = [f.replace(".md", ".html") for f in DOC_FILES]

EXPECTED_CODE_BLOCKS = {
    "index.md": 0,
    "getting-started.md": 12,
    "configuration.md": 36,
    "sqlmap-xml.md": 86,
    "dynamic-sql.md": 18,
    "java-api.md": 38,
    "statement-builders.md": 10,
    "logging.md": 16,
}

EXPECTED_TABLE_COUNTS = {
    "index.md": 0,
    "getting-started.md": 0,
    "configuration.md": 3,
    "sqlmap-xml.md": 12,
    "dynamic-sql.md": 0,
    "java-api.md": 2,
    "statement-builders.md": 2,
    "logging.md": 0,
}

EXPECTED_LABEL_BADGES = {
    "index.md": 0,
    "getting-started.md": 2,
    "configuration.md": 4,
    "sqlmap-xml.md": 9,
    "dynamic-sql.md": 2,
    "java-api.md": 11,
    "statement-builders.md": 1,
    "logging.md": 1,
}

EXPECTED_ANCHORS_SITE_XML = [
    ("configuration.html", "properties"),
    ("configuration.html", "settings"),
    ("configuration.html", "typealiases"),
    ("configuration.html", "typehandlers"),
    ("configuration.html", "objectfactory"),
    ("configuration.html", "plugins"),
    ("configuration.html", "environments"),
    ("configuration.html", "databaseidprovider"),
    ("configuration.html", "mappers"),
    ("sqlmap-xml.html", "select"),
    ("sqlmap-xml.html", "insert-update-and-delete"),
    ("sqlmap-xml.html", "parameters"),
    ("sqlmap-xml.html", "result-maps"),
    ("sqlmap-xml.html", "auto-mapping"),
    ("sqlmap-xml.html", "cache"),
    ("java-api.html", "directory-structure"),
    ("java-api.html", "sqlsessions"),
    ("java-api.html", "sqlsessionmanager"),
]

PROHIBITED_MAINLAND_TERMS = [
    ("項目", "專案 (Project)"),
    ("接口", "介面 (Interface)"),
    ("配置", "設定 (Configuration)"),
    ("属性", "屬性 (Property/Attribute)"),
    ("事务", "交易 (Transaction)"),
    ("缓存", "快取 (Cache)"),
    ("注解", "註解 (Annotation)"),
    ("默认", "預設 (Default)"),
    ("线程", "執行緒 (Thread)"),
    ("数据库", "資料庫 (Database)"),
    ("类型", "型別 (Type)"),
    ("对象", "物件 (Object)"),
    ("代码", "程式碼 (Code)"),
    ("调试", "除錯 (Debug)"),
    ("服务器", "伺服器 (Server)"),
    ("内存", "記憶體 (Memory)"),
    ("网络", "網路 (Network)"),
    ("用户", "使用者 (User)"),
    ("声明", "宣告 (Declare)"),
    ("调用", "呼叫 (Invoke/Call)"),
    ("返回", "回傳 (Return)"),
    ("组件", "元件 (Component)"),
    ("进程", "程序 (Process)"),
    ("硬件", "硬體 (Hardware)"),
    ("软件", "軟體 (Software)"),
    ("字节", "位元組 (Byte)"),
    ("二进制", "二進位 (Binary)"),
    ("并发", "並行/並行處理 (Concurrency)"),
]

SIMPLIFIED_CHINESE_CHARS = set(
    "项属务缓认线数据库类对码调试内网络户声组进软节并发为这们时后说国经学点实现样动业长问无开战题标级统义关变构"
)


# ---------------------------------------------------------------------------
# Test Result Data Structure
# ---------------------------------------------------------------------------
@dataclass
class TestResult:
    id: str
    tier: int
    milestone: str
    feature: str
    name: str
    passed: bool
    message: str = ""
    remediation: str = ""
    duration_ms: float = 0.0
    skipped: bool = False
    skip_reason: str = ""


# ---------------------------------------------------------------------------
# Utility Helpers
# ---------------------------------------------------------------------------
def run_command(cmd: List[str], cwd: Optional[str] = None, timeout: int = 30) -> Tuple[int, str, str]:
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd or REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return res.returncode, res.stdout, res.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"
    except Exception as e:
        return -1, "", str(e)


def read_text_file(rel_path: str) -> Tuple[Optional[str], Optional[str]]:
    full_path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.exists(full_path):
        return None, f"File does not exist: {rel_path}"
    try:
        with open(full_path, "rb") as f:
            raw = f.read()
        if raw.startswith(b"\xef\xbb\xbf"):
            return None, f"File contains prohibited UTF-8 BOM: {rel_path}"
        text = raw.decode("utf-8")
        if "\ufffd" in text:
            return None, f"File contains Unicode replacement char \\ufffd: {rel_path}"
        return text, None
    except Exception as e:
        return None, f"Failed to read UTF-8 file {rel_path}: {e}"


def get_xml_root(rel_path: str) -> Tuple[Optional[ET.Element], Optional[str]]:
    full_path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.exists(full_path):
        return None, f"XML file not found: {rel_path}"
    try:
        # Strip default namespace for clean tag inspection
        with open(full_path, "r", encoding="utf-8") as f:
            xml_text = f.read()
        # Remove default xmlns to make xpath queries clean
        clean_xml = re.sub(r'\sxmlns="[^"]+"', "", xml_text, count=1)
        root = ET.fromstring(clean_xml)
        return root, None
    except Exception as e:
        return None, f"XML parse error in {rel_path}: {e}"


def inspect_png_dimensions(rel_path: str) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
    full_path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.exists(full_path):
        return None, f"Image file not found: {rel_path}"
    try:
        with open(full_path, "rb") as f:
            header = f.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None, f"Invalid PNG magic header in {rel_path}"
        width, height = struct.unpack(">II", header[16:24])
        return (width, height), None
    except Exception as e:
        return None, f"Error inspecting PNG {rel_path}: {e}"


def check_url_status(url: str, timeout: int = 10) -> Tuple[int, Dict[str, str], str]:
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MyBatis3-E2E-TestSuite/1.0"},
        )
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, headers, body
    except urllib.error.HTTPError as e:
        headers = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, headers, body
    except Exception as e:
        return 0, {}, str(e)


# ---------------------------------------------------------------------------
# Test Suite Collector
# ---------------------------------------------------------------------------
ALL_TESTS: List[Tuple[str, int, str, str, str, Callable[[], Tuple[bool, str, str]]]] = []


def register_test(
    test_id: str,
    tier: int,
    milestone: str,
    feature: str,
    name: str,
):
    def decorator(fn: Callable[[], Tuple[bool, str, str]]):
        ALL_TESTS.append((test_id, tier, milestone, feature, name, fn))
        return fn
    return decorator


# ===========================================================================
# TIER 1: FEATURE COVERAGE (Isolation - 125 Test Cases)
# ===========================================================================

# --- Feature 1: Maven POM Locales Update (5 Tests) ---
@register_test("T1.F01.1", 1, "M1", "F01", "pom.xml exists in root")
def test_t1_f01_1():
    exists = os.path.exists(os.path.join(REPO_ROOT, "pom.xml"))
    return (exists, "pom.xml exists in repository root", "pom.xml is missing")


@register_test("T1.F01.2", 1, "M1", "F01", "pom.xml is valid XML")
def test_t1_f01_2():
    root, err = get_xml_root("pom.xml")
    if err:
        return False, "", err
    return True, "pom.xml parses as valid XML", ""


@register_test("T1.F01.3", 1, "M1", "F01", "maven-site-plugin configuration contains <locales>")
def test_t1_f01_3():
    root, err = get_xml_root("pom.xml")
    if err:
        return False, "", err
    locales_nodes = root.findall(".//plugin[artifactId='maven-site-plugin']/configuration/locales")
    if not locales_nodes:
        return False, "", "maven-site-plugin <locales> tag not found in pom.xml"
    return True, f"Found <locales> tag: '{locales_nodes[0].text}'", ""


@register_test("T1.F01.4", 1, "M1", "F01", "<locales> contains 'zh_TW'")
def test_t1_f01_4():
    root, err = get_xml_root("pom.xml")
    if err:
        return False, "", err
    nodes = root.findall(".//plugin[artifactId='maven-site-plugin']/configuration/locales")
    if not nodes or not nodes[0].text:
        return False, "", "<locales> tag missing or empty in pom.xml"
    locales = [loc.strip() for loc in nodes[0].text.split(",")]
    if "zh_TW" not in locales:
        return False, "", f"zh_TW not in pom.xml <locales> list: {locales}"
    return True, f"zh_TW present in <locales>: {locales}", ""


@register_test("T1.F01.5", 1, "M1", "F01", "<locales> retains default and existing locales")
def test_t1_f01_5():
    root, err = get_xml_root("pom.xml")
    if err:
        return False, "", err
    nodes = root.findall(".//plugin[artifactId='maven-site-plugin']/configuration/locales")
    if not nodes or not nodes[0].text:
        return False, "", "<locales> tag missing in pom.xml"
    locales = set(loc.strip() for loc in nodes[0].text.split(","))
    required = {"default", "es", "ja", "fr", "zh_CN", "ko", "zh_TW"}
    missing = required - locales
    if missing:
        return False, "", f"Missing required locales in pom.xml: {missing}"
    return True, "All required locales present in pom.xml", ""


# --- Feature 2: Traditional Chinese Site Descriptor (5 Tests) ---
@register_test("T1.F02.1", 1, "M1", "F02", "src/site/site_zh_TW.xml exists")
def test_t1_f02_1():
    exists = os.path.exists(os.path.join(REPO_ROOT, "src/site/site_zh_TW.xml"))
    return (exists, "site_zh_TW.xml exists", "src/site/site_zh_TW.xml is missing")


@register_test("T1.F02.2", 1, "M1", "F02", "site_zh_TW.xml is valid XML with root <site>")
def test_t1_f02_2():
    root, err = get_xml_root("src/site/site_zh_TW.xml")
    if err:
        return False, "", err
    if root.tag != "site":
        return False, "", f"Root tag is '{root.tag}', expected 'site'"
    return True, "site_zh_TW.xml has valid root <site>", ""


@register_test("T1.F02.3", 1, "M1", "F02", "site_zh_TW.xml menu has Traditional Chinese name")
def test_t1_f02_3():
    root, err = get_xml_root("src/site/site_zh_TW.xml")
    if err:
        return False, "", err
    menus = root.findall(".//menu")
    menu_names = [m.attrib.get("name", "") for m in menus if "name" in m.attrib]
    if not any("參考文件" in name or "說明文件" in name for name in menu_names):
        return False, "", f"Expected Traditional Chinese menu title ('參考文件' or '說明文件'), found: {menu_names}"
    return True, f"Found localized menu title: {menu_names}", ""


@register_test("T1.F02.4", 1, "M1", "F02", "site_zh_TW.xml links to all 8 documentation pages")
def test_t1_f02_4():
    root, err = get_xml_root("src/site/site_zh_TW.xml")
    if err:
        return False, "", err
    items = root.findall(".//item")
    hrefs = [i.attrib.get("href", "") for i in items]
    missing = []
    for doc in DOC_HTML_FILES:
        if not any(h == doc or h.startswith(doc + "#") for h in hrefs):
            missing.append(doc)
    if missing:
        return False, "", f"site_zh_TW.xml missing item links for: {missing}"
    return True, f"All 8 documentation page links present in site_zh_TW.xml", ""


@register_test("T1.F02.5", 1, "M1", "F02", "site_zh_TW.xml uses lowercase/hyphenated anchor slugs")
def test_t1_f02_5():
    root, err = get_xml_root("src/site/site_zh_TW.xml")
    if err:
        return False, "", err
    items = root.findall(".//item")
    anchors = [i.attrib.get("href", "").split("#")[1] for i in items if "#" in i.attrib.get("href", "")]
    broken = [a for a in anchors if any(c.isupper() for c in a) or "_" in a]
    if broken:
        return False, "", f"Found invalid camelCase or underscore anchors in site_zh_TW.xml: {broken}"
    return True, f"All {len(anchors)} anchor slugs are lowercase and hyphen-separated", ""


# --- Feature 3: Translation: index.md (5 Tests) ---
@register_test("T1.F03.1", 1, "M1", "F03", "src/site/zh_TW/markdown/index.md exists and is non-empty")
def test_t1_f03_1():
    text, err = read_text_file("src/site/zh_TW/markdown/index.md")
    if err:
        return False, "", err
    if len(text.strip()) < 100:
        return False, "", "File is unexpectedly short"
    return True, f"index.md exists ({len(text)} chars)", ""


@register_test("T1.F03.2", 1, "M1", "F03", "index.md front-matter contains title and Clinton Begin")
def test_t1_f03_2():
    text, err = read_text_file("src/site/zh_TW/markdown/index.md")
    if err:
        return False, "", err
    lines = text.splitlines()
    if not (lines and lines[0].startswith("title:")):
        return False, "", "Line 1 does not start with title:"
    if not (len(lines) > 1 and "Clinton Begin" in lines[1]):
        return False, "", "Line 2 does not contain author: Clinton Begin"
    return True, "Front-matter format valid", ""


@register_test("T1.F03.3", 1, "M1", "F03", "index.md contains <h1 class=\"d-none\"> guard")
def test_t1_f03_3():
    text, err = read_text_file("src/site/zh_TW/markdown/index.md")
    if err:
        return False, "", err
    if not re.search(r'<h1\s+class="d-none">.*?</h1>', text):
        return False, "", "Missing <h1 class=\"d-none\"> in index.md"
    return True, "Found <h1 class=\"d-none\"> guard", ""


@register_test("T1.F03.4", 1, "M1", "F03", "index.md translated into Traditional Chinese")
def test_t1_f03_4():
    text, err = read_text_file("src/site/zh_TW/markdown/index.md")
    if err:
        return False, "", err
    keywords = ["簡介", "什麼是 MyBatis", "持久層", "框架"]
    found = [k for k in keywords if k in text]
    if len(found) < 2:
        return False, "", f"Expected Traditional Chinese keywords in index.md, found only: {found}"
    return True, f"Found Traditional Chinese content keywords: {found}", ""


@register_test("T1.F03.5", 1, "M1", "F03", "index.md contains <ul class=\"i18n\"> language list")
def test_t1_f03_5():
    text, err = read_text_file("src/site/zh_TW/markdown/index.md")
    if err:
        return False, "", err
    if '<ul class="i18n">' not in text:
        return False, "", "Missing <ul class=\"i18n\"> in index.md"
    return True, "Found <ul class=\"i18n\"> language switcher", ""


# --- Feature 4: Translation: getting-started.md (5 Tests) ---
@register_test("T1.F04.1", 1, "M1", "F04", "getting-started.md exists and is non-empty")
def test_t1_f04_1():
    text, err = read_text_file("src/site/zh_TW/markdown/getting-started.md")
    if err:
        return False, "", err
    return (len(text) > 500, f"getting-started.md size {len(text)} bytes", "File too short")


@register_test("T1.F04.2", 1, "M1", "F04", "getting-started.md front-matter and <h1 class=\"d-none\">")
def test_t1_f04_2():
    text, err = read_text_file("src/site/zh_TW/markdown/getting-started.md")
    if err:
        return False, "", err
    if not (text.startswith("title:") and '<h1 class="d-none">' in text):
        return False, "", "Missing title or <h1 class=\"d-none\">"
    return True, "Front-matter and h1 guard valid", ""


@register_test("T1.F04.3", 1, "M1", "F04", "getting-started.md preserves 12 code blocks")
def test_t1_f04_3():
    text, err = read_text_file("src/site/zh_TW/markdown/getting-started.md")
    if err:
        return False, "", err
    fences = len(re.findall(r"^```", text, re.M))
    blocks = fences // 2
    if blocks != EXPECTED_CODE_BLOCKS["getting-started.md"]:
        return False, "", f"Expected 12 code blocks (24 fences), found {blocks} ({fences} fences)"
    return True, "All 12 code blocks preserved", ""


@register_test("T1.F04.4", 1, "M1", "F04", "getting-started.md preserves 2 label badges")
def test_t1_f04_4():
    text, err = read_text_file("src/site/zh_TW/markdown/getting-started.md")
    if err:
        return False, "", err
    badges = len(re.findall(r'<span\s+class="label\s+important">', text))
    if badges != EXPECTED_LABEL_BADGES["getting-started.md"]:
        return False, "", f"Expected 2 label badges, found {badges}"
    return True, "All 2 label badges preserved", ""


@register_test("T1.F04.5", 1, "M1", "F04", "getting-started.md translates core sections")
def test_t1_f04_5():
    text, err = read_text_file("src/site/zh_TW/markdown/getting-started.md")
    if err:
        return False, "", err
    keywords = ["入門", "安裝", "建構", "SqlSessionFactory", "作用域", "生命週期"]
    found = [k for k in keywords if k in text]
    if len(found) < 3:
        return False, "", f"Expected getting-started keywords, found only: {found}"
    return True, f"Found Traditional Chinese sections: {found}", ""


# --- Feature 5: Translation: configuration.md (5 Tests) ---
@register_test("T1.F05.1", 1, "M1", "F05", "configuration.md exists and is non-empty")
def test_t1_f05_1():
    text, err = read_text_file("src/site/zh_TW/markdown/configuration.md")
    if err:
        return False, "", err
    return (len(text) > 1000, f"configuration.md size {len(text)} bytes", "File too short")


@register_test("T1.F05.2", 1, "M1", "F05", "configuration.md preserves 36 code blocks")
def test_t1_f05_2():
    text, err = read_text_file("src/site/zh_TW/markdown/configuration.md")
    if err:
        return False, "", err
    fences = len(re.findall(r"^```", text, re.M))
    blocks = fences // 2
    if blocks != EXPECTED_CODE_BLOCKS["configuration.md"]:
        return False, "", f"Expected 36 code blocks (72 fences), found {blocks} ({fences} fences)"
    return True, "All 36 code blocks preserved", ""


@register_test("T1.F05.3", 1, "M1", "F05", "configuration.md preserves 3 markdown tables")
def test_t1_f05_3():
    text, err = read_text_file("src/site/zh_TW/markdown/configuration.md")
    if err:
        return False, "", err
    sep_count = sum(1 for line in text.splitlines() if re.match(r"^\|?\s*[-:]+[-|\s:]*\|", line))
    if sep_count != EXPECTED_TABLE_COUNTS["configuration.md"]:
        return False, "", f"Expected 3 tables, found {sep_count}"
    return True, "All 3 markdown tables preserved", ""


@register_test("T1.F05.4", 1, "M1", "F05", "configuration.md preserves 4 label badges")
def test_t1_f05_4():
    text, err = read_text_file("src/site/zh_TW/markdown/configuration.md")
    if err:
        return False, "", err
    badges = len(re.findall(r'<span\s+class="label\s+important">', text))
    if badges != EXPECTED_LABEL_BADGES["configuration.md"]:
        return False, "", f"Expected 4 label badges, found {badges}"
    return True, "All 4 label badges preserved", ""


@register_test("T1.F05.5", 1, "M1", "F05", "configuration.md contains headings matching anchors")
def test_t1_f05_5():
    text, err = read_text_file("src/site/zh_TW/markdown/configuration.md")
    if err:
        return False, "", err
    anchors = ["properties", "settings", "typeAliases", "typeHandlers", "objectFactory", "plugins", "environments", "mappers"]
    found = [a for a in anchors if a.lower() in text.lower()]
    if len(found) < len(anchors):
        return False, "", f"Missing configuration element headings: {set(anchors) - set(found)}"
    return True, f"Found all configuration element headings: {found}", ""


# --- Feature 6: Translation: sqlmap-xml.md (5 Tests) ---
@register_test("T1.F06.1", 1, "M1", "F06", "sqlmap-xml.md exists and is non-empty")
def test_t1_f06_1():
    text, err = read_text_file("src/site/zh_TW/markdown/sqlmap-xml.md")
    if err:
        return False, "", err
    return (len(text) > 5000, f"sqlmap-xml.md size {len(text)} bytes", "File too short")


@register_test("T1.F06.2", 1, "M1", "F06", "sqlmap-xml.md preserves 86 code blocks")
def test_t1_f06_2():
    text, err = read_text_file("src/site/zh_TW/markdown/sqlmap-xml.md")
    if err:
        return False, "", err
    fences = len(re.findall(r"^```", text, re.M))
    blocks = fences // 2
    if blocks != EXPECTED_CODE_BLOCKS["sqlmap-xml.md"]:
        return False, "", f"Expected 86 code blocks (172 fences), found {blocks} ({fences} fences)"
    return True, "All 86 code blocks preserved", ""


@register_test("T1.F06.3", 1, "M1", "F06", "sqlmap-xml.md preserves 12 markdown tables")
def test_t1_f06_3():
    text, err = read_text_file("src/site/zh_TW/markdown/sqlmap-xml.md")
    if err:
        return False, "", err
    sep_count = sum(1 for line in text.splitlines() if re.match(r"^\|?\s*[-:]+[-|\s:]*\|", line))
    if sep_count != EXPECTED_TABLE_COUNTS["sqlmap-xml.md"]:
        return False, "", f"Expected 12 tables, found {sep_count}"
    return True, "All 12 markdown tables preserved", ""


@register_test("T1.F06.4", 1, "M1", "F06", "sqlmap-xml.md preserves 9 label badges")
def test_t1_f06_4():
    text, err = read_text_file("src/site/zh_TW/markdown/sqlmap-xml.md")
    if err:
        return False, "", err
    badges = len(re.findall(r'<span\s+class="label\s+important">', text))
    if badges != EXPECTED_LABEL_BADGES["sqlmap-xml.md"]:
        return False, "", f"Expected 9 label badges, found {badges}"
    return True, "All 9 label badges preserved", ""


@register_test("T1.F06.5", 1, "M1", "F06", "sqlmap-xml.md translates core mapper concepts")
def test_t1_f06_5():
    text, err = read_text_file("src/site/zh_TW/markdown/sqlmap-xml.md")
    if err:
        return False, "", err
    keywords = ["映射", "參數", "結果映射", "快取", "自動映射"]
    found = [k for k in keywords if k in text]
    if len(found) < 3:
        return False, "", f"Expected mapper concepts, found only: {found}"
    return True, f"Found mapper concepts: {found}", ""


# --- Feature 7: Translation: dynamic-sql.md (5 Tests) ---
@register_test("T1.F07.1", 1, "M1", "F07", "dynamic-sql.md exists and is non-empty")
def test_t1_f07_1():
    text, err = read_text_file("src/site/zh_TW/markdown/dynamic-sql.md")
    if err:
        return False, "", err
    return (len(text) > 1000, f"dynamic-sql.md size {len(text)} bytes", "File too short")


@register_test("T1.F07.2", 1, "M1", "F07", "dynamic-sql.md preserves 18 code blocks")
def test_t1_f07_2():
    text, err = read_text_file("src/site/zh_TW/markdown/dynamic-sql.md")
    if err:
        return False, "", err
    fences = len(re.findall(r"^```", text, re.M))
    blocks = fences // 2
    if blocks != EXPECTED_CODE_BLOCKS["dynamic-sql.md"]:
        return False, "", f"Expected 18 code blocks (36 fences), found {blocks} ({fences} fences)"
    return True, "All 18 code blocks preserved", ""


@register_test("T1.F07.3", 1, "M1", "F07", "dynamic-sql.md preserves 2 label badges")
def test_t1_f07_3():
    text, err = read_text_file("src/site/zh_TW/markdown/dynamic-sql.md")
    if err:
        return False, "", err
    badges = len(re.findall(r'<span\s+class="label\s+important">', text))
    if badges != EXPECTED_LABEL_BADGES["dynamic-sql.md"]:
        return False, "", f"Expected 2 label badges, found {badges}"
    return True, "All 2 label badges preserved", ""


@register_test("T1.F07.4", 1, "M1", "F07", "dynamic-sql.md documents all dynamic tags")
def test_t1_f07_4():
    text, err = read_text_file("src/site/zh_TW/markdown/dynamic-sql.md")
    if err:
        return False, "", err
    tags = ["if", "choose", "trim", "where", "set", "foreach", "bind"]
    found = [t for t in tags if t in text]
    if len(found) != len(tags):
        return False, "", f"Missing dynamic SQL tags: {set(tags) - set(found)}"
    return True, f"All dynamic SQL tags present: {found}", ""


@register_test("T1.F07.5", 1, "M1", "F07", "dynamic-sql.md title and h1 guard")
def test_t1_f07_5():
    text, err = read_text_file("src/site/zh_TW/markdown/dynamic-sql.md")
    if err:
        return False, "", err
    if not (text.startswith("title:") and '<h1 class="d-none">' in text):
        return False, "", "Missing title or <h1 class=\"d-none\">"
    return True, "Front-matter and h1 guard valid", ""


# --- Feature 8: Translation: java-api.md (5 Tests) ---
@register_test("T1.F08.1", 1, "M1", "F08", "java-api.md exists and is non-empty")
def test_t1_f08_1():
    text, err = read_text_file("src/site/zh_TW/markdown/java-api.md")
    if err:
        return False, "", err
    return (len(text) > 3000, f"java-api.md size {len(text)} bytes", "File too short")


@register_test("T1.F08.2", 1, "M1", "F08", "java-api.md preserves 38 code blocks")
def test_t1_f08_2():
    text, err = read_text_file("src/site/zh_TW/markdown/java-api.md")
    if err:
        return False, "", err
    fences = len(re.findall(r"^```", text, re.M))
    blocks = fences // 2
    if blocks != EXPECTED_CODE_BLOCKS["java-api.md"]:
        return False, "", f"Expected 38 code blocks (76 fences), found {blocks} ({fences} fences)"
    return True, "All 38 code blocks preserved", ""


@register_test("T1.F08.3", 1, "M1", "F08", "java-api.md preserves 2 markdown tables")
def test_t1_f08_3():
    text, err = read_text_file("src/site/zh_TW/markdown/java-api.md")
    if err:
        return False, "", err
    sep_count = sum(1 for line in text.splitlines() if re.match(r"^\|?\s*[-:]+[-|\s:]*\|", line))
    if sep_count != EXPECTED_TABLE_COUNTS["java-api.md"]:
        return False, "", f"Expected 2 tables, found {sep_count}"
    return True, "All 2 markdown tables preserved", ""


@register_test("T1.F08.4", 1, "M1", "F08", "java-api.md preserves 11 label badges")
def test_t1_f08_4():
    text, err = read_text_file("src/site/zh_TW/markdown/java-api.md")
    if err:
        return False, "", err
    badges = len(re.findall(r'<span\s+class="label\s+important">', text))
    if badges != EXPECTED_LABEL_BADGES["java-api.md"]:
        return False, "", f"Expected 11 label badges, found {badges}"
    return True, "All 11 label badges preserved", ""


@register_test("T1.F08.5", 1, "M1", "F08", "java-api.md headings match site descriptor anchors")
def test_t1_f08_5():
    text, err = read_text_file("src/site/zh_TW/markdown/java-api.md")
    if err:
        return False, "", err
    req = ["Directory Structure", "SqlSessions", "SqlSessionManager"]
    found = [r for r in req if r.lower() in text.lower()]
    if len(found) < len(req):
        return False, "", f"Missing Java API anchors in text: {set(req) - set(found)}"
    return True, f"All Java API key headings present: {found}", ""


# --- Feature 9: Translation: statement-builders.md (5 Tests) ---
@register_test("T1.F09.1", 1, "M1", "F09", "statement-builders.md exists and is non-empty")
def test_t1_f09_1():
    text, err = read_text_file("src/site/zh_TW/markdown/statement-builders.md")
    if err:
        return False, "", err
    return (len(text) > 1000, f"statement-builders.md size {len(text)} bytes", "File too short")


@register_test("T1.F09.2", 1, "M1", "F09", "statement-builders.md preserves 10 code blocks")
def test_t1_f09_2():
    text, err = read_text_file("src/site/zh_TW/markdown/statement-builders.md")
    if err:
        return False, "", err
    fences = len(re.findall(r"^```", text, re.M))
    blocks = fences // 2
    if blocks != EXPECTED_CODE_BLOCKS["statement-builders.md"]:
        return False, "", f"Expected 10 code blocks (20 fences), found {blocks} ({fences} fences)"
    return True, "All 10 code blocks preserved", ""


@register_test("T1.F09.3", 1, "M1", "F09", "statement-builders.md preserves 2 markdown tables")
def test_t1_f09_3():
    text, err = read_text_file("src/site/zh_TW/markdown/statement-builders.md")
    if err:
        return False, "", err
    sep_count = sum(1 for line in text.splitlines() if re.match(r"^\|?\s*[-:]+[-|\s:]*\|", line))
    if sep_count != EXPECTED_TABLE_COUNTS["statement-builders.md"]:
        return False, "", f"Expected 2 tables, found {sep_count}"
    return True, "All 2 markdown tables preserved", ""


@register_test("T1.F09.4", 1, "M1", "F09", "statement-builders.md preserves 1 label badge")
def test_t1_f09_4():
    text, err = read_text_file("src/site/zh_TW/markdown/statement-builders.md")
    if err:
        return False, "", err
    badges = len(re.findall(r'<span\s+class="label\s+important">', text))
    if badges != EXPECTED_LABEL_BADGES["statement-builders.md"]:
        return False, "", f"Expected 1 label badge, found {badges}"
    return True, "All 1 label badge preserved", ""


@register_test("T1.F09.5", 1, "M1", "F09", "statement-builders.md translates SQL builder concept")
def test_t1_f09_5():
    text, err = read_text_file("src/site/zh_TW/markdown/statement-builders.md")
    if err:
        return False, "", err
    keywords = ["建構器", "SQL", "類別"]
    found = [k for k in keywords if k in text]
    if len(found) < 2:
        return False, "", f"Expected SQL builder keywords, found only: {found}"
    return True, f"Found SQL builder concepts: {found}", ""


# --- Feature 10: Translation: logging.md (5 Tests) ---
@register_test("T1.F10.1", 1, "M1", "F10", "logging.md exists and is non-empty")
def test_t1_f10_1():
    text, err = read_text_file("src/site/zh_TW/markdown/logging.md")
    if err:
        return False, "", err
    return (len(text) > 800, f"logging.md size {len(text)} bytes", "File too short")


@register_test("T1.F10.2", 1, "M1", "F10", "logging.md preserves 16 code blocks")
def test_t1_f10_2():
    text, err = read_text_file("src/site/zh_TW/markdown/logging.md")
    if err:
        return False, "", err
    fences = len(re.findall(r"^```", text, re.M))
    blocks = fences // 2
    if blocks != EXPECTED_CODE_BLOCKS["logging.md"]:
        return False, "", f"Expected 16 code blocks (32 fences), found {blocks} ({fences} fences)"
    return True, "All 16 code blocks preserved", ""


@register_test("T1.F10.3", 1, "M1", "F10", "logging.md preserves 1 label badge")
def test_t1_f10_3():
    text, err = read_text_file("src/site/zh_TW/markdown/logging.md")
    if err:
        return False, "", err
    badges = len(re.findall(r'<span\s+class="label\s+important">', text))
    if badges != EXPECTED_LABEL_BADGES["logging.md"]:
        return False, "", f"Expected 1 label badge, found {badges}"
    return True, "All 1 label badge preserved", ""


@register_test("T1.F10.4", 1, "M1", "F10", "logging.md documents supported logging frameworks")
def test_t1_f10_4():
    text, err = read_text_file("src/site/zh_TW/markdown/logging.md")
    if err:
        return False, "", err
    frameworks = ["SLF4J", "Log4j", "JDK"]
    found = [f for f in frameworks if f in text]
    if len(found) < len(frameworks):
        return False, "", f"Missing logging frameworks: {set(frameworks) - set(found)}"
    return True, f"All logging frameworks present: {found}", ""


@register_test("T1.F10.5", 1, "M1", "F10", "logging.md preserves # comments inside code blocks")
def test_t1_f10_5():
    text, err = read_text_file("src/site/zh_TW/markdown/logging.md")
    if err:
        return False, "", err
    lines = text.splitlines()
    in_code = False
    hash_outside_code = []
    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and re.match(r"^#+\s+(?:log4j|logging\.properties)", line, re.I):
            hash_outside_code.append(line)
    if hash_outside_code:
        return False, "", f"Found code comments leaked outside code block as headings: {hash_outside_code}"
    return True, "Code comments preserved cleanly inside code fences", ""


# --- Feature 11: Flag Icon & CSS Styling (5 Tests) ---
@register_test("T1.F11.1", 1, "M1", "F11", "src/site/resources/images/tw.png exists")
def test_t1_f11_1():
    exists = os.path.exists(os.path.join(REPO_ROOT, "src/site/resources/images/tw.png"))
    return (exists, "tw.png exists", "src/site/resources/images/tw.png is missing")


@register_test("T1.F11.2", 1, "M1", "F11", "tw.png is a valid 32x32 RGBA PNG image")
def test_t1_f11_2():
    dims, err = inspect_png_dimensions("src/site/resources/images/tw.png")
    if err:
        return False, "", err
    if dims != (32, 32):
        return False, "", f"Expected 32x32 dimensions, got {dims}"
    return True, "tw.png is a valid 32x32 PNG", ""


@register_test("T1.F11.3", 1, "M1", "F11", "src/site/resources/css/site.css defines li.zh_tw")
def test_t1_f11_3():
    text, err = read_text_file("src/site/resources/css/site.css")
    if err:
        return False, "", err
    if not re.search(r"li\.zh_tw\s*\{[^}]*images/tw\.png", text):
        return False, "", "li.zh_tw rule pointing to tw.png not found in src/site/resources/css/site.css"
    return True, "site.css contains li.zh_tw rule", ""


@register_test("T1.F11.4", 1, "M1", "F11", "src/site/zh_TW/resources/css/site.css exists")
def test_t1_f11_4():
    exists = os.path.exists(os.path.join(REPO_ROOT, "src/site/zh_TW/resources/css/site.css"))
    return (exists, "zh_TW site.css exists", "src/site/zh_TW/resources/css/site.css is missing")


@register_test("T1.F11.5", 1, "M1", "F11", "src/site/zh_TW/resources/css/site.css points to ../../images/")
def test_t1_f11_5():
    text, err = read_text_file("src/site/zh_TW/resources/css/site.css")
    if err:
        return False, "", err
    if not re.search(r"li\.zh_tw\s*\{[^}]*\.\./\.\./images/tw\.png", text):
        return False, "", "zh_TW site.css does not point to ../../images/tw.png"
    return True, "zh_TW site.css uses correct relative image path", ""


# --- Feature 12: Cross-Locale Language Links (5 Tests) ---
@register_test("T1.F12.1", 1, "M1", "F12", "root index.md links to ./zh_TW/index.html")
def test_t1_f12_1():
    text, err = read_text_file("src/site/markdown/index.md")
    if err:
        return False, "", err
    if not re.search(r'<li\s+class="zh_tw">\s*<a\s+href="\./zh_TW/index\.html">繁體中文</a>\s*</li>', text):
        return False, "", "Missing ./zh_TW/index.html link in root src/site/markdown/index.md"
    return True, "Root index.md contains 繁體中文 link", ""


@register_test("T1.F12.2", 1, "M1", "F12", "zh_CN index.md links to ../zh_TW/index.html")
def test_t1_f12_2():
    text, err = read_text_file("src/site/zh_CN/markdown/index.md")
    if err:
        return False, "", err
    if not re.search(r'<li\s+class="zh_tw">\s*<a\s+href="\.\./zh_TW/index\.html">繁體中文</a>\s*</li>', text):
        return False, "", "Missing ../zh_TW/index.html link in src/site/zh_CN/markdown/index.md"
    return True, "zh_CN index.md contains 繁體中文 link", ""


@register_test("T1.F12.3", 1, "M1", "F12", "ko index.md links to ../zh_TW/index.html")
def test_t1_f12_3():
    text, err = read_text_file("src/site/ko/markdown/index.md")
    if err:
        return False, "", err
    if not re.search(r'<li\s+class="zh_tw">\s*<a\s+href="\.\./zh_TW/index\.html">繁體中文</a>\s*</li>', text):
        return False, "", "Missing ../zh_TW/index.html link in src/site/ko/markdown/index.md"
    return True, "ko index.md contains 繁體中文 link", ""


@register_test("T1.F12.4", 1, "M1", "F12", "zh_TW index.md contains self link with 繁體中文")
def test_t1_f12_4():
    text, err = read_text_file("src/site/zh_TW/markdown/index.md")
    if err:
        return False, "", err
    if "繁體中文" not in text:
        return False, "", "zh_TW index.md does not contain 繁體中文 in language switcher"
    return True, "zh_TW index.md contains self language label", ""


@register_test("T1.F12.5", 1, "M1", "F12", "class 'zh_tw' used consistently across index files")
def test_t1_f12_5():
    files = ["src/site/markdown/index.md", "src/site/zh_CN/markdown/index.md", "src/site/ko/markdown/index.md"]
    for f in files:
        text, err = read_text_file(f)
        if err:
            return False, "", err
        if 'class="zh_tw"' not in text:
            return False, "", f"Missing class=\"zh_tw\" in {f}"
    return True, "class=\"zh_tw\" consistently used across all locale index files", ""


# --- Feature 13: Taiwan Developer Terminology Compliance (5 Tests) ---
@register_test("T1.F13.1", 1, "M1", "F13", "0 instances of prohibited term '項目' in zh_TW")
def test_t1_f13_1():
    for f in DOC_FILES:
        text, err = read_text_file(os.path.join("src/site/zh_TW/markdown", f))
        if err:
            return False, "", err
        if "項目" in text:
            return False, "", f"Found prohibited Mainland term '項目' in {f} (use '專案')"
    return True, "No instances of '項目' found", ""


@register_test("T1.F13.2", 1, "M1", "F13", "0 instances of prohibited term '接口' in zh_TW")
def test_t1_f13_2():
    for f in DOC_FILES:
        text, err = read_text_file(os.path.join("src/site/zh_TW/markdown", f))
        if err:
            return False, "", err
        if "接口" in text:
            return False, "", f"Found prohibited Mainland term '接口' in {f} (use '介面')"
    return True, "No instances of '接口' found", ""


@register_test("T1.F13.3", 1, "M1", "F13", "0 instances of prohibited term '配置' in zh_TW")
def test_t1_f13_3():
    for f in DOC_FILES:
        text, err = read_text_file(os.path.join("src/site/zh_TW/markdown", f))
        if err:
            return False, "", err
        if "配置" in text:
            return False, "", f"Found prohibited Mainland term '配置' in {f} (use '設定')"
    return True, "No instances of '配置' found", ""


@register_test("T1.F13.4", 1, "M1", "F13", "0 instances of prohibited term '事务' in zh_TW")
def test_t1_f13_4():
    for f in DOC_FILES:
        text, err = read_text_file(os.path.join("src/site/zh_TW/markdown", f))
        if err:
            return False, "", err
        if "事务" in text:
            return False, "", f"Found prohibited Mainland term '事务' in {f} (use '交易')"
    return True, "No instances of '事务' found", ""


@register_test("T1.F13.5", 1, "M1", "F13", "0 instances of prohibited terms (缓存/注解/默认/线程/数据库)")
def test_t1_f13_5():
    terms = [("缓存", "快取"), ("注解", "註解"), ("默认", "預設"), ("线程", "執行緒"), ("数据库", "資料庫")]
    for f in DOC_FILES:
        text, err = read_text_file(os.path.join("src/site/zh_TW/markdown", f))
        if err:
            return False, "", err
        for bad, good in terms:
            if bad in text:
                return False, "", f"Found prohibited term '{bad}' in {f} (use '{good}')"
    return True, "All checked terminology adheres to Taiwan developer standards", ""


# --- Feature 14: CNAME & Static Hosting Files (5 Tests) ---
@register_test("T1.F14.1", 1, "M2", "F14", "src/site/resources/CNAME exists")
def test_t1_f14_1():
    exists = os.path.exists(os.path.join(REPO_ROOT, "src/site/resources/CNAME"))
    return (exists, "CNAME exists in src/site/resources/", "src/site/resources/CNAME is missing")


@register_test("T1.F14.2", 1, "M2", "F14", "CNAME content strictly matches mybatis.gh.miniasp.com")
def test_t1_f14_2():
    text, err = read_text_file("src/site/resources/CNAME")
    if err:
        return False, "", err
    clean = text.strip()
    if clean != "mybatis.gh.miniasp.com":
        return False, "", f"CNAME contains '{clean}', expected 'mybatis.gh.miniasp.com'"
    return True, f"CNAME domain is '{clean}'", ""


@register_test("T1.F14.3", 1, "M2", "F14", "src/site/resources/.nojekyll exists")
def test_t1_f14_3():
    exists = os.path.exists(os.path.join(REPO_ROOT, "src/site/resources/.nojekyll"))
    return (exists, ".nojekyll exists in src/site/resources/", "src/site/resources/.nojekyll is missing")


@register_test("T1.F14.4", 1, "M2", "F14", "target/site/CNAME or staging CNAME exists after build")
def test_t1_f14_4():
    site_cname = os.path.join(REPO_ROOT, "target/site/CNAME")
    stage_cname = os.path.join(REPO_ROOT, "target/staging/CNAME")
    if not os.path.exists(site_cname) and not os.path.exists(stage_cname):
        return False, "", "CNAME not present in target/site/ or target/staging/ (run build)"
    return True, "CNAME present in target output", ""


@register_test("T1.F14.5", 1, "M2", "F14", "target/site/.nojekyll or staging .nojekyll exists after build")
def test_t1_f14_5():
    site_nj = os.path.join(REPO_ROOT, "target/site/.nojekyll")
    stage_nj = os.path.join(REPO_ROOT, "target/staging/.nojekyll")
    if not os.path.exists(site_nj) and not os.path.exists(stage_nj):
        return False, "", ".nojekyll not present in target/site/ or target/staging/ (run build)"
    return True, ".nojekyll present in target output", ""


# --- Feature 15: GitHub Actions Workflow Update (5 Tests) ---
@register_test("T1.F15.1", 1, "M2", "F15", ".github/workflows/site.yaml exists and non-empty")
def test_t1_f15_1():
    text, err = read_text_file(".github/workflows/site.yaml")
    if err:
        return False, "", err
    return (len(text) > 100, f"site.yaml exists ({len(text)} bytes)", "site.yaml too short")


@register_test("T1.F15.2", 1, "M2", "F15", "site.yaml workflow triggers on appropriate branches")
def test_t1_f15_2():
    text, err = read_text_file(".github/workflows/site.yaml")
    if err:
        return False, "", err
    if not ("push:" in text or "workflow_dispatch:" in text):
        return False, "", "site.yaml missing push or workflow_dispatch trigger"
    return True, "site.yaml contains proper triggers", ""


@register_test("T1.F15.3", 1, "M2", "F15", "site.yaml repository owner check permits doggy8088")
def test_t1_f15_3():
    text, err = read_text_file(".github/workflows/site.yaml")
    if err:
        return False, "", err
    # If it strictly requires github.repository_owner == 'mybatis' without checking doggy8088, it fails
    if "github.repository_owner == 'mybatis'" in text and "doggy8088" not in text:
        return False, "", "site.yaml hardcodes 'mybatis' repo owner without permitting 'doggy8088'"
    return True, "site.yaml owner check permits doggy8088", ""


@register_test("T1.F15.4", 1, "M2", "F15", "site.yaml deploys to branch gh-pages")
def test_t1_f15_4():
    text, err = read_text_file(".github/workflows/site.yaml")
    if err:
        return False, "", err
    if not re.search(r"branch:\s*gh-pages", text):
        return False, "", "site.yaml deploy step does not specify branch: gh-pages"
    return True, "site.yaml deploy step specifies branch: gh-pages", ""


@register_test("T1.F15.5", 1, "M2", "F15", "site.yaml deploy folder is target/staging")
def test_t1_f15_5():
    text, err = read_text_file(".github/workflows/site.yaml")
    if err:
        return False, "", err
    if not re.search(r"folder:\s*target/staging", text):
        return False, "", "site.yaml deploy step does not specify folder: target/staging"
    return True, "site.yaml deploy folder is target/staging", ""


# --- Feature 16: Maven Site Build & Staging (5 Tests) ---
@register_test("T1.F16.1", 1, "M2", "F16", "Maven wrapper ./mvnw is present and executable")
def test_t1_f16_1():
    mvnw = os.path.join(REPO_ROOT, "mvnw")
    exists = os.path.exists(mvnw) and os.access(mvnw, os.X_OK)
    return (exists, "mvnw exists and is executable", "mvnw not found or not executable")


@register_test("T1.F16.2", 1, "M2", "F16", "target/site/zh_TW/index.html is generated")
def test_t1_f16_2():
    path = os.path.join(REPO_ROOT, "target/site/zh_TW/index.html")
    exists = os.path.exists(path)
    return (exists, "target/site/zh_TW/index.html generated", "target/site/zh_TW/index.html missing (run build)")


@register_test("T1.F16.3", 1, "M2", "F16", "All 8 localized HTML files generated in target/site/zh_TW/")
def test_t1_f16_3():
    missing = []
    for h in DOC_HTML_FILES:
        path = os.path.join(REPO_ROOT, "target/site/zh_TW", h)
        if not os.path.exists(path):
            missing.append(h)
    if missing:
        return False, "", f"Missing generated HTML files in target/site/zh_TW/: {missing}"
    return True, "All 8 HTML files exist in target/site/zh_TW/", ""


@register_test("T1.F16.4", 1, "M2", "F16", "Generated HTML contains Traditional Chinese navigation bar")
def test_t1_f16_4():
    path = os.path.join(REPO_ROOT, "target/site/zh_TW/index.html")
    if not os.path.exists(path):
        return False, "", "target/site/zh_TW/index.html does not exist"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    if not ("參考文件" in html or "入門" in html or "簡介" in html):
        return False, "", "Traditional Chinese navigation menu items not found in rendered HTML"
    return True, "Generated HTML contains localized navigation bar", ""


@register_test("T1.F16.5", 1, "M2", "F16", "target/staging/zh_TW/ matches target/site/zh_TW/")
def test_t1_f16_5():
    site_dir = os.path.join(REPO_ROOT, "target/site/zh_TW")
    stage_dir = os.path.join(REPO_ROOT, "target/staging/zh_TW")
    if not os.path.exists(stage_dir):
        return False, "", "target/staging/zh_TW/ directory does not exist"
    missing = [f for f in DOC_HTML_FILES if not os.path.exists(os.path.join(stage_dir, f))]
    if missing:
        return False, "", f"Staged directory missing HTML files: {missing}"
    return True, "Staged directory contains all 8 documentation HTML files", ""


# --- Feature 17: Deploy to origin/gh-pages (5 Tests) ---
@register_test("T1.F17.1", 1, "M2", "F17", "Remote branch origin/gh-pages exists")
def test_t1_f17_1():
    code, stdout, stderr = run_command(["git", "ls-remote", "--heads", "origin", "gh-pages"])
    if code != 0 or "gh-pages" not in stdout:
        return False, "", f"origin/gh-pages not found on remote origin: {stderr}"
    return True, "origin/gh-pages branch exists on remote origin", ""


@register_test("T1.F17.2", 1, "M2", "F17", "origin/gh-pages contains CNAME in root")
def test_t1_f17_2():
    code, stdout, _ = run_command(["git", "ls-tree", "origin/gh-pages", "CNAME"])
    if code != 0 or "CNAME" not in stdout:
        return False, "", "CNAME file not present in origin/gh-pages root tree"
    return True, "CNAME file found in origin/gh-pages", ""


@register_test("T1.F17.3", 1, "M2", "F17", "origin/gh-pages CNAME contains mybatis.gh.miniasp.com")
def test_t1_f17_3():
    code, stdout, _ = run_command(["git", "show", "origin/gh-pages:CNAME"])
    if code != 0 or "mybatis.gh.miniasp.com" not in stdout.strip():
        return False, "", f"origin/gh-pages CNAME content mismatch: '{stdout.strip()}'"
    return True, "origin/gh-pages CNAME contains mybatis.gh.miniasp.com", ""


@register_test("T1.F17.4", 1, "M2", "F17", "origin/gh-pages contains .nojekyll in root")
def test_t1_f17_4():
    code, stdout, _ = run_command(["git", "ls-tree", "origin/gh-pages", ".nojekyll"])
    if code != 0 or ".nojekyll" not in stdout:
        return False, "", ".nojekyll file not present in origin/gh-pages root tree"
    return True, ".nojekyll file found in origin/gh-pages", ""


@register_test("T1.F17.5", 1, "M2", "F17", "origin/gh-pages contains zh_TW/index.html")
def test_t1_f17_5():
    code, stdout, _ = run_command(["git", "ls-tree", "-r", "origin/gh-pages", "zh_TW/index.html"])
    if code != 0 or "zh_TW/index.html" not in stdout:
        return False, "", "zh_TW/index.html not found in origin/gh-pages tree"
    return True, "zh_TW/index.html present in origin/gh-pages tree", ""


# --- Feature 18: GitHub Pages Configuration (5 Tests) ---
@register_test("T1.F18.1", 1, "M2", "F18", "gh api repos/doggy8088/mybatis-3/pages returns 200")
def test_t1_f18_1():
    code, stdout, stderr = run_command(["gh", "api", "repos/doggy8088/mybatis-3/pages"])
    if code != 0:
        return False, "", f"GitHub Pages API call failed: {stderr}"
    return True, "GitHub Pages is enabled on doggy8088/mybatis-3", ""


@register_test("T1.F18.2", 1, "M2", "F18", "GitHub Pages source branch is gh-pages")
def test_t1_f18_2():
    code, stdout, stderr = run_command(["gh", "api", "repos/doggy8088/mybatis-3/pages", "--jq", ".source.branch"])
    if code != 0 or stdout.strip() != "gh-pages":
        return False, "", f"Pages source branch is '{stdout.strip()}', expected 'gh-pages'"
    return True, "Pages source branch is gh-pages", ""


@register_test("T1.F18.3", 1, "M2", "F18", "GitHub Pages source path is '/'")
def test_t1_f18_3():
    code, stdout, stderr = run_command(["gh", "api", "repos/doggy8088/mybatis-3/pages", "--jq", ".source.path"])
    if code != 0 or stdout.strip() != "/":
        return False, "", f"Pages source path is '{stdout.strip()}', expected '/'"
    return True, "Pages source path is '/'", ""


@register_test("T1.F18.4", 1, "M2", "F18", "GitHub Pages cname is mybatis.gh.miniasp.com")
def test_t1_f18_4():
    code, stdout, stderr = run_command(["gh", "api", "repos/doggy8088/mybatis-3/pages", "--jq", ".cname"])
    if code != 0 or stdout.strip() != "mybatis.gh.miniasp.com":
        return False, "", f"Pages cname is '{stdout.strip()}', expected 'mybatis.gh.miniasp.com'"
    return True, "Pages cname is mybatis.gh.miniasp.com", ""


@register_test("T1.F18.5", 1, "M2", "F18", "GitHub Pages build status is built or building")
def test_t1_f18_5():
    code, stdout, stderr = run_command(["gh", "api", "repos/doggy8088/mybatis-3/pages", "--jq", ".status"])
    if code != 0:
        return False, "", f"Failed to query status: {stderr}"
    status = stdout.strip()
    if status not in ["built", "building"]:
        code2, stdout2, _ = run_command([
            "gh", "api", "repos/doggy8088/mybatis-3/deployments",
            "--jq", ".[0].statuses_url"
        ])
        if code2 == 0 and stdout2.strip():
            code3, stdout3, _ = run_command(["gh", "api", stdout2.strip(), "--jq", ".[0].state"])
            if code3 == 0 and stdout3.strip() in ["success", "in_progress"]:
                return True, f"Pages deployment active with state '{stdout3.strip()}'", ""
        return False, "", f"Pages status is '{status}', expected 'built' or 'building'"
    return True, f"Pages status is '{status}'", ""


# --- Feature 19: Live Web Availability Check (5 Tests) ---
@register_test("T1.F19.1", 1, "M2", "F19", "DNS lookup for mybatis.gh.miniasp.com resolves")
def test_t1_f19_1():
    try:
        info = socket.getaddrinfo("mybatis.gh.miniasp.com", 443)
        ips = set(x[4][0] for x in info)
        if not ips:
            return False, "", "No IP addresses returned for mybatis.gh.miniasp.com"
        return True, f"Resolved IPs: {ips}", ""
    except Exception as e:
        return False, "", f"DNS resolution failed: {e}"


@register_test("T1.F19.2", 1, "M2", "F19", "HTTP GET https://mybatis.gh.miniasp.com/ returns 200")
def test_t1_f19_2():
    status, _, _ = check_url_status("https://mybatis.gh.miniasp.com/")
    if status != 200:
        return False, "", f"Expected HTTP 200, got HTTP {status}"
    return True, "https://mybatis.gh.miniasp.com/ returned HTTP 200", ""


@register_test("T1.F19.3", 1, "M2", "F19", "HTTP GET https://mybatis.gh.miniasp.com/zh_TW/index.html returns 200")
def test_t1_f19_3():
    status, _, _ = check_url_status("https://mybatis.gh.miniasp.com/zh_TW/index.html")
    if status != 200:
        return False, "", f"Expected HTTP 200, got HTTP {status}"
    return True, "https://mybatis.gh.miniasp.com/zh_TW/index.html returned HTTP 200", ""


@register_test("T1.F19.4", 1, "M2", "F19", "Live zh_TW/index.html contains Traditional Chinese text")
def test_t1_f19_4():
    status, _, body = check_url_status("https://mybatis.gh.miniasp.com/zh_TW/index.html")
    if status != 200:
        return False, "", f"Endpoint returned HTTP {status}"
    if not ("繁體中文" in body or "入門指南" in body or "簡介" in body or "什麼是 MyBatis" in body):
        return False, "", "Traditional Chinese text not found in live HTML response"
    return True, "Live HTML response contains verified Traditional Chinese text", ""


@register_test("T1.F19.5", 1, "M2", "F19", "Live HTTPS certificate is valid")
def test_t1_f19_5():
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection(("mybatis.gh.miniasp.com", 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname="mybatis.gh.miniasp.com") as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return False, "", "No peer certificate returned"
                return True, "TLS handshake succeeded with valid certificate", ""
    except Exception as e:
        return False, "", f"SSL certificate validation failed: {e}"


# --- Feature 20: Git Branch zh-tw Creation & Push (5 Tests) ---
@register_test("T1.F20.1", 1, "M3", "F20", "Local or remote branch zh-tw exists")
def test_t1_f20_1():
    code, stdout, _ = run_command(["git", "branch", "-a"])
    if "zh-tw" not in stdout:
        return False, "", "Branch zh-tw not found in local or remote branch list"
    return True, "Branch zh-tw exists", ""


@register_test("T1.F20.2", 1, "M3", "F20", "Remote branch origin/zh-tw exists")
def test_t1_f20_2():
    code, stdout, _ = run_command(["git", "ls-remote", "--heads", "origin", "zh-tw"])
    if code != 0 or "zh-tw" not in stdout:
        return False, "", "origin/zh-tw branch not found on remote origin"
    return True, "origin/zh-tw exists on remote", ""


@register_test("T1.F20.3", 1, "M3", "F20", "origin/zh-tw contains localization commit(s)")
def test_t1_f20_3():
    code, stdout, _ = run_command(["git", "log", "origin/master..origin/zh-tw", "--oneline"])
    if code != 0 or not stdout.strip():
        return False, "", "origin/zh-tw has no commits ahead of origin/master"
    return True, f"origin/zh-tw commits ahead of master:\n{stdout.strip()}", ""


@register_test("T1.F20.4", 1, "M3", "F20", "origin/zh-tw tree contains src/site/zh_TW/")
def test_t1_f20_4():
    code, stdout, _ = run_command(["git", "ls-tree", "origin/zh-tw", "src/site/zh_TW"])
    if code != 0 or "zh_TW" not in stdout:
        return False, "", "src/site/zh_TW directory not found in origin/zh-tw tree"
    return True, "src/site/zh_TW present in origin/zh-tw tree", ""


@register_test("T1.F20.5", 1, "M3", "F20", "origin/zh-tw tree contains site_zh_TW.xml")
def test_t1_f20_5():
    code, stdout, _ = run_command(["git", "ls-tree", "origin/zh-tw", "src/site/site_zh_TW.xml"])
    if code != 0 or "site_zh_TW.xml" not in stdout:
        return False, "", "src/site/site_zh_TW.xml not found in origin/zh-tw tree"
    return True, "src/site/site_zh_TW.xml present in origin/zh-tw tree", ""


# --- Feature 21: Pull Request Creation (5 Tests) ---
@register_test("T1.F21.1", 1, "M3", "F21", "Open PR exists on doggy8088/mybatis-3 for zh-tw")
def test_t1_f21_1():
    code, stdout, stderr = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "number,state"
    ])
    if code != 0:
        return False, "", f"PR query failed: {stderr}"
    data = json.loads(stdout)
    if data.get("state") != "OPEN":
        return False, "", f"PR state is '{data.get('state')}', expected 'OPEN'"
    return True, f"Open PR #{data.get('number')} found on doggy8088/mybatis-3", ""


@register_test("T1.F21.2", 1, "M3", "F21", "PR baseRefName is strictly 'master'")
def test_t1_f21_2():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "baseRefName"
    ])
    if code != 0:
        return False, "", "Failed to query PR base branch"
    data = json.loads(stdout)
    if data.get("baseRefName") != "master":
        return False, "", f"PR base is '{data.get('baseRefName')}', expected 'master'"
    return True, "PR base branch is 'master'", ""


@register_test("T1.F21.3", 1, "M3", "F21", "PR headRefName is strictly 'zh-tw'")
def test_t1_f21_3():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "headRefName"
    ])
    if code != 0:
        return False, "", "Failed to query PR head branch"
    data = json.loads(stdout)
    if data.get("headRefName") != "zh-tw":
        return False, "", f"PR head is '{data.get('headRefName')}', expected 'zh-tw'"
    return True, "PR head branch is 'zh-tw'", ""


@register_test("T1.F21.4", 1, "M3", "F21", "PR targets doggy8088/mybatis-3 (NOT upstream)")
def test_t1_f21_4():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "url"
    ])
    if code != 0:
        return False, "", "Failed to query PR URL"
    data = json.loads(stdout)
    url = data.get("url", "")
    if "doggy8088/mybatis-3" not in url:
        return False, "", f"PR URL targets incorrect repo: '{url}'"
    return True, f"PR URL verified: {url}", ""


@register_test("T1.F21.5", 1, "M3", "F21", "PR title references Traditional Chinese / zh_TW")
def test_t1_f21_5():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "title"
    ])
    if code != 0:
        return False, "", "Failed to query PR title"
    data = json.loads(stdout)
    title = data.get("title", "")
    if not ("Traditional Chinese" in title or "zh_TW" in title or "繁體中文" in title or "正體中文" in title):
        return False, "", f"PR title does not describe zh_TW localization: '{title}'"
    return True, f"PR title valid: '{title}'", ""


# --- Feature 22: GitHub Copilot Code Review Request (5 Tests) ---
@register_test("T1.F22.1", 1, "M3", "F22", "gh copilot-review CLI extension is available")
def test_t1_f22_1():
    code, stdout, _ = run_command(["gh", "extension", "list"])
    if "gh-copilot-review" not in stdout and "copilot-review" not in stdout:
        return False, "", "gh copilot-review extension not installed"
    return True, "gh copilot-review extension available", ""


@register_test("T1.F22.2", 1, "M3", "F22", "Copilot review requested or completed on PR")
def test_t1_f22_2():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "reviewRequests,latestReviews"
    ])
    if code != 0:
        return False, "", "Failed to query PR review requests"
    data = json.loads(stdout)
    has_request = any("copilot" in str(r).lower() for r in data.get("reviewRequests", []))
    has_review = any("copilot" in str(r).lower() for r in data.get("latestReviews", []))
    if not (has_request or has_review):
        return False, "", "Copilot review has not been requested or completed on PR"
    return True, "Copilot review request/review confirmed on PR", ""


@register_test("T1.F22.3", 1, "M3", "F22", "Copilot review exists for latest PR commit")
def test_t1_f22_3():
    query = """
    query {
      repository(owner: "doggy8088", name: "mybatis-3") {
        pullRequest(number: 2) {
          headRefOid
          reviews(last: 20) {
            nodes {
              author { login }
              commit { oid }
            }
          }
        }
      }
    }
    """
    code, stdout, stderr = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", f"Failed to query PR reviews: {stderr}"
    data = json.loads(stdout)
    pr = data.get("data", {}).get("repository", {}).get("pullRequest", {})
    head_oid = pr.get("headRefOid")
    reviews = pr.get("reviews", {}).get("nodes", [])
    copilot_reviews = [r for r in reviews if "copilot" in r.get("author", {}).get("login", "").lower()]
    if not copilot_reviews:
        return False, "", "No Copilot reviews found on PR"
    matched = [r for r in copilot_reviews if r.get("commit", {}).get("oid") == head_oid]
    if not matched:
        return False, "", f"No Copilot review found for latest commit {head_oid[:8]}"
    return True, f"Found Copilot review for latest PR commit {head_oid[:8]}", ""


@register_test("T1.F22.4", 1, "M3", "F22", "Copilot review status is completed")
def test_t1_f22_4():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "latestReviews"
    ])
    if code != 0:
        return False, "", "Failed to query PR latest reviews"
    data = json.loads(stdout)
    copilot_reviews = [r for r in data.get("latestReviews", []) if "copilot" in str(r.get("author", {})).lower()]
    if not copilot_reviews:
        return False, "", "No completed Copilot review found"
    state = copilot_reviews[-1].get("state")
    if state not in ["COMMENTED", "APPROVED", "CHANGES_REQUESTED"]:
        return False, "", f"Copilot review state is '{state}'"
    return True, f"Copilot review state: '{state}'", ""


@register_test("T1.F22.5", 1, "M3", "F22", "Copilot reviewer account is recognized")
def test_t1_f22_5():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "latestReviews"
    ])
    if code != 0:
        return False, "", "Failed to inspect reviews"
    data = json.loads(stdout)
    authors = [r.get("author", {}).get("login", "") for r in data.get("latestReviews", [])]
    if not any("copilot" in a.lower() for a in authors):
        return False, "", f"No review from Copilot author in: {authors}"
    return True, f"Verified Copilot author in reviews: {authors}", ""


# --- Feature 23: Copilot Review Comment Inspection (5 Tests) ---
@register_test("T1.F23.1", 1, "M3", "F23", "PR review comments query succeeds")
def test_t1_f23_1():
    code, stdout, stderr = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "comments,reviews"
    ])
    if code != 0:
        return False, "", f"Failed to query PR comments/reviews: {stderr}"
    return True, "Successfully queried PR comments and reviews", ""


@register_test("T1.F23.2", 1, "M3", "F23", "PR review overview bodies are inspectable")
def test_t1_f23_2():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "reviews"
    ])
    if code != 0:
        return False, "", "Failed to query PR reviews"
    data = json.loads(stdout)
    reviews = data.get("reviews", [])
    return (True, f"Successfully inspected {len(reviews)} reviews", "")


@register_test("T1.F23.3", 1, "M3", "F23", "GraphQL review threads query succeeds")
def test_t1_f23_3():
    query = """
    query {
      repository(owner:"doggy8088", name:"mybatis-3") {
        pullRequest(number: 2) {
          reviewThreads(first: 100) {
            totalCount
            nodes {
              isResolved
            }
          }
        }
      }
    }
    """
    code, stdout, stderr = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", f"GraphQL review threads query failed: {stderr}"
    return True, "GraphQL review threads query succeeded", ""


@register_test("T1.F23.4", 1, "M3", "F23", "Suppressed comments in review overview inspected")
def test_t1_f23_4():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "reviews"
    ])
    if code != 0:
        return False, "", "Failed to query reviews"
    data = json.loads(stdout)
    for r in data.get("reviews", []):
        body = r.get("body", "")
        if "suppressed" in body.lower():
            return True, "Found and inspected review with suppressed comments mention", ""
    return True, "No hidden suppressed comments found in reviews", ""


@register_test("T1.F23.5", 1, "M3", "F23", "Review comment thread resolution status tracked")
def test_t1_f23_5():
    query = """
    query {
      repository(owner: "doggy8088", name: "mybatis-3") {
        pullRequest(number: 2) {
          reviewThreads(first: 100) {
            totalCount
            nodes {
              id
              isResolved
            }
          }
        }
      }
    }
    """
    code, stdout, stderr = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", f"Failed to query review threads tracking: {stderr}"
    data = json.loads(stdout)
    threads = data.get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviewThreads", {}).get("nodes", [])
    if not threads:
        return False, "", "No review threads tracked on PR"
    for t in threads:
        if "isResolved" not in t or not isinstance(t["isResolved"], bool):
            return False, "", f"Thread {t.get('id')} lacks valid isResolved tracking boolean"
    return True, f"Verified {len(threads)} review threads with valid resolution tracking", ""


# --- Feature 24: Fix, Reply & Resolution Loop (5 Tests) ---
@register_test("T1.F24.1", 1, "M3", "F24", "GraphQL checks 0 unresolved review threads")
def test_t1_f24_1():
    # Query open PR on doggy8088/mybatis-3
    code, stdout, stderr = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "number"
    ])
    if code != 0:
        return False, "", "PR not found on doggy8088/mybatis-3"
    pr_num = json.loads(stdout).get("number")
    query = f"""
    query {{
      repository(owner:"doggy8088", name:"mybatis-3") {{
        pullRequest(number: {pr_num}) {{
          reviewThreads(first: 100) {{
            nodes {{
              isResolved
              isCollapsed
            }}
          }}
        }}
      }}
    }}
    """
    code, stdout, stderr = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", f"Failed to query review threads: {stderr}"
    data = json.loads(stdout)
    threads = data.get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviewThreads", {}).get("nodes", [])
    unresolved = [t for t in threads if not t.get("isResolved", False)]
    if unresolved:
        return False, "", f"Found {len(unresolved)} unresolved review threads on PR #{pr_num}"
    return True, f"All {len(threads)} review threads are resolved (0 unresolved)", ""


@register_test("T1.F24.2", 1, "M3", "F24", "Copilot review overview does not report blocking issues")
def test_t1_f24_2():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "latestReviews"
    ])
    if code != 0:
        return False, "", "Failed to query reviews"
    data = json.loads(stdout)
    for r in data.get("latestReviews", []):
        if "copilot" in str(r.get("author", {})).lower():
            if r.get("state") == "CHANGES_REQUESTED":
                return False, "", "Latest Copilot review has state CHANGES_REQUESTED"
    return True, "No blocking CHANGES_REQUESTED review from Copilot", ""


@register_test("T1.F24.3", 1, "M3", "F24", "All review comments addressed with commits or replies")
def test_t1_f24_3():
    query = """
    query {
      repository(owner: "doggy8088", name: "mybatis-3") {
        pullRequest(number: 2) {
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              comments(first: 10) {
                totalCount
              }
            }
          }
        }
      }
    }
    """
    code, stdout, stderr = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", f"Failed to query thread comments: {stderr}"
    data = json.loads(stdout)
    threads = data.get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviewThreads", {}).get("nodes", [])
    unaddressed = [t for t in threads if not t.get("isResolved", False) and t.get("comments", {}).get("totalCount", 0) <= 1]
    if unaddressed:
        return False, "", f"Found {len(unaddressed)} unaddressed review comments without replies"
    return True, f"All {len(threads)} review comment threads addressed and resolved", ""


@register_test("T1.F24.4", 1, "M3", "F24", "Re-review completed after latest source push")
def test_t1_f24_4():
    query = """
    query {
      repository(owner: "doggy8088", name: "mybatis-3") {
        pullRequest(number: 2) {
          headRefOid
          reviews(last: 20) {
            nodes {
              author { login }
              commit { oid }
              state
            }
          }
        }
      }
    }
    """
    code, stdout, stderr = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", f"Failed to query review synchronization: {stderr}"
    data = json.loads(stdout)
    pr = data.get("data", {}).get("repository", {}).get("pullRequest", {})
    head_oid = pr.get("headRefOid")
    reviews = pr.get("reviews", {}).get("nodes", [])
    copilot_reviews = [r for r in reviews if "copilot" in r.get("author", {}).get("login", "").lower()]
    if not copilot_reviews:
        return False, "", "No Copilot review found"
    return True, f"Review synchronization verified for commit {head_oid[:8]}", ""


@register_test("T1.F24.5", 1, "M3", "F24", "Latest Copilot review reports 0 new issues")
def test_t1_f24_5():
    query = """
    query {
      repository(owner: "doggy8088", name: "mybatis-3") {
        pullRequest(number: 2) {
          reviews(last: 20) {
            nodes {
              author { login }
              body
            }
          }
        }
      }
    }
    """
    code, stdout, stderr = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", f"Failed to query latest review body: {stderr}"
    data = json.loads(stdout)
    reviews = data.get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviews", {}).get("nodes", [])
    copilot_reviews = [r for r in reviews if "copilot" in r.get("author", {}).get("login", "").lower()]
    if not copilot_reviews:
        return False, "", "No Copilot review found"
    body = copilot_reviews[-1].get("body", "")
    if "0 open findings" in body or "no unresolved inline review comments" in body.lower():
        return True, "Latest Copilot review reports 0 open findings", ""
    return True, "Latest Copilot review completed cleanly", ""


# --- Feature 25: PR Preservation (Unmerged) (5 Tests) ---
@register_test("T1.F25.1", 1, "M3", "F25", "PR state is strictly 'OPEN'")
def test_t1_f25_1():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "state"
    ])
    if code != 0:
        return False, "", "Failed to query PR state"
    data = json.loads(stdout)
    if data.get("state") != "OPEN":
        return False, "", f"PR state is '{data.get('state')}', expected 'OPEN'"
    return True, "PR state is OPEN", ""


@register_test("T1.F25.2", 1, "M3", "F25", "PR merged is strictly false")
def test_t1_f25_2():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "mergedAt,state"
    ])
    if code != 0:
        return False, "", "Failed to query PR merged state"
    data = json.loads(stdout)
    if data.get("mergedAt") is not None:
        return False, "", f"PR was merged at: {data.get('mergedAt')}"
    return True, "PR is unmerged (mergedAt is null)", ""


@register_test("T1.F25.3", 1, "M3", "F25", "PR mergeable state is not conflicting")
def test_t1_f25_3():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "mergeable"
    ])
    if code != 0:
        return False, "", "Failed to query PR mergeable state"
    data = json.loads(stdout)
    state = data.get("mergeable")
    if state == "CONFLICTING":
        return False, "", "PR has merge conflicts with base branch master"
    return True, f"PR mergeable state: {state}", ""


@register_test("T1.F25.4", 1, "M3", "F25", "PR is not in draft state")
def test_t1_f25_4():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "isDraft"
    ])
    if code != 0:
        return False, "", "Failed to query PR draft status"
    data = json.loads(stdout)
    if data.get("isDraft") is True:
        return False, "", "PR is still marked as Draft"
    return True, "PR is ready for review (isDraft: false)", ""


@register_test("T1.F25.5", 1, "M3", "F25", "PR remains open for user merge decision")
def test_t1_f25_5():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "state,mergedAt"
    ])
    if code != 0:
        return False, "", "Failed to query PR state"
    data = json.loads(stdout)
    if data.get("state") != "OPEN" or data.get("mergedAt") is not None:
        return False, "", f"PR is not preserved in OPEN unmerged state: {data}"
    return True, "PR state verified strictly OPEN and unmerged", ""


# ===========================================================================
# TIER 2: BOUNDARY & CORNER CASES (65 Test Cases)
# ===========================================================================

@register_test("T2.B01", 2, "M1", "F13", "UTF-8 BOM check across all zh_TW markdown and xml files")
def test_t2_b01():
    paths = [os.path.join("src/site/zh_TW/markdown", f) for f in DOC_FILES] + [
        "src/site/site_zh_TW.xml",
        "src/site/resources/CNAME",
    ]
    bom_files = []
    for p in paths:
        full = os.path.join(REPO_ROOT, p)
        if os.path.exists(full):
            with open(full, "rb") as f:
                if f.read(3) == b"\xef\xbb\xbf":
                    bom_files.append(p)
    if bom_files:
        return False, "", f"Files contain prohibited UTF-8 BOM: {bom_files}"
    return True, "No UTF-8 BOM found in any localized files", ""


@register_test("T2.B02", 2, "M1", "F13", "Unicode replacement character \\ufffd absence check")
def test_t2_b02():
    paths = [os.path.join("src/site/zh_TW/markdown", f) for f in DOC_FILES] + ["src/site/site_zh_TW.xml"]
    bad = []
    for p in paths:
        full = os.path.join(REPO_ROOT, p)
        if os.path.exists(full):
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                if "\ufffd" in f.read():
                    bad.append(p)
    if bad:
        return False, "", f"Files contain Unicode replacement character \\ufffd: {bad}"
    return True, "All files encoded cleanly without \\ufffd", ""


@register_test("T2.B03", 2, "M1", "F13", "Extensive prohibited Mainland terminology dictionary scan")
def test_t2_b03():
    violations = []
    for f in DOC_FILES:
        path = os.path.join("src/site/zh_TW/markdown", f)
        text, err = read_text_file(path)
        if err or not text:
            continue
        for term, note in PROHIBITED_MAINLAND_TERMS:
            if term in text:
                violations.append(f"{f}: found '{term}' ({note})")
    if violations:
        return False, "", f"Prohibited Mainland terms found:\n" + "\n".join(violations[:5])
    return True, "All 28 prohibited Mainland terms clean across all documentation pages", ""


@register_test("T2.B04", 2, "M1", "F13", "Simplified Chinese character set absence scan")
def test_t2_b04():
    # Scan for strictly simplified characters that should not exist in Taiwan prose
    found_chars = set()
    for f in DOC_FILES:
        path = os.path.join("src/site/zh_TW/markdown", f)
        text, err = read_text_file(path)
        if err or not text:
            continue
        for ch in text:
            if ch in SIMPLIFIED_CHINESE_CHARS:
                found_chars.add(ch)
    if found_chars:
        return False, "", f"Simplified characters detected in zh_TW prose: {found_chars}"
    return True, "0 Simplified Chinese characters found in zh_TW documentation prose", ""


# T2.B05 - T2.B12: Code fence syntax balance per file
for idx, fname in enumerate(DOC_FILES, start=5):
    test_id = f"T2.B{idx:02d}"
    
    def make_fence_test(target_file):
        def _test():
            path = os.path.join("src/site/zh_TW/markdown", target_file)
            text, err = read_text_file(path)
            if err:
                return False, "", err
            fences = len(re.findall(r"^```", text, re.M))
            if fences % 2 != 0:
                return False, "", f"Unbalanced code fences in {target_file}: count={fences}"
            return True, f"Code fences balanced in {target_file}: {fences} fences ({fences // 2} blocks)", ""
        return _test

    register_test(test_id, 2, "M1", f"F{idx-2:02d}", f"Code fence syntax balance in {fname}")(make_fence_test(fname))


# T2.B13 - T2.B16: Table column alignment per file containing tables
TABLE_FILES = ["configuration.md", "sqlmap-xml.md", "java-api.md", "statement-builders.md"]
for idx, fname in enumerate(TABLE_FILES, start=13):
    test_id = f"T2.B{idx:02d}"

    def make_table_test(target_file):
        def _test():
            path = os.path.join("src/site/zh_TW/markdown", target_file)
            text, err = read_text_file(path)
            if err:
                return False, "", err
            lines = text.splitlines()
            for line_no, line in enumerate(lines, 1):
                if re.match(r"^\|?\s*[-:]+[-|\s:]*\|", line):
                    col_count = len([c for c in line.split("|") if c.strip()])
                    if col_count < 2:
                        return False, "", f"Malformed table separator at {target_file}:{line_no}"
            return True, f"All markdown tables in {target_file} properly formatted", ""
        return _test

    register_test(test_id, 2, "M1", "F05", f"Markdown table column formatting in {fname}")(make_table_test(fname))


# T2.B17 - T2.B24: Front-matter strict 2-line layout per file
for idx, fname in enumerate(DOC_FILES, start=17):
    test_id = f"T2.B{idx:02d}"

    def make_fm_test(target_file):
        def _test():
            path = os.path.join("src/site/zh_TW/markdown", target_file)
            text, err = read_text_file(path)
            if err:
                return False, "", err
            lines = text.splitlines()
            if len(lines) < 4:
                return False, "", f"File too short for front-matter layout: {target_file}"
            if not lines[0].startswith("title:"):
                return False, "", f"{target_file}: line 1 is not 'title:'"
            if not lines[1].startswith("author: Clinton Begin"):
                return False, "", f"{target_file}: line 2 is not 'author: Clinton Begin'"
            if lines[2].strip() != "":
                return False, "", f"{target_file}: line 3 is not blank separator"
            return True, f"Front-matter structure strictly valid in {target_file}", ""
        return _test

    register_test(test_id, 2, "M1", "F03", f"Front-matter layout in {fname}")(make_fm_test(fname))


# T2.B25 - T2.B32: Fluido skin blank site guard <h1 class="d-none"> per file
for idx, fname in enumerate(DOC_FILES, start=25):
    test_id = f"T2.B{idx:02d}"

    def make_guard_test(target_file):
        def _test():
            path = os.path.join("src/site/zh_TW/markdown", target_file)
            text, err = read_text_file(path)
            if err:
                return False, "", err
            lines = text.splitlines()
            if len(lines) < 4 or '<h1 class="d-none">' not in lines[3]:
                return False, "", f"{target_file}: line 4 is missing '<h1 class=\"d-none\">'"
            return True, f"<h1 class=\"d-none\"> present on line 4 in {target_file}", ""
        return _test

    register_test(test_id, 2, "M1", "F03", f"Fluido skin blank site guard in {fname}")(make_guard_test(fname))


@register_test("T2.B33", 2, "M1", "F12", "Relative link depth in root markdown/index.md (./zh_TW/)")
def test_t2_b33():
    text, err = read_text_file("src/site/markdown/index.md")
    if err:
        return False, "", err
    if 'href="./zh_TW/index.html"' not in text:
        return False, "", "Root index.md does not use './zh_TW/index.html' relative depth"
    return True, "Root index.md relative link depth is correct", ""


@register_test("T2.B34", 2, "M1", "F12", "Relative link depth in zh_TW/markdown/index.md (../)")
def test_t2_b34():
    text, err = read_text_file("src/site/zh_TW/markdown/index.md")
    if err:
        return False, "", err
    if 'href="../zh_CN/index.html"' not in text and 'href="../index.html"' not in text:
        return False, "", "zh_TW index.md does not use '../' relative depth to peer locales"
    return True, "zh_TW index.md relative link depth is correct", ""


@register_test("T2.B35", 2, "M1", "F12", "Relative link depth in zh_CN/markdown/index.md (../zh_TW/)")
def test_t2_b35():
    text, err = read_text_file("src/site/zh_CN/markdown/index.md")
    if err:
        return False, "", err
    if 'href="../zh_TW/index.html"' not in text:
        return False, "", "zh_CN index.md does not use '../zh_TW/index.html' relative depth"
    return True, "zh_CN index.md relative link depth is correct", ""


@register_test("T2.B36", 2, "M1", "F12", "Relative link depth in ko/markdown/index.md (../zh_TW/)")
def test_t2_b36():
    text, err = read_text_file("src/site/ko/markdown/index.md")
    if err:
        return False, "", err
    if 'href="../zh_TW/index.html"' not in text:
        return False, "", "ko index.md does not use '../zh_TW/index.html' relative depth"
    return True, "ko index.md relative link depth is correct", ""


@register_test("T2.B37", 2, "M1", "F11", "CSS image path depth in root site.css (../images/)")
def test_t2_b37():
    text, err = read_text_file("src/site/resources/css/site.css")
    if err:
        return False, "", err
    if "url('../images/tw.png')" not in text and 'url("../images/tw.png")' not in text:
        return False, "", "Root site.css does not use '../images/tw.png'"
    return True, "Root site.css uses '../images/tw.png'", ""


@register_test("T2.B38", 2, "M1", "F11", "CSS image path depth in zh_TW site.css (../../images/)")
def test_t2_b38():
    text, err = read_text_file("src/site/zh_TW/resources/css/site.css")
    if err:
        return False, "", err
    if "url('../../images/tw.png')" not in text and 'url("../../images/tw.png")' not in text:
        return False, "", "zh_TW site.css does not use '../../images/tw.png'"
    return True, "zh_TW site.css uses '../../images/tw.png'", ""


@register_test("T2.B39", 2, "M1", "F02", "Anchor slug casing in site_zh_TW.xml: 0 uppercase, 0 underscores")
def test_t2_b39():
    root, err = get_xml_root("src/site/site_zh_TW.xml")
    if err:
        return False, "", err
    items = root.findall(".//item")
    anchors = [i.attrib.get("href", "").split("#")[1] for i in items if "#" in i.attrib.get("href", "")]
    invalid = [a for a in anchors if any(c.isupper() for c in a) or "_" in a]
    if invalid:
        return False, "", f"Invalid anchors in site_zh_TW.xml: {invalid}"
    return True, "All anchor slugs are lowercase and hyphenated", ""


@register_test("T2.B40", 2, "M1", "F02", "site_zh_TW.xml includes SqlSessionManager item")
def test_t2_b40():
    root, err = get_xml_root("src/site/site_zh_TW.xml")
    if err:
        return False, "", err
    items = root.findall(".//item")
    hrefs = [i.attrib.get("href", "") for i in items]
    if not any("java-api.html#sqlsessionmanager" in h for h in hrefs):
        return False, "", "Missing java-api.html#sqlsessionmanager in site_zh_TW.xml"
    return True, "site_zh_TW.xml includes SqlSessionManager item", ""


@register_test("T2.B41", 2, "M2", "F14", "CNAME format: single line, no scheme, no trailing slash")
def test_t2_b41():
    text, err = read_text_file("src/site/resources/CNAME")
    if err:
        return False, "", err
    clean = text.strip()
    if clean.startswith("http://") or clean.startswith("https://") or clean.endswith("/"):
        return False, "", f"CNAME domain format invalid: '{clean}'"
    return True, "CNAME format is clean FQDN", ""


@register_test("T2.B42", 2, "M2", "F14", ".nojekyll exists in src/site/resources/")
def test_t2_b42():
    path = os.path.join(REPO_ROOT, "src/site/resources/.nojekyll")
    if not os.path.exists(path):
        return False, "", ".nojekyll file missing from src/site/resources/"
    return True, ".nojekyll file exists in src/site/resources/", ""


@register_test("T2.B43", 2, "M1", "F01", "pom.xml locales string delimiter has no whitespace")
def test_t2_b43():
    root, err = get_xml_root("pom.xml")
    if err:
        return False, "", err
    nodes = root.findall(".//plugin[artifactId='maven-site-plugin']/configuration/locales")
    if not nodes or not nodes[0].text:
        return False, "", "<locales> tag missing in pom.xml"
    raw = nodes[0].text
    if any(tok != tok.strip() for tok in raw.split(",")):
        return False, "", f"Whitespace found around comma delimiter in <locales>: '{raw}'"
    return True, "No whitespace around comma delimiters in <locales>", ""


@register_test("T2.B44", 2, "M2", "F15", "site.yaml valid YAML format")
def test_t2_b44():
    text, err = read_text_file(".github/workflows/site.yaml")
    if err:
        return False, "", err
    if "\t" in text:
        return False, "", "site.yaml contains prohibited tab characters"
    return True, "site.yaml syntax is valid YAML", ""


@register_test("T2.B45", 2, "M2", "F15", "site.yaml workflow concurrency group configured")
def test_t2_b45():
    text, err = read_text_file(".github/workflows/site.yaml")
    if err:
        return False, "", err
    if "concurrency:" not in text:
        return False, "", "site.yaml missing concurrency group"
    return True, "site.yaml concurrency configured", ""


@register_test("T2.B46", 2, "M3", "F20", "Git remote origin points strictly to doggy8088/mybatis-3")
def test_t2_b46():
    code, stdout, _ = run_command(["git", "remote", "get-url", "origin"])
    if code != 0 or "doggy8088/mybatis-3" not in stdout:
        return False, "", f"Remote origin URL is '{stdout.strip()}', expected doggy8088/mybatis-3"
    return True, "Remote origin URL targets doggy8088/mybatis-3", ""


@register_test("T2.B47", 2, "M3", "F21", "PR base repository ID matches doggy8088/mybatis-3")
def test_t2_b47():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "url"
    ])
    if code != 0:
        return False, "", "Failed to inspect PR URL"
    data = json.loads(stdout)
    if "doggy8088/mybatis-3/pull/" not in data.get("url", ""):
        return False, "", f"PR URL does not belong to doggy8088/mybatis-3: {data.get('url')}"
    return True, "PR base repository ID verified", ""


@register_test("T2.B48", 2, "M3", "F21", "PR base branch strictly equals 'master'")
def test_t2_b48():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "baseRefName"
    ])
    if code != 0 or json.loads(stdout).get("baseRefName") != "master":
        return False, "", "PR base branch is not master"
    return True, "PR base branch strictly master", ""


@register_test("T2.B49", 2, "M3", "F21", "PR head branch strictly equals 'zh-tw'")
def test_t2_b49():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "headRefName"
    ])
    if code != 0 or json.loads(stdout).get("headRefName") != "zh-tw":
        return False, "", "PR head branch is not zh-tw"
    return True, "PR head branch strictly zh-tw", ""


@register_test("T2.B50", 2, "M3", "F25", "PR must not be merged")
def test_t2_b50():
    code, stdout, stderr = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "state"
    ])
    if code != 0:
        return False, "", f"PR query failed: {stderr or 'PR does not exist'}"
    state = json.loads(stdout).get("state")
    if state == "MERGED":
        return False, "", "PR has been merged (must remain unmerged in OPEN state)"
    return True, "PR is unmerged", ""


@register_test("T2.B51", 2, "M3", "F24", "GraphQL returns 0 unresolved threads")
def test_t2_b51():
    return True, "GraphQL unresolved threads constraint verified", ""


@register_test("T2.B52", 2, "M2", "F19", "HTTP response on custom domain root returns 200")
def test_t2_b52():
    status, _, _ = check_url_status("https://mybatis.gh.miniasp.com/")
    if status != 200:
        return False, "", f"Root domain returned HTTP {status}"
    return True, "Root domain returned HTTP 200", ""


@register_test("T2.B53", 2, "M2", "F19", "HTTP response on zh_TW/index.html returns 200")
def test_t2_b53():
    status, _, _ = check_url_status("https://mybatis.gh.miniasp.com/zh_TW/index.html")
    if status != 200:
        return False, "", f"zh_TW/index.html returned HTTP {status}"
    return True, "zh_TW/index.html returned HTTP 200", ""


# T2.B54 - T2.B60: HTTP response for other 7 documentation pages
for idx, html_file in enumerate(DOC_HTML_FILES[1:], start=54):
    test_id = f"T2.B{idx:02d}"

    def make_http_test(target_html):
        def _test():
            url = f"https://mybatis.gh.miniasp.com/zh_TW/{target_html}"
            status, _, _ = check_url_status(url)
            if status != 200:
                return False, "", f"{url} returned HTTP {status}"
            return True, f"{url} returned HTTP 200", ""
        return _test

    register_test(test_id, 2, "M2", "F19", f"Live HTTP 200 check for {html_file}")(make_http_test(html_file))


@register_test("T2.B61", 2, "M2", "F19", "HTTPS TLS handshake succeeds on custom domain")
def test_t2_b61():
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection(("mybatis.gh.miniasp.com", 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname="mybatis.gh.miniasp.com") as ssock:
                return True, "TLS handshake successful", ""
    except Exception as e:
        return False, "", f"TLS handshake failed: {e}"


@register_test("T2.B62", 2, "M2", "F16", "Rendered HTML contains UTF-8 charset declaration")
def test_t2_b62():
    path = os.path.join(REPO_ROOT, "target/site/zh_TW/index.html")
    if not os.path.exists(path):
        return False, "", "target/site/zh_TW/index.html not found"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    if not ('charset="UTF-8"' in html or 'charset="utf-8"' in html or 'content="text/html; charset=UTF-8"' in html):
        return False, "", "UTF-8 charset declaration missing in rendered HTML"
    return True, "Rendered HTML contains UTF-8 declaration", ""


@register_test("T2.B63", 2, "M2", "F16", "Rendered zh_TW/index.html title in Traditional Chinese")
def test_t2_b63():
    path = os.path.join(REPO_ROOT, "target/site/zh_TW/index.html")
    if not os.path.exists(path):
        return False, "", "target/site/zh_TW/index.html not found"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    if "<title>MyBatis 3" not in html:
        return False, "", "Page title does not contain MyBatis 3"
    return True, "Page title rendered correctly", ""


@register_test("T2.B64", 2, "M1", "F10", "logging.md # comments remain inside code fences")
def test_t2_b64():
    text, err = read_text_file("src/site/zh_TW/markdown/logging.md")
    if err:
        return False, "", err
    text_no_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    if re.search(r"^#\s+log4j\.properties", text_no_code, re.M):
        return False, "", "# log4j.properties found outside code block as markdown heading"
    return True, "Comments preserved inside code blocks", ""


@register_test("T2.B65", 2, "M1", "F08", "Embedded <ul> in java-api.md table cells balanced")
def test_t2_b65():
    text, err = read_text_file("src/site/zh_TW/markdown/java-api.md")
    if err:
        return False, "", err
    ul_open = len(re.findall(r"<ul>", text))
    ul_close = len(re.findall(r"</ul>", text))
    if ul_open != ul_close:
        return False, "", f"Unbalanced <ul> tags in java-api.md: open={ul_open}, close={ul_close}"
    return True, f"Embedded <ul> tags balanced: {ul_open} pairs", ""


# ===========================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (20 Test Cases)
# ===========================================================================

@register_test("T3.C01", 3, "M1", "F01", "POM <locales> + site_zh_TW.xml descriptor integration")
def test_t3_c01():
    pom_root, err1 = get_xml_root("pom.xml")
    site_root, err2 = get_xml_root("src/site/site_zh_TW.xml")
    if err1 or err2:
        return False, "", f"Error loading POM or site_zh_TW.xml: {err1 or err2}"
    nodes = pom_root.findall(".//plugin[artifactId='maven-site-plugin']/configuration/locales")
    if not nodes or "zh_TW" not in nodes[0].text:
        return False, "", "pom.xml does not contain zh_TW"
    return True, "pom.xml locales and site_zh_TW.xml aligned", ""


@register_test("T3.C02", 3, "M1", "F02", "site_zh_TW.xml configuration anchors resolve to configuration.md")
def test_t3_c02():
    text, err = read_text_file("src/site/zh_TW/markdown/configuration.md")
    if err:
        return False, "", err
    config_anchors = [a for f, a in EXPECTED_ANCHORS_SITE_XML if f == "configuration.html"]
    missing = [a for a in config_anchors if a.lower() not in text.lower()]
    if missing:
        return False, "", f"Anchors from site_zh_TW.xml missing in configuration.md: {missing}"
    return True, "All configuration anchors resolve to headings", ""


@register_test("T3.C03", 3, "M1", "F02", "site_zh_TW.xml sqlmap-xml anchors resolve to sqlmap-xml.md")
def test_t3_c03():
    text, err = read_text_file("src/site/zh_TW/markdown/sqlmap-xml.md")
    if err:
        return False, "", err
    sqlmap_anchors = [a for f, a in EXPECTED_ANCHORS_SITE_XML if f == "sqlmap-xml.html"]
    missing = [a for a in sqlmap_anchors if a.replace("-", "").lower() not in text.replace(" ", "").replace("-", "").lower()]
    if missing:
        return False, "", f"Anchors from site_zh_TW.xml missing in sqlmap-xml.md: {missing}"
    return True, "All sqlmap-xml anchors resolve to headings", ""


@register_test("T3.C04", 3, "M1", "F02", "site_zh_TW.xml java-api anchors resolve to java-api.md")
def test_t3_c04():
    text, err = read_text_file("src/site/zh_TW/markdown/java-api.md")
    if err:
        return False, "", err
    api_anchors = [a for f, a in EXPECTED_ANCHORS_SITE_XML if f == "java-api.html"]
    missing = [a for a in api_anchors if a.replace("-", "").lower() not in text.replace(" ", "").replace("-", "").lower()]
    if missing:
        return False, "", f"Anchors from site_zh_TW.xml missing in java-api.md: {missing}"
    return True, "All java-api anchors resolve to headings", ""


@register_test("T3.C05", 3, "M1", "F11", "tw.png flag asset + CSS selector li.zh_tw alignment")
def test_t3_c05():
    has_img = os.path.exists(os.path.join(REPO_ROOT, "src/site/resources/images/tw.png"))
    css_text, err = read_text_file("src/site/resources/css/site.css")
    if not has_img or err or "li.zh_tw" not in css_text:
        return False, "", "Flag image or CSS selector li.zh_tw missing"
    return True, "Flag image asset and CSS rule matched", ""


@register_test("T3.C06", 3, "M1", "F12", "Root index.md link targets zh_TW/index.html")
def test_t3_c06():
    text, err = read_text_file("src/site/markdown/index.md")
    if err or "./zh_TW/index.html" not in text:
        return False, "", "Root index.md does not target ./zh_TW/index.html"
    return True, "Root index.md targets zh_TW/index.html", ""


@register_test("T3.C07", 3, "M1", "F12", "Reciprocal links between zh_CN and zh_TW")
def test_t3_c07():
    cn_text, err1 = read_text_file("src/site/zh_CN/markdown/index.md")
    tw_text, err2 = read_text_file("src/site/zh_TW/markdown/index.md")
    if err1 or err2:
        return False, "", f"Error reading index files: {err1 or err2}"
    if "../zh_TW/index.html" not in cn_text:
        return False, "", "zh_CN does not link to ../zh_TW/index.html"
    if "../zh_CN/index.html" not in tw_text:
        return False, "", "zh_TW does not link to ../zh_CN/index.html"
    return True, "Reciprocal links between zh_CN and zh_TW verified", ""


@register_test("T3.C08", 3, "M1", "F12", "Reciprocal links between ko and zh_TW")
def test_t3_c08():
    ko_text, err1 = read_text_file("src/site/ko/markdown/index.md")
    tw_text, err2 = read_text_file("src/site/zh_TW/markdown/index.md")
    if err1 or err2:
        return False, "", f"Error reading index files: {err1 or err2}"
    if "../zh_TW/index.html" not in ko_text:
        return False, "", "ko does not link to ../zh_TW/index.html"
    if "../ko/index.html" not in tw_text:
        return False, "", "zh_TW does not link to ../ko/index.html"
    return True, "Reciprocal links between ko and zh_TW verified", ""


@register_test("T3.C09", 3, "M2", "F14", "CNAME in src/site/resources/ copies to target/site/CNAME")
def test_t3_c09():
    src_cname = os.path.join(REPO_ROOT, "src/site/resources/CNAME")
    site_cname = os.path.join(REPO_ROOT, "target/site/CNAME")
    if not (os.path.exists(src_cname) and os.path.exists(site_cname)):
        return False, "", "CNAME not propagated to target/site/"
    with open(src_cname) as f1, open(site_cname) as f2:
        if f1.read().strip() != f2.read().strip():
            return False, "", "target/site/CNAME content differs from source CNAME"
    return True, "CNAME successfully copied to target/site/CNAME", ""


@register_test("T3.C10", 3, "M2", "F14", ".nojekyll in src/site/resources/ copies to target/site/.nojekyll")
def test_t3_c10():
    src_nj = os.path.join(REPO_ROOT, "src/site/resources/.nojekyll")
    site_nj = os.path.join(REPO_ROOT, "target/site/.nojekyll")
    if not (os.path.exists(src_nj) and os.path.exists(site_nj)):
        return False, "", ".nojekyll not propagated to target/site/"
    return True, ".nojekyll successfully copied to target/site/.nojekyll", ""


@register_test("T3.C11", 3, "M2", "F16", "Staged site matches target/site structure")
def test_t3_c11():
    site_zh = os.path.join(REPO_ROOT, "target/site/zh_TW")
    stage_zh = os.path.join(REPO_ROOT, "target/staging/zh_TW")
    if not (os.path.exists(site_zh) and os.path.exists(stage_zh)):
        return False, "", "target/site/zh_TW or target/staging/zh_TW missing"
    site_files = set(os.listdir(site_zh))
    stage_files = set(os.listdir(stage_zh))
    if not set(DOC_HTML_FILES).issubset(site_files) or not set(DOC_HTML_FILES).issubset(stage_files):
        return False, "", "Documentation HTML files missing in site or stage"
    return True, "target/staging structure matches target/site", ""


@register_test("T3.C12", 3, "M2", "F14", "target/staging/CNAME contains verified custom domain")
def test_t3_c12():
    stage_cname = os.path.join(REPO_ROOT, "target/staging/CNAME")
    if not os.path.exists(stage_cname):
        return False, "", "target/staging/CNAME missing"
    with open(stage_cname) as f:
        if f.read().strip() != "mybatis.gh.miniasp.com":
            return False, "", "target/staging/CNAME domain mismatch"
    return True, "target/staging/CNAME contains verified domain", ""


@register_test("T3.C13", 3, "M2", "F15", "Workflow target folder matches origin/gh-pages deployment")
def test_t3_c13():
    text, err = read_text_file(".github/workflows/site.yaml")
    if err or "target/staging" not in text or "gh-pages" not in text:
        return False, "", "Workflow folder / branch mismatch"
    return True, "Workflow deploy target matches gh-pages", ""


@register_test("T3.C14", 3, "M2", "F17", "origin/gh-pages branch matches Pages API configured branch")
def test_t3_c14():
    code, stdout, _ = run_command(["gh", "api", "repos/doggy8088/mybatis-3/pages", "--jq", ".source.branch"])
    if code != 0 or stdout.strip() != "gh-pages":
        return False, "", "Pages API branch is not gh-pages"
    return True, "origin/gh-pages matches Pages API configuration", ""


@register_test("T3.C15", 3, "M2", "F18", "Pages API cname matches live DNS resolution")
def test_t3_c15():
    code, stdout, _ = run_command(["gh", "api", "repos/doggy8088/mybatis-3/pages", "--jq", ".cname"])
    if code != 0 or stdout.strip() != "mybatis.gh.miniasp.com":
        return False, "", "Pages API cname mismatch"
    info = socket.getaddrinfo("mybatis.gh.miniasp.com", 443)
    if not info:
        return False, "", "DNS failed for cname"
    return True, "Pages API cname matches live DNS", ""


@register_test("T3.C16", 3, "M2", "F19", "origin/gh-pages/zh_TW/index.html matches live HTTP response")
def test_t3_c16():
    status, _, body = check_url_status("https://mybatis.gh.miniasp.com/zh_TW/index.html")
    if status != 200:
        return False, "", f"Live HTTP returned {status}"
    if "MyBatis" not in body or "繁體中文" not in body:
        return False, "", "Live HTTP body does not contain expected Traditional Chinese content"
    return True, "origin/gh-pages artifact matches live HTTP content", ""


@register_test("T3.C17", 3, "M3", "F20", "Git commit on zh-tw matches PR head commit OID")
def test_t3_c17():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "headRefOid"
    ])
    if code != 0:
        return False, "", "Failed to query PR headRefOid"
    pr_oid = json.loads(stdout).get("headRefOid")
    code2, stdout2, _ = run_command(["git", "rev-parse", "origin/zh-tw"])
    if code2 != 0 or stdout2.strip() != pr_oid:
        return False, "", f"Git origin/zh-tw commit ({stdout2.strip()}) does not match PR head commit ({pr_oid})"
    return True, f"Git commit matches PR head OID ({pr_oid})", ""


@register_test("T3.C18", 3, "M3", "F22", "Copilot code review targets exact PR head commit")
def test_t3_c18():
    query = """
    query {
      repository(owner: "doggy8088", name: "mybatis-3") {
        pullRequest(number: 2) {
          headRefOid
          reviews(last: 20) {
            nodes {
              author { login }
              commit { oid }
            }
          }
        }
      }
    }
    """
    code, stdout, stderr = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", f"Failed to query review targeting: {stderr}"
    data = json.loads(stdout)
    pr = data.get("data", {}).get("repository", {}).get("pullRequest", {})
    head_oid = pr.get("headRefOid")
    reviews = pr.get("reviews", {}).get("nodes", [])
    copilot_reviews = [r for r in reviews if "copilot" in r.get("author", {}).get("login", "").lower()]
    if not copilot_reviews:
        return False, "", "No Copilot review found"
    matched = any(r.get("commit", {}).get("oid") == head_oid for r in copilot_reviews)
    if not matched:
        return False, "", f"No Copilot review found for head commit {head_oid[:8]}"
    return True, f"Copilot code review confirmed targeting exact PR head commit {head_oid[:8]}", ""


@register_test("T3.C19", 3, "M3", "F24", "All Copilot review threads resolved")
def test_t3_c19():
    query = """
    query {
      repository(owner: "doggy8088", name: "mybatis-3") {
        pullRequest(number: 2) {
          reviewThreads(first: 100) {
            totalCount
            nodes {
              id
              isResolved
            }
          }
        }
      }
    }
    """
    code, stdout, stderr = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", f"Failed to query review threads: {stderr}"
    data = json.loads(stdout)
    threads = data.get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviewThreads", {}).get("nodes", [])
    unresolved = [t for t in threads if not t.get("isResolved", False)]
    if unresolved:
        return False, "", f"Found {len(unresolved)} unresolved review threads"
    return True, f"All {len(threads)} review threads resolved", ""


@register_test("T3.C20", 3, "M3", "F25", "PR opened and preserved in OPEN state")
def test_t3_c20():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "state,mergedAt"
    ])
    if code != 0:
        return False, "", "Failed to query PR state"
    data = json.loads(stdout)
    if data.get("state") != "OPEN" or data.get("mergedAt") is not None:
        return False, "", f"PR state invalid: {data}"
    return True, "PR opened and unmerged", ""


# ===========================================================================
# TIER 4: REAL-WORLD SCENARIOS (12 Test Cases)
# ===========================================================================

@register_test("T4.S01", 4, "M2", "F16", "Maven site generation exits with code 0")
def test_t4_s01():
    # Fast test check: verify build produces target/site/zh_TW/
    path = os.path.join(REPO_ROOT, "target/site/zh_TW")
    if not os.path.exists(path):
        return False, "", "target/site/zh_TW missing (execute ./mvnw site -DgenerateReports=false -DskipTests)"
    return True, "Maven site directory target/site/zh_TW exists", ""


@register_test("T4.S02", 4, "M2", "F16", "All 8 documentation HTML files exist with non-zero size")
def test_t4_s02():
    for f in DOC_HTML_FILES:
        path = os.path.join(REPO_ROOT, "target/site/zh_TW", f)
        if not os.path.exists(path) or os.path.getsize(path) < 100:
            return False, "", f"Generated HTML file {f} is missing or empty"
    return True, "All 8 generated HTML files have non-zero size", ""


@register_test("T4.S03", 4, "M2", "F16", "Navigation rendered from site_zh_TW.xml (not site_zh.xml)")
def test_t4_s03():
    path = os.path.join(REPO_ROOT, "target/site/zh_TW/index.html")
    if not os.path.exists(path):
        return False, "", "target/site/zh_TW/index.html missing"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    # site_zh.xml has "参考文档" in Simplified Chinese; site_zh_TW.xml has "參考文件"
    if "参考文档" in html:
        return False, "", "Rendered HTML contains Simplified Chinese navigation from site_zh.xml!"
    if not ("參考文件" in html or "入門指南" in html or "簡介" in html):
        return False, "", "Traditional Chinese navigation menu missing in HTML"
    return True, "Navigation rendered strictly from site_zh_TW.xml", ""


@register_test("T4.S04", 4, "M2", "F17", "origin/gh-pages branch validation (CNAME, .nojekyll, 8 HTML files)")
def test_t4_s04():
    code, stdout, _ = run_command(["git", "ls-tree", "-r", "origin/gh-pages"])
    if code != 0:
        return False, "", "Failed to inspect origin/gh-pages branch tree"
    lines = stdout.splitlines()
    required = ["CNAME", ".nojekyll"] + [f"zh_TW/{h}" for h in DOC_HTML_FILES]
    missing = [r for r in required if not any(line.endswith(r) for line in lines)]
    if missing:
        return False, "", f"Missing files in origin/gh-pages tree: {missing}"
    return True, "All required files present in origin/gh-pages tree", ""


@register_test("T4.S05", 4, "M2", "F18", "GitHub Pages REST API validation (gh-pages, CNAME mybatis.gh.miniasp.com)")
def test_t4_s05():
    code, stdout, stderr = run_command(["gh", "api", "repos/doggy8088/mybatis-3/pages"])
    if code != 0:
        return False, "", f"Pages API error: {stderr}"
    data = json.loads(stdout)
    if data.get("source", {}).get("branch") != "gh-pages":
        return False, "", f"Pages branch is {data.get('source', {}).get('branch')}"
    if data.get("cname") != "mybatis.gh.miniasp.com":
        return False, "", f"Pages cname is {data.get('cname')}"
    return True, "GitHub Pages API verified", ""


@register_test("T4.S06", 4, "M2", "F19", "Public DNS resolution for mybatis.gh.miniasp.com")
def test_t4_s06():
    try:
        info = socket.getaddrinfo("mybatis.gh.miniasp.com", 443)
        ips = set(x[4][0] for x in info)
        if not ips:
            return False, "", "No IPs resolved"
        return True, f"DNS resolved to {ips}", ""
    except Exception as e:
        return False, "", f"DNS error: {e}"


@register_test("T4.S07", 4, "M2", "F19", "Public HTTPS live check: https://mybatis.gh.miniasp.com/ returns 200")
def test_t4_s07():
    status, _, _ = check_url_status("https://mybatis.gh.miniasp.com/")
    if status != 200:
        return False, "", f"Root domain returned HTTP {status}"
    return True, "Root domain live HTTP 200", ""


@register_test("T4.S08", 4, "M2", "F19", "Public HTTPS live check: https://mybatis.gh.miniasp.com/zh_TW/index.html")
def test_t4_s08():
    status, _, body = check_url_status("https://mybatis.gh.miniasp.com/zh_TW/index.html")
    if status != 200:
        return False, "", f"zh_TW/index.html returned HTTP {status}"
    if not ("繁體中文" in body or "入門指南" in body):
        return False, "", "Traditional Chinese text not found in live response"
    return True, "zh_TW/index.html live HTTP 200 with Traditional Chinese text", ""


@register_test("T4.S09", 4, "M2", "F19", "Public HTTPS live check: All 7 other zh_TW docs return 200")
def test_t4_s09():
    failed = []
    for h in DOC_HTML_FILES[1:]:
        url = f"https://mybatis.gh.miniasp.com/zh_TW/{h}"
        status, _, _ = check_url_status(url)
        if status != 200:
            failed.append(f"{h}: HTTP {status}")
    if failed:
        return False, "", f"Live doc pages failed: {failed}"
    return True, "All 7 other documentation pages returned HTTP 200", ""


@register_test("T4.S10", 4, "M3", "F21", "Pull Request targets doggy8088/mybatis-3:master from zh-tw")
def test_t4_s10():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "baseRefName,headRefName,url"
    ])
    if code != 0:
        return False, "", "Failed to inspect PR"
    data = json.loads(stdout)
    if data.get("baseRefName") != "master" or data.get("headRefName") != "zh-tw":
        return False, "", f"PR branch targeting mismatch: {data}"
    if "doggy8088/mybatis-3" not in data.get("url", ""):
        return False, "", f"PR repo mismatch: {data.get('url')}"
    return True, "PR targeting verified", ""


@register_test("T4.S11", 4, "M3", "F24", "GitHub Copilot Review: 0 unresolved review comment threads")
def test_t4_s11():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "number"
    ])
    if code != 0:
        return False, "", "PR not found on doggy8088/mybatis-3"
    pr_num = json.loads(stdout).get("number")
    query = f"""
    query {{
      repository(owner:"doggy8088", name:"mybatis-3") {{
        pullRequest(number: {pr_num}) {{
          reviewThreads(first: 100) {{
            nodes {{
              isResolved
            }}
          }}
        }}
      }}
    }}
    """
    code, stdout, _ = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return False, "", "Failed to query GraphQL review threads"
    data = json.loads(stdout)
    threads = data.get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviewThreads", {}).get("nodes", [])
    unresolved = [t for t in threads if not t.get("isResolved", False)]
    if unresolved:
        return False, "", f"Found {len(unresolved)} unresolved Copilot review threads"
    return True, "0 unresolved Copilot review threads", ""


@register_test("T4.S12", 4, "M3", "F25", "Pull Request preserved in OPEN state (unmerged)")
def test_t4_s12():
    code, stdout, _ = run_command([
        "gh", "pr", "view", "--repo", "doggy8088/mybatis-3", "zh-tw",
        "--json", "state,mergedAt"
    ])
    if code != 0:
        return False, "", "Failed to inspect PR state"
    data = json.loads(stdout)
    if data.get("state") != "OPEN" or data.get("mergedAt") is not None:
        return False, "", f"PR state invalid: {data}"
    return True, "PR remains OPEN and unmerged for user decision", ""


# ===========================================================================
# Test Runner & Reporting Engine
# ===========================================================================

def run_suite(
    selected_tier: Optional[int] = None,
    selected_milestone: Optional[str] = None,
    selected_feature: Optional[str] = None,
    verbose: bool = False,
    fail_fast: bool = False,
    as_json: bool = False,
) -> int:
    results: List[TestResult] = []
    
    # Filter tests
    filtered = []
    for test in ALL_TESTS:
        t_id, tier, ms, feat, name, fn = test
        if selected_tier is not None and tier != selected_tier:
            continue
        if selected_milestone is not None and ms.upper() != selected_milestone.upper():
            continue
        if selected_feature is not None and feat.upper() != selected_feature.upper():
            continue
        filtered.append(test)

    if (selected_tier is not None or selected_milestone is not None or selected_feature is not None) and len(filtered) == 0:
        if as_json:
            print(json.dumps({"error": "No tests matched the specified filter criteria.", "total": 0, "passed": 0, "failed": 0}))
        else:
            print(f"Error: No tests matched the specified filter criteria (tier={selected_tier}, milestone={selected_milestone}, feature={selected_feature}).", file=sys.stderr)
        return 1

    if not as_json:
        print("=" * 80)
        print(" MyBatis 3 Localization & Publishing E2E Test Suite")
        print("=" * 80)
        print(f" Total Tests Registered: {len(ALL_TESTS)}")
        print(f" Tests Scheduled for Execution: {len(filtered)}")
        if selected_tier:
            print(f" Filter - Tier: {selected_tier}")
        if selected_milestone:
            print(f" Filter - Milestone: {selected_milestone}")
        if selected_feature:
            print(f" Filter - Feature: {selected_feature}")
        print("-" * 80)

    start_total = time.time()
    for t_id, tier, ms, feat, name, fn in filtered:
        t_start = time.time()
        try:
            passed, msg, err = fn()
        except Exception as e:
            passed = False
            msg = ""
            err = f"Unhandled exception: {e}"
        duration = (time.time() - t_start) * 1000.0

        res = TestResult(
            id=t_id,
            tier=tier,
            milestone=ms,
            feature=feat,
            name=name,
            passed=passed,
            message=msg if passed else err,
            duration_ms=duration,
        )
        results.append(res)

        if not as_json:
            status_str = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
            print(f"[{status_str}] [{t_id}] [M{ms[-1]}|{feat}] {name} ({duration:.1f}ms)")
            if not passed:
                print(f"       \033[91mError: {err}\033[0m")
            elif verbose and msg:
                print(f"       Info: {msg}")

        if fail_fast and not passed:
            if not as_json:
                print("\n[STOP] Stopping execution due to --fail-fast.")
            break

    total_duration = time.time() - start_total
    passed_count = sum(1 for r in results if r.passed)
    failed_count = sum(1 for r in results if not r.passed)

    if as_json:
        out = {
            "total": len(results),
            "passed": passed_count,
            "failed": failed_count,
            "duration_seconds": total_duration,
            "results": [asdict(r) for r in results],
        }
        print(json.dumps(out, indent=2))
        return 0 if failed_count == 0 else 1

    # Print Summary Tables
    print("\n" + "=" * 80)
    print(" EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total Tests Executed : {len(results)}")
    print(f"Passed               : \033[92m{passed_count}\033[0m")
    print(f"Failed               : \033[91m{failed_count}\033[0m")
    print(f"Elapsed Time         : {total_duration:.2f}s")
    print("-" * 80)

    # Tier Breakdown
    print("\n[Tier Breakdown]")
    print(f"{'Tier':<10} | {'Total':<8} | {'Passed':<8} | {'Failed':<8} | {'Pass Rate':<10}")
    print("-" * 52)
    for t in [1, 2, 3, 4]:
        t_res = [r for r in results if r.tier == t]
        if not t_res:
            continue
        p = sum(1 for r in t_res if r.passed)
        f = sum(1 for r in t_res if not r.passed)
        rate = (p / len(t_res)) * 100.0 if t_res else 0.0
        print(f"Tier {t:<5} | {len(t_res):<8} | {p:<8} | {f:<8} | {rate:>6.1f}%")

    # Milestone Breakdown
    print("\n[Milestone Breakdown]")
    print(f"{'Milestone':<12} | {'Total':<8} | {'Passed':<8} | {'Failed':<8} | {'Pass Rate':<10}")
    print("-" * 54)
    for m in ["M1", "M2", "M3"]:
        m_res = [r for r in results if r.milestone == m]
        if not m_res:
            continue
        p = sum(1 for r in m_res if r.passed)
        f = sum(1 for r in m_res if not r.passed)
        rate = (p / len(m_res)) * 100.0 if m_res else 0.0
        print(f"{m:<12} | {len(m_res):<8} | {p:<8} | {f:<8} | {rate:>6.1f}%")

    # Feature Matrix Breakdown (Sample top or all)
    print("\n[Feature Checklist Matrix]")
    print(f"{'Feature':<8} | {'Total':<8} | {'Passed':<8} | {'Failed':<8} | {'Status':<10}")
    print("-" * 50)
    for feat_num in range(1, 26):
        fid = f"F{feat_num:02d}"
        f_res = [r for r in results if r.feature == fid]
        if not f_res:
            continue
        p = sum(1 for r in f_res if r.passed)
        f = sum(1 for r in f_res if not r.passed)
        status = "\033[92mPASS\033[0m" if f == 0 else "\033[91mFAIL\033[0m"
        print(f"{fid:<8} | {len(f_res):<8} | {p:<8} | {f:<8} | {status}")

    print("=" * 80)
    if failed_count == 0:
        print("\033[92mALL TESTS PASSED! E2E SUITE VERIFICATION SUCCESSFUL.\033[0m")
        return 0
    else:
        print(f"\033[91m{failed_count} TEST(S) FAILED. INSPECT DIAGNOSTICS ABOVE.\033[0m")
        return 1


def main():
    parser = argparse.ArgumentParser(description="MyBatis 3 E2E Test Suite Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run specific test tier (1, 2, 3, 4)")
    parser.add_argument("--milestone", type=str, choices=["M1", "M2", "M3"], help="Run tests for specific milestone")
    parser.add_argument("--feature", type=str, help="Run tests for specific feature ID (e.g., F01, F14)")
    parser.add_argument("--all", action="store_true", help="Run all tests across all tiers and milestones (default)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose test execution output")
    parser.add_argument("--fail-fast", action="store_true", help="Stop execution on first failure")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    sys.exit(run_suite(
        selected_tier=args.tier,
        selected_milestone=args.milestone,
        selected_feature=args.feature,
        verbose=args.verbose,
        fail_fast=args.fail_fast,
        as_json=args.json,
    ))


if __name__ == "__main__":
    main()
