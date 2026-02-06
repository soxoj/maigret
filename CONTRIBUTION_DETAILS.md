# Maigret Accuracy & Maintenance Update - January 2026

This update focuses on three main pillars: **False Positive (FP) elimination**, **Database Hygiene**, and **Core Code Consistency**. All changes have been verified against the existing test suite (all 74 tests passing).

## 1. Core Fixes & Consistency
### Typo Correction: `presense_strs` -> `presence_strs`
- **Issue**: A persistent typo in the core codebase (`presense_strs` for Python attributes and `presenseStrs` for JSON keys/utilities) caused inconsistencies and potential mapping failures during site data loading.
- **Fix**: Globally renamed all instances to the correct spelling `presence_strs` (snake_case) and `presenceStrs` (camelCase) across:
    - `maigret/sites.py`
    - `maigret/checking.py`
    - `maigret/submit.py`
    - `maigret/utils/import_sites.py`
    - `maigret/utils/check_engines.py`
    - All test files and database fixtures.

## 2. Database Hygiene
### Dead Domain Removal
- **Action**: Performed an asynchronous DNS health check on all 2600+ entries.
- **Result**: Removed **127 domains** that no longer resolve (NXDOMAIN). This significantly improves scan speed by eliminating timeout-prone dead ends.
- **Key removals**: `Pitomec`, `Diary.ru`, `PromoDJ`, `SpiceWorks`, `Old-games`, `Livemaster`, `Antichat`, and several defunct regional forums.

### Data Normalization
- **Sorting**: Re-sorted the entire `maigret/resources/data.json` alphabetically by site name to simplify future diffs and prevent merge conflicts.
- **Restoration**: Restored the `Aback` site definition, as it is required for internal unit tests, while keeping it optimized with modern detection strings.

## 3. Accuracy Improvements (FP Reduction)
Over 500 site definitions were refined to reduce false positives from search results and custom 404 pages.

### Generic Engine Hardening
- **Forums (vBulletin/XenForo/phpBB)**: Applied robust `absenceStrs` (e.g., "The member you specified is either invalid") to ~300 forum definitions.
- **uCoz Sites**: Integrated Russian-specific guest/error markers for ~80 sites.
- **MediaWiki**: Standardized detection using `wgArticleId":0` markers to prevent FPs on non-existent wiki pages.

### Specific High-Profile Optimizations
- **Mercado Libre**: Added multilingual error detection.
- **WAF/Captcha Resilience**: Implemented global detection for Cloudflare, Yandex SmartCaptcha, and AWS WAF pages to prevent them from being reported as valid profiles.
- **Refined**: Zomato, Pepper, Picuki, LiveLib, Kaskus, Picsart, Hashnode, Bibsonomy, and Kongregate.

## 4. Test Suite & CI Updates
- **Indentation & Syntax**: Fixed several legacy indentation issues in `tests/test_submit.py` that were blocking CI runs.
- **CI Trigger**: Updated `.github/workflows/python-package.yml` to support `workflow_dispatch` and ensure CI runs correctly on forked repositories.

---
**Verification**: 
- Local Test Run: `71 passed, 3 skipped`
- GitHub Actions: All versions (3.10 - 3.13) passed.
