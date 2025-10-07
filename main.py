
import discord
from discord.ext import commands
from discord import ui, app_commands
import os
import random
import string
import json
import subprocess
from dotenv import load_dotenv
import asyncio
import datetime
import docker
import time
import logging
import traceback
import aiohttp
import socket
import re
import psutil
import platform
import shutil
from typing import Optional, Literal
import sqlite3
import pickle
import base64
import threading
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import docker
import paramiko
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bot setup with intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='+', intents=intents)
tree = bot.tree  # Use the bot's existing command tree

# Files to store data
DATA_FILE = "user_data.json"
STOCK_FILE = "stock.json"
REFERRAL_FILE = "referral_codes.json"
STOCK_MSG_FILE = "stock_message.json"  # To store stock channel and message ID

# Specific user ID for purchase notifications
SPECIFIC_USER_ID = 1422299518052864080  # Replace with the Discord user ID of the recipient

# Channel IDs (replace with actual IDs)
WELCOME_CHANNEL_ID = 1385968886490599560  # Welcome channel ID
STOCK_CHANNEL_ID = 1425215497003208734  # Stock display channel ID

# Role milestones: {coins: role_id}
ROLE_MILESTONES = {
    200: 1425215942589415536,  # COINE_XPERT role ID
    500: 1425216104715911180,  # COIN_RULER role ID
    # Add more as needed
}

# Custom emoji IDs
COIN_EMOJI = ":coin:"
RAM_EMOJI = "<:ram:1424760195913089086>"
CPU_EMOJI = "<:cpu:1424770547950288936>"
STORAGE_EMOJI = "<:ssd:1424770805652258868>"

# Global for stock message info
stock_message_info = {"channel_id": STOCK_CHANNEL_ID, "message_id": None}

# Load user data from JSON file
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    # Initialize specs for new users
                    for user_id in data:
                        if 'specs' not in data[user_id]:
                            data[user_id]['specs'] = {'ram': 2, 'storage': 4, 'cpu': 0.75}
                        if 'first_join' not in data[user_id]:
                            data[user_id]['first_join'] = True
                    logger.info("Successfully loaded user_data.json")
                    return data
                else:
                    logger.warning("user_data.json is empty, initializing with {}")
                    return {}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading user_data.json: {e}")
            return {}
    logger.info("user_data.json does not exist, initializing with {}")
    return {}

# Save user data to JSON file
def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info("Successfully saved user_data.json")
    except IOError as e:
        logger.error(f"Error saving user_data.json: {e}")

