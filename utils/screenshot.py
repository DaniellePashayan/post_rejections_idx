"""Screenshot utility for error debugging"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from selenium import webdriver


class ScreenshotManager:
    """Manages screenshot capture for debugging purposes"""
    
    def __init__(self, driver: webdriver.Chrome, log_folder_path: str):
        self.driver = driver
        self.log_folder_path = Path(log_folder_path)
        self.screenshots_dir = self.log_folder_path / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
    
    def capture_error_screenshot(self, error_context: str = "", exception: Optional[Exception] = None) -> str:
        """
        Capture screenshot when an error occurs
        
        Args:
            error_context: Description of what was happening when error occurred
            exception: The exception that was caught (optional)
            
        Returns:
            Path to the saved screenshot file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        
        # Create descriptive filename
        context_part = error_context.replace(" ", "_").replace("/", "-")[:50] if error_context else "error"
        filename = f"error_{timestamp}_{context_part}.png"
        filepath = self.screenshots_dir / filename
        
        try:
            # Capture screenshot
            self.driver.save_screenshot(str(filepath))
            
            # Log the screenshot with context
            log_msg = f"Screenshot captured: {filename}"
            if error_context:
                log_msg += f" | Context: {error_context}"
            if exception:
                log_msg += f" | Exception: {type(exception).__name__}: {str(exception)}"
            
            logger.debug(log_msg)
            return str(filepath)
            
        except Exception as screenshot_error:
            logger.error(f"Failed to capture screenshot: {screenshot_error}")
            return ""
    
    def capture_page_source(self, error_context: str = "") -> str:
        """
        Also capture page source for detailed debugging
        
        Returns:
            Path to the saved HTML file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        context_part = error_context.replace(" ", "_").replace("/", "-")[:50] if error_context else "error"
        filename = f"page_source_{timestamp}_{context_part}.html"
        filepath = self.screenshots_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.debug(f"Page source saved: {filename}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save page source: {e}")
            return ""


def screenshot_on_error(screenshot_manager: ScreenshotManager, context: str = ""):
    """
    Decorator to automatically capture screenshots when exceptions occur
    
    Usage:
        @screenshot_on_error(screenshot_manager, "login process")
        def login_function():
            # your code here
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                screenshot_manager.capture_error_screenshot(
                    error_context=f"{context} - {func.__name__}",
                    exception=e
                )
                raise  # Re-raise the exception
        return wrapper
    return decorator


def safe_execute_with_screenshot(screenshot_manager: ScreenshotManager, 
                                func, 
                                context: str = "",
                                *args, **kwargs):
    """
    Execute a function and capture screenshot if it fails
    
    Args:
        screenshot_manager: ScreenshotManager instance
        func: Function to execute
        context: Description of the operation
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        Tuple of (success: bool, result: any, error: Exception|None)
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        screenshot_manager.capture_error_screenshot(
            error_context=context,
            exception=e
        )
        return False, None, e