# THE CREW MODULE

![Version](https://img.shields.io/badge/version-2.2.0-orchid)
![Kodi](https://img.shields.io/badge/Kodi-v20+-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![License](https://img.shields.io/badge/license-GPL--3.0-red)

## Overview

**THE CREW MODULE** (script.module.thecrew) is a comprehensive Kodi addon module that provides entertainment content aggregation and streaming capabilities. The project is developed and maintained by The Crew team and serves as a powerful backend module for organizing, discovering, and playing movies, TV shows, documentaries, live channels, and other media content.

> **Tagline:** *"Many come, Many go. The true and dedicated are here."*

## Key Features

### Content Categories
- **Movies** - Browse, search, and stream movies from multiple sources
- **TV Shows** - Access TV series with full episode and season support
- **Live TV & IPTV** - Live channel streaming capabilities
- **Sports** - Sports content and live sports events
- **Documentaries** - Documentary films and series
- **Kids Content** - Family-friendly content for children
- **Specialty Collections** - Curated collections and themed content
- **Holiday Content** - Seasonal content (automatically shown in December)

### Advanced Features
- **Trakt Integration** - Full Trakt.tv integration for:
  - Watch progress tracking and syncing across devices
  - Watchlist management
  - Collection management
  - History and statistics
  - Recommendations based on viewing habits
  
- **Real-time Progress Tracking**
  - Local and cloud-based bookmarks
  - Resume playback from where you left off
  - Progress time remaining display when paused
  - Watched/unwatched episode tracking
  
- **Debrid Service Support**
  - Premium link resolution
  - High-quality source prioritization
  - Cached torrent support
  
- **Orion Integration**
  - Extensive Orion API support for enhanced source finding
  - Premium cached content access
  
- **Multi-Source Aggregation**
  - 70+ content sources (torrents and streaming)
  - Intelligent source filtering and ranking
  - Quality-based source selection
  
- **Rich Metadata**
  - TMDb integration for comprehensive media information
  - High-quality artwork (posters, fanart, clearlogo, clearart)
  - Cast and crew information
  - Ratings and reviews
  
- **Smart Search**
  - Unified search across all content types
  - Search history with item-level deletion
  - Actor/director filmography search
  
- **User Interface**
  - Multiple view options compatible with various Kodi skins
  - Widget support for home screen integration
  - Context menus for quick actions
  - Trailer playback support

## Technical Architecture

### Project Structure

```
script.module.thecrew/
├── lib/
│   └── resources/
│       └── lib/
│           ├── indexers/          # Content indexers and navigators
│           │   ├── movies.py      # Movie indexing and listing
│           │   ├── tvshows.py     # TV show indexing
│           │   ├── episodes.py    # Episode management
│           │   ├── lists.py       # Custom list management
│           │   ├── navigator.py   # Main navigation system
│           │   └── channels.py    # Live TV channels
│           │
│           ├── modules/           # Core functionality modules (~75 files, 31K+ lines)
│           │   ├── sources.py     # Source scraping engine
│           │   ├── control.py     # Kodi control functions
│           │   ├── trakt.py       # Trakt.tv integration
│           │   ├── bookmarks.py   # Progress tracking
│           │   ├── cache.py       # Caching system
│           │   ├── player.py      # Media player
│           │   ├── debrid.py      # Debrid service integration
│           │   ├── client.py      # HTTP client
│           │   ├── workers.py     # Concurrent task processing
│           │   ├── cleantitle.py  # Title normalization
│           │   ├── cleangenre.py  # Genre processing
│           │   ├── metacache.py   # Metadata caching
│           │   ├── fanart.py      # Artwork management
│           │   ├── views.py       # View management
│           │   └── ...            # Additional utility modules
│           │
│           └── sources/           # Content source scrapers
│               ├── en/            # English streaming sources (23 scrapers)
│               ├── en_tor/        # English torrent sources (47 scrapers)
│               └── en_de/         # Multi-language sources
│
├── addon.xml                      # Addon metadata and dependencies
├── changelog.txt                  # Version history and changes
├── LICENSE                        # GPL-3.0 license
└── README.md                      # This file
```

### Core Components

#### 1. **Indexers** (`lib/resources/lib/indexers/`)
Responsible for content discovery, organization, and presentation:
- **navigator.py** - Main menu and navigation logic
- **movies.py** - Movie catalog management (trending, popular, genres, etc.)
- **tvshows.py** - TV show catalog and season/episode organization
- **episodes.py** - Episode-level management and metadata
- **lists.py** - Custom user lists and collections
- **channels.py** - Live TV channel management

#### 2. **Modules** (`lib/resources/lib/modules/`)
Over 75 Python modules providing core functionality:
- **sources.py** - Multi-threaded source scraping engine
- **control.py** - Kodi API wrapper and utility functions
- **trakt.py** - Trakt.tv API integration
- **bookmarks.py** - Watch progress and resume point management
- **cache.py** - Intelligent caching system for metadata and sources
- **player.py** - Custom video player with tracking
- **debrid.py** - Premium debrid service integration (Real-Debrid, Premiumize, etc.)
- **workers.py** - Concurrent task execution framework
- **metacache.py** - Metadata caching and management
- **fanart.py** - Artwork fetching from FanArt.tv
- **cleantitle.py** - Title normalization for matching
- **client.py** - HTTP client with retry logic
- **utils.py** - General utility functions

#### 3. **Sources** (`lib/resources/lib/sources/`)
70+ source scrapers organized by type:
- **en/** - Direct streaming sources (23 scrapers)
- **en_tor/** - Torrent sources (47 scrapers)
  - Major torrent sites: PirateBay, EZTV, TorrentGalaxy, LimeTorrents, etc.
  - Specialized trackers and mirrors
- Multi-threaded scraping for fast results
- Quality detection and filtering
- Cached torrent support via debrid services

### Technology Stack

- **Platform:** Kodi Media Center (v20+)
- **Language:** Python 3.8+
- **Dependencies:**
  - `xbmc.python` (v3.0.0+) - Kodi Python API
  - `script.module.beautifulsoup4` - HTML parsing
  - `requests` - HTTP client
  - `sqlite3` - Local database
  - `resolveurl` - Link resolution
  - Optional: Orion module for premium sources

### Data Sources & APIs

- **TMDb (The Movie Database)** - Primary metadata source
- **Trakt.tv** - Watch tracking, recommendations, lists
- **FanArt.tv** - High-quality artwork
- **IMDb** - Additional metadata and ratings
- **Orion** - Premium cached content aggregation (optional)

## Version Information

**Current Version:** 2.2.0 (Module) / 2.1.0 (Addon)

### Major Changes in v2.x
The 2.x series represents a complete rewrite for Python 3 compatibility:

**Added:**
- Total episodes/seasons and watched/unwatched counts
- Widget support with smart filtering (no unaired episodes)
- Holiday movies menu (auto-shown in December)
- "Now Watching" menu
- Search history with item-level deletion
- Progress time remaining display
- Trakt progress syncing
- Extensive Orion support

**Fixed:**
- Complete Python 2 to 3 migration
- Trailer playback
- Fanart quality settings
- Actor search with TMDb
- All pagination issues
- Progress indicators
- Trakt authentication and syncing
- Info screen metadata display
- Dolby Vision (DV) tag support

**Changed:**
- Uses modern Kodi ListItem API
- Improved artwork handling
- Enhanced bookmark system (local + Trakt)
- Silent boot option
- Trailer selection dialog

**Removed:**
- Kodi-six dependency
- Furk.net support
- Python 2 compatibility

## System Requirements

- **Kodi Version:** v20 (Nexus) or higher
- **Python:** 3.8 or higher
- **Operating System:** Cross-platform (Windows, Linux, macOS, Android, iOS)
- **Storage:** Minimal (cache size configurable)
- **Network:** Internet connection required for content streaming

## Installation

This is a module addon that is typically installed as a dependency of other addons. It can be installed through:

1. Kodi addon repositories that include The Crew module
2. Manual installation via ZIP file
3. As a dependency automatically when installing compatible addons

## Configuration

The module provides extensive configuration options:

- **Menu Items** - Enable/disable navigation menu sections
- **Sources** - Configure source providers and priorities
- **Trakt** - Connect Trakt account for syncing
- **Debrid** - Configure debrid service credentials
- **Playback** - Quality preferences, auto-play settings
- **Downloads** - Download path configuration
- **Cache** - Cache size and duration settings
- **Artwork** - Fanart quality and display options

## Usage

As a module, this addon provides functionality to other addons. When used directly:

1. Launch the addon from Kodi's addon menu
2. Navigate through content categories (Movies, TV Shows, etc.)
3. Browse or search for content
4. Select a title to view details and available sources
5. Play content from the best available source

## Development

### Code Statistics
- **Total Python Files:** 223
- **Total Lines of Code:** 31,435+ (modules alone)
- **Indexers:** 7 main indexers
- **Modules:** 75+ utility and core modules
- **Source Scrapers:** 70+ sources

### Code Quality
- PEP 8 compliant (with pylintrc configuration)
- Type hints in modern code
- Comprehensive error handling
- Extensive logging for debugging
- Developer mode for testing

### Contributing

The project appears to follow these conventions:
- GPL-3.0 licensing for all contributions
- Python 3.8+ compatibility required
- Kodi v20+ API compliance
- Modular architecture for maintainability

## Legal Disclaimer

> The author of this addon does not host any of the content which is found and has no affiliation with any of the content providers. This addon simply searches websites for content. Use at your own risk!

This module is a search aggregator and does not host or distribute any copyrighted content. Users are responsible for compliance with their local laws regarding content streaming and copyright.

## License

This project is licensed under the **GNU General Public License v3.0**.

See the [LICENSE](LICENSE) file for full license text.

## Credits

**Developed by:** The Crew Team

**Copyright:** © 2023-2026 The Crew

## Support

For issues, feature requests, or questions, please refer to the addon's support channels within the Kodi community.

---

**Note:** This is a community-developed addon for Kodi. It is not officially endorsed by or affiliated with Kodi/XBMC Foundation.
