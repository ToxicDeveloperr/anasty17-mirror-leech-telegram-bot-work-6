#!/usr/bin/env python3
"""
Terabox Automation Module for Mirror-Leech Bot
Automatically processes terabox links from source channel
"""

import asyncio
import re
import logging
import os
import time
from queue import Queue
from urllib.parse import quote
from requests import Session
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChannelPrivate, ChatWriteForbidden

from bot import LOGGER, bot, user
from bot.helper.mirror_leech_utils.download_utils.direct_link_generator import terabox
from bot.helper.ext_utils.status_utils import speed_string_to_bytes
from bot.core.config_manager import Config

# Terabox Automation Configuration
class TeraboxConfig:
    # ⚠️ UPDATE THESE CHANNEL IDs ⚠️
    SOURCE_CHANNEL_ID = -1002487065354      # Source channel where terabox links are posted
    DESTINATION_CHANNEL_ID = -1002176533426 # Destination channel where files will be uploaded
    DETAILS_CHANNEL_ID = -1002271035070     # Details channel for tracking
    
    # Processing settings
    MAX_CONCURRENT_DOWNLOADS = 3
    QUEUE_MAX_SIZE = 100
    PROCESS_DELAY = 2
    DEBUG_MODE = True

# Message processing queue
terabox_queue = Queue(maxsize=TeraboxConfig.QUEUE_MAX_SIZE)
processing_active = True

