"""
URL Utilities - URL validation, normalization, and manipulation
"""

from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)


class URLUtils:
    """Utility class for URL operations"""
    
    SUPPORTED_FORMATS = {
        'gif': ['.gif'],
        'webp': ['.webp'],
        'mp4': ['.mp4'],
        'jpg': ['.jpg', '.jpeg'],
        'png': ['.png']
    }
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format
        
        Args:
            url: URL string to validate
            
        Returns:
            bool: True if URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False
    
    @staticmethod
    def normalize_url(relative_url: str, base_url: str) -> str:
        """
        Convert relative URL to absolute URL
        
        Args:
            relative_url: Potentially relative URL
            base_url: Base URL for resolution
            
        Returns:
            str: Absolute URL
        """
        try:
            return urljoin(base_url, relative_url)
        except Exception as e:
            logger.error(f"URL normalization error: {e}")
            return relative_url
    
    @staticmethod
    def get_filename_from_url(url: str) -> str:
        """
        Extract filename from URL
        
        Args:
            url: URL string
            
        Returns:
            str: Filename or 'media' if not found
        """
        try:
            path = urlparse(url).path
            filename = path.split('/')[-1]
            return filename if filename else 'media'
        except Exception as e:
            logger.error(f"Filename extraction error: {e}")
            return 'media'
    
    @staticmethod
    def get_extension_from_url(url: str) -> str:
        """
        Extract file extension from URL
        
        Args:
            url: URL string
            
        Returns:
            str: File extension (including dot) or empty string
        """
        try:
            # Remove query parameters
            path = urlparse(url).path.split('?')[0]
            if '.' in path:
                extension = path.rsplit('.', 1)[-1].lower()
                return f".{extension}" if extension else ""
            return ""
        except Exception as e:
            logger.error(f"Extension extraction error: {e}")
            return ""
    
    @staticmethod
    def is_valid_format(url: str, formats: list) -> bool:
        """
        Check if URL has a supported format
        
        Args:
            url: URL string
            formats: List of format names (e.g., ['gif', 'jpg'])
            
        Returns:
            bool: True if URL matches one of the formats
        """
        extension = URLUtils.get_extension_from_url(url).lower()
        
        for format_name in formats:
            if format_name.lower() in URLUtils.SUPPORTED_FORMATS:
                if extension in URLUtils.SUPPORTED_FORMATS[format_name.lower()]:
                    return True
        
        return False
    
    @staticmethod
    def get_domain_name(url: str) -> str:
        """
        Extract domain name from URL
        
        Args:
            url: URL string
            
        Returns:
            str: Domain name (without www, dots replaced with underscores)
        """
        try:
            domain = urlparse(url).netloc.replace('www.', '')
            return domain.replace('.', '_')
        except Exception as e:
            logger.error(f"Domain extraction error: {e}")
            return "unknown"
