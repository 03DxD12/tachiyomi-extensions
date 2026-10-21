# 03DxD12 Legacy Tachiyomi Extensions

A dedicated, actively maintained extension repository built specifically for **legacy Tachiyomi** (v0.15.2+, v0.14.x) and compatible forks that require the legacy JSON repository catalog (`index.min.json`).

---

## 🚀 Repository URL

Add this URL directly into your Tachiyomi app:

```text
https://raw.githubusercontent.com/03DxD12/tachiyomi-extensions/repo/index.min.json
```

### 📱 How to Add to Tachiyomi (v0.15.2+)
1. Open **Tachiyomi** on your device.
2. Tap **More** (bottom navigation) → **Settings** → **Browse** → **Extension repos**.
3. Tap **Add repository** (`+`).
4. Paste the URL:
   ```text
   https://raw.githubusercontent.com/03DxD12/tachiyomi-extensions/repo/index.min.json
   ```
5. Tap **Add** / **Accept**.
6. Navigate to the **Browse** → **Extensions** tab and pull down to refresh the extension list.
7. Tap **Install** on your desired sources, then tap **Trust** if prompted.

---

## 🏛️ Architecture & Compatibility Overview

Unlike modern Mihon and modern Keiyoushi repositories which have migrated to protobuf (`index.pb`) and modern extension libraries (`libVersion = 1.5/1.6`), this repository strictly targets the **legacy Tachiyomi extension architecture**:

| Component | Legacy Tachiyomi (This Repo) | Modern Mihon / Keiyoushi |
|---|---|---|
| **Catalog Format** | `index.min.json` + `index.json` | `index.pb` (Protocol Buffers) |
| **Extension Lib Version** | `1.4.x` (e.g. `1.4.15`) | `1.5.x` / `1.6.x` |
| **Package Prefix** | `eu.kanade.tachiyomi.extension` | `eu.kanade.tachiyomi.extension` / `mihon.extension` |
| **App Compatibility** | Tachiyomi 0.14.x, 0.15.x, TachiyomiSY, Neko, J2K | Mihon 0.16.x+, modern forks |
| **Extension Distribution** | `repo` branch (`/apk`, `/icon`, `index.min.json`) | Release assets / protobuf index |

---

## 📂 Repository Layout

```text
tachiyomi-extensions/
├── .github/
│   └── workflows/
│       └── build.yml             # GitHub Actions CI/CD to build APKs & publish repo branch
├── core/
│   ├── AndroidManifest.xml       # Shared AndroidManifest metadata template
│   └── build.gradle.kts          # Base library configuration
├── gradle/
│   ├── libs.versions.toml        # Gradle Version Catalog with legacy dependencies
│   └── wrapper/                  # Gradle wrapper files
├── lib/                          # Reusable helper libraries
├── lib-multisrc/                 # Multi-source theme generators (e.g. MangaBox, Madara)
├── src/                          # Individual extension source code
│   ├── all/                      # Multi-language extensions (MangaDex, Webtoons)
│   └── en/                       # English extensions (MangaKakalot, MangaFox, etc.)
├── scripts/
│   └── generate-index.py         # Automatic index generator for index.json & index.min.json
├── common.gradle                 # Standard Gradle build logic for extensions
├── build.gradle.kts              # Root Gradle build script
├── settings.gradle.kts           # Dynamic extension discovery & module loader
├── LICENSE                       # Apache-2.0 open source license
└── README.md                     # Documentation & setup guide
```

---

## 🛠️ Local Development & Building

### Prerequisites
- Java JDK 17 (recommended: Eclipse Temurin 17)
- Android SDK (API level 34 build-tools and platform 34)
- Python 3.9+

### Build All Extensions
```bash
# On Linux/macOS
./gradlew assembleRelease

# On Windows PowerShell
.\gradlew.bat assembleRelease
```

### Generate Local Index Files
To inspect built APKs and regenerate `index.json` and `index.min.json` locally:
```bash
python scripts/generate-index.py --apk-dir repo/apk --output-dir repo --icon-dir repo/icon
```

---

## ➕ Adding a New Extension

For instructions on adding new sources, see the development guide below or check existing modules under `src/`.
