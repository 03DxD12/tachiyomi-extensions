#!/usr/bin/env python3
"""
generate-index.py

Generates legacy Tachiyomi extension repository metadata files:
- index.json (pretty-printed JSON array)
- index.min.json (minified single-line JSON array)
- repo.json (repository metadata for Tachiyomi 0.15.2+ and forks)
- Extracts extension icons to icon/{pkg}.png
"""

import os
import sys
import json
import shutil
import zipfile
import re
import argparse
import subprocess
import traceback
import hashlib
import struct
from pathlib import Path


def generate_source_id(name: str, lang: str, version_id: int = 1) -> str:
    """Computes deterministic 63-bit source ID matching Tachiyomi's native formula."""
    key = f"{name.lower()}/{lang}/{version_id}".encode("utf-8")
    digest = hashlib.md5(key).digest()
    val = struct.unpack(">q", digest[:8])[0] & 0x7FFFFFFFFFFFFFFF
    return str(val)


KNOWN_SOURCES = {
    "eu.kanade.tachiyomi.extension.en.mangakakalot": [{
        "name": "MangaKakalot",
        "lang": "en",
        "id": "2528986671771677900",
        "baseUrl": "https://www.mangakakalove.com",
        "versionId": 1,
        "hasCloudflare": 0
    }],
    "eu.kanade.tachiyomi.extension.en.mangabat": [{
        "name": "MangaBat",
        "lang": "en",
        "id": "4215511432986138970",
        "baseUrl": "https://mangabat.com",
        "versionId": 1,
        "hasCloudflare": 0
    }],
    "eu.kanade.tachiyomi.extension.en.mangafox": [{
        "name": "MangaFox",
        "lang": "en",
        "id": "6484561431658238800",
        "baseUrl": "https://fanfox.net",
        "versionId": 1,
        "hasCloudflare": 0
    }],
    "eu.kanade.tachiyomi.extension.en.mangahere": [{
        "name": "MangaHere",
        "lang": "en",
        "id": "2488379533137806105",
        "baseUrl": "https://www.mangahere.cc",
        "versionId": 1,
        "hasCloudflare": 0
    }],
    "eu.kanade.tachiyomi.extension.en.manganelo": [{
        "name": "MangaNato",
        "lang": "en",
        "id": "1024627298672457456",
        "baseUrl": "https://manganato.com",
        "versionId": 1,
        "hasCloudflare": 0
    }],
    "eu.kanade.tachiyomi.extension.en.mangapill": [{
        "name": "MangaPill",
        "lang": "en",
        "id": "8448310129093543312",
        "baseUrl": "https://mangapill.com",
        "versionId": 1,
        "hasCloudflare": 0
    }],
    "eu.kanade.tachiyomi.extension.en.webtoons": [{
        "name": "Webtoons.com",
        "lang": "en",
        "id": "2522335540328470744",
        "baseUrl": "https://www.webtoons.com",
        "versionId": 1,
        "hasCloudflare": 0
    }],
    "eu.kanade.tachiyomi.extension.en.allanime": [{
        "name": "AllAnime",
        "lang": "en",
        "id": "4709139914729853090",
        "baseUrl": "https://allanime.to",
        "versionId": 1,
        "hasCloudflare": 0
    }],
    "eu.kanade.tachiyomi.extension.en.batoto": [{
        "name": "Bato.to",
        "lang": "en",
        "id": "7890050626002177109",
        "baseUrl": "https://bato1.com",
        "versionId": 1,
        "hasCloudflare": 0
    }]
}



def safe_int(val, default=0):
    """Safely converts string, hex, or bool representation into an int."""
    if val is None:
        return default
    s = str(val).strip().strip("'").strip('"')
    if not s:
        return default
    if s.lower() in ("true", "yes"):
        return 1
    if s.lower() in ("false", "no"):
        return 0
    try:
        if s.startswith("0x") or s.startswith("0X"):
            return int(s, 16)
        return int(s)
    except Exception:
        return default


