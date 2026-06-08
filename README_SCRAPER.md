# Media Scraper & Downloader

A powerful Python application for scraping and downloading media files from websites.

## Features

✅ **URL Validation** - Validates URL format and reachability
✅ **Format Selection** - Choose from GIF, WEBP, MP4, JPG, PNG
✅ **HTML Parsing** - Extracts media from img, video, source, and picture tags
✅ **Smart Downloading** - Stream downloads with progress tracking
✅ **Duplicate Detection** - Automatic deduplication using sets
✅ **Auto Folder Creation** - Creates unique timestamped folders
✅ **File Collision Handling** - Renames duplicate filenames automatically
✅ **Error Handling** - Continues downloading even if some files fail
✅ **Progress Reporting** - Detailed statistics and download report
✅ **Logging** - Comprehensive logging to file and console

## Supported Formats

- **GIF** - `.gif`
- **WEBP** - `.webp`
- **MP4** - `.mp4`
- **JPG** - `.jpg`, `.jpeg`
- **PNG** - `.png`

## Installation

### Prerequisites
- Python 3.8+

### Setup

1. Clone or download the project

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python main.py
```

or 

```bash
python FileScrapper.py
```

### Interactive Menu

1. **Enter URL** - Provide the webpage URL to scrape
2. **Select Formats** - Choose which media formats to download
3. **Download** - The tool automatically downloads matching media
4. **Review Report** - Summary of downloads and statistics

### Example Session

```
==================================================
MEDIA SCRAPER & DOWNLOADER
==================================================

Enter URL (or 'quit' to exit):
> https://example.com/gallery
Validating URL...
✓ URL is valid and reachable

Select media formats to download:
----------------------------------------
1. gif
2. webm
3. mp4
4. jpg
5. png
6. Select All
----------------------------------------

Enter format numbers (comma-separated):
> 4,5
✓ Selected: JPG, PNG

Fetching webpage...
✓ Page fetched successfully
Searching for media files...
✓ Found 42 media files

Downloading to: downloads/example_com_20260603_113000
--------------------------------------------------
Downloading media: 100%|████████| 42/42 [00:45<00:00]

==================================================
SCRAPE COMPLETE
==================================================

URL:
https://example.com/gallery

Files Found:
42

Downloaded:
40

Failed:
2

Total Size:
125.45 MB

Location:
downloads/example_com_20260603_113000

