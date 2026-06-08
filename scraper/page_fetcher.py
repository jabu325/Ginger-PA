"""
Page Fetcher - Retrieve and validate webpages
"""

import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class PageFetcher:
    """Fetch and validate webpage content"""
    
    def __init__(self, timeout: int = 30, retries: int = 3):
        """
        Initialize PageFetcher
        
        Args:
            timeout: Request timeout in seconds
            retries: Number of retry attempts
        """
        self.timeout = timeout
        self.retries = retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry strategy
        
        Returns:
            requests.Session: Configured session
        """
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        return session
    
    def validate_url(self, url: str) -> tuple[bool, str]:
        """
        Validate URL is reachable with 200 status
        
        Args:
            url: URL to validate
            
        Returns:
            tuple: (is_valid, message)
        """
        try:
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            
            if response.status_code == 200:
                return True, "URL is valid and reachable"
            else:
                return False, f"URL returned status code {response.status_code}"
                
        except requests.exceptions.MissingSchema:
            return False, "Invalid URL format (missing http:// or https://)"
        except requests.exceptions.ConnectionError:
            return False, "Connection error - URL is not reachable"
        except requests.exceptions.Timeout:
            return False, "Request timeout - URL took too long to respond"
        except requests.exceptions.RequestException as e:
            return False, f"Request error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def fetch_page(self, url: str) -> tuple[str | None, str]:
        """
        Fetch webpage HTML content
        
        Args:
            url: URL to fetch
            
        Returns:
            tuple: (html_content, message)
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            
            logger.info(f"Successfully fetched {url}")
            return response.text, "Page fetched successfully"
            
        except requests.exceptions.HTTPError as e:
            return None, f"HTTP error: {e.response.status_code}"
        except requests.exceptions.Timeout:
            return None, "Request timeout while fetching page"
        except requests.exceptions.RequestException as e:
            return None, f"Request error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"
    
    def save_page_html(self, html: str, output_file: str | Path) -> Path:
        """Save the fetched HTML page to a local file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"Saved page HTML to {output_path}")
        return output_path

    def load_local_html(self, file_path: str) -> tuple[str | None, str]:
        """Load HTML content from a local file path."""
        try:
            path = Path(file_path).expanduser()
            if not path.is_file():
                return None, "Local file not found"
            if path.suffix.lower() not in {'.html', '.htm'}:
                return None, "File is not an HTML document"

            html = path.read_text(encoding='utf-8', errors='ignore')
            logger.info(f"Loaded local HTML file {path}")
            return html, "Local HTML file loaded successfully"
        except Exception as e:
            return None, f"Local file read error: {e}"

    def close(self):
        """Close the session"""
        self.session.close()
        logger.info("PageFetcher session closed")