def clean_extension_name(slug):
    """Converts extension package slug into standard display name."""
    lower = slug.lower()
    known = {
        "mangakakalot": "MangaKakalot",
        "mangabat": "MangaBat",
        "mangafox": "MangaFox",
        "mangahere": "MangaHere",
        "mangadex": "MangaDex",
        "mangapark": "MangaPark",
        "mangareader": "MangaReader",
        "mangahub": "MangaHub",
        "webtoons": "Webtoons.com",
        "allanime": "AllAnime",
        "manganelo": "MangaNato",
        "mangapill": "MangaPill",
        "batoto": "Bato.to",
        "asurascans": "Asura Scans",
        "comick": "Comick",
        "comickfun": "Comick"
    }
    return known.get(lower, slug.capitalize())



def find_aapt():
    """Find aapt or aapt2 from PATH or ANDROID_HOME."""
    aapt_cmd = shutil.which("aapt")
    if aapt_cmd:
        return aapt_cmd

    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if android_home:
        build_tools = Path(android_home) / "build-tools"
        if build_tools.is_dir():
            versions = sorted(build_tools.iterdir(), reverse=True)
            for v in versions:
                cand = v / ("aapt.exe" if os.name == "nt" else "aapt")
                if cand.is_file():
                    return str(cand)
    return None


