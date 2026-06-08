# 🚀 Quick Start Guide - Media Scraper

## Installation

```bash
# Navigate to project directory
cd "c:\Users\HP\Documents\Telegram Bots\GingerAI\Ginger-PA"

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
# Method 1: Using main.py
python main.py

# Method 2: Using FileScrapper.py directly
python FileScrapper.py
```

## Example Usage Session

### Input
```
==================================================
MEDIA SCRAPER & DOWNLOADER
==================================================

Enter URL (or 'quit' to exit):
> https://example.com/gallery
```

### URL Validation
```
Validating URL...
✓ URL is valid and reachable
```

### Format Selection
```
Select media formats to download:
----------------------------------------
1. gif
2. webp
3. mp4
4. jpg
5. png
6. Select All
----------------------------------------

Enter format numbers (comma-separated):
> 4,5
✓ Selected: JPG, PNG
```

### Processing
```
Fetching webpage...
✓ Page fetched successfully
Searching for media files...
✓ Found 42 media files

Downloading to: downloads/example_com_20260603_113000
--------------------------------------------------
Downloading media: 100%|████████| 42/42 [00:45<00:00]
```

### Results
```
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

Download another URL? (y/n): n

Thank you for using Media Scraper. Goodbye!
```

---

## File Structure After Download

```
downloads/
└── example_com_20260603_113000/
    ├── image1.jpg
    ├── image2.jpg
    ├── image3_1.jpg     (duplicate handling)
    ├── photo1.png
    ├── photo2.png
    └── ... (more files)
```

---

## Features at a Glance

| Feature | Details |
|---------|---------|
| **URL Validation** | Checks format and reachability |
| **Format Support** | GIF, WEBP, MP4, JPG, PNG |
| **Deduplication** | Prevents downloading same file twice |
| **Progress Bars** | Real-time download progress |
| **Error Recovery** | Continues if some files fail |
| **Auto Organization** | Creates timestamped folders |
| **Collision Handling** | Renames duplicate filenames |
| **Logging** | Saves logs to logs/scraper.log |
| **Statistics** | Shows detailed download report |

---

## Troubleshooting

### Issue: "URL is not reachable"
**Solution**: Check your internet connection and verify the URL is correct

### Issue: "No media files found"
**Solution**: The website might not have media in those formats. Try selecting different formats.

### Issue: Permission error
**Solution**: Ensure you have write permissions to the project directory

### Issue: Downloads failing
**Solution**: Check logs/scraper.log for detailed error messages

---

## Advanced Options

### View Logs
```bash
# Windows
type logs/scraper.log

# Linux/Mac
cat logs/scraper.log
```

### Clear Old Downloads
```bash
# Remove all downloaded media
rmdir /s downloads

# Then create empty downloads folder again
mkdir downloads
```

---

## Supported File Types

| Format | Extensions | Example |
|--------|-----------|---------|
| GIF | .gif | `animation.gif` |
| WEBP | .webp | `image.webp` |
| MP4 | .mp4 | `movie.mp4` |
| JPG | .jpg, .jpeg | `photo.jpg` |
| PNG | .png | `image.png` |

---

## Tips & Best Practices

### ✅ DO:
- Use specific formats when possible (faster)
- Check robots.txt of websites
- Respect website terms of service
- Test with small pages first

### ❌ DON'T:
- Scrape copyrighted content without permission
- Download from sites that prohibit scraping
- Scrape too rapidly (might get blocked)
- Modify files while downloading

---

## Module Overview

### scraper/url_utils.py
Handles URL validation, normalization, and format checking

### scraper/page_fetcher.py
Retrieves webpage HTML with automatic retries

### scraper/media_finder.py
Extracts media URLs from HTML content

### scraper/downloader.py
Downloads files with progress tracking

### FileScrapper.py
Main application with CLI interface

---

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Run the application: `python main.py`
3. ✅ Test with a website you know
4. ✅ Check logs/scraper.log for any issues
5. ✅ Review downloaded files in downloads/

---

## Performance Notes

- **Typical webpage**: 5-15 seconds
- **100 files**: 2-5 minutes (file size dependent)
- **Memory**: Efficient streaming downloads
- **Retries**: 3 attempts with backoff

---

## Support & Documentation

- **User Guide**: See README_SCRAPER.md
- **Implementation Details**: See IMPLEMENTATION_SUMMARY.md
- **Logs**: Check logs/scraper.log
- **Code Documentation**: Review docstrings in source code

---

## Example Test Cases

### Simple Website
```
URL: https://example.com
Formats: jpg
Expected: A few JPEG files
```

### Image Gallery
```
URL: https://picsum.photos
Formats: jpg,png
Expected: Many image files
```

### Media-Rich Site
```
URL: https://unsplash.com
Formats: jpg,png,gif
Expected: Hundreds of files
```

---

**Ready to scrape!** 🎉

For more details, see README_SCRAPER.md