class TeraboxProcessor:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
        self.active_downloads = 0
        self.max_downloads = TeraboxConfig.MAX_CONCURRENT_DOWNLOADS

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
            LOGGER.info(f"Starting terabox download: {filename}")
            
            # Get direct download link
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
                try:
                    # Download file
                    with Session() as session:
                        session.headers.update({'User-Agent': self.user_agent})
                        response = session.get(file_url, stream=True)
                        response.raise_for_status()
                        
                        # Save file temporarily
                        temp_file_path = f"downloads/terabox_{file_name}"
                        os.makedirs("downloads", exist_ok=True)
                        
                        with open(temp_file_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                    
                    # Upload to destination channel
                    sent_message = await bot.send_document(
                        chat_id=destination_channel,
                        document=temp_file_path,
                        caption=f"📁 **{file_name}**\n\n🔗 **Source:** Terabox Auto-Upload\n⏰ **Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
                        progress=self.upload_progress,
                        progress_args=(file_name,)
                    )
                    
                    uploaded_file_ids.append(sent_message.id)
                    LOGGER.info(f"Uploaded terabox file: {file_name} (Message ID: {sent_message.id})")
                    
                    # Clean up
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        
                except Exception as upload_error:
                    LOGGER.error(f"Upload failed for {file_name}: {upload_error}")
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
            
            return uploaded_file_ids
            
        except Exception as e:
            LOGGER.error(f"Error processing terabox file {filename}: {e}")
            return []

    async def upload_progress(self, current, total, filename):
        """Upload progress callback"""
        percentage = (current / total) * 100
        if percentage % 25 == 0:  # Log every 25%
            LOGGER.info(f"Uploading {filename}: {percentage:.1f}%")

    async def process_message(self, message_data):
        """Process a single message from the queue"""
        try:
            message, terabox_links = message_data
            
            if self.active_downloads >= self.max_downloads:
                LOGGER.warning(f"Max downloads reached ({self.max_downloads}), queuing message")
                return
            
            self.active_downloads += 1
            
            LOGGER.info(f"Processing message with {len(terabox_links)} terabox links")
            
            all_uploaded_file_ids = []
            original_message_text = message.text or message.caption or ""
            
            # Process each terabox link
            for i, link in enumerate(terabox_links, 1):
                try:
                    filename = f"TeraboxFile_{i}_{int(time.time())}"
                    
                    file_ids = await self.download_and_upload_file(
                        link, 
                        filename, 
                        TeraboxConfig.DESTINATION_CHANNEL_ID
                    )
                    
                    all_uploaded_file_ids.extend(file_ids)
                    
                    # Add delay between downloads
                    if i < len(terabox_links):
                        await asyncio.sleep(TeraboxConfig.PROCESS_DELAY)
                        
                except Exception as link_error:
                    LOGGER.error(f"Error processing terabox link {link}: {link_error}")
                    continue
            
            # Send details summary
            if all_uploaded_file_ids:
                await self.send_details_summary(
                    original_message_text,
                    terabox_links,
                    all_uploaded_file_ids,
                    message
                )
            
        except Exception as e:
            LOGGER.error(f"Error in terabox process_message: {e}")
        finally:
            self.active_downloads -= 1

    async def send_details_summary(self, original_text, links, file_ids, original_message):
        """Send summary to details channel"""
        try:
            summary_text = f"📊 **Terabox Processing Summary**\n\n"
            summary_text += f"🔗 **Links Found:** {len(links)}\n"
            summary_text += f"📁 **Files Uploaded:** {len(file_ids)}\n"
            summary_text += f"⏰ **Processed At:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            summary_text += "**Original Message:**\n"
            summary_text += f"```\n{original_text[:400]}{'...' if len(original_text) > 400 else ''}\n```\n\n"
            
            summary_text += "**Terabox Links:**\n"
            for i, link in enumerate(links, 1):
                summary_text += f"{i}. `{link}`\n"
            
            summary_text += f"\n**Uploaded File IDs:**\n"
            for i, file_id in enumerate(file_ids, 1):
                summary_text += f"{i}. Message ID: `{file_id}`\n"
            
            await bot.send_message(
                chat_id=TeraboxConfig.DETAILS_CHANNEL_ID,
                text=summary_text,
                disable_web_page_preview=True
            )
            
            LOGGER.info(f"Sent terabox details summary with {len(file_ids)} file IDs")
            
        except Exception as e:
            LOGGER.error(f"Error sending terabox details summary: {e}")

# Global processor instance
terabox_processor = TeraboxProcessor()

# Message handler for source channel
@bot.on_message(filters.chat(TeraboxConfig.SOURCE_CHANNEL_ID))
async def handle_terabox_source_message(client, message: Message):
    """Handle messages from terabox source channel"""
    try:
        LOGGER.debug(f"Received message {message.id} from terabox source channel {message.chat.id}")
        
        # Extract text from message
        text = message.text or message.caption or ""
        
        if not text:
            return
        
        # Extract terabox links
        terabox_links = terabox_processor.extract_terabox_links(text)
        
        if not terabox_links:
            return
        
        LOGGER.info(f"✅ Found {len(terabox_links)} terabox links in message {message.id}")
        LOGGER.info(f"Terabox Links: {terabox_links}")
        
        # Add to queue for processing
        try:
            terabox_queue.put_nowait((message, terabox_links))
            LOGGER.info(f"✅ Added terabox message to queue. Queue size: {terabox_queue.qsize()}")
            
            # Send confirmation if debug mode
            if TeraboxConfig.DEBUG_MODE:
                try:
                    await message.reply_text(f"🔄 Processing {len(terabox_links)} terabox links automatically...")
                except:
                    pass
                    
        except Exception as queue_error:
            LOGGER.warning(f"Terabox queue is full or error: {queue_error}")
            
    except Exception as e:
        LOGGER.error(f"❌ Error handling terabox source message: {e}")

# Queue processor
async def process_terabox_queue():
    """Process terabox messages from queue"""
    while processing_active:
        try:
            if not terabox_queue.empty():
                message_data = terabox_queue.get_nowait()
                await terabox_processor.process_message(message_data)
                terabox_queue.task_done()
            else:
                await asyncio.sleep(1)
                
        except Exception as e:
            LOGGER.error(f"Error in terabox queue processing: {e}")
            await asyncio.sleep(5)

# Commands
@bot.on_message(filters.command("terabox_test") & filters.private)
async def terabox_test(client, message: Message):
    """Test terabox automation functionality"""
    await message.reply_text(
        f"🧪 **Terabox Automation Test**\n\n"
        f"📱 **Bot Active:** ✅ Yes\n"
        f"🔗 **Source Channel ID:** `{TeraboxConfig.SOURCE_CHANNEL_ID}`\n"
        f"📤 **Destination Channel ID:** `{TeraboxConfig.DESTINATION_CHANNEL_ID}`\n"
        f"📊 **Details Channel ID:** `{TeraboxConfig.DETAILS_CHANNEL_ID}`\n"
        f"📋 **Queue Size:** {terabox_queue.qsize()}\n\n"
        f"**How to test:**\n"
        f"1. Post a terabox link in your source channel\n"
        f"2. Bot will automatically detect and process it\n"
        f"3. Files will be uploaded to destination channel\n"
        f"4. Summary will be posted in details channel\n\n"
        f"⚠️ **Make sure bot is admin in all channels!**"
    )

@bot.on_message(filters.command("terabox_status") & filters.private)
async def terabox_status(client, message: Message):
    """Get terabox automation status"""
    await message.reply_text(
        f"📊 **Terabox Automation Status**\n\n"
        f"🔄 **Active Downloads:** {terabox_processor.active_downloads}/{TeraboxConfig.MAX_CONCURRENT_DOWNLOADS}\n"
        f"📋 **Queue Size:** {terabox_queue.qsize()}/{TeraboxConfig.QUEUE_MAX_SIZE}\n"
        f"⚡ **Processing Active:** {'✅ Yes' if processing_active else '❌ No'}\n"
        f"🐛 **Debug Mode:** {'✅ On' if TeraboxConfig.DEBUG_MODE else '❌ Off'}\n\n"
        f"**Commands:**\n"
        f"• `/terabox_test` - Test functionality\n"
        f"• `/terabox_status` - Check status"
    )

# Check permissions at startup
async def check_terabox_permissions():
    """Check bot permissions in terabox channels"""
    LOGGER.info("🔍 Checking terabox automation permissions...")
    
    channels = {
        "Source": TeraboxConfig.SOURCE_CHANNEL_ID,
        "Destination": TeraboxConfig.DESTINATION_CHANNEL_ID,  
        "Details": TeraboxConfig.DETAILS_CHANNEL_ID
    }
    
    for name, channel_id in channels.items():
        try:
            chat = await bot.get_chat(channel_id)
            LOGGER.info(f"✅ Terabox {name} channel found: {chat.title}")
            
            try:
                bot_member = await bot.get_chat_member(channel_id, "me")
                LOGGER.info(f"✅ Bot permissions in {name}: {bot_member.status}")
            except Exception as perm_error:
                LOGGER.error(f"❌ Cannot check terabox permissions in {name}: {perm_error}")
                
        except ChannelPrivate:
            LOGGER.error(f"❌ Terabox {name} channel is private or bot is not a member: {channel_id}")
        except Exception as e:
            LOGGER.error(f"❌ Error accessing terabox {name} channel {channel_id}: {e}")

# Initialize terabox automation
async def init_terabox_automation():
    """Initialize terabox automation"""
    try:
        LOGGER.info("🚀 Initializing Terabox Automation...")
        
        # Check permissions
        await check_terabox_permissions()
        
        # Start queue processor
        asyncio.create_task(process_terabox_queue())
        LOGGER.info("✅ Terabox queue processor started")
        
        # Send startup notification
        try:
            await bot.send_message(
                TeraboxConfig.DETAILS_CHANNEL_ID,
                "🤖 **Terabox Automation Started!**\n\n"
                f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📥 Monitoring: `{TeraboxConfig.SOURCE_CHANNEL_ID}`\n"
                f"📤 Upload to: `{TeraboxConfig.DESTINATION_CHANNEL_ID}`\n\n"
                "✅ Ready to process terabox links automatically!"
            )
        except Exception as notif_error:
            LOGGER.warning(f"Could not send terabox startup notification: {notif_error}")
        
        LOGGER.info("🎯 Terabox automation is now active!")
        
    except Exception as e:
        LOGGER.error(f"❌ Failed to initialize terabox automation: {e}")

# Auto-start terabox automation when module is loaded
asyncio.create_task(init_terabox_automation())
