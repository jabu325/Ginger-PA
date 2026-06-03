"""
Media Downloader - Download media files with progress tracking
"""

import os
import logging
from pathlib import Path
from tqdm import tqdm
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .url_utils import URLUtils

logger = logging.getLogger(__name__)


class MediaDownloader:
    """Download media files with progress tracking and error handling"""
    
    def __init__(self, timeout: int = 30, retries: int = 3, chunk_size: int = 8192):
        """
        Initialize MediaDownloader
        
        Args:
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            chunk_size: Download chunk size in bytes
        """
        self.timeout = timeout
        self.retries = retries
        self.chunk_size = chunk_size
        self.session = self._create_session()
        self.download_stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'total_size': 0
        }
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy and browser-like headers"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Browser-like headers to avoid 403 Forbidden
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        return session
    
    def download_media(self, urls: list, output_dir: str, show_progress: bool = True) -> dict:
        """
        Download multiple media files
        
        Args:
            urls: List of media URLs
            output_dir: Directory to save files
            show_progress: Show progress bar
            
        Returns:
            dict: Download statistics
        """
        self.download_stats = {
            'total': len(urls),
            'successful': 0,
            'failed': 0,
            'total_size': 0,
            'failed_urls': []
        }
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        if show_progress:
            urls = tqdm(urls, desc="Downloading media", unit="file")
        
        for url in urls:
            self._download_file(url, output_dir)
        
        return self.download_stats
    
    def _download_file(self, url: str, output_dir: str) -> bool:
        """
        Download a single file
        
        Args:
            url: Media URL
            output_dir: Directory to save file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            filename = URLUtils.get_filename_from_url(url)
            if not filename:
                filename = 'media'
            
            # Handle duplicate filenames
            filepath = Path(output_dir) / filename
            filepath = self._get_unique_filename(filepath)
            
            # Try HEAD request to get file size (optional)
            file_size = 0
            try:
                head_response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
                if head_response.status_code == 200:
                    file_size = int(head_response.headers.get('content-length', 0))
            except Exception as e:
                logger.debug(f"HEAD request failed for {url}: {e}. Will try GET anyway.")
            
            # Download file with GET
            response = self.session.get(url, timeout=self.timeout, stream=True)
            
            if response.status_code == 403:
                logger.warning(f"Access forbidden (403) for {url} - website may block scrapers")
                self.download_stats['failed'] += 1
                self.download_stats['failed_urls'].append(url)
                return False
            elif response.status_code == 404:
                logger.warning(f"Not found (404): {url}")
                self.download_stats['failed'] += 1
                self.download_stats['failed_urls'].append(url)
                return False
            
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
            
            actual_size = filepath.stat().st_size
            self.download_stats['successful'] += 1
            self.download_stats['total_size'] += actual_size
            
            logger.info(f"Downloaded: {filename} ({actual_size} bytes)")
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if '403' in error_msg:
                logger.warning(f"HTTP 403 Forbidden for {url} - website blocks this request")
            else:
                logger.warning(f"Failed to download {url}: {error_msg}")
            self.download_stats['failed'] += 1
            self.download_stats['failed_urls'].append(url)
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            self.download_stats['failed'] += 1
            self.download_stats['failed_urls'].append(url)
            return False
    
    @staticmethod
    def _get_unique_filename(filepath: Path) -> Path:
        """
        Get unique filename if file exists
        
        Args:
            filepath: Original filepath
            
        Returns:
            Path: Unique filepath
        """
        if not filepath.exists():
            return filepath
        
        stem = filepath.stem
        suffix = filepath.suffix
        parent = filepath.parent
        
        counter = 1
        while True:
            new_filename = f"{stem}_{counter}{suffix}"
            new_filepath = parent / new_filename
            if not new_filepath.exists():
                return new_filepath
            counter += 1
    
    def close(self):
        """Close the session"""
        self.session.close()
        logger.info("MediaDownloader session closed")
