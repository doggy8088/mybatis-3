# MyBatis 3 Localization & Publishing E2E Test Infrastructure Specification

## 1. Test Philosophy & Design Principles

The MyBatis 3 Localization and Publishing End-to-End (E2E) Test Suite is designed to provide comprehensive, opaque-box, reproducible quality assurance for the Traditional Chinese (`zh_TW`) documentation localization, GitHub Pages deployment, and Pull Request / GitHub Copilot code review lifecycle.

### Core Tenets
1. **Opaque-Box Specification Verification**:
   Tests evaluate observable behaviors, build outputs, file artifacts, XML structures, markdown syntax, network responses, and Git/GitHub API states against documented requirements (`ORIGINAL_REQUEST.md` and `PROJECT.md`), without relying on internal implementation shortcuts.
2. **Authoritative Output Derivation**:
   Expected values are derived directly from the official English reference documentation (`src/site/markdown/*.md`), Maven Site Plugin 3.22.0 / Fluido Skin 2.1.0 specifications, Taiwan Traditional Chinese (正體中文慣用術語) terminology standards, and GitHub REST/GraphQL API specifications.
3. **Progressive Testability & Isolation**:
   Tests are organized by milestone (M1: Localization, M2: GitHub Pages, M3: Git & Copilot Review) and tier (Tiers 1–4). The test runner supports milestone filtering (`--milestone M1`, `--milestone M2`, `--milestone M3`, or `--all`) so that tests can be verified progressively as each milestone reaches completion.
4. **Adversarial & Boundary Verification**:
   Tests probe UTF-8 encoding (rejecting UTF-8 BOM, replacement characters `\ufffd`), scans for prohibited Mainland/Simplified Chinese terminology, inspects fenced code-block syntax parity, audits markdown table column alignment and pipe escaping, enforces Fluido skin `<h1 class="d-none">` guards against blank sites, and validates URL depth resolution across multi-locale directories.
5. **Deterministic Diagnostics**:
   Every test case produces a distinct identifier (`T{tier}.F{feature}.{subcase}`), explicit failure rationale, and concrete remediation instructions to accelerate defect escalation.

---

## 2. Feature Inventory (25 Features)

| Feature ID | Category | Feature Name | Description | Milestone | Authoritative Specification |
|------------|----------|--------------|-------------|-----------|-----------------------------|
| **F01** | Build | Maven POM Locales Update | Add `zh_TW` to `<locales>` in `pom.xml` (`default,es,ja,fr,zh_CN,ko,zh_TW`) | M1 | `pom.xml:413` |
| **F02** | Descriptor | Traditional Chinese Site Descriptor | Create `src/site/site_zh_TW.xml` with Taiwan menu labels and lowercase/hyphenated anchor slugs | M1 | `src/site/site_zh_TW.xml` |
| **F03** | Doc | Translation: `index.md` | Complete Taiwan Traditional Chinese translation of Introduction page with language selector | M1 | `src/site/zh_TW/markdown/index.md` |
| **F04** | Doc | Translation: `getting-started.md` | Complete Taiwan Traditional Chinese translation of Getting Started guide | M1 | `src/site/zh_TW/markdown/getting-started.md` |
| **F05** | Doc | Translation: `configuration.md` | Complete Taiwan Traditional Chinese translation of Configuration reference | M1 | `src/site/zh_TW/markdown/configuration.md` |
| **F06** | Doc | Translation: `sqlmap-xml.md` | Complete Taiwan Traditional Chinese translation of Mapper XML reference | M1 | `src/site/zh_TW/markdown/sqlmap-xml.md` |
| **F07** | Doc | Translation: `dynamic-sql.md` | Complete Taiwan Traditional Chinese translation of Dynamic SQL guide | M1 | `src/site/zh_TW/markdown/dynamic-sql.md` |
| **F08** | Doc | Translation: `java-api.md` | Complete Taiwan Traditional Chinese translation of Java API guide | M1 | `src/site/zh_TW/markdown/java-api.md` |
| **F09** | Doc | Translation: `statement-builders.md` | Complete Taiwan Traditional Chinese translation of SQL Builder guide | M1 | `src/site/zh_TW/markdown/statement-builders.md` |
| **F10** | Doc | Translation: `logging.md` | Complete Taiwan Traditional Chinese translation of Logging guide | M1 | `src/site/zh_TW/markdown/logging.md` |
| **F11** | Asset | Flag Icon & CSS Styling | Add `src/site/resources/images/tw.png` (32x32) and `site.css` `li.zh_tw` rules | M1 | `src/site/resources/images/tw.png`, CSS |
| **F12** | Nav | Cross-Locale Language Links | Update `<ul class="i18n">` across `src/site/**/index.md` with 繁體中文 links | M1 | `src/site/**/index.md` |
| **F13** | Quality | Taiwan Terminology Compliance | 100% adherence to 正體中文慣用術語, 0 Mainland/Simplified terms | M1 | Terminology standard |
| **F14** | Static | CNAME & Static Hosting Files | Add `src/site/resources/CNAME` (`mybatis.gh.miniasp.com`) and `.nojekyll` | M2 | Pages custom domain spec |
| **F15** | CI/CD | GitHub Actions Workflow Update | Update `.github/workflows/site.yaml` for `doggy8088`, branch triggers, CNAME retention | M2 | `.github/workflows/site.yaml` |
| **F16** | Build | Maven Site Build & Staging | Execute `./mvnw site site:stage` producing `target/site/zh_TW/` and staged output | M2 | Maven Site Plugin 3.22.0 |
| **F17** | Deploy | Deploy to `origin/gh-pages` | Push staged site with `/zh_TW/*.html` and `/CNAME` to `origin/gh-pages` branch | M2 | `origin/gh-pages` tree |
| **F18** | API | GitHub Pages Configuration | Enable Pages on `doggy8088/mybatis-3` (gh-pages, CNAME `mybatis.gh.miniasp.com`) | M2 | GitHub REST Pages API |
| **F19** | Live | Live Web Availability Check | Verify `https://mybatis.gh.miniasp.com/` and `/zh_TW/index.html` return HTTP 200 | M2 | Live HTTP endpoint check |
| **F20** | Git | Branch `zh-tw` Creation & Push | Branch `zh-tw` created off `master`, source committed and pushed to `origin` | M3 | Git remote refs |
| **F21** | PR | Pull Request Creation | PR opened targeting `master` on `doggy8088/mybatis-3` (NOT upstream) | M3 | GitHub REST / CLI PR API |
| **F22** | Review | Copilot Review Request | Trigger Copilot code review via `gh copilot-review` and await completion | M3 | `gh copilot-review` tool |
| **F23** | Review | Copilot Review Inspection | Inspect inline threads, review overview, and suppressed comments | M3 | GitHub GraphQL Review API |
| **F24** | Review | Fix, Reply & Resolution Loop | Address feedback, push fixes, reply, resolve GraphQL threads until 0 issues | M3 | GraphQL thread resolution |
| **F25** | PR | PR Preservation (Unmerged) | PR remains open (`state == "OPEN"`) and unmerged for user decision | M3 | GitHub PR state |