def extract_metadata_aapt(aapt_path, apk_path):
    """Extract metadata using aapt dump badging."""
    cmd = [aapt_path, "dump", "--include-meta-data", "badging", str(apk_path)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return None

    output = result.stdout
    meta = {}

    # Package info: package: name='...' versionCode='...' versionName='...'
    pkg_match = re.search(r"package:\s+name=['\"]([^'\"]+)['\"]\s+versionCode=['\"]([^'\"]+)['\"]\s+versionName=['\"]([^'\"]+)['\"]", output)
    if pkg_match:
        meta["pkg"] = pkg_match.group(1)
        meta["code"] = safe_int(pkg_match.group(2), default=1)
        meta["version"] = pkg_match.group(3)

    # Label: application-label:'...' or application: label='...'
    label_match = re.search(r"application-label(?:-[a-zA-Z]+)?:\s*['\"]([^'\"]+)['\"]", output)
    if not label_match:
        label_match = re.search(r"application:\s+.*label=['\"]([^'\"]+)['\"]", output)
    if label_match:
        name = label_match.group(1)
        if name.startswith("Tachiyomi: "):
            name = name[len("Tachiyomi: "):]
        meta["name"] = name
    else:
        meta["name"] = None

    # NSFW meta-data
    nsfw_match = re.search(r"meta-data:\s+name=['\"]tachiyomi\.extension\.nsfw['\"]\s+value=['\"]([^'\"]+)['\"]", output)
    if nsfw_match:
        meta["nsfw"] = safe_int(nsfw_match.group(1), default=0)
    else:
        meta["nsfw"] = 0

    # Extension class
    class_match = re.search(r"meta-data:\s+name=['\"]tachiyomi\.extension\.class['\"]\s+value=['\"]([^'\"]+)['\"]", output)
    if class_match:
        meta["class"] = class_match.group(1)

    # Icon path in APK
    icon_matches = re.findall(r"application-icon-\d+:\s*['\"]([^'\"]+)['\"]", output)
    if icon_matches:
        meta["icon_path"] = icon_matches[-1]
    else:
        fallback_icon = re.search(r"application:\s+.*icon=['\"]([^'\"]+)['\"]", output)
        if fallback_icon:
            meta["icon_path"] = fallback_icon.group(1)

    return meta


def extract_metadata_fallback(apk_path):
    """Fallback metadata extractor using filename convention."""
    clean_stem = re.sub(r"-release(-unsigned)?$", "", apk_path.stem)
    match = re.match(r"^tachiyomi-([a-zA-Z0-9_\-]+)\.([a-zA-Z0-9_\-]+)-v([0-9\.]+)$", clean_stem)
    meta = {}
    if match:
        meta["lang"] = match.group(1)
        ext_slug = match.group(2)
        meta["version"] = match.group(3)
        parts = meta["version"].split(".")
        meta["code"] = safe_int(parts[-1], default=1)
        meta["name"] = clean_extension_name(ext_slug)
        meta["pkg"] = f"eu.kanade.tachiyomi.extension.{meta['lang']}.{ext_slug}"
    else:
        meta["name"] = clean_extension_name(clean_stem)
        meta["pkg"] = f"eu.kanade.tachiyomi.extension.{clean_stem}"
        meta["code"] = 1
        meta["version"] = "1.4.1"
        meta["lang"] = "en"

    meta["nsfw"] = 0
    return meta


def extract_icon(apk_path, icon_in_apk, output_icon_path):
    """Extract an icon file from the APK."""
    try:
        with zipfile.ZipFile(apk_path, "r") as z:
            if icon_in_apk and icon_in_apk in z.namelist():
                with open(output_icon_path, "wb") as out:
                    out.write(z.read(icon_in_apk))
                return True
            candidates = [n for n in z.namelist() if "ic_launcher" in n and n.endswith(".png")]
            if candidates:
                candidates.sort(key=lambda x: ("xxxhdpi" in x, "xxhdpi" in x, "xhdpi" in x, "hdpi" in x), reverse=True)
                with open(output_icon_path, "wb") as out:
                    out.write(z.read(candidates[0]))
                return True
            fallback_images = [n for n in z.namelist() if n.startswith("res/") and (n.endswith(".png") or n.endswith(".webp"))]
            if fallback_images:
                with open(output_icon_path, "wb") as out:
                    out.write(z.read(fallback_images[0]))
                return True
    except Exception as e:
        print(f"Notice: Icon extraction note for {apk_path.name}: {e}", file=sys.stderr)
    return False


def normalize_apk_name(apk_path):
    """Normalizes an APK file name by stripping '-release*' suffixes."""
    filename = apk_path.name
    clean_name = re.sub(r"-release(-unsigned)?\.apk$", ".apk", filename)
    if clean_name != filename:
        target = apk_path.parent / clean_name
        if target.exists():
            target.unlink()
        apk_path.rename(target)
        return target
    return apk_path


def main():
    try:
        parser = argparse.ArgumentParser(description="Generate legacy Tachiyomi extension repository indexes")
        parser.add_argument("--apk-dir", default="repo/apk", help="Directory where APKs are located")
        parser.add_argument("--output-dir", default="repo", help="Output directory for index.json and index.min.json")
        parser.add_argument("--icon-dir", default="repo/icon", help="Directory where icons should be saved")
        parser.add_argument("--inspector-json", default="", help="Path to output.json from Inspector.jar")
        parser.add_argument("--repo-name", default="03DxD12 Legacy Tachiyomi Extensions", help="Repo display name")
        parser.add_argument("--repo-short-name", default="03DxD12", help="Repo short name")
        parser.add_argument("--repo-website", default="https://github.com/03DxD12/tachiyomi-extensions", help="Repo website")
        parser.add_argument("--signing-fingerprint", default="", help="Signing key SHA-256 fingerprint")

        args = parser.parse_args()

        apk_dir = Path(args.apk_dir)
        output_dir = Path(args.output_dir)
        icon_dir = Path(args.icon_dir)

        output_dir.mkdir(parents=True, exist_ok=True)
        icon_dir.mkdir(parents=True, exist_ok=True)

        if not apk_dir.exists():
            print(f"Error: APK directory '{apk_dir}' does not exist.", file=sys.stderr)
            sys.exit(1)

        current_apks = list(apk_dir.glob("*.apk"))
        apk_files = []
        for apk in current_apks:
            norm = normalize_apk_name(apk)
            apk_files.append(norm)
        apk_files.sort()

        if len(apk_files) == 0:
            print(f"Error: No APK files found in '{apk_dir}'. Aborting index generation to prevent publishing empty repository.", file=sys.stderr)
            sys.exit(1)

        print(f"Processing {len(apk_files)} APKs in '{apk_dir}'...")

        inspector_data = {}
        if args.inspector_json and os.path.isfile(args.inspector_json) and os.path.getsize(args.inspector_json) > 0:
            try:
                with open(args.inspector_json, "r", encoding="utf-8") as f:
                    inspector_data = json.load(f)
                print(f"Loaded inspector data for {len(inspector_data)} packages.")
            except Exception as e:
                print(f"Notice: Failed to load inspector JSON ({e}), continuing with defaults.")

        aapt_path = find_aapt()
        if aapt_path:
            print(f"Using aapt: {aapt_path}")

        extensions = []

        for apk in apk_files:
            meta = None
            if aapt_path:
                try:
                    meta = extract_metadata_aapt(aapt_path, apk)
                except Exception as e:
                    print(f"Notice: aapt extraction exception on {apk.name}: {e}")
                    meta = None

            if not meta or not meta.get("pkg"):
                meta = extract_metadata_fallback(apk)

            pkg_name = str(meta.get("pkg") or f"eu.kanade.tachiyomi.extension.{apk.stem}")
            slug = pkg_name.split(".")[-1]
            ext_name = meta.get("name")
            if not ext_name or ext_name.startswith("tachiyomi-"):
                ext_name = clean_extension_name(slug)

            version_str = str(meta.get("version") or "1.4.1")
            version_code = safe_int(meta.get("code", 1), default=1)
            nsfw_val = safe_int(meta.get("nsfw", 0), default=0)

            lang_match = re.search(r"^tachiyomi-([a-zA-Z0-9_\-]+)\.", apk.name)
            lang = lang_match.group(1) if lang_match else str(meta.get("lang", "en"))

            icon_path = icon_dir / f"{pkg_name}.png"
            extract_icon(apk, meta.get("icon_path"), icon_path)

            sources = []
            if pkg_name in inspector_data and isinstance(inspector_data[pkg_name], list):
                sources = inspector_data[pkg_name]
                if len(sources) == 1 and isinstance(sources[0], dict) and "lang" in sources[0]:
                    src_lang = sources[0]["lang"]
                    if src_lang not in ("all", "other") and lang not in ("all", "other"):
                        lang = src_lang
                for s in sources:
                    if not s.get("baseUrl") and pkg_name in KNOWN_SOURCES:
                        known_src = next((k for k in KNOWN_SOURCES[pkg_name] if k.get("name") == s.get("name")), KNOWN_SOURCES[pkg_name][0])
                        s["baseUrl"] = known_src.get("baseUrl", "")
            elif pkg_name in KNOWN_SOURCES:
                sources = [dict(s) for s in KNOWN_SOURCES[pkg_name]]
            else:
                source_id = generate_source_id(ext_name, lang, 1)
                sources.append({
                    "name": ext_name,
                    "lang": lang,
                    "id": source_id,
                    "baseUrl": f"https://{slug}.com",
                    "versionId": 1,
                    "hasCloudflare": 0
                })

            entry = {
                "name": ext_name,
                "pkg": pkg_name,
                "apk": apk.name,
                "lang": lang,
                "code": version_code,
                "version": version_str,
                "nsfw": nsfw_val,
                "sources": sources
            }
            extensions.append(entry)
            print(f"Indexed: {entry['name']} ({entry['pkg']}) v{entry['version']}")

        extensions.sort(key=lambda x: (x.get("lang") != "en", str(x.get("name", "")).lower()))

        index_json_path = output_dir / "index.json"
        with open(index_json_path, "w", encoding="utf-8") as f:
            json.dump(extensions, f, indent=2, ensure_ascii=False)
            f.write("\n")

        index_min_json_path = output_dir / "index.min.json"
        with open(index_min_json_path, "w", encoding="utf-8") as f:
            json.dump(extensions, f, separators=(",", ":"), ensure_ascii=False)

        repo_json_path = output_dir / "repo.json"
        repo_data = {
            "meta": {
                "name": args.repo_name,
                "shortName": args.repo_short_name,
                "website": args.repo_website,
                "signingKeyFingerprint": args.signing_fingerprint
            }
        }
        with open(repo_json_path, "w", encoding="utf-8") as f:
            json.dump(repo_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        repo_readme_path = output_dir / "README.md"
        readme_content = f"""# 03DxD12 Legacy Tachiyomi Extension Repository

This repository provides manga extensions compatible with legacy **Tachiyomi** (v0.15.2+, v0.14.x) and compatible forks that require the `index.min.json` repository index format.

## Repository URL

To add this repository to your Tachiyomi app:

```text
https://raw.githubusercontent.com/03DxD12/tachiyomi-extensions/repo/index.min.json
```

### Available Extensions ({len(extensions)})

| Name | Package | Language | Version | NSFW |
|---|---|---|---|---|
"""
        for ext in extensions:
            nsfw_tag = "🔞 Yes" if ext["nsfw"] == 1 else "No"
            readme_content += f"| {ext['name']} | `{ext['pkg']}` | {ext['lang']} | {ext['version']} | {nsfw_tag} |\n"

        with open(repo_readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        print(f"SUCCESS: Generated index files for {len(extensions)} extensions in '{output_dir}'.")

    except Exception:
        print("FATAL ERROR in generate-index.py:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