==================================================
```

## Project Structure

```
Ginger-PA/
│
├── main.py                    # Entry point
├── FileScrapper.py           # Main application
├── requirements.txt          # Python dependencies
│
├── scraper/
│   ├── __init__.py          # Module initialization
│   ├── page_fetcher.py      # Webpage retrieval
│   ├── media_finder.py      # Media extraction
│   ├── downloader.py        # File downloading
│   └── url_utils.py         # URL utilities
│
├── downloads/               # Downloaded media folder
│   └── example_com_20260603_113000/
│       ├── image1.jpg
│       ├── image2.png
│       └── ...
│
├── logs/
│   └── scraper.log         # Application logs
│
└── README.md               # This file
```

## Module Documentation

### `scraper.page_fetcher.PageFetcher`

Retrieves and validates webpage content.

**Key Methods:**
- `validate_url(url)` - Validates URL format and reachability
- `fetch_page(url)` - Retrieves HTML content with automatic retries
- `close()` - Closes the session

**Features:**
- Automatic retry strategy for failed requests
- User-Agent header to avoid blocking
- HTTP status validation
- Timeout handling

### `scraper.media_finder.MediaFinder`

Extracts media URLs from HTML content.

**Key Methods:**
- `find_media_urls(html, base_url, formats)` - Finds all matching media URLs

**Supports:**
- img tags with src and data-src attributes
- video tags
- source tags (for video/audio)
- picture tags with srcset
- Direct links to media files

**Features:**
- Uses BeautifulSoup with Python's built-in `html.parser`
- Automatic deduplication using sets
- Relative URL resolution
- Format-based filtering

### `scraper.downloader.MediaDownloader`

Downloads media files with progress tracking.

**Key Methods:**
- `download_media(urls, output_dir)` - Downloads multiple files
- `close()` - Closes the session

**Features:**
- Progress bar display using tqdm
- Automatic retry on failure
- Duplicate filename handling
- File size tracking
- Streaming downloads

### `scraper.url_utils.URLUtils`

URL validation and manipulation utilities.

**Key Methods:**
- `validate_url(url)` - Validates URL format
- `normalize_url(relative_url, base_url)` - Converts relative to absolute URLs
- `get_filename_from_url(url)` - Extracts filename from URL
- `get_extension_from_url(url)` - Extracts file extension
- `is_valid_format(url, formats)` - Checks if URL matches format
- `get_domain_name(url)` - Extracts domain name

## Configuration

The application uses sensible defaults:

- **Timeout**: 30 seconds per request
- **Retries**: 3 attempts for failed requests
- **Chunk Size**: 8192 bytes for downloads
- **Output Directory**: `downloads/`
- **Logs Directory**: `logs/`

## Logging

Logs are saved to `logs/scraper.log` and displayed in the console.

**Log Levels:**
- `INFO` - General information and progress
- `WARNING` - Non-critical issues
- `ERROR` - Errors during operation

Example log entries:
```
2026-06-03 11:30:45,123 - scraper.page_fetcher - INFO - Successfully fetched https://example.com
2026-06-03 11:30:46,456 - scraper.media_finder - INFO - Found 42 unique media URLs
2026-06-03 11:30:47,789 - scraper.downloader - INFO - Downloaded: image1.jpg (125456 bytes)
```

## Error Handling

The application handles various error scenarios:

### URL Errors
- Invalid URL format
- Unreachable URLs
- HTTP error codes
- Timeout errors

### Download Errors
- Connection failures
- Corrupted files
- Missing files
- Permission errors

The scraper continues downloading remaining files even if some fail, and provides a summary of failures in the report.

## Advanced Features

### Duplicate Detection

The application automatically deduplicates media URLs using Python sets, preventing redundant downloads.

### Relative URL Resolution

Automatically converts relative paths to absolute URLs:
```
Relative: /media/cat.gif
Base URL: https://example.com
Result: https://example.com/media/cat.gif
```

### Filename Collision Prevention

When duplicate filenames are encountered:
```
Original: cat.gif
Collision 1: cat_1.gif
Collision 2: cat_2.gif
```

### Progress Tracking

Real-time progress bar using tqdm:
```
Downloading media: 100%|████████| 42/42 [00:45<00:00, 0.93 files/s]
```

## Performance

- **Optimized for**: Pages with 500+ media assets
- **Parallel-ready**: Session reuse reduces connection overhead
- **Memory-efficient**: Streaming downloads to avoid loading full files in memory

## Troubleshooting

### "URL is not reachable"
- Check internet connection
- Verify URL is correct
- Try adding http:// or https:// prefix

### "No media files found"
- Website may not contain the selected formats
- Try selecting different formats
- Media may be in iframes or dynamically loaded

### "Failed to download X files"
- Check logs in `logs/scraper.log`
- Some hosts may block rapid downloads
- Try again later with fewer files

### Permission Denied
- Check write permissions in downloads folder
- Run with appropriate permissions

## Stretch Goals & Future Enhancements

### Phase 1: Core Features ✅
- URL input and validation
- Format selection
- HTML retrieval and parsing
- Media extraction

### Phase 2: Downloads ✅
- Folder generation
- Media downloading
- Progress tracking
- Download reporting

### Phase 3: Robustness ✅
- Error handling
- Logging
- Duplicate detection
- File naming

### Phase 4: Advanced (Future)
- [ ] Multithreaded downloads (ThreadPoolExecutor)
- [ ] Content hashing (hashlib)
- [ ] Recursive crawling
- [ ] GUI interface (Tkinter/PyQt)
- [ ] Site-specific scrapers (Reddit, Pinterest, etc.)
- [ ] ZIP archive export
- [ ] Telegram bot integration

## Dependencies

- **requests** - HTTP requests and downloads
- **beautifulsoup4** - HTML parsing
- **tqdm** - Progress bars
- **urllib3** - URL utilities and retry logic

> Note: The scraper now uses BeautifulSoup with Python's built-in `html.parser` and does not require `lxml` for basic operation.

## License

This project is provided as-is for educational and personal use.

## Notes

- Always respect website terms of service and robots.txt
- Ensure you have permission to download content
- Use responsibly to avoid overwhelming target servers
- Some websites may require additional headers or authentication

## Support

For issues, check the logs in `logs/scraper.log` or create an issue in your project repository.
