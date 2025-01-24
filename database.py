from pymongo import MongoClient

# MongoDB connection details
MONGO_URI = "mongodb+srv://dieteamarbeit:Chatbot2025@cluster0.0mjq6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # Update with your MongoDB URI
DATABASE_NAME = "chatbotdb"

# Initialize the MongoDB client
client = MongoClient(MONGO_URI)
database = client[DATABASE_NAME]
