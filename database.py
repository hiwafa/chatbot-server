from urllib.parse import quote_plus
from pymongo import MongoClient

username = quote_plus("Chatbot")
password = quote_plus("Chatbot@2025")

# username = "Chatbot"
# password = "Chatbot@2025"

# MongoDB connection details
MONGO_URI = f"mongodb+srv://{username}:{password}@cluster0.fr9qk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "chatbotdb"

# Initialize the MongoDB client
client = MongoClient(MONGO_URI)
database = client[DATABASE_NAME]
