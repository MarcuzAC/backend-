from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

# Initialize MongoDB connection
client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.get_database()  

async def get_db():
    return db
