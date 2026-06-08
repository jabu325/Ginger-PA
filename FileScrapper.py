"""
Main Media Scraper Module - Complete CLI Interface
"""

import logging
import random
import time
from datetime import datetime
from pathlib import Path
from scraper import PageFetcher, MediaFinder, MediaDownloader
from scraper.logging_config import setup_scraper_logging
from scraper.url_utils import URLUtils

# Configure logging
setup_scraper_logging()
logger = logging.getLogger(__name__)


class MediaScraperApp:
    """Main Media Scraper Application"""
    
    SUPPORTED_FORMATS = list(URLUtils.SUPPORTED_FORMATS.keys())
    
    def __init__(self):
        """Initialize the application"""
        # Always create PageFetcher upfront so both local HTML and remote URL
        # paths (validation + load/fetch) have a valid instance. The session is
        # cheap to create and gets reused across multiple scrapes in one run.
        self.page_fetcher = PageFetcher()

        # Beef up the PageFetcher session headers (used for initial URL validation HEAD
        # and the main HTML fetch). This makes the *page* request look more like a real
        # browser, which helps reduce flagging/403s on the HTML fetch itself.
        # (The actual media downloads use the even richer Downloader session.)
        try:
            self.page_fetcher.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
        except Exception:
            pass  # If internals change, don't break the app

        self.downloader = None
    
    def run(self):
        """Run the main application loop"""
        print("\n" + "="*50)
        print("MEDIA SCRAPER & DOWNLOADER")
        print("="*50 + "\n")
        
        while True:
            try:
                # Get user input
                url = self._get_url_input()
                if not url:
                    break
                
                formats = self._get_format_selection()
                # _get_format_selection() always returns a non-empty list (it reprompts internally
                # on invalid input until the user provides a valid selection or interrupts).

                max_files = self._get_media_limit()
                
                # Scrape and download
                self._scrape_and_download(url, formats, max_files)
                
                # Ask if user wants to continue
                if not self._ask_continue():
                    break
                    
            except KeyboardInterrupt:
                print("\n\nScraper interrupted by user.")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                print(f"Error: {e}\n")
        
        self._cleanup()
        print("\nThank you for using Media Scraper. Goodbye!\n")
    
    def _get_url_input(self) -> str:
        """Get and validate URL or local HTML file path from user"""
        while True:
            url = input("Enter URL or local HTML file path (or 'quit' to exit):\n> ").strip()
            
            if url.lower() == 'quit':
                return None
            
            if not url:
                print("Input cannot be empty.\n")
                continue

            candidate_path = Path(url).expanduser()
            # Treat as local HTML path if it has .html/.htm suffix or looks like a
            # filesystem path (drive letter, backslashes, ./ ../ or leading /).
            # This prevents mangling mistyped local paths into https:// URLs and
            # gives a clear "not found" error instead of a confusing validation failure.
            looks_like_local = (
                candidate_path.suffix.lower() in {'.html', '.htm'} or
                any(sep in url for sep in ('\\', ':')) or
                url.startswith(('./', '../')) or
                (url.startswith('/') and not url.startswith('//'))
            )
            if looks_like_local:
                if candidate_path.is_file() and candidate_path.suffix.lower() in {'.html', '.htm'}:
                    return str(candidate_path)
                else:
                    print("Local HTML file not found. Check the path or enter a full URL.\n")
                    continue
            
            # Add scheme if missing (for remote URLs)
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Validate URL format (local paths were already handled above)
            if not URLUtils.validate_url(url):
                print("Invalid URL format. Please check and try again.\n")
                continue
            
            # Validate URL is reachable (reuses the instance created in __init__)
            print("Validating URL...")
            is_valid, message = self.page_fetcher.validate_url(url)
            
            if not is_valid:
                print(f"URL validation failed: {message}\n")
                continue
            
            print(f"✓ {message}\n")
            return url
    
    def _get_format_selection(self) -> list:
        """Get format selection from user.
        
        The menu is printed on every prompt (including reprompts after invalid input)
        so the user always sees the current options.
        """
        while True:
            print("Select media formats to download:")
            print("-" * 40)
            
            for i, fmt in enumerate(self.SUPPORTED_FORMATS, 1):
                print(f"{i}. {fmt.upper()}")
            
            print(f"{len(self.SUPPORTED_FORMATS) + 1}. Select All")
            print("-" * 40)
            
            selection = input("Enter format numbers (comma-separated):\n> ").strip()
            
            if not selection:
                print("Please enter at least one format.\n")
                continue
            
            try:
                selected = [int(x.strip()) for x in selection.split(',') if x.strip()]
                
                if not selected:
                    print("Please enter at least one format.\n")
                    continue
                
                all_num = len(self.SUPPORTED_FORMATS) + 1
                if any(idx == all_num for idx in selected):
                    print("✓ Selected: All formats\n")
                    return self.SUPPORTED_FORMATS
                
                formats = []
                has_invalid = False
                for idx in selected:
                    if 1 <= idx <= len(self.SUPPORTED_FORMATS):
                        fmt = self.SUPPORTED_FORMATS[idx - 1]
                        if fmt not in formats:
                            formats.append(fmt)
                    else:
                        print(f"Invalid selection: {idx}\n")
                        has_invalid = True
                
                if has_invalid or not formats:
                    print("Please try again with valid format numbers (or the Select All number).\n")
                    continue
                
                print(f"✓ Selected: {', '.join([f.upper() for f in formats])}\n")
                return formats
                
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.\n")
                continue

    def _get_media_limit(self) -> int:
        """Ask the user how many media files to download"""
        while True:
            limit_input = input("Maximum number of files to download (press Enter for no limit):\n> ").strip()
            
            if not limit_input:
                return 0
            
            if limit_input.isdigit():
                limit = int(limit_input)
                if limit < 0:
                    print("Please enter a non-negative number (0 or press Enter for no limit).\n")
                    continue
                if limit == 0:
                    print("✓ No limit on number of files.\n")
                else:
                    print(f"✓ Will download up to {limit} files.\n")
                return limit
            
            print("Invalid input. Enter a non-negative integer or press Enter for no limit.\n")
    
    def _scrape_and_download(self, url: str, formats: list, max_files: int):
        """Scrape webpage and download media"""
        try:
            # Ensure we have a fetcher (defensive; normally created in __init__)
            if self.page_fetcher is None:
                self.page_fetcher = PageFetcher()

            # Fetch or load page (use a single local check to avoid duplication)
            input_path = Path(url).expanduser()
            is_local_html = input_path.is_file() and input_path.suffix.lower() in {'.html', '.htm'}
            if is_local_html:
                print("Loading local HTML file...")
                html, message = self.page_fetcher.load_local_html(url)
                base_url = input_path.resolve().as_uri()
            else:
                print("Fetching webpage...")
                html, message = self.page_fetcher.fetch_page(url)
                base_url = url
            
            if not html:
                print(f"Failed to load page: {message}\n")
                return
            
            print(f"✓ {message}")
            
            # Find media
            print("Searching for media files...")
            media_urls = MediaFinder.find_media_urls(html, base_url, formats)

            # === DEBUG START (temporary to diagnose 0 media on Tenor) ===
            print(f"[DEBUG] base_url={base_url}")
            print(f"[DEBUG] html_length={len(html) if html else 0}")
            print(f"[DEBUG] formats_requested={formats}")
            print(f"[DEBUG] media_urls_found_before_limit={len(media_urls)}")
            if media_urls:
                print(f"[DEBUG] first_3_urls={media_urls[:3]}")
            else:
                print("[DEBUG] ZERO media found by finder.")
                if html:
                    # Save HTML for manual inspection
                    try:
                        debug_html_path = "last_fetched_debug.html"
                        with open(debug_html_path, "w", encoding="utf-8", errors="ignore") as df:
                            df.write(html)
                        print(f"[DEBUG] Saved fetched HTML to {debug_html_path} for inspection (open in browser or editor)")
                    except Exception as e:
                        print(f"[DEBUG] Could not save debug HTML: {e}")

                    # Print first 1500 chars to see what we actually got
                    preview = html[:1500].replace('\n', ' ')[:500]
                    print(f"[DEBUG] HTML preview (first ~500 chars): {preview}...")

                    if 'tenor.com' in base_url.lower():
                        import re
                        raw_gifs = re.findall(r'https?://[^"\s<>]+\.(?:gif|webp)', html, re.I)
                        print(f"[DEBUG] raw .gif/.webp matches in HTML source: {len(raw_gifs)}")
                        if raw_gifs:
                            print(f"[DEBUG] sample_raw_url={raw_gifs[0]}")
                        # Check for common Tenor patterns (data-src, picture, etc.)
                        if 'data-src' in html or '<picture' in html:
                            print("[DEBUG] HTML contains data-src or <picture> tags (possible lazy load)")
                        # Check for signs of blocking / consent / JS-only page
                        lower_html = html.lower()
                        for indicator in ['captcha', 'cloudflare', 'access denied', 'bot', 'consent', 'enable javascript', 'please wait']:
                            if indicator in lower_html:
                                print(f"[DEBUG] HTML contains possible blocking/consent text: '{indicator}'")
            # === DEBUG END ===

            if not media_urls:
                print("No media files found matching selected formats.\n")
                return
            
            total_found = len(media_urls)
            to_download = media_urls[:max_files] if max_files > 0 else media_urls
            
            print(f"✓ Found {total_found} media files")
            if max_files > 0:
                print(f"✓ Downloading up to {len(to_download)} files\n")
            else:
                print("\n")
            
            # Create output directory (use the same local check + original url for domain)
            if is_local_html:
                domain = input_path.stem
            else:
                domain = URLUtils.get_domain_name(url)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(__file__).parent / "downloads" / f"{domain}_{timestamp}"
            
            print(f"Downloading to: {output_dir}")
            print("-" * 50)

            # Small polite pause before the download batch starts. Makes the overall
            # scraping session look less robotic to the target site.
            time.sleep(1.0 + random.uniform(0, 1.5))  # 1.0 - 2.5s random jitter

            # Download media (close any previous downloader from an earlier scrape in this run).
            # We pass rotate_user_agents + resume + source_url so the per-request UA
            # rotation and dynamic Referer logic in MediaDownloader are activated.
            # This makes CLI downloads behave more like the bot integration for anti-bot resistance.
            if self.downloader:
                self.downloader.close()
            self.downloader = MediaDownloader(
                delay_between_requests=2.5,   # Conservative delay to reduce flagging / rate limits
                rotate_user_agents=True,
                backoff_factor=1.5,           # Slightly more backoff on retries
            )
            source_for_referer = url if not is_local_html else None
            stats = self.downloader.download_media(
                to_download,
                str(output_dir),
                show_progress=True,
                resume=True,
                source_url=source_for_referer
            )
            
            # Display report (pass original discovered count so "Files Found" in the
            # final report reflects what was on the page, not the post-limit number)
            self._display_report(url, stats, output_dir, total_found)
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            print(f"Error during scraping: {e}\n")
    
    def _display_report(self, url: str, stats: dict, output_dir: Path, total_found: int | None = None):
        """Display download report"""
        print("\n" + "="*50)
        print("SCRAPE COMPLETE")
        print("="*50)
        print(f"\nURL:\n{url}")
        found_display = total_found if total_found is not None else stats.get('total', 0)
        print(f"\nFiles Found:\n{found_display}")
        print(f"\nDownloaded:\n{stats.get('successful', 0)}")
        skipped = stats.get('skipped', 0)
        if skipped:
            print(f"\nSkipped:\n{skipped}")
        print(f"\nFailed:\n{stats.get('failed', 0)}")
        print(f"\nTotal Size:\n{self._format_size(stats.get('total_size', 0))}")
        print(f"\nLocation:\n{output_dir}")
        
        if stats.get('failed', 0) > 0:
            print(f"\nFailed Downloads ({stats['failed']}):")
            failed_urls = stats.get('failed_urls', [])
            for u in failed_urls[:5]:
                print(f"  - {u}")
            if len(failed_urls) > 5:
                print(f"  ... and {len(failed_urls) - 5} more")
        
        print("\n" + "="*50 + "\n")
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def _ask_continue(self) -> bool:
        """Ask user if they want to continue"""
        response = input("Download another URL? (y/n): ").strip().lower()
        return response == 'y'
    
    def _cleanup(self):
        """Clean up resources"""
        if self.page_fetcher:
            self.page_fetcher.close()
            self.page_fetcher = None
        if self.downloader:
            self.downloader.close()
            self.downloader = None


def main():
    """Entry point"""
    app = MediaScraperApp()
    app.run()


if __name__ == "__main__":
    main()