# Load stock data from JSON file
def load_stock():
    if os.path.exists(STOCK_FILE):
        try:
            with open(STOCK_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    # Initialize pterodactyl stock if missing
                    if 'pterodactyl' not in data:
                        data['pterodactyl'] = {"count": 0, "details": []}
                    logger.info("Successfully loaded stock.json")
                    return data
                else:
                    logger.warning("stock.json is empty, initializing with defaults")
                    return {"ram": 0, "cpu": 0, "storage": 0, "vps": {"count": 0, "details": []}, "pterodactyl": {"count": 0, "details": []}}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading stock.json: {e}")
            return {"ram": 0, "cpu": 0, "storage": 0, "vps": {"count": 0, "details": []}, "pterodactyl": {"count": 0, "details": []}}
    logger.info("stock.json does not exist, initializing with defaults")
    return {"ram": 0, "cpu": 0, "storage": 0, "vps": {"count": 0, "details": []}, "pterodactyl": {"count": 0, "details": []}}

# Save stock data to JSON file
def save_stock(stock):
    try:
        with open(STOCK_FILE, 'w') as f:
            json.dump(stock, f, indent=4)
        logger.info("Successfully saved stock.json")
    except IOError as e:
        logger.error(f"Error saving stock.json: {e}")

# Load referral codes from JSON file
def load_referral_codes():
    if os.path.exists(REFERRAL_FILE):
        try:
            with open(REFERRAL_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    logger.info("Successfully loaded referral_codes.json")
                    return data
                else:
                    logger.warning("referral_codes.json is empty, initializing with {}")
                    return {}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading referral_codes.json: {e}")
            return {}
    logger.info("referral_codes.json does not exist, initializing with {}")
    return {}

# Save referral codes to JSON file
def save_referral_codes(codes):
    try:
        with open(REFERRAL_FILE, 'w') as f:
            json.dump(codes, f, indent=4)
        logger.info("Successfully saved referral_codes.json")
    except IOError as e:
        logger.error(f"Error saving referral_codes.json: {e}")

# Load stock message info
def load_stock_message():
    global stock_message_info
    if os.path.exists(STOCK_MSG_FILE):
        try:
            with open(STOCK_MSG_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    stock_message_info.update(json.loads(content))
                    logger.info("Successfully loaded stock_message.json")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading stock_message.json: {e}")

# Save stock message info
def save_stock_message():
    try:
        with open(STOCK_MSG_FILE, 'w') as f:
            json.dump(stock_message_info, f, indent=4)
        logger.info("Successfully saved stock_message.json")
    except IOError as e:
        logger.error(f"Error saving stock_message.json: {e}")

# Initialize data
user_data = load_data()
stock_data = load_stock()
referral_codes = load_referral_codes()
load_stock_message()

# Shop items
shop_items = {
    "pterodactyl": {"name": "Pterodactyl Panel", "price": 200, "description": "Access to Pterodactyl Panel.", "stock_key": "pterodactyl"},
    "ram": {"name": "RAM Upgrade", "price": 50, "description": "Extra RAM for your server.", "stock_key": "ram"},
    "cpu": {"name": "CPU Upgrade", "price": 100, "description": "More processing cores for your server.", "stock_key": "cpu"},
    "storage": {"name": "Storage Upgrade", "price": 100, "description": "Additional disk space for your server.", "stock_key": "storage"},
    "vps": {"name": "VPS", "price": 400, "description": "A virtual private server for your hosting needs.", "stock_key": "vps"}
}

# Function to check and assign roles based on coins
async def check_and_assign_roles(guild, user_id, coins):
    if user_id not in user_data:
        return
    member = guild.get_member(int(user_id))
    if not member:
        return
    for threshold, role_id in sorted(ROLE_MILESTONES.items(), reverse=True):
        if coins >= threshold:
            role = guild.get_role(role_id)
            if role and not any(r.id == role_id for r in member.roles):
                try:
                    await member.add_roles(role)
                    logger.info(f"Assigned role {role.name} to {member.display_name}")
                except discord.errors.Forbidden:
                    logger.error(f"Cannot assign role {role.name} to {member.display_name}: Missing permissions")

# Function to update stock display
async def update_stock_display():
    global stock_message_info
    if not stock_message_info["message_id"]:
        channel = bot.get_channel(stock_message_info["channel_id"])
        if channel:
            embed = discord.Embed(title="📊 VIZORA HOST Stock", description="Current stock levels for shop items.", color=0x00ff00)
            embed.add_field(name="RAM", value=f"{stock_data.get('ram', 0)} units", inline=True)
            embed.add_field(name="CPU", value=f"{stock_data.get('cpu', 0)} units", inline=True)
            embed.add_field(name="Storage", value=f"{stock_data.get('storage', 0)} units", inline=True)
            embed.add_field(name="VPS", value=f"{stock_data.get('vps', {'count': 0})['count']} units", inline=True)
            embed.add_field(name="Pterodactyl", value=f"{stock_data.get('pterodactyl', {'count': 0})['count']} panels", inline=True)
            msg = await channel.send(embed=embed)
            stock_message_info["message_id"] = msg.id
            save_stock_message()
        return

    channel = bot.get_channel(stock_message_info["channel_id"])
    if not channel:
        return
    try:
        msg = await channel.fetch_message(stock_message_info["message_id"])
        embed = discord.Embed(title="📊 VIZORA HOST Stock", description="Current stock levels for shop items.", color=0x00ff00)
        embed.add_field(name="RAM", value=f"{stock_data.get('ram', 0)} units", inline=True)
        embed.add_field(name="CPU", value=f"{stock_data.get('cpu', 0)} units", inline=True)
        embed.add_field(name="Storage", value=f"{stock_data.get('storage', 0)} units", inline=True)
        embed.add_field(name="VPS", value=f"{stock_data.get('vps', {'count': 0})['count']} units", inline=True)
        embed.add_field(name="Pterodactyl", value=f"{stock_data.get('pterodactyl', {'count': 0})['count']} panels", inline=True)
        await msg.edit(embed=embed)
    except discord.errors.NotFound:
        logger.warning("Stock message not found, recreating...")
        await update_stock_display()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    # Initial stock display setup
    await update_stock_display()
    # Sync slash commands globally with retry mechanism
    max_retries = 3
    retry_delay = 60  # seconds
    for attempt in range(max_retries):
        try:
            synced_commands = await bot.tree.sync()
            command_names = [cmd.name for cmd in synced_commands]
            logger.info(f"Slash commands synced globally successfully: {', '.join(command_names)}")
            if 'addreffral' in command_names:
                logger.info("/addreffral synced successfully")
            else:
                logger.warning("/addreffral not found in synced commands")
            break
        except discord.errors.Forbidden as e:
            logger.error(f"Sync failed: Missing permissions - {e}. Ensure bot has 'applications.commands' scope.")
            break
        except discord.errors.HTTPException as e:
            logger.warning(f"Sync attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Max sync retries reached. Commands may not appear.")
        except Exception as e:
            logger.error(f"Unexpected error during sync: {e}")
            break

@bot.event
async def on_member_join(member):
    # Welcome message in specific channel
    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        await welcome_channel.send(f"Welcome {member.mention}! Enjoy your stay at Vizora Host! 🚀")

    user_id = str(member.id)
    guild_id = str(member.guild.id)
    is_first_join = user_data.get(user_id, {}).get('first_join', True)
    
    if user_id not in user_data:
        user_data[user_id] = {'coins': 50 if is_first_join else 0, 'items': [], 'redeemed_codes': [], 'specs': {'ram': 2, 'storage': 4, 'cpu': 0.75}, 'invite_count': 0, 'first_join': False}
    else:
        if is_first_join:
            user_data[user_id]['coins'] += 50
            user_data[user_id]['first_join'] = False
            # Ping the new user in welcome channel for first join bonus
            if welcome_channel:
                await welcome_channel.send(f"{member.mention}, welcome! You've received 50 coins for joining! :coin:")

    # Track invites (1 invite = 50 coins)
    invites_before = user_data.get(guild_id, {}).get('invites', {})
    try:
        invites_after = await member.guild.invites()
    except discord.errors.Forbidden:
        logger.error(f"Cannot fetch invites for guild {guild_id}: Missing permissions")
        save_data(user_data)
        await check_and_assign_roles(member.guild, user_id, user_data[user_id]['coins'])
        return

    for invite in invites_after:
        invite_id = invite.id
        if invite_id in invites_before:
            if invites_before[invite_id]['uses'] < invite.uses:
                inviter_id = str(invite.inviter.id)
                if inviter_id not in user_data:
                    user_data[inviter_id] = {'coins': 0, 'items': [], 'redeemed_codes': [], 'specs': {'ram': 2, 'storage': 4, 'cpu': 0.75}, 'invite_count': 0, 'first_join': False}
                user_data[inviter_id]['coins'] += 50
                user_data[inviter_id]['invite_count'] = user_data[inviter_id].get('invite_count', 0) + 1
                save_data(user_data)
                await check_and_assign_roles(member.guild, inviter_id, user_data[inviter_id]['coins'])
                try:
                    await invite.inviter.send(f"You earned 50 coins for inviting {member.mention}! :coin:")
                except discord.errors.Forbidden:
                    logger.warning(f"Cannot send DM to {invite.inviter.id} for invite reward")
        invites_before[invite_id] = {'uses': invite.uses, 'inviter_id': str(invite.inviter.id)}
    user_data[guild_id] = {'invites': invites_before}
    save_data(user_data)
    await check_and_assign_roles(member.guild, user_id, user_data[user_id]['coins'])

@bot.event
async def on_member_remove(member):
    # Deduct 50 coins when a member leaves
    user_id = str(member.id)
    if user_id in user_data:
        user_data[user_id]['coins'] = max(0, user_data[user_id]['coins'] - 50)
        save_data(user_data)

@bot.command(name="c")
async def check_coins(ctx):
    user_id = str(ctx.author.id)
    if user_id in user_data:
        coins = user_data[user_id]['coins']
        embed = discord.Embed(title="Coin Balance", color=0x00ff00)
        embed.add_field(name="Coins", value=f"{coins} :coin:", inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Coin Balance", color=0x00ff00)
        embed.add_field(name="Coins", value="0 :coin:", inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)

@bot.command(name="i")
async def check_invites(ctx):
    user_id = str(ctx.author.id)
    if user_id in user_data:
        invite_count = user_data[user_id].get('invite_count', 0)
        embed = discord.Embed(title="Invite Count", color=0x00ff00)
        embed.add_field(name="Invites", value=f"{invite_count}", inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Invite Count", color=0x00ff00)
        embed.add_field(name="Invites", value="0", inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)

@bot.command(name="specs")
async def check_specs(ctx):
    user_id = str(ctx.author.id)
    if user_id in user_data:
        specs = user_data[user_id].get('specs', {'ram': 2, 'storage': 4, 'cpu': 0.75})
        embed = discord.Embed(title="Server Specs", color=0x00ff00)
        embed.add_field(name=f"{RAM_EMOJI} RAM", value=f"{specs['ram']} GB", inline=True)
        embed.add_field(name=f"{CPU_EMOJI} CPU", value=f"{specs['cpu']} cores", inline=True)
        embed.add_field(name=f"{STORAGE_EMOJI} Storage", value=f"{specs['storage']} GB", inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Server Specs", color=0x00ff00)
        embed.add_field(name=f"{RAM_EMOJI} RAM", value="2 GB", inline=True)
        embed.add_field(name=f"{CPU_EMOJI} CPU", value="0.75 cores", inline=True)
        embed.add_field(name=f"{STORAGE_EMOJI} Storage", value="4 GB", inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)

@bot.command(name="purchase")
async def check_purchase(ctx):
    user_id = str(ctx.author.id)
    if user_id in user_data:
        items = user_data[user_id].get('items', [])
        if items:
            item_list = "\n".join([f"• {shop_items[item]['name']}" for item in items if item in shop_items])
            embed = discord.Embed(title="Purchased Items", description=item_list, color=0x00ff00)
        else:
            embed = discord.Embed(title="Purchased Items", description="No items purchased yet.", color=0x00ff00)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Purchased Items", description="No items purchased yet.", color=0x00ff00)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)

@tree.command(name="sync", description="Admin command to force sync slash commands")
@app_commands.checks.has_permissions(administrator=True)
async def sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        synced_commands = await bot.tree.sync()
        command_names = [cmd.name for cmd in synced_commands]
        logger.info(f"Manual sync triggered successfully: {', '.join(command_names)}")
        if 'addreffral' in command_names:
            await interaction.followup.send("Commands synced successfully, including /addreffral! :white_check_mark:", ephemeral=True)
        else:
            await interaction.followup.send("Commands synced, but /addreffral was not included. Check logs for details. :warning:", ephemeral=True)
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        await interaction.followup.send(f"Sync failed: {e}", ephemeral=True)

@tree.command(name="coins", description="Check your or another user's coin balance and purchased items (admin-only for other users).")
@app_commands.describe(user="The user to check coins for (admin-only, optional)")
async def coins(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer()
    if user is None:
        user_id = str(interaction.user.id)
        if user_id in user_data:
            coins = user_data[user_id]['coins']
            items = user_data[user_id].get('items', [])
            item_list = ", ".join(items) if items else "None"
            embed = discord.Embed(title="Coin Balance", color=0x00ff00)
            embed.add_field(name="Coins", value=f"{coins} :coin:", inline=True)
            embed.add_field(name="Purchased Items", value=item_list, inline=False)
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(title="Coin Balance", color=0x00ff00)
            embed.add_field(name="Coins", value="0 :coin:", inline=True)
            embed.add_field(name="Purchased Items", value="None", inline=False)
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            await interaction.followup.send(embed=embed)
        return

    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to check another user's coins.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    user_id = str(user.id)
    if user_id in user_data:
        coins = user_data[user_id]['coins']
        items = user_data[user_id].get('items', [])
        item_list = ", ".join(items) if items else "None"
        embed = discord.Embed(title=f"{user.display_name}'s Coin Balance", color=0x00ff00)
        embed.add_field(name="Coins", value=f"{coins} :coin:", inline=True)
        embed.add_field(name="Purchased Items", value=item_list, inline=False)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
        embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
        await interaction.followup.send(embed=embed)
    else:
        embed = discord.Embed(title=f"{user.display_name}'s Coin Balance", color=0x00ff00)
        embed.add_field(name="Coins", value="0 :coin:", inline=True)
        embed.add_field(name="Purchased Items", value="None", inline=False)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
        embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
        await interaction.followup.send(embed=embed)

@tree.command(name="buy", description="Purchase an item from the shop.")
@app_commands.describe(item_name="The item to purchase (e.g., ram, cpu, storage, pterodactyl, vps)")
async def buy(interaction: discord.Interaction, item_name: str):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    item_name = item_name.lower()
    
    if item_name not in shop_items:
        embed = discord.Embed(title="Invalid Item", description="Available items: ram, cpu, storage, pterodactyl, vps.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return

    item = shop_items[item_name]
    price = item['price']
    
    if user_id not in user_data:
        user_data[user_id] = {'coins': 0, 'items': [], 'redeemed_codes': [], 'specs': {'ram': 2, 'storage': 4, 'cpu': 0.75}, 'invite_count': 0, 'first_join': False}
    
    if user_data[user_id]['coins'] < price:
        embed = discord.Embed(title="Insufficient Coins", description=f"You need {price} coins to buy {item['name']}. You have {user_data[user_id]['coins']} coins.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return

    # Check stock
    if 'stock_key' in item:
        stock_key = item['stock_key']
        if stock_key in ['vps', 'pterodactyl']:
            stock_count = stock_data[stock_key]['count']
        else:
            stock_count = stock_data.get(stock_key, 0)
        if stock_count <= 0:
            embed = discord.Embed(title="Out of Stock", description=f"{item['name']} is out of stock!", color=0xff0000)
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            await interaction.followup.send(embed=embed)
            return
        
        if stock_key in ['vps', 'pterodactyl']:
            stock_data[stock_key]['count'] -= 1
            details = stock_data[stock_key]['details'].pop(0) if stock_data[stock_key]['details'] else {}
        else:
            stock_data[stock_key] -= 1
            details = {}
        save_stock(stock_data)
        await update_stock_display()

    # Deduct coins and add item
    old_coins = user_data[user_id]['coins']
    user_data[user_id]['coins'] -= price
    user_data[user_id]['items'].append(item['name'])
    
    # Update specs based on purchase
    if item_name == "ram":
        user_data[user_id]['specs']['ram'] += 1  # Add 1 GB RAM
    elif item_name == "cpu":
        user_data[user_id]['specs']['cpu'] += 0.25  # Add 0.25 cores
    elif item_name == "storage":
        user_data[user_id]['specs']['storage'] += 2  # Add 2 GB storage
    
    save_data(user_data)
    
    # Handle item effects
    if item_name == "pterodactyl":
        # Send details to user
        embed = discord.Embed(title="✨ Pterodactyl Panel Access ✨", description="🎉 Your Pterodactyl Panel has been activated! 🎉", color=0x00ff00)
        embed.add_field(name="🔑 Panel Details:", value=f"👤 **Username**: {details.get('username', 'N/A')}\n🔒 **Password**: {details.get('password', 'N/A')}", inline=False)
        embed.set_footer(text="💎 Thank you for choosing Vizora Host! 🚀")
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        try:
            await interaction.user.send(embed=embed)
            success_embed = discord.Embed(title="Purchase Successful", description=f"Pterodactyl Panel details sent to your DMs! :white_check_mark:", color=0x00ff00)
            success_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
            success_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            await interaction.followup.send(embed=success_embed)
        except discord.errors.Forbidden:
            error_embed = discord.Embed(title="DM Error", description=f"Cannot send details via DM. Please enable DMs from server members. :warning:", color=0xff0000)
            error_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
            error_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            await interaction.followup.send(embed=error_embed)
    else:
        success_embed = discord.Embed(title="Purchase Successful", description=f"You purchased **{item['name']}** for {price} coins! An admin will handle your upgrade soon. :white_check_mark:", color=0x00ff00)
        success_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        success_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=success_embed)

    await check_and_assign_roles(interaction.guild, user_id, user_data[user_id]['coins'])

    # Notify specific user about the purchase
    try:
        specific_user = await bot.fetch_user(SPECIFIC_USER_ID)
        await specific_user.send(f"{interaction.user.mention} purchased {item['name']} for {price} coins.")
    except discord.errors.NotFound:
        pass
    except discord.errors.Forbidden:
        pass

@tree.command(name="reffral", description="Redeem a referral code to earn coins (one-time use per code).")
@app_commands.describe(code="The referral code to redeem")
async def reffral(interaction: discord.Interaction, code: str):
    logger.info(f"Executing /reffral for user {interaction.user.id} with code={code}")
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    
    if user_id not in user_data:
        user_data[user_id] = {'coins': 0, 'items': [], 'redeemed_codes': [], 'specs': {'ram': 2, 'storage': 4, 'cpu': 0.75}, 'invite_count': 0, 'first_join': False}
    
    if code not in referral_codes:
        embed = discord.Embed(title="Invalid Code", description="This referral code does not exist!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    
    if code in user_data[user_id]['redeemed_codes']:
        embed = discord.Embed(title="Already Redeemed", description="You have already redeemed this code!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    
    if referral_codes[code].get('current_users', 0) >= referral_codes[code].get('max_users', float('inf')):
        embed = discord.Embed(title="Limit Reached", description="This code has reached its maximum redemption limit!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    
    coins_reward = referral_codes[code]['coins']
    old_coins = user_data[user_id]['coins']
    user_data[user_id]['coins'] += coins_reward
    user_data[user_id]['redeemed_codes'].append(code)
    referral_codes[code]['current_users'] = referral_codes[code].get('current_users', 0) + 1
    save_data(user_data)
    save_referral_codes(referral_codes)
    embed = discord.Embed(title="Code Redeemed! :white_check_mark:", description=f"You redeemed code '{code}' for {coins_reward} coins! :coin:", color=0x00ff00)
    embed.add_field(name="New Balance", value=f"{user_data[user_id]['coins']} coins", inline=False)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.followup.send(embed=embed)
    await check_and_assign_roles(interaction.guild, user_id, user_data[user_id]['coins'])

@tree.command(name="addreffral", description="Admin command to create a referral code with a coin reward and user limit.")
@app_commands.describe(coins="The amount of coins the code will reward", code="The referral code to create", max_users="Maximum number of users who can redeem this code")
@app_commands.checks.has_permissions(administrator=True)
async def addreffral(interaction: discord.Interaction, coins: int, code: str, max_users: int):
    logger.info(f"Executing /addreffral for user {interaction.user.id} with coins={coins}, code={code}, max_users={max_users}")
    await interaction.response.defer(ephemeral=True)
    
    if coins <= 0:
        logger.warning(f"Invalid coins value: {coins}")
        embed = discord.Embed(title="Invalid Amount", description="Coin amount must be positive!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    if max_users <= 0:
        logger.warning(f"Invalid max_users value: {max_users}")
        embed = discord.Embed(title="Invalid Limit", description="Maximum users must be positive!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    if not code.strip():
        logger.warning("Referral code is empty or whitespace")
        embed = discord.Embed(title="Invalid Code", description="The referral code cannot be empty!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    if code in referral_codes:
        logger.warning(f"Referral code already exists: {code}")
        embed = discord.Embed(title="Code Exists", description="This code already exists!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    
    try:
        referral_codes[code] = {'coins': coins, 'max_users': max_users, 'current_users': 0}
        save_referral_codes(referral_codes)
        logger.info(f"Successfully created referral code '{code}' for {coins} coins, max_users={max_users}")
        embed = discord.Embed(title="Referral Code Created! :white_check_mark:", description=f"Code: `{code}`\nCoins: {coins} :coin:\nMax Users: {max_users}", color=0x00ff00)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.error(f"Error creating referral code: {e}")
        embed = discord.Embed(title="Error", description="An error occurred while creating the referral code. Please try again.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)

@tree.command(name="coin_give", description="Admin command to give coins to a user.")
@app_commands.describe(user="The user to give coins to", amount="The amount of coins to give")
@app_commands.checks.has_permissions(administrator=True)
async def coin_give(interaction: discord.Interaction, user: discord.Member, amount: int):
    await interaction.response.defer()
    user_id = str(user.id)
    if user_id not in user_data:
        user_data[user_id] = {'coins': 0, 'items': [], 'redeemed_codes': [], 'specs': {'ram': 2, 'storage': 4, 'cpu': 0.75}, 'invite_count': 0, 'first_join': False}
    
    user_data[user_id]['coins'] += amount
    save_data(user_data)
    embed = discord.Embed(title="Coins Given! :white_check_mark:", description=f"Gave {amount} coins to {user.mention}. They now have {user_data[user_id]['coins']} coins :coin:", color=0x00ff00)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.followup.send(embed=embed)
    await check_and_assign_roles(interaction.guild, user_id, user_data[user_id]['coins'])

@tree.command(name="coin_take", description="Admin command to take coins from a user.")
@app_commands.describe(user="The user to take coins from", amount="The amount of coins to take")
@app_commands.checks.has_permissions(administrator=True)
async def coin_take(interaction: discord.Interaction, user: discord.Member, amount: int):
    await interaction.response.defer()
    user_id = str(user.id)
    if user_id not in user_data:
        user_data[user_id] = {'coins': 0, 'items': [], 'redeemed_codes': [], 'specs': {'ram': 2, 'storage': 4, 'cpu': 0.75}, 'invite_count': 0, 'first_join': False}
    
    user_data[user_id]['coins'] = max(0, user_data[user_id]['coins'] - amount)
    save_data(user_data)
    embed = discord.Embed(title="Coins Taken! :white_check_mark:", description=f"Took {amount} coins from {user.mention}. They now have {user_data[user_id]['coins']} coins :coin:", color=0x00ff00)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.followup.send(embed=embed)
    await check_and_assign_roles(interaction.guild, user_id, user_data[user_id]['coins'])

@tree.command(name="vpsadd", description="Admin command to add VPS stock with details.")
@app_commands.describe(number="Number of VPS units to add", ip="The VPS IP address", port="The VPS port", username="The VPS username", password="The VPS password")
@app_commands.checks.has_permissions(administrator=True)
async def vpsadd(interaction: discord.Interaction, number: int, ip: str, port: str, username: str, password: str):
    logger.info(f"Executing /vpsadd for user {interaction.user.id} with number={number}, ip={ip}, port={port}, username={username}")
    await interaction.response.defer()
    if number <= 0:
        embed = discord.Embed(title="Invalid Number", description="Number of VPS units must be positive!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    
    stock_data['vps']['count'] = stock_data.get('vps', {'count': 0, 'details': []})['count'] + number
    for _ in range(number):
        stock_data['vps']['details'].append({
            'ip': ip,
            'port': port,
            'username': username,
            'password': password
        })
    save_stock(stock_data)
    await update_stock_display()
    embed = discord.Embed(title="VPS Stock Added! :white_check_mark:", description=f"Added {number} VPS units to stock. Total: {stock_data['vps']['count']} units", color=0x00ff00)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.followup.send(embed=embed)

@tree.command(name="addpterodactyl", description="Admin command to add Pterodactyl Panel stock with details.")
@app_commands.describe(number="Number of panels to add", username="The panel username", password="The panel password")
@app_commands.checks.has_permissions(administrator=True)
async def addpterodactyl(interaction: discord.Interaction, number: int, username: str, password: str):
    logger.info(f"Executing /addpterodactyl for user {interaction.user.id} with number={number}, username={username}")
    await interaction.response.defer()
    if number <= 0:
        embed = discord.Embed(title="Invalid Number", description="Number of panels must be positive!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    
    stock_data['pterodactyl']['count'] = stock_data.get('pterodactyl', {'count': 0, 'details': []})['count'] + number
    for _ in range(number):
        stock_data['pterodactyl']['details'].append({
            'username': username,
            'password': password
        })
    save_stock(stock_data)
    await update_stock_display()
    embed = discord.Embed(title="Pterodactyl Stock Added! :white_check_mark:", description=f"Added {number} Pterodactyl panels to stock. Total: {stock_data['pterodactyl']['count']} panels", color=0x00ff00)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.followup.send(embed=embed)

@tree.command(name="ramupdate", description="Admin command to send RAM upgrade details to a user.")
@app_commands.describe(user="The user to send details to", gb="The amount of RAM in GB")
@app_commands.checks.has_permissions(administrator=True)
async def ramupdate(interaction: discord.Interaction, user: discord.Member, gb: str):
    await interaction.response.defer()
    embed = discord.Embed(title="💠 RAM Upgrade Completed! 💠", description="🎉 Your RAM upgrade has been applied! 🎉", color=0x00ff00)
    embed.add_field(name="🖥️ Details", value=f"Added {gb} GB of RAM to your server.\n⚡ Enjoy smoother performance!", inline=False)
    embed.set_footer(text="💎 Vizora Host 🚀")
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
    try:
        await user.send(embed=embed)
        success_embed = discord.Embed(title="Update Sent", description=f"Successfully sent RAM upgrade details to {user.mention}.", color=0x00ff00)
        success_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        success_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=success_embed)
    except discord.errors.Forbidden:
        error_embed = discord.Embed(title="DM Error", description=f"Cannot send DM to {user.mention}. They may have DMs disabled.", color=0xff0000)
        error_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        error_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=error_embed)

@tree.command(name="cpuupdate", description="Admin command to send CPU upgrade details to a user.")
@app_commands.describe(user="The user to send details to", cpu="The CPU specification")
@app_commands.checks.has_permissions(administrator=True)
async def cpuupdate(interaction: discord.Interaction, user: discord.Member, cpu: str):
    await interaction.response.defer()
    embed = discord.Embed(title="🔰 CPU Upgrade Confirmed! 🔰", description="✅ Your CPU upgrade is now active! ✅", color=0x00ff00)
    embed.add_field(name="🖥️ Details", value=f"Upgraded to {cpu}.\n⚡ Expect faster speeds and better performance!", inline=False)
    embed.set_footer(text="💎 Vizora Host ⚡")
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
    try:
        await user.send(embed=embed)
        success_embed = discord.Embed(title="Update Sent", description=f"Successfully sent CPU upgrade details to {user.mention}.", color=0x00ff00)
        success_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        success_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=success_embed)
    except discord.errors.Forbidden:
        error_embed = discord.Embed(title="DM Error", description=f"Cannot send DM to {user.mention}. They may have DMs disabled.", color=0xff0000)
        error_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        error_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=error_embed)

@tree.command(name="storageupdate", description="Admin command to send storage upgrade details to a user.")
@app_commands.describe(user="The user to send details to", gb="The amount of storage in GB")
@app_commands.checks.has_permissions(administrator=True)
async def storageupdate(interaction: discord.Interaction, user: discord.Member, gb: str):
    await interaction.response.defer()
    embed = discord.Embed(title="📀 Storage Upgrade Confirmed! 📀", description="📦 Your storage upgrade has been completed! 📦", color=0x00ff00)
    embed.add_field(name="🖥️ Details", value=f"Added {gb} GB of storage.\n⚡ Store more data, run more projects!", inline=False)
    embed.set_footer(text="💎 Vizora Host 🌌")
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
    try:
        await user.send(embed=embed)
        success_embed = discord.Embed(title="Update Sent", description=f"Successfully sent storage upgrade details to {user.mention}.", color=0x00ff00)
        success_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        success_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=success_embed)
    except discord.errors.Forbidden:
        error_embed = discord.Embed(title="DM Error", description=f"Cannot send DM to {user.mention}. They may have DMs disabled.", color=0xff0000)
        error_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        error_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=error_embed)

@tree.command(name="stock", description="Admin command to view current stock of RAM, CPU, storage, VPS, and Pterodactyl.")
@app_commands.checks.has_permissions(administrator=True)
async def stock(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="📊 VIZORA HOST Stock", description="Current stock levels for shop items.", color=0x00ff00)
    embed.add_field(name="RAM", value=f"{stock_data.get('ram', 0)} units", inline=True)
    embed.add_field(name="CPU", value=f"{stock_data.get('cpu', 0)} units", inline=True)
    embed.add_field(name="Storage", value=f"{stock_data.get('storage', 0)} units", inline=True)
    embed.add_field(name="VPS", value=f"{stock_data.get('vps', {'count': 0})['count']} units", inline=True)
    embed.add_field(name="Pterodactyl", value=f"{stock_data.get('pterodactyl', {'count': 0})['count']} panels", inline=True)
    embed.add_field(name="Manage Stock", value="Use `/stock_add` for upgrades or `/vpsadd`/`/addpterodactyl` for VPS/Pterodactyl.", inline=False)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.followup.send(embed=embed)

@tree.command(name="stock_add", description="Admin command to add stock for RAM, CPU, or storage.")
@app_commands.describe(item="The item to add stock for (ram, cpu, storage)", amount="The amount to add")
@app_commands.checks.has_permissions(administrator=True)
async def stock_add(interaction: discord.Interaction, item: str, amount: int):
    await interaction.response.defer()
    item = item.lower()
    if item not in ["ram", "cpu", "storage"]:
        embed = discord.Embed(title="Invalid Item", description="Use `ram`, `cpu`, or `storage`. For VPS/Pterodactyl, use `/vpsadd` or `/addpterodactyl`.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    if amount <= 0:
        embed = discord.Embed(title="Invalid Amount", description="Amount must be positive!", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.followup.send(embed=embed)
        return
    
    stock_data[item] = stock_data.get(item, 0) + amount
    save_stock(stock_data)
    await update_stock_display()
    embed = discord.Embed(title="Stock Added! :white_check_mark:", description=f"Added {amount} units to **{item.upper()}** stock. New stock: {stock_data[item]} units", color=0x00ff00)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.followup.send(embed=embed)

@tree.command(name="help", description="List all available commands with descriptions.")
async def help_command(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="📚 Vizora Host Commands", color=0x00ff00)
    embed.add_field(
        name="User Commands",
        value="`/coins` - Check coin balance\n`/buy <item>` - Purchase shop items\n`/reffral <code>` - Redeem referral code\n`/leaderboard` - View top players\n`/profile` - View your profile",
        inline=False
    )
    embed.add_field(
        name="Legacy Prefix Commands (+)",
        value="`+c` - Check coins\n`+i` - Check invites\n`+specs` - View server specs\n`+purchase` - View purchased items",
        inline=False
    )
    embed.add_field(
        name="Admin Commands",
        value="`/sync` - Sync commands\n`/addreffral` - Create referral\n`/coin_give/take` - Manage user coins\n`/vpsadd` - Add VPS stock\n`/addpterodactyl` - Add panel stock\n`/ramupdate/cpuupdate/storageupdate` - Send upgrades\n`/stock` - View stock\n`/stock_add` - Add upgrade stock",
        inline=False
    )
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_footer(text="Use /coins [user] for admin check. Enjoy hosting! 🚀")
    await interaction.followup.send(embed=embed)

@tree.command(name="leaderboard", description="View top players by coins.")
@app_commands.describe(sort_by="Sort by coins or invites (default: coins)")
async def leaderboard(interaction: discord.Interaction, sort_by: str = "coins"):
    await interaction.response.defer()
    if sort_by.lower() not in ["coins", "invites"]:
        sort_by = "coins"
    
    # Get sorted users
    sorted_users = sorted(
        [(uid, data.get(sort_by, 0)) for uid, data in user_data.items() if uid != str(interaction.guild.id)],  # Exclude guild entries
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    embed = discord.Embed(title=f"🏆 Top {sort_by.capitalize()} Leaderboard", color=0x00ff00)
    leaderboard_text = ""
    for i, (uid, value) in enumerate(sorted_users, 1):
        user = bot.get_user(int(uid))
        display_name = user.display_name if user else uid
        leaderboard_text += f"{i}. **{display_name}**: {value}\n"
    embed.description = leaderboard_text or "No data yet."
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.followup.send(embed=embed)

# Error handling for admin commands
@sync.error
async def sync_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        logger.error(f"Unexpected error in /sync: {error}")
        embed = discord.Embed(title="Unexpected Error", description="An unexpected error occurred. Please try again.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@coins.error
async def coins_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to check another user's coins.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/coins [user]`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        logger.error(f"Unexpected error in /coins: {error}")
        embed = discord.Embed(title="Unexpected Error", description="An unexpected error occurred. Please try again.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@addreffral.error
async def addreffral_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/addreffral coins code max_users`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        logger.error(f"Unexpected error in /addreffral: {error}")
        embed = discord.Embed(title="Unexpected Error", description="An unexpected error occurred. Please try again.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@coin_give.error
async def coin_give_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/coin_give user amount`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@coin_take.error
async def coin_take_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/coin_take user amount`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@vpsadd.error
async def vpsadd_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/vpsadd number ip port username password`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@addpterodactyl.error
async def addpterodactyl_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/addpterodactyl number username password`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@ramupdate.error
async def ramupdate_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/ramupdate user gb`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@cpuupdate.error
async def cpuupdate_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/cpuupdate user cpu`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@storageupdate.error
async def storageupdate_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/storageupdate user gb`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@stock.error
async def stock_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@stock_add.error
async def stock_add_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(title="Access Denied", description=f"You need administrator permissions to use this command.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please use the format: `/stock_add item amount`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@buy.error
async def buy_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please specify an item: `/buy <item_name>` (e.g., ram, cpu, storage, pterodactyl, vps)", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        logger.error(f"Unexpected error in /buy: {error}")
        embed = discord.Embed(title="Unexpected Error", description="An unexpected error occurred. Please try again.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@reffral.error
async def reffral_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Missing Argument", description=f"Please specify a code: `/reffral <code>`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        logger.error(f"Unexpected error in /reffral: {error}")
        embed = discord.Embed(title="Unexpected Error", description="An unexpected error occurred. Please try again.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@help_command.error
async def help_error(interaction: discord.Interaction, error):
    logger.error(f"Unexpected error in /help: {error}")
    embed = discord.Embed(title="Unexpected Error", description="An unexpected error occurred. Please try again.", color=0xff0000)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@leaderboard.error
async def leaderboard_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingRequiredArgument):
        embed = discord.Embed(title="Usage", description="`/leaderboard [sort_by: coins|invites]`", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        logger.error(f"Unexpected error in /leaderboard: {error}")
        embed = discord.Embed(title="Unexpected Error", description="An unexpected error occurred. Please try again.", color=0xff0000)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Bot token (replace with your bot token)
bot.run('MTM5OTA4NDk4NjU2ODY3NTM1OA.GWVUe5.sPQTkfQbo-wIKVMVHK-aoxmdkotJsVOV_sFYy0')
