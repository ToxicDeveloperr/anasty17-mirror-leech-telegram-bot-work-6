#!/usr/bin/env python3
"""
Configuration file for Terabox Automation Bot
Modify this file according to your requirements
"""

class TeraboxConfig:
    """
    Terabox Automation Configuration
    """
    
    # ===== CHANNEL CONFIGURATION =====
    # Replace these with your actual channel IDs
    # To get channel ID: Forward a message from the channel to @userinfobot
    
    SOURCE_CHANNEL_ID = -1002487065354      # Source channel where terabox links are posted
    DESTINATION_CHANNEL_ID = -1002176533426 # Destination channel where files will be uploaded
    DETAILS_CHANNEL_ID = -1002271035070     # Details channel for tracking and logging
    
    # ===== BOT CREDENTIALS =====
    # Get these from your existing config.py or from @BotFather and my.telegram.org
    
    BOT_TOKEN = "6716467783:AAHyqcU2BAJ9sKQv1fbMsF5Oxl4iOU-txrQ"
    TELEGRAM_API = 27710337
    TELEGRAM_HASH = "354e1dd8e1e3041ee2145196da8d6aac"
    
    # ===== PROCESSING SETTINGS =====
    
    # Maximum number of parallel downloads (1-5 recommended)
    MAX_CONCURRENT_DOWNLOADS = 3
    
    # Maximum number of messages to keep in queue
    QUEUE_MAX_SIZE = 100
    
    # Delay between processing messages (seconds) - to avoid rate limits
    PROCESS_DELAY = 2
    
    # Maximum number of terabox links to process per message
    MAX_LINKS_PER_MESSAGE = 10
    
    # ===== FILE SETTINGS =====
    
    # Maximum file size to upload (in bytes) - Telegram limit is 2GB
    MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
    
    # Temporary download folder
    TEMP_DOWNLOAD_DIR = "downloads"
    
    # File naming pattern for downloaded files
    FILE_NAME_PATTERN = "TeraboxFile_{index}_{timestamp}"
    
    # ===== LOGGING SETTINGS =====
    
    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL = "INFO"
    
    # Log file name (leave empty to disable file logging)
    LOG_FILE = "terabox_automation.log"
    
    # ===== RETRY SETTINGS =====
    
    # Number of retries for failed downloads
    DOWNLOAD_RETRIES = 3
    
    # Number of retries for failed uploads
    UPLOAD_RETRIES = 2
    
    # Delay between retries (seconds)
    RETRY_DELAY = 5
    
    # ===== NOTIFICATION SETTINGS =====
    
    # Send notification when automation starts/stops
    SEND_STARTUP_NOTIFICATION = True
    
    # Send notification for errors
    SEND_ERROR_NOTIFICATIONS = True
    
    # Admin user ID for notifications (optional)
    ADMIN_USER_ID = None  # Replace with your user ID if needed
    
    # ===== TERABOX API SETTINGS =====
    
    # Custom Terabox API endpoints (if you have your own)
    CUSTOM_TERABOX_API = None  # e.g., "https://your-api.com/terabox"
    
    # API timeout in seconds
    API_TIMEOUT = 30
    
    # User agent for requests
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
    
    # ===== ADVANCED SETTINGS =====
    
    # Enable/disable automatic cleanup of temporary files
    AUTO_CLEANUP = True
    
    # Cleanup interval (seconds) - how often to clean temp files
    CLEANUP_INTERVAL = 3600  # 1 hour
    
    # Maximum age of temp files before cleanup (seconds)
    TEMP_FILE_MAX_AGE = 7200  # 2 hours
    
    # Enable/disable progress messages during upload
    SHOW_UPLOAD_PROGRESS = True
    
    # Progress update interval (percentage)
    PROGRESS_UPDATE_INTERVAL = 10  # Every 10%
    
    # ===== DATABASE SETTINGS (Optional) =====
    
    # MongoDB connection string for logging processed links
    DATABASE_URL = None  # e.g., "mongodb://localhost:27017/terabox_automation"
    
    # Collection name for storing processed links
    PROCESSED_LINKS_COLLECTION = "processed_links"

# ===== VALIDATION FUNCTIONS =====

def validate_config():
    """Validate configuration values"""
    errors = []
    
    # Check required fields
    if not TeraboxConfig.BOT_TOKEN:
        errors.append("BOT_TOKEN is required")
    
    if not TeraboxConfig.TELEGRAM_API:
        errors.append("TELEGRAM_API is required")
    
    if not TeraboxConfig.TELEGRAM_HASH:
        errors.append("TELEGRAM_HASH is required")
    
    # Check channel IDs
    if not TeraboxConfig.SOURCE_CHANNEL_ID or TeraboxConfig.SOURCE_CHANNEL_ID == -1001234567890:
        errors.append("Please set a valid SOURCE_CHANNEL_ID")
    
    if not TeraboxConfig.DESTINATION_CHANNEL_ID or TeraboxConfig.DESTINATION_CHANNEL_ID == -1001234567891:
        errors.append("Please set a valid DESTINATION_CHANNEL_ID")
    
    if not TeraboxConfig.DETAILS_CHANNEL_ID or TeraboxConfig.DETAILS_CHANNEL_ID == -1001234567892:
        errors.append("Please set a valid DETAILS_CHANNEL_ID")
    
    # Check numeric values
    if TeraboxConfig.MAX_CONCURRENT_DOWNLOADS < 1 or TeraboxConfig.MAX_CONCURRENT_DOWNLOADS > 10:
        errors.append("MAX_CONCURRENT_DOWNLOADS should be between 1 and 10")
    
    if TeraboxConfig.QUEUE_MAX_SIZE < 10:
        errors.append("QUEUE_MAX_SIZE should be at least 10")
    
    if TeraboxConfig.PROCESS_DELAY < 0:
        errors.append("PROCESS_DELAY cannot be negative")
    
    return errors

def print_config_summary():
    """Print configuration summary"""
    print("=" * 50)
    print("TERABOX AUTOMATION CONFIGURATION SUMMARY")
    print("=" * 50)
    print(f"Source Channel ID: {TeraboxConfig.SOURCE_CHANNEL_ID}")
    print(f"Destination Channel ID: {TeraboxConfig.DESTINATION_CHANNEL_ID}")
    print(f"Details Channel ID: {TeraboxConfig.DETAILS_CHANNEL_ID}")
    print(f"Max Concurrent Downloads: {TeraboxConfig.MAX_CONCURRENT_DOWNLOADS}")
    print(f"Queue Max Size: {TeraboxConfig.QUEUE_MAX_SIZE}")
    print(f"Process Delay: {TeraboxConfig.PROCESS_DELAY}s")
    print(f"Max Links Per Message: {TeraboxConfig.MAX_LINKS_PER_MESSAGE}")
    print(f"Log Level: {TeraboxConfig.LOG_LEVEL}")
    print("=" * 50)

if __name__ == "__main__":
    # Validate and print configuration
    errors = validate_config()
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid!")
    
    print_config_summary()
