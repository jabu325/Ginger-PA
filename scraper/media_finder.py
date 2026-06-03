"""
Media Finder - Extract media URLs from HTML content
"""

from bs4 import BeautifulSoup
import logging
from .url_utils import URLUtils

logger = logging.getLogger(__name__)


class MediaFinder:
    """Extract media URLs from HTML content"""
    
    @staticmethod
    def find_media_urls(html: str, base_url: str, formats: list) -> list:
        """
        Find all media URLs matching specified formats
        
        Args:
            html: HTML content
            base_url: Base URL for relative path resolution
            formats: List of formats to search for (e.g., ['gif', 'jpg'])
            
        Returns:
            list: List of absolute media URLs
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            media_urls = set()  # Use set for automatic deduplication
            
            # Find in img tags
            media_urls.update(MediaFinder._extract_from_img_tags(soup, base_url, formats))
            
            # Find in video tags
            media_urls.update(MediaFinder._extract_from_video_tags(soup, base_url, formats))
            
            # Find in source tags
            media_urls.update(MediaFinder._extract_from_source_tags(soup, base_url, formats))
            
            # Find in picture tags
            media_urls.update(MediaFinder._extract_from_picture_tags(soup, base_url, formats))
            
            # Find direct links in content
            media_urls.update(MediaFinder._extract_from_links(soup, base_url, formats))
            
            logger.info(f"Found {len(media_urls)} unique media URLs")
            return list(media_urls)
            
        except Exception as e:
            logger.error(f"Error finding media URLs: {e}")
            return []
    
    @staticmethod
    def _extract_from_img_tags(soup, base_url: str, formats: list) -> set:
        """Extract URLs from img tags"""
        urls = set()
        try:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src:
                    absolute_url = URLUtils.normalize_url(src, base_url)
                    if URLUtils.is_valid_format(absolute_url, formats):
                        urls.add(absolute_url)
        except Exception as e:
            logger.warning(f"Error extracting from img tags: {e}")
        
        return urls
    
    @staticmethod
    def _extract_from_video_tags(soup, base_url: str, formats: list) -> set:
        """Extract URLs from video tags"""
        urls = set()
        try:
            for video in soup.find_all('video'):
                src = video.get('src')
                if src:
                    absolute_url = URLUtils.normalize_url(src, base_url)
                    if URLUtils.is_valid_format(absolute_url, formats):
                        urls.add(absolute_url)
        except Exception as e:
            logger.warning(f"Error extracting from video tags: {e}")
        
        return urls
    
    @staticmethod
    def _extract_from_source_tags(soup, base_url: str, formats: list) -> set:
        """Extract URLs from source tags (inside video/audio)"""
        urls = set()
        try:
            for source in soup.find_all('source'):
                src = source.get('src')
                if src:
                    absolute_url = URLUtils.normalize_url(src, base_url)
                    if URLUtils.is_valid_format(absolute_url, formats):
                        urls.add(absolute_url)
        except Exception as e:
            logger.warning(f"Error extracting from source tags: {e}")
        
        return urls
    
    @staticmethod
    def _extract_from_picture_tags(soup, base_url: str, formats: list) -> set:
        """Extract URLs from picture tags"""
        urls = set()
        try:
            for picture in soup.find_all('picture'):
                for img in picture.find_all('img'):
                    src = img.get('src')
                    if src:
                        absolute_url = URLUtils.normalize_url(src, base_url)
                        if URLUtils.is_valid_format(absolute_url, formats):
                            urls.add(absolute_url)
                
                for source in picture.find_all('source'):
                    srcset = source.get('srcset')
                    if srcset:
                        for item in srcset.split(','):
                            url = item.split()[0].strip()
                            if url:
                                absolute_url = URLUtils.normalize_url(url, base_url)
                                if URLUtils.is_valid_format(absolute_url, formats):
                                    urls.add(absolute_url)
        except Exception as e:
            logger.warning(f"Error extracting from picture tags: {e}")
        
        return urls
    
    @staticmethod
    def _extract_from_links(soup, base_url: str, formats: list) -> set:
        """Extract URLs from direct links"""
        urls = set()
        try:
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href:
                    absolute_url = URLUtils.normalize_url(href, base_url)
                    if URLUtils.is_valid_format(absolute_url, formats):
                        urls.add(absolute_url)
        except Exception as e:
            logger.warning(f"Error extracting from links: {e}")
        
        return urls
