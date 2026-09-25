import os
from datetime import datetime, timezone

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient


# ==========================================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================================

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "attendance_tracker"
)


# ==========================================================
# VALIDATE CONFIGURATION
# ==========================================================

if not MONGODB_URI:
    raise RuntimeError(
        "MONGODB_URI is missing from .env"
    )


# ==========================================================
# MONGODB CONNECTION
# ==========================================================

client = MongoClient(
    MONGODB_URI,

    tls=True,
    tlsCAFile=certifi.where(),

    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000,

    retryWrites=True,
)


db = client[MONGODB_DATABASE]

attendance_collection = db["attendance_cache"]


# ==========================================================
# SAVE ATTENDANCE
# ==========================================================

def save_attendance(username, attendance):

    attendance_collection.update_one(
        {
            "username": username
        },
        {
            "$set": {
                "username": username,
                "attendance": attendance,
                "updated_at": datetime.now(
                    timezone.utc
                ),
            }
        },
        upsert=True,
    )


# ==========================================================
# GET CACHED ATTENDANCE
# ==========================================================

def get_cached_attendance(username):

    document = attendance_collection.find_one(
        {
            "username": {
                "$regex": f"^{username}$",
                "$options": "i"
            }
        },
        {
            "_id": 0
        }
    )

    return document


# ==========================================================
# TIMETABLE CACHE
# ==========================================================

timetable_collection = db["timetable_cache"]


def save_timetable(username, timetable):
    timetable_collection.update_one(
        {
            "username": username
        },
        {
            "$set": {
                "username": username,
                "timetable": timetable,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )


def get_cached_timetable(username):
    document = timetable_collection.find_one(
        {
            "username": {
                "$regex": f"^{username}$",
                "$options": "i"
            }
        },
        {
            "_id": 0
        }
    )
    return document


# ==========================================================
# DELETE CACHED ATTENDANCE
# ==========================================================

def delete_cached_attendance(username):

    attendance_collection.delete_one(
        {
            "username": username
        }
    )


# ==========================================================
# TEST CONNECTION
# ==========================================================

def test_mongodb_connection():

    client.admin.command("ping")

    return True