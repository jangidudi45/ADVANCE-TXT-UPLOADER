import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import logging
from typing import Optional, Tuple, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Database:
    def __init__(self, database_url: str):
        try:
            self.client = MongoClient(database_url)
            db_name = database_url.split('/')[-1].split('?')[0] if '/' in database_url else "your_bot_db"
            if not db_name or db_name.startswith('mongodb'):
                db_name = "your_bot_db"
            self.db = self.client[db_name]
            self.sudo_users_collection = self.db["sudo_users"]
            self.topic_auth_collection = self.db["topic_auth"]

            # Ensure indexes
            self.sudo_users_collection.create_index([("user_id", pymongo.ASCENDING)], unique=True)
            self.topic_auth_collection.create_index([("chat_id", pymongo.ASCENDING), ("thread_id", pymongo.ASCENDING)], unique=True)
            
            self.client.admin.command('ping')
            logging.info(f"MongoDB database '{db_name}' connected successfully.")
        except ConnectionFailure as e:
            logging.error(f"Could not connect to MongoDB: {e}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred during MongoDB initialization: {e}")
            raise

    def add_sudo_user(self, user_id: int, username: str = None) -> bool:
        """Adds a user to the sudo list."""
        try:
            user_data = {"user_id": user_id}
            if username:
                user_data["username"] = username
            self.sudo_users_collection.insert_one(user_data)
            logging.info(f"User {user_id} added to sudo list.")
            return True
        except DuplicateKeyError:
            logging.info(f"User {user_id} is already a sudo user.")
            return False
        except Exception as e:
            logging.error(f"Error adding sudo user {user_id}: {e}")
            return False

    def add_topic_auth(self, chat_id: int, thread_id: Optional[int] = None) -> bool:
        """Adds a chat or topic to authorized list."""
        try:
            auth_data = {"chat_id": chat_id, "thread_id": thread_id}
            self.topic_auth_collection.insert_one(auth_data)
            logging.info(f"Chat {chat_id}{f'/topic {thread_id}' if thread_id else ''} added to authorized list.")
            return True
        except DuplicateKeyError:
            logging.info(f"Chat/Topic already authorized.")
            return False
        except Exception as e:
            logging.error(f"Error adding chat/topic: {e}")
            return False

    def remove_sudo_user(self, user_id: int) -> bool:
        """Removes a user from the sudo list."""
        try:
            result = self.sudo_users_collection.delete_one({"user_id": user_id})
            if result.deleted_count > 0:
                logging.info(f"User {user_id} removed from sudo list.")
                return True
            logging.info(f"User {user_id} not found in sudo list.")
            return False
        except Exception as e:
            logging.error(f"Error removing sudo user {user_id}: {e}")
            return False

    def remove_topic_auth(self, chat_id: int, thread_id: Optional[int] = None) -> bool:
        """Removes a chat or topic from authorized list."""
        try:
            query = {"chat_id": chat_id}
            if thread_id is not None:
                query["thread_id"] = thread_id
            result = self.topic_auth_collection.delete_one(query)
            if result.deleted_count > 0:
                logging.info(f"Chat/Topic removed from authorized list.")
                return True
            logging.info(f"Chat/Topic not found in authorized list.")
            return False
        except Exception as e:
            logging.error(f"Error removing chat/topic: {e}")
            return False

    def get_sudo_users(self) -> List[int]:
        """Returns a list of all sudo user IDs."""
        try:
            users = self.sudo_users_collection.find({}, {"user_id": 1, "_id": 0})
            return [user["user_id"] for user in users]
        except Exception as e:
            logging.error(f"Error getting sudo users: {e}")
            return []

    def get_authorized_chats(self) -> List[Dict]:
        """Returns a list of all authorized chats/topics."""
        try:
            chats = self.topic_auth_collection.find({}, {"_id": 0})
            return list(chats)
        except Exception as e:
            logging.error(f"Error getting authorized chats: {e}")
            return []

    def is_sudo_user(self, user_id: int) -> bool:
        """Checks if a user is a sudo user."""
        try:
            return self.sudo_users_collection.find_one({"user_id": user_id}) is not None
        except Exception as e:
            logging.error(f"Error checking sudo status for user {user_id}: {e}")
            return False

    def is_authorized_chat(self, chat_id: int, thread_id: Optional[int] = None) -> bool:
        """Checks if a chat or topic is authorized."""
        try:
            query = {"chat_id": chat_id}
            if thread_id is not None:
                query["thread_id"] = thread_id
            else:
                # Check if chat is authorized without specific topic
                query["thread_id"] = None
            
            return self.topic_auth_collection.find_one(query) is not None
        except Exception as e:
            logging.error(f"Error checking chat authorization: {e}")
            return False

    def parse_topic_string(self, input_str: str) -> Tuple[int, Optional[int]]:
        """Parses string like '-1003341469614' or '-1003341469614/34' into chat_id and thread_id."""
        try:
            if '/' in input_str:
                chat_id_str, thread_id_str = input_str.split('/', 1)
                return int(chat_id_str), int(thread_id_str)
            else:
                return int(input_str), None
        except Exception as e:
            logging.error(f"Error parsing topic string: {e}")
            raise ValueError("Invalid topic format. Use 'chat_id' or 'chat_id/thread_id'")

# Global database instance
db = None
