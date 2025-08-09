#!/usr/bin/env python3
"""
Terabox Link Auto-Processor with Source-Destination Channel Automation
This script automatically processes terabox links from source channel, 
downloads and uploads to destination channel with file tracking.
"""

import asyncio
import re
import logging
import os
import sys
import time
from queue import Queue
from threading import Thread
from urllib.parse import quote
from requests import Session
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaDocument
from pyrogram.errors import FloodWait, ChannelPrivate, ChatWriteForbidden

# Try to import bot modules with fallback
try:
    from bot.helper.mirror_leech_utils.download_utils.direct_link_generator import terabox
except ImportError:
    # Fallback terabox function if bot module not available
    def terabox(url):
        # Simple implementation using API
        from urllib.parse import quote
        import requests
        
        api_url = f"https://render-api-1-t692.onrender.com/fetch?url={quote(url)}"
        try:
            response = requests.get(api_url, timeout=30)
            data = response.json()
            
            if "proxy_url" in data:
                return data["proxy_url"]
            elif "✅ Status" in data:
                return data["📜 Extracted Info"][0]["🔽 Direct Download Link"]
            else:
                raise Exception("No download link found")
        except Exception as e:
            raise Exception(f"Terabox API error: {e}")

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('terabox_automation.log')
    ]
)
logger = logging.getLogger(__name__)

# ⚠️⚠️⚠️ IMPORTANT: UPDATE THESE CHANNEL IDs ⚠️⚠️⚠️
class Config:
    # GET YOUR CHANNEL IDs:
    # 1. Forward any message from your channel to @userinfobot
    # 2. Copy the channel ID (like -1001234567890)
    # 3. Replace the values below
    
    # 🔴 REPLACE WITH YOUR ACTUAL CHANNEL IDs 🔴
    SOURCE_CHANNEL_ID = -1002487065354      # Source channel where terabox links are posted
    DESTINATION_CHANNEL_ID = -1002176533426 # Destination channel where files will be uploaded
    DETAILS_CHANNEL_ID = -1002271035070     # Details channel for tracking and logging
    
    # ⚠️ THE BOT WILL NOT WORK UNTIL YOU UPDATE THESE IDs! ⚠️
    
    # Bot credentials (from your config.py)
    BOT_TOKEN = "6716467783:AAHyqcU2BAJ9sKQv1fbMsF5Oxl4iOU-txrQ"
    TELEGRAM_API = 27710337
    TELEGRAM_HASH = "354e1dd8e1e3041ee2145196da8d6aac"
    
    # Processing settings
    MAX_CONCURRENT_DOWNLOADS = 3  # Maximum parallel downloads
    QUEUE_MAX_SIZE = 100  # Maximum queue size
    PROCESS_DELAY = 2  # Delay between processing messages (seconds)
    
    # Enable debug mode
    DEBUG_MODE = True

# Initialize Pyrogram client
app = Client(
    "terabox_bot",
    api_id=Config.TELEGRAM_API,
    api_hash=Config.TELEGRAM_HASH,
    bot_token=Config.BOT_TOKEN
)

# Message processing queue
message_queue = Queue(maxsize=Config.QUEUE_MAX_SIZE)
processing_active = True

