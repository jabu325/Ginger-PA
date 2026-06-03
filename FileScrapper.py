"""
Main Media Scraper Module - Complete CLI Interface
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from scraper import PageFetcher, MediaFinder, MediaDownloader
from scraper.url_utils import URLUtils

# Configure logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class MediaScraperApp:
    """Main Media Scraper Application"""
    
    SUPPORTED_FORMATS = list(URLUtils.SUPPORTED_FORMATS.keys())
    
    def __init__(self):
        """Initialize the application"""
        self.page_fetcher = None
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
                if not formats:
                    print("No formats selected. Try again.\n")
                    continue

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
        """Get and validate URL from user"""
        while True:
            url = input("Enter URL (or 'quit' to exit):\n> ").strip()
            
            if url.lower() == 'quit':
                return None
            
            if not url:
                print("URL cannot be empty.\n")
                continue
            
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Validate URL format
            if not URLUtils.validate_url(url):
                print("Invalid URL format. Please check and try again.\n")
                continue
            
            # Validate URL is reachable
            print("Validating URL...")
            self.page_fetcher = PageFetcher()
            is_valid, message = self.page_fetcher.validate_url(url)
            
            if not is_valid:
                print(f"URL validation failed: {message}\n")
                continue
            
            print(f"✓ {message}\n")
            return url
    
    def _get_format_selection(self) -> list:
        """Get format selection from user"""
        print("Select media formats to download:")
        print("-" * 40)
        
        for i, fmt in enumerate(self.SUPPORTED_FORMATS, 1):
            print(f"{i}. {fmt.upper()}")
        
        print(f"{len(self.SUPPORTED_FORMATS) + 1}. Select All")
        print("-" * 40)
        
        while True:
            selection = input("Enter format numbers (comma-separated):\n> ").strip()
            
            if not selection:
                print("Please enter at least one format.\n")
                continue
            
            try:
                selected = [int(x.strip()) for x in selection.split(',')]
                
                formats = []
                for idx in selected:
                    if idx == len(self.SUPPORTED_FORMATS) + 1:
                        return self.SUPPORTED_FORMATS
                    elif 1 <= idx <= len(self.SUPPORTED_FORMATS):
                        formats.append(self.SUPPORTED_FORMATS[idx - 1])
                    else:
                        print(f"Invalid selection: {idx}\n")
                        return None
                
                if formats:
                    print(f"✓ Selected: {', '.join([f.upper() for f in formats])}\n")
                    return formats
                
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.\n")

    def _get_media_limit(self) -> int:
        """Ask the user how many media files to download"""
        while True:
            limit_input = input("Maximum number of files to download (press Enter for no limit):\n> ").strip()
            
            if not limit_input:
                return 0
            
            if limit_input.isdigit():
                limit = int(limit_input)
                if limit < 1:
                    print("Please enter a number greater than zero, or press Enter for no limit.\n")
                    continue
                print(f"✓ Will download up to {limit} files.\n")
                return limit
            
            print("Invalid input. Enter a positive integer or press Enter for no limit.\n")
    
    def _scrape_and_download(self, url: str, formats: list, max_files: int):
        """Scrape webpage and download media"""
        try:
            # Fetch page
            print("Fetching webpage...")
            html, message = self.page_fetcher.fetch_page(url)
            
            if not html:
                print(f"Failed to fetch page: {message}\n")
                return
            
            print(f"✓ {message}")
            
            # Find media
            print("Searching for media files...")
            media_urls = MediaFinder.find_media_urls(html, url, formats)
            
            if not media_urls:
                print("No media files found matching selected formats.\n")
                return
            
            total_found = len(media_urls)
            if max_files > 0:
                media_urls = media_urls[:max_files]
            
            print(f"✓ Found {total_found} media files")
            if max_files > 0:
                print(f"✓ Downloading up to {len(media_urls)} files\n")
            else:
                print("\n")
            
            # Create output directory
            domain = URLUtils.get_domain_name(url)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(__file__).parent / "downloads" / f"{domain}_{timestamp}"
            
            print(f"Downloading to: {output_dir}")
            print("-" * 50)
            
            # Download media
            self.downloader = MediaDownloader()
            stats = self.downloader.download_media(media_urls, str(output_dir), show_progress=True)
            
            # Display report
            self._display_report(url, stats, output_dir)
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            print(f"Error during scraping: {e}\n")
    
    def _display_report(self, url: str, stats: dict, output_dir: Path):
        """Display download report"""
        print("\n" + "="*50)
        print("SCRAPE COMPLETE")
        print("="*50)
        print(f"\nURL:\n{url}")
        print(f"\nFiles Found:\n{stats['total']}")
        print(f"\nDownloaded:\n{stats['successful']}")
        print(f"\nFailed:\n{stats['failed']}")
        print(f"\nTotal Size:\n{self._format_size(stats['total_size'])}")
        print(f"\nLocation:\n{output_dir}")
        
        if stats['failed'] > 0:
            print(f"\nFailed Downloads ({stats['failed']}):")
            for url in stats['failed_urls'][:5]:
                print(f"  - {url}")
            if len(stats['failed_urls']) > 5:
                print(f"  ... and {len(stats['failed_urls']) - 5} more")
        
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
        if self.downloader:
            self.downloader.close()


def main():
    """Entry point"""
    app = MediaScraperApp()
    app.run()


if __name__ == "__main__":
    main()