---

## 3. Systematic 4-Tier Test Architecture

```
+-------------------------------------------------------------------------------+
|                        MyBatis 3 E2E Test Suite                               |
+-------------------------------------------------------------------------------+
| Tier 1: Feature Coverage (>=5 test cases per feature for representative inputs) |
|         - 125 granular test cases verifying F01 through F25 in isolation      |
+-------------------------------------------------------------------------------+
| Tier 2: Boundary & Corner Cases (>=5 test cases per feature where applicable)  |
|         - UTF-8 BOM, Mainland terms, Code fence balance, Table alignment,     |
|           Fluido skin blank page guard, Relative URL depths, CNAME formatting |
+-------------------------------------------------------------------------------+
| Tier 3: Cross-Feature Combinations (Pairwise / Multi-feature interactions)     |
|         - POM + Descriptor + Markdown -> Multi-locale site generation        |
|         - Descriptor anchors <-> Markdown headings parity                     |
|         - Flag image + CSS selector + HTML list rendering                     |
|         - Staged site matches deployed Pages tree                             |
+-------------------------------------------------------------------------------+
| Tier 4: Real-World Scenarios (End-to-End Live Verification)                   |
|         - Full Maven site & stage generation                                  |
|         - Origin gh-pages branch inspection                                   |
|         - GitHub Pages API configuration & deployment state                   |
|         - Public DNS resolution for mybatis.gh.miniasp.com                    |
|         - Public HTTPS live endpoint status (HTTP 200, valid SSL, zh_TW text) |
|         - Pull Request target, status OPEN, 0 unresolved Copilot comments    |
+-------------------------------------------------------------------------------+
```

---

## 4. Coverage Thresholds & Target Counts

| Tier | Focus | Minimum Target | Actual Implemented |
|------|-------|----------------|--------------------|
| **Tier 1** | Feature Coverage (Isolation) | 125 (>=5 per feature * 25) | 125 |
| **Tier 2** | Boundary & Corner Cases | 50 (>=2 per feature / >=5 where boundaries exist) | 65 |
| **Tier 3** | Cross-Feature Combinations | 15 (Pairwise / integration) | 20 |
| **Tier 4** | Real-World Scenarios | 8 (Full build, Git, API, DNS, HTTP, PR) | 12 |
| **Total** | **Full E2E Suite** | **198** | **222** |

---

## 5. Test Runner Invocation

### Executable Runners
- Bash entrypoint: `/Users/will/projects/mybatis-3/test_e2e_suite.sh`
- Python core engine: `/Users/will/projects/mybatis-3/test_e2e_suite.py`

### Common Invocation Examples
```bash
# Run entire E2E test suite across all 4 tiers:
./test_e2e_suite.sh

# Run only Milestone 1 (Localization) tests:
./test_e2e_suite.sh --milestone M1

# Run only Milestone 2 (GitHub Pages Publishing) tests:
./test_e2e_suite.sh --milestone M2

# Run only Milestone 3 (Branch, PR & Copilot Review) tests:
./test_e2e_suite.sh --milestone M3

# Run a specific Tier:
./test_e2e_suite.sh --tier 1
./test_e2e_suite.sh --tier 2
./test_e2e_suite.sh --tier 3
./test_e2e_suite.sh --tier 4

# Run tests for a specific Feature (e.g., F02 Site Descriptor):
./test_e2e_suite.sh --feature F02

# Verbose output with detailed diagnostics:
./test_e2e_suite.sh -v

# Output JSON report:
./test_e2e_suite.sh --json
```

### Exit Code Semantics
- `0`: All executed test cases passed successfully.
- `1`: One or more test cases failed. Diagnostic details and remediation steps are logged to stderr/stdout.
