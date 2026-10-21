#!/usr/bin/env python3
"""
sync-keiyoushi.py

Syncs and mirrors curated top-tier extensions from Keiyoushi's official
repository into the local repository format. Downloads APKs and icons,
and creates a metadata map for index generation.
"""

import os
import sys
import json
import urllib.request
import argparse
from pathlib import Path

KEIYOUSHI_INDEX_URL = "https://raw.githubusercontent.com/keiyoushi/extensions/repo/index.json"

# Curated high-demand English and multi-language manga/webtoon extensions
CURATED_PACKAGES = [
    # Top Scanlators & Manhwa sources
    "eu.kanade.tachiyomi.extension.en.asurascans",
    "eu.kanade.tachiyomi.extension.en.flamecomics",
    "eu.kanade.tachiyomi.extension.en.comicasura",
    "eu.kanade.tachiyomi.extension.en.infernalvoidscans",  # Hive Scans
    "eu.kanade.tachiyomi.extension.en.aquamanga",
    "eu.kanade.tachiyomi.extension.en.manhuaus",
    "eu.kanade.tachiyomi.extension.en.manhuaplus",
    "eu.kanade.tachiyomi.extension.en.topmanhua",
    "eu.kanade.tachiyomi.extension.en.kunmangaonline",
    "eu.kanade.tachiyomi.extension.en.zinmanga",
    "eu.kanade.tachiyomi.extension.en.webtoonxyz",
    "eu.kanade.tachiyomi.extension.en.dragontea",
    "eu.kanade.tachiyomi.extension.en.arenascans",
    "eu.kanade.tachiyomi.extension.en.bbato",
    "eu.kanade.tachiyomi.extension.en.coffeemangaunoriginal",
    "eu.kanade.tachiyomi.extension.en.mangapandaonl",
    # Top Manga Aggregators
    "eu.kanade.tachiyomi.extension.all.mangadex",
    "eu.kanade.tachiyomi.extension.en.mangaparktv",
    "eu.kanade.tachiyomi.extension.en.mangareadersite",
    "eu.kanade.tachiyomi.extension.en.mangatown",
    "eu.kanade.tachiyomi.extension.en.mangafreak",
    "eu.kanade.tachiyomi.extension.en.mangakakalotfun",
    "eu.kanade.tachiyomi.extension.en.mangago",
    # Adult / NSFW popular sources
    "eu.kanade.tachiyomi.extension.all.manhwa18cc",
    "eu.kanade.tachiyomi.extension.en.readmanga18",
    "eu.kanade.tachiyomi.extension.all.manga18fx",
    "eu.kanade.tachiyomi.extension.en.manhwatop",
]


def download_file(url: str, dest_path: Path, timeout: int = 30) -> bool:
    """Downloads a file if not already present or empty."""
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return True
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        print(f"Warning: Failed to download {url} -> {dest_path}: {e}", file=sys.stderr)
        if dest_path.exists():
            dest_path.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(description="Mirror curated Keiyoushi extensions")
    parser.add_argument("--output-apk", default="repo/apk", help="Output directory for APKs")
    parser.add_argument("--output-icon", default="repo/icon", help="Output directory for icons")
    parser.add_argument("--output-meta", default="repo/keiyoushi-curated.json", help="Path for metadata JSON")
    parser.add_argument("--limit", type=int, default=0, help="Optional max extensions to sync")
    args = parser.parse_args()

    apk_dir = Path(args.output_apk)
    icon_dir = Path(args.output_icon)
    meta_path = Path(args.output_meta)

    apk_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Fetching Keiyoushi index from {KEIYOUSHI_INDEX_URL}...")
    try:
        req = urllib.request.Request(KEIYOUSHI_INDEX_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching Keiyoushi index: {e}", file=sys.stderr)
        sys.exit(1)

    all_extensions = data.get("extensionList", {}).get("extensions", [])
    print(f"Loaded {len(all_extensions)} total extensions from Keiyoushi.")

    # Match curated packages
    curated_map = {pkg: None for pkg in CURATED_PACKAGES}
    for ext in all_extensions:
        pkg = ext.get("packageName")
        if pkg in curated_map:
            curated_map[pkg] = ext

    matched = [ext for ext in curated_map.values() if ext is not None]
    if args.limit > 0:
        matched = matched[:args.limit]

    print(f"Selected {len(matched)} curated extensions to mirror.")

    metadata_result = {}
    synced_count = 0

    for ext in matched:
        name = ext.get("name")
        pkg = ext.get("packageName")
        resources = ext.get("resources", {})
        apk_url = resources.get("apkUrl")
        icon_url = resources.get("iconUrl")

        if not apk_url:
            continue

        apk_filename = apk_url.split("/")[-1]
        apk_dest = apk_dir / apk_filename
        icon_dest = icon_dir / f"{pkg}.png"

        # Download APK
        apk_ok = download_file(apk_url, apk_dest)
        if not apk_ok:
            continue

        # Download Icon if available
        if icon_url:
            download_file(icon_url, icon_dest)

        metadata_result[pkg] = {
            "name": name,
            "pkg": pkg,
            "apk": apk_filename,
            "version": ext.get("versionName", "1.6.0"),
            "code": int(ext.get("versionCode", 1)),
            "nsfw": 1 if ext.get("contentWarning") == "CONTENT_WARNING_NSFW" else 0,
            "libVersion": ext.get("extensionLib", "1.6"),
            "sources": [
                {
                    "name": s.get("name", name),
                    "lang": s.get("language", "en"),
                    "id": str(s.get("id")),
                    "baseUrl": s.get("homeUrl", ""),
                    "versionId": 1,
                    "hasCloudflare": 0
                }
                for s in ext.get("sources", [])
            ]
        }
        synced_count += 1
        print(f"  [+] Synced: {name} ({pkg}) -> {apk_filename}")

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata_result, f, indent=2, ensure_ascii=False)

    print(f"\nSUCCESS: Synced {synced_count} Keiyoushi extensions. Metadata saved to {meta_path}")


if __name__ == "__main__":
    main()
