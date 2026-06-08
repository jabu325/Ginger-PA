"""
Media Downloader - Download media files with progress tracking
"""

import json
import logging
import time
import random
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .url_utils import URLUtils

logger = logging.getLogger(__name__)


class MediaDownloader:
    """Download media files with progress tracking and error handling"""
    
    def __init__(self, timeout: int = 30, retries: int = 3, chunk_size: int = 8192, backoff_factor: float = 1.0,
                 delay_between_requests: float = 1.0, rotate_user_agents: bool = False, user_agents: list | None = None):
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
        self.backoff_factor = backoff_factor
        self.delay_between_requests = delay_between_requests
        self.rotate_user_agents = rotate_user_agents
        # default list of browser UAs to rotate when requested
        self.user_agents = user_agents or [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
        ]
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
    
    def download_media(self, urls: list, output_dir: str, show_progress: bool = True, resume: bool = False, source_url: str | None = None) -> dict:
        """
        Download multiple media files with retry and resume support.
        
        Args:
            urls: List of media URLs
            output_dir: Directory to save files
            show_progress: Show progress bar
            resume: Whether to resume from previous downloads in the same folder
            source_url: Original page URL used to identify a resume folder/state
            
        Returns:
            dict: Download statistics
        """
        self.download_stats = {
            'total': len(urls),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'downloaded_paths': [],
            'failed_urls': [],
            'processed_urls': []
        }
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        state_file = output_path / ".download_state.json"
        state = {}

        if resume and state_file.exists():
            state = self._load_state(state_file)
            if source_url and state.get('source_url') != source_url:
                state = {}

        if not state:
            state = {
                'source_url': source_url,
                'media_urls': urls,
                'processed_urls': [],
                'downloaded_urls': [],
                'failed_urls': [],
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'last_updated': datetime.utcnow().isoformat() + 'Z'
            }

        if show_progress:
            urls = tqdm(urls, desc="Downloading media", unit="file")

        for url in urls:
            # rotate UA per-request if requested to reduce fingerprinting
            if resume and self.rotate_user_agents:
                try:
                    self.session.headers['User-Agent'] = random.choice(self.user_agents)
                except Exception:
                    pass
            # set referer header to the source URL when available to mimic browser navigation
            if source_url:
                try:
                    self.session.headers['Referer'] = source_url
                except Exception:
                    pass
            if resume and url in state['processed_urls']:
                self.download_stats['skipped'] += 1
                logger.info(f"Skipping already processed URL: {url}")
                # small polite pause when skipping during resumed sessions
                time.sleep(self.delay_between_requests * (0.5 + random.random() * 0.5))
                continue

            success = self._download_file(url, output_dir)
            self.download_stats['processed_urls'].append(url)

            if success:
                state['downloaded_urls'].append(url)
            else:
                state['failed_urls'].append(url)

            state['last_updated'] = datetime.utcnow().isoformat() + 'Z'
            self._save_state(state_file, state)

            # polite delay between requests to avoid triggering anti-bot
            time.sleep(self.delay_between_requests + random.uniform(0, self.delay_between_requests * 0.5))

        return self.download_stats
    
    def _download_file(self, url: str, output_dir: str) -> bool:
        """
        Download a single file with retry support.
        
        Args:
            url: Media URL
            output_dir: Directory to save file
            
        Returns:
            bool: True if successful, False otherwise
        """
        filename = URLUtils.get_filename_from_url(url) or 'media'
        filepath = Path(output_dir) / filename
        filepath = self._get_unique_filename(filepath)

        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                head_response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
                if head_response.status_code == 200:
                    logger.debug(f"HEAD response length for {url}: {head_response.headers.get('content-length')}")
            except Exception as e:
                logger.debug(f"HEAD request failed for {url}: {e}. Will try GET anyway.")

            try:
                response = self.session.get(url, timeout=self.timeout, stream=True)

                if response.status_code == 403:
                    logger.warning(f"Access forbidden (403) for {url} - website may block scrapers")
                    last_error = '403'
                    break
                if response.status_code == 404:
                    logger.warning(f"Not found (404): {url}")
                    last_error = '404'
                    break

                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)

                actual_size = filepath.stat().st_size
                self.download_stats['successful'] += 1
                self.download_stats['total_size'] += actual_size
                self.download_stats['downloaded_paths'].append(filepath)

                logger.info(f"Downloaded: {filepath.name} ({actual_size} bytes)")
                return True

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                if filepath.exists():
                    filepath.unlink(missing_ok=True)
                if attempt < self.retries:
                    logger.warning(f"Download failed for {url} (attempt {attempt}/{self.retries}): {e}. Retrying...")
                    time.sleep(self.backoff_factor * attempt)
                    continue
                logger.warning(f"Download failed for {url}: {e}")
            except Exception as e:
                last_error = str(e)
                if filepath.exists():
                    filepath.unlink(missing_ok=True)
                logger.error(f"Unexpected error downloading {url}: {e}")

            if attempt < self.retries:
                time.sleep(self.backoff_factor * attempt)

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

    def _save_state(self, state_path: Path, state: dict) -> None:
        try:
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save download state to {state_path}: {e}")

    def _load_state(self, state_path: Path) -> dict:
        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load download state from {state_path}: {e}")
            return {}

    def close(self):
        """Close the session"""
        self.session.close()
        logger.info("MediaDownloader session closed")