class TeraboxProcessor:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
        self.active_downloads = 0
        self.max_downloads = Config.MAX_CONCURRENT_DOWNLOADS

    def extract_terabox_links(self, text):
        """Extract all terabox links from message text"""
        terabox_patterns = [
            r'https?://(?:www\.)?terabox\.com/[^\s]+',
            r'https?://(?:www\.)?nephobox\.com/[^\s]+',
            r'https?://(?:www\.)?4funbox\.com/[^\s]+',
            r'https?://(?:www\.)?mirrobox\.com/[^\s]+',
            r'https?://(?:www\.)?momerybox\.com/[^\s]+',
            r'https?://(?:www\.)?teraboxapp\.com/[^\s]+',
            r'https?://(?:www\.)?1024tera\.com/[^\s]+',
            r'https?://(?:www\.)?terabox\.app/[^\s]+',
            r'https?://(?:www\.)?gibibox\.com/[^\s]+',
            r'https?://(?:www\.)?goaibox\.com/[^\s]+',
            r'https?://(?:www\.)?terasharelink\.com/[^\s]+',
            r'https?://(?:www\.)?teraboxlink\.com/[^\s]+',
            r'https?://(?:www\.)?freeterabox\.com/[^\s]+',
            r'https?://(?:www\.)?1024terabox\.com/[^\s]+',
            r'https?://(?:www\.)?teraboxshare\.com/[^\s]+',
            r'https?://(?:www\.)?terafileshare\.com/[^\s]+',
            r'https?://(?:www\.)?terabox\.club/[^\s]+'
        ]
        
        links = []
        for pattern in terabox_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            links.extend(matches)
        
        return list(set(links))  # Remove duplicates

    async def download_and_upload_file(self, url, filename, destination_channel):
        """Download file from terabox and upload to destination channel"""
        try:
            logger.info(f"Starting download: {filename}")
            
            # Get direct download link using existing terabox function
            direct_link = terabox(url)
            
            if isinstance(direct_link, dict):
                # Multiple files case
                file_urls = [item['url'] for item in direct_link['contents']]
                filenames = [item['filename'] for item in direct_link['contents']]
            else:
                # Single file case
                file_urls = [direct_link]
                filenames = [filename]
            
            uploaded_file_ids = []
            
            for file_url, file_name in zip(file_urls, filenames):
                # Download file
                with Session() as session:
                    session.headers.update({'User-Agent': self.user_agent})
                    response = session.get(file_url, stream=True)
                    response.raise_for_status()
                    
                    # Save file temporarily
                    temp_file_path = f"temp_{file_name}"
                    with open(temp_file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                
                # Upload to destination channel
                try:
                    sent_message = await app.send_document(
                        chat_id=destination_channel,
                        document=temp_file_path,
                        caption=f"📁 **{file_name}**\n\n🔗 **Original Link:** {url}",
                        progress=self.upload_progress,
                        progress_args=(file_name,)
                    )
                    
                    uploaded_file_ids.append(sent_message.id)
                    logger.info(f"Uploaded: {file_name} (Message ID: {sent_message.id})")
                    
                except Exception as upload_error:
                    logger.error(f"Upload failed for {file_name}: {upload_error}")
                    
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
            
            return uploaded_file_ids
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return []

    async def upload_progress(self, current, total, filename):
        """Upload progress callback"""
        percentage = (current / total) * 100
        if percentage % 10 == 0:  # Log every 10%
            logger.info(f"Uploading {filename}: {percentage:.1f}%")

    async def process_message(self, message_data):
        """Process a single message from the queue"""
        try:
            message, terabox_links = message_data
            
            if self.active_downloads >= self.max_downloads:
                logger.warning(f"Max downloads reached ({self.max_downloads}), queuing message")
                return
            
            self.active_downloads += 1
            
            logger.info(f"Processing message with {len(terabox_links)} terabox links")
            
            all_uploaded_file_ids = []
            original_message_text = message.text or message.caption or ""
            
            # Process each terabox link
            for i, link in enumerate(terabox_links, 1):
                try:
                    # Extract filename from link or use default
                    filename = f"TeraboxFile_{i}.bin"
                    
                    # Download and upload
                    file_ids = await self.download_and_upload_file(
                        link, 
                        filename, 
                        Config.DESTINATION_CHANNEL_ID
                    )
                    
                    all_uploaded_file_ids.extend(file_ids)
                    
                    # Add delay between downloads to avoid rate limits
                    if i < len(terabox_links):
                        await asyncio.sleep(Config.PROCESS_DELAY)
                        
                except Exception as link_error:
                    logger.error(f"Error processing link {link}: {link_error}")
                    continue
            
            # Send details to details channel
            if all_uploaded_file_ids:
                await self.send_details_summary(
                    original_message_text,
                    terabox_links,
                    all_uploaded_file_ids,
                    message
                )
            
        except Exception as e:
            logger.error(f"Error in process_message: {e}")
        finally:
            self.active_downloads -= 1

    async def send_details_summary(self, original_text, links, file_ids, original_message):
        """Send summary to details channel"""
        try:
            summary_text = f"📊 **Processing Summary**\n\n"
            summary_text += f"🔗 **Original Links Found:** {len(links)}\n"
            summary_text += f"📁 **Files Uploaded:** {len(file_ids)}\n\n"
            
            summary_text += "**Original Message:**\n"
            summary_text += f"```\n{original_text[:500]}{'...' if len(original_text) > 500 else ''}\n```\n\n"
            
            summary_text += "**Terabox Links:**\n"
            for i, link in enumerate(links, 1):
                summary_text += f"{i}. {link}\n"
            
            summary_text += f"\n**Uploaded File IDs:**\n"
            for i, file_id in enumerate(file_ids, 1):
                summary_text += f"{i}. Message ID: `{file_id}`\n"
            
            # Add forward link to original message if available
            if hasattr(original_message, 'link'):
                summary_text += f"\n🔗 **Original Message:** {original_message.link}"
            
            await app.send_message(
                chat_id=Config.DETAILS_CHANNEL_ID,
                text=summary_text,
                disable_web_page_preview=True
            )
            
            logger.info(f"Sent details summary with {len(file_ids)} file IDs")
            
        except Exception as e:
            logger.error(f"Error sending details summary: {e}")

# Message handler for source channel with better error handling
@app.on_message(filters.chat(Config.SOURCE_CHANNEL_ID) if Config.SOURCE_CHANNEL_ID != -1001234567890 else filters.all)
async def handle_source_message(client: Client, message: Message):
    """Handle messages from source channel"""
    try:
        logger.debug(f"Received message {message.id} from chat {message.chat.id}")
        
        # Check if this is the right channel
        if Config.SOURCE_CHANNEL_ID != -1001234567890 and message.chat.id != Config.SOURCE_CHANNEL_ID:
            logger.debug(f"Message not from source channel. Got: {message.chat.id}, Expected: {Config.SOURCE_CHANNEL_ID}")
            return
            
        # Extract text from message
        text = message.text or message.caption or ""
        logger.debug(f"Message text: {text[:100]}...")
        
        if not text:
            logger.debug("No text in message, skipping")
            return
        
        # Extract terabox links
        processor = TeraboxProcessor()
        terabox_links = processor.extract_terabox_links(text)
        
        if not terabox_links:
            logger.debug("No terabox links found in message")
            return
        
        logger.info(f"✅ Found {len(terabox_links)} terabox links in message {message.id}")
        logger.info(f"Links: {terabox_links}")
        
        # Add to queue for processing
        try:
            message_queue.put_nowait((message, terabox_links))
            logger.info(f"✅ Added message to queue. Queue size: {message_queue.qsize()}")
            
            # Send confirmation if debug mode
            if Config.DEBUG_MODE:
                try:
                    await message.reply_text(f"🔄 Processing {len(terabox_links)} terabox links...")
                except:
                    pass
                    
        except Exception as queue_error:
            logger.warning(f"Queue is full or error adding to queue: {queue_error}")
            
    except Exception as e:
        logger.error(f"❌ Error handling source message: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Queue processor function
async def process_queue():
    """Process messages from queue"""
    processor = TeraboxProcessor()
    
    while processing_active:
        try:
            if not message_queue.empty():
                message_data = message_queue.get_nowait()
                await processor.process_message(message_data)
                message_queue.task_done()
            else:
                await asyncio.sleep(1)  # Wait if queue is empty
                
        except Exception as e:
            logger.error(f"Error in queue processing: {e}")
            await asyncio.sleep(5)

# Start command handler
@app.on_message(filters.command("start_terabox") & filters.private)
async def start_terabox(client: Client, message: Message):
    """Start terabox automation"""
    await message.reply_text(
        "🤖 **Terabox Automation Started!**\n\n"
        f"📥 **Source Channel:** `{Config.SOURCE_CHANNEL_ID}`\n"
        f"📤 **Destination Channel:** `{Config.DESTINATION_CHANNEL_ID}`\n"
        f"📊 **Details Channel:** `{Config.DETAILS_CHANNEL_ID}`\n\n"
        f"⚙️ **Max Concurrent Downloads:** {Config.MAX_CONCURRENT_DOWNLOADS}\n"
        f"📋 **Queue Size:** {message_queue.qsize()}/{Config.QUEUE_MAX_SIZE}\n\n"
        "The bot will now automatically process terabox links from the source channel!"
    )

# Status command handler
@app.on_message(filters.command("status_terabox") & filters.private)
async def status_terabox(client: Client, message: Message):
    """Get terabox automation status"""
    processor = TeraboxProcessor()
    await message.reply_text(
        "📊 **Terabox Automation Status**\n\n"
        f"🔄 **Active Downloads:** {processor.active_downloads}/{Config.MAX_CONCURRENT_DOWNLOADS}\n"
        f"📋 **Queue Size:** {message_queue.qsize()}/{Config.QUEUE_MAX_SIZE}\n"
        f"⚡ **Processing Active:** {'Yes' if processing_active else 'No'}\n\n"
        "Use /start_terabox to start automation"
    )

# Test message handler for debugging
@app.on_message(filters.command("test_terabox") & filters.private)
async def test_terabox(client: Client, message: Message):
    """Test terabox functionality"""
    await message.reply_text(
        f"🧪 **Test Results:**\n\n"
        f"📱 **Bot Active:** Yes\n"
        f"🔗 **Source Channel ID:** `{Config.SOURCE_CHANNEL_ID}`\n"
        f"📤 **Destination Channel ID:** `{Config.DESTINATION_CHANNEL_ID}`\n"
        f"📊 **Details Channel ID:** `{Config.DETAILS_CHANNEL_ID}`\n"
        f"📋 **Queue Size:** {message_queue.qsize()}\n\n"
        f"**Send a message with terabox links to your source channel to test!**\n\n"
        f"⚠️ **Make sure:**\n"
        f"• Bot is admin in all channels\n"
        f"• Channel IDs are correct\n"
        f"• Bot has read/write permissions"
    )

# Check bot permissions
async def check_permissions():
    """Check bot permissions in channels"""
    logger.info("🔍 Checking bot permissions...")
    
    channels = {
        "Source": Config.SOURCE_CHANNEL_ID,
        "Destination": Config.DESTINATION_CHANNEL_ID,  
        "Details": Config.DETAILS_CHANNEL_ID
    }
    
    for name, channel_id in channels.items():
        if channel_id == -1001234567890 or channel_id == -1001234567891 or channel_id == -1001234567892:
            logger.warning(f"⚠️ {name} channel ID not configured properly: {channel_id}")
            continue
            
        try:
            chat = await app.get_chat(channel_id)
            logger.info(f"✅ {name} channel found: {chat.title}")
            
            # Try to get bot member info
            try:
                bot_member = await app.get_chat_member(channel_id, "me")
                logger.info(f"✅ Bot permissions in {name}: {bot_member.status}")
            except Exception as perm_error:
                logger.error(f"❌ Cannot check permissions in {name}: {perm_error}")
                
        except ChannelPrivate:
            logger.error(f"❌ {name} channel is private or bot is not a member: {channel_id}")
        except Exception as e:
            logger.error(f"❌ Error accessing {name} channel {channel_id}: {e}")

# Main function
async def main():
    """Main function to run the bot"""
    logger.info("🚀 Starting Terabox Automation Bot...")
    
    try:
        # Start the bot
        await app.start()
        logger.info("✅ Bot started successfully!")
        
        # Check permissions
        await check_permissions()
        
        # Start the queue processor
        asyncio.create_task(process_queue())
        logger.info("✅ Queue processor started")
        
        # Send startup notification if configured
        if Config.DETAILS_CHANNEL_ID not in [-1001234567890, -1001234567891, -1001234567892]:
            try:
                await app.send_message(
                    Config.DETAILS_CHANNEL_ID,
                    "🤖 **Terabox Automation Bot Started!**\n\n"
                    f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"📥 Monitoring: `{Config.SOURCE_CHANNEL_ID}`\n"
                    f"📤 Upload to: `{Config.DESTINATION_CHANNEL_ID}`\n\n"
                    "✅ Ready to process terabox links!"
                )
            except Exception as notif_error:
                logger.warning(f"Could not send startup notification: {notif_error}")
        
        logger.info("🎯 Bot is now monitoring for terabox links...")
        
        # Keep the bot running
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        processing_active = False
    except Exception as e:
        logger.error(f"Fatal error: {e}")
