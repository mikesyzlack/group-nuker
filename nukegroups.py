import json
import logging
import asyncio
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, ChatForbidden, ChatBannedRights
from datetime import timedelta

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from JSON file
with open("config.json", "r") as f:
    config = json.load(f)


api_id = config["api_id"]
api_hash = config["api_hash"]
client = TelegramClient('temp', api_id, api_hash)

# Function to get chats where the user is an admin and has the 'ban_users' permission
async def get_admin_chats(client):
    admin_chats = []
    last_date = None
    chunk_size = 200
    result = await client(GetDialogsRequest(
        offset_date=last_date,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=chunk_size,
        hash=0
    ))
    chats = result.chats
    for chat in chats:
        if not isinstance(chat, ChatForbidden):
            if hasattr(chat, 'admin_rights') and chat.admin_rights:
                if chat.admin_rights.ban_users:
                    admin_chats.append(chat)
    return admin_chats

# Function to get member IDs of a given group
async def get_group_member_ids(client, group_id):
    member_ids = []
    async for user in client.iter_participants(group_id):
        member_ids.append(user.id)
    return member_ids

# Function to ban a list of user IDs from a specific group
async def ban_users(client, group_id, user_ids, group_name, member_count):
    print(f"Warning: You are about to ban {member_count} members from the group '{group_name}'.")
    # confirmation = input("Type the group member count to proceed:")
    # if confirmation.toString() != member_count.toString():
    #     logger.warning("Incorrectly entered member count.")
    # elif confirmation.toString() != member_count.toString():
        # logger.info(f"correct member number")
    total_ids = len(user_ids)
    banned_users = 0
    ban_failures = 0
    batch_start_index = 0

    for i in range(batch_start_index, total_ids):
        batch = user_ids[i:i+(100 if len(user_ids) > 100 else len(user_ids))]
        for user_id in batch:
            try:
                # Fetch the user information
                user = await client.get_entity(user_id)
                # Return the username
                user_name = user.username if user else None

                # Define rights of restriction to place
                # Note You must set to ``True`` the permissions
                # you want to REMOVE, and leave as ``None`` those you want to KEEP.
                rights = ChatBannedRights(
                    until_date=timedelta(days=400), # Any value >365 is treatest as permanent
                    view_messages=True,
                    send_messages=True,
                    send_media=True,
                    send_stickers=True,
                    send_gifs=True,
                    send_games=True,
                    send_inline=True,
                    embed_links=True
                )
                logger.info(f"About to ban @{user_name}[{user_id}] from group {group_id}.")
                await client(EditBannedRequest(
                    group_id,
                    user_id,
                    rights
                ))
                banned_users += 1
                logger.info(f"Successfully banned user {user_name}[{user_id}] from group {group_id}.")
                await asyncio.sleep(0.1)

            except Exception as e:
                ban_failures += 1
                logger.warning(f"Failed to ban user {user_name}[{user_id}] from group {group_id}. Error: {e}")
            if banned_users + ban_failures == total_ids:
                print("Proess complete.")
            if len(total_ids) >= 100:
                batch_start_index += 100

        logger.info(f"Banned {banned_users} from {group_name}. Could not ban {ban_failures}.")

# Main function to run the script
async def main():
    api_id = config["api_id"]
    api_hash = config["api_hash"]
    phone = config["phone"]
    admin_chats = []
    async with TelegramClient('anon', api_id, api_hash) as client:
        try:
            if await client.is_user_authorized():
                await client.send_code_request(phone)
                await client.sign_in(phone, input('Enter the code: '))
            pass
        except:
            logger.error("Failed to sign in")
        try:
            admin_chats = await get_admin_chats(client)
            pass
        except:
            logger.error("Failed to get chats you are admin with ban permissions in")
        
        print("Chats where you are an admin and can ban users:")
        for i, chat in enumerate(admin_chats):
            print(f"[{i}] {chat.title}")
        
        index = int(input("Enter the group index number to find the member IDs: "))
        
        if 0 <= index < len(admin_chats):
            group_id = admin_chats[index].id
            group_name = admin_chats[index].title
            member_ids = await get_group_member_ids(client, group_id)
            member_count = len(member_ids)
            
            print("Member IDs of the group:")
            print(member_ids)
            
            try:
                await ban_users(client, group_id, member_ids, group_name, member_count)
            except:
                logger.info("Error occured while attempting to ban users")
        else:
            print("Invalid index. Exiting.")

if __name__ == '__main__':
    asyncio.run(main())