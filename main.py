from fastapi import FastAPI, HTTPException
from database import database 
from pydantic import BaseModel, Field
from bson import ObjectId
import logging
import random
import re

from fastapi.middleware.cors import CORSMiddleware


# ------------------------------------------------------------------------------------------------------------------------------
# initializations

app = FastAPI()

# Allow all origins (for development purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Define the collection name
COLLECTION_NAME = "dictionary"
user_story = "userstory"


# ------------------------------------------------------------------------------------------------------------------------------
# Helper function to serialize MongoDB documents
def serialize_item(item):
    return {**item, "_id": str(item["_id"])}


# Get the questions
@app.get("/questions")
def get_questions():
    try:
        collection = database[COLLECTION_NAME]
        items = collection.find()  # Retrieve all documents
        serialized_items = [serialize_item(item) for item in items]  # Serialize ObjectId
        return serialized_items
    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in get_questions function: {e}")
        raise HTTPException(status_code=500, detail=f"get_questions: {e}")

# ------------------------------------------------------------------------------------------------------------------------------
# Get a random answer based on question text
# @app.get("/random_answer")
# async def get_random_answer(question_text: str):
#     try:
#         # Fetch the question document based on question_text
#         collection = database[COLLECTION_NAME]
#         question = collection.find_one({"question_text": {"$regex": question_text, "$options": "i"}})

#         # Check if the question exists
#         if not question:
#             raise HTTPException(status_code=404, detail="Question not found")

#         # Get the answers and pick a random one
#         answers = question.get("question_answers", [])
#         if not answers:
#             raise HTTPException(status_code=404, detail="No answers found for the question")

#         return random.choice(answers)

#     except Exception as e:
#         # Log unexpected errors
#         logger.error(f"An error occurred in get_random_answer function: {e}")
#         raise HTTPException(status_code=500, detail=f"get_random_answer: {e}")

def clean_text(text: str) -> str:
    """Convert text to lowercase, remove punctuation, and escape regex characters."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)  # Remove punctuation
    return text

@app.get("/random_answer")
async def get_random_answer(question_text: str):
    try:
        if not question_text.strip():
            raise HTTPException(status_code=400, detail="Invalid question_text: Cannot be empty.")

        # Detect multiple questions and identify the delimiter
        delimiters = [", und ", ", oder ", " und ", ", ", ",und ", ",oder"]
        detected_delimiter = None

        for delimiter in delimiters:
            if delimiter in question_text:
                detected_delimiter = delimiter
                questions = [clean_text(q) for q in question_text.split(delimiter) if q.strip()]
                break
        else:
            questions = [clean_text(question_text)]  # Single question case

        if not questions:
            raise HTTPException(status_code=400, detail="No valid questions detected.")

        # Perform a single MongoDB query using $or to fetch all matching questions at once
        collection = database[COLLECTION_NAME]
        query = {"$or": [{"question_text": {"$regex": re.escape(q), "$options": "i"}} for q in questions]}
        question_docs = list(collection.find(query))

        if not question_docs:
            return "No answers found for the given questions."

        # Map found questions to answers
        question_answer_map = {
            clean_text(q["question_text"]): random.choice(q.get("question_answers", ["No answers available"]))
            for q in question_docs
        }

        # Prepare the response
        answers = [
            question_answer_map.get(q, f"No answer found for: {q}")  # Use found answer or a default message
            for q in questions
        ]

        # Join answers using the detected delimiter or default to ", "
        response_text = detected_delimiter.join(answers) if detected_delimiter else ", ".join(answers)

        return response_text

    except Exception as e:
        logger.error(f"An error occurred in get_random_answer: {e}")
        raise HTTPException(status_code=500, detail=f"get_random_answer: {e}")
    
# ------------------------------------------------------------------------------------------------------------------------------
# Get question by id
@app.get("/get_question_by_id")
async def get_question_by_id(question_id: str):
    try:

         # Validate the question ID
        if not ObjectId.is_valid(question_id):
            raise HTTPException(status_code=400, detail="Invalid question ID format")
        
        # Convert question_id to ObjectId
        question_obj_id = ObjectId(question_id)

        # Fetch the question document based on question_text
        collection = database[COLLECTION_NAME]
        question = collection.find_one({"_id": question_obj_id})

        # Check if the question exists
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        # Convert MongoDB ObjectId to string for JSON serialization
        question["_id"] = str(question["_id"])

        return question

    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in get_question_by_id function: {e}")
        raise HTTPException(status_code=500, detail=f"get_question_by_id: {e}")


# ------------------------------------------------------------------------------------------------------------------------------
# Pydantic model for the input data 
class Question(BaseModel):
    question_text: str
    question_answers: list[str]

# Post a question
@app.post("/add_question")
async def add_question(question: Question):
    try:
        # Prepare the document to insert
        question_document = {
            "question_text": question.question_text,
            "question_answers": question.question_answers,
        }

        # Insert the document into the collection
        collection = database[COLLECTION_NAME]

        # Check if the question already exists
        existing_question = collection.find_one({"question_text": question.question_text})
        if existing_question:
            raise HTTPException(status_code=400, detail="This question already exists.")
        
        result = collection.insert_one(question_document)

        # Return success message with the inserted ID
        return {
            "message": "Question added successfully",
            "question_id": str(result.inserted_id),
        }

    except Exception as e:
        logger.error(f"An error occurred in add_question function: {e}")
        raise HTTPException(status_code=500, detail=f"add_question: {e}")



# ------------------------------------------------------------------------------------------------------------------------------
# Endpoint to add multiple questions
@app.post("/add_multiple_questions")
async def add_multiple_questions(questions: list[Question]):
    try:

        collection = database[COLLECTION_NAME]

        # Convert Pydantic models to dictionary and insert into MongoDB
        questions_dict = [question.dict() for question in questions]
        result = collection.insert_many(questions_dict)
        
        # Return the inserted ids
        return {
            "message": "Questions added successfully",
            "question_ids": str(result.inserted_ids),
        }

    
    except Exception as e:
        logger.error(f"An error occurred in add_multiple_questions function: {e}")
        raise HTTPException(status_code=500, detail=f"add_multiple_questions: {e}")
# ------------------------------------------------------------------------------------------------------------------------------
# Edit the question text
@app.put("/edit_question_text")
async def edit_question_text(question_id: str, new_text: str):
    try:
        # Validate the question ID
        if not ObjectId.is_valid(question_id):
            raise HTTPException(status_code=400, detail="Invalid question ID format")
        
        # Convert question_id to ObjectId
        question_obj_id = ObjectId(question_id)

        # Update the question text
        collection = database[COLLECTION_NAME]
        result = collection.update_one(
            {"_id": question_obj_id}, {"$set": {"question_text": new_text}}
        )

        # Check if the question was found and updated
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Question not found")

        return {"message": "Question text updated successfully"}

    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in edit_question_text function: {e}")
        raise HTTPException(status_code=500, detail=f"edit_question_text: {e}")
    


# ------------------------------------------------------------------------------------------------------------------------------
@app.delete("/delete_question")
async def delete_question(question_id: str):
    try:

        # Validate ObjectId
        if not ObjectId.is_valid(question_id):
            raise HTTPException(status_code=400, detail="Invalid question ID format")

        # Convert question_id to ObjectId
        question_obj_id = ObjectId(question_id)

        # Get the collection object from the database
        collection = database[COLLECTION_NAME]

        # Attempt to delete the document
        result = collection.delete_one({"_id": question_obj_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Question not found")

        return {"message": "Question deleted successfully"}

    except Exception as e:
        # Log the error
        logger.error(f"An error occurred in delete_question function: {e}")
        raise HTTPException(status_code=500, detail=f"delete_question: {e}")
    
# ------------------------------------------------------------------------------------------------------------------------------
# Delete an answer   
@app.delete("/delete_answer")
async def delete_answer(question_id: str, answer: str):
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(question_id):
            raise HTTPException(status_code=400, detail="Invalid question ID")

        # Convert question_id to ObjectId
        question_obj_id = ObjectId(question_id)

        collection = database[COLLECTION_NAME]

        # Check if the document exists
        question = collection.find_one({"_id": question_obj_id})
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Check if the answer exists in the question_answers array
        if answer not in question.get("question_answers", []):
            raise HTTPException(status_code=404, detail="Answer not found in the question")

        # Perform the update operation to remove the answer
        result = collection.update_one(
            {"_id": question_obj_id},
            {"$pull": {"question_answers": answer}}
        )

        if result.modified_count == 1:
            return {"message": "Answer deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete answer")
        
    except Exception as e:
        # Log the error
        logger.error(f"An error occurred in delete_answer function: {e}")
        raise HTTPException(status_code=500, detail=f"delete_answer: {e}")
    


# ------------------------------------------------------------------------------------------------------------------------------
# Add a new answer to a question
@app.put("/add_answer")
async def add_answer(question_id: str, new_answer: str):
    try:

        # Validate the question ID
        if not ObjectId.is_valid(question_id):
            raise HTTPException(status_code=400, detail="Invalid question ID format")
        
        # Convert question_id to ObjectId
        question_obj_id = ObjectId(question_id)

        # Append the new answer to the question_answers array
        collection = database[COLLECTION_NAME]
        result = collection.update_one(
            {"_id": question_obj_id},
            {"$push": {"question_answers": new_answer}}
        )

        # Check if the question was found and updated
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Question not found")

        return {"message": "New answer added successfully"}
    
    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in add_answer function: {e}")
        raise HTTPException(status_code=500, detail=f"add_answer: {e}")


# ------------------------------------------------------------------------------------------------------------------------------
# Add a new answer to a question
@app.put("/edit_answer")
async def edit_answer(question_id: str, old_answer: str, new_answer: str):
    try:

        # Validate the question ID
        if not ObjectId.is_valid(question_id):
            raise HTTPException(status_code=400, detail="Invalid question ID format")
        
        # Convert question_id to ObjectId
        question_obj_id = ObjectId(question_id)

        # Append the new answer to the question_answers array
        collection = database[COLLECTION_NAME]
        result = collection.update_one(
            {"_id": question_obj_id, "question_answers": old_answer},
            {"$set": {"question_answers.$": new_answer}}
        )

        # Check if the question was found and updated
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Question not found")

        return {"message": "New answer added successfully"}
    
    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in edit_answer function: {e}")
        raise HTTPException(status_code=500, detail=f"edit_answer: {e}")
    
 
# ------------------------------------------------------------------------------------------------------------------------------
# Define the collection name
user_story_collection = "userstory"

# ------------------------------------------------------------------------------------------------------------------------------
class UserStory(BaseModel):
    user_id: str
    user_name: str
    user_question: str
    user_answer: str
    date_of_question: str

# Add a new answer to a question
@app.post("/add_user_story")
async def add_user_story(user_story: UserStory):
    try:

       # Prepare the document to insert
        user_story_document = {
                "user_id": user_story.user_id,
                "user_name": user_story.user_name,
                "user_question": user_story.user_question,
                "user_answer": user_story.user_answer,
                "date_of_question": user_story.date_of_question,
        }

        # Insert the document into the collection
        collection = database[user_story_collection]

        result = collection.insert_one(user_story_document)

        # Return success message with the inserted ID
        return {
            "message": "Question added successfully",
            "question_id": str(result.inserted_id),
        }
    
    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in add_user_story function: {e}")
        raise HTTPException(status_code=500, detail=f"add_user_story: {e}")






# ------------------------------------------------------------------------------------------------------------------------------
# Define the collection name
USER_COLLECTION = "user"

# ------------------------------------------------------------------------------------------------------------------------------
class AddUser(BaseModel):
    user_id: str
    user_first_name: str
    user_last_name: str
    user_about: str
    user_image: str
    user_date_of_birth: str
    user_role: str

class User(BaseModel):
    id: str = Field(..., alias="_id", description="The MongoDB ObjectId of the user")
    user_id: str
    user_first_name: str
    user_last_name: str
    user_about: str
    user_image: str
    user_date_of_birth: str
    user_role: str

# Add a new user
@app.post("/add_user")
async def add_user(user: AddUser):
    try:

       # Prepare the document to insert
        user_document = {
                "user_id": user.user_id,
                "user_role": user.user_role,
                "user_first_name": user.user_first_name,
                "user_last_name": user.user_last_name,
                "user_about": user.user_about,
                "user_about": user.user_about,
                "user_image": user.user_image,
                "user_date_of_birth": user.user_date_of_birth,
        }

        # Insert the document into the collection
        collection = database[USER_COLLECTION]

        # Check if the user already exists
        existing_user = collection.find_one({"user_id": user.user_id})
        if existing_user:
            raise HTTPException(status_code=400, detail="This user already exists.")

        result = collection.insert_one(user_document)

        # Return success message with the inserted ID
        return {
            "message": "User added successfully",
            "user_id": str(result.inserted_id),
        }
    
    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in add_user function: {e}")
        raise HTTPException(status_code=500, detail=f"add_user: {e}")


# Get the users
@app.get("/users")
def get_users():
    try:
        collection = database[USER_COLLECTION]
        items = collection.find()  # Retrieve all documents
        serialized_users = [serialize_item(item) for item in items]  # Serialize ObjectId
        return serialized_users
    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in get_users function: {e}")
        raise HTTPException(status_code=500, detail=f"get_users: {e}")

# ------------------------------------------------------------------------------------------------------------------------------
# Get user by id
@app.get("/get_user_by_id")
async def get_user_by_id(user_id: str):
    try:

        # Fetch the user document based on user_id
        collection = database[USER_COLLECTION]
        user = collection.find_one({"user_id": user_id})

        # Check if the user exists
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Convert MongoDB ObjectId to string for JSON serialization
        user["_id"] = str(user["_id"])

        return user

    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in get_user_by_id function: {e}")
        raise HTTPException(status_code=500, detail=f"get_user_by_id: {e}")


# ------------------------------------------------------------------------------------------------------------------------------
# Edit the user
@app.put("/edit_user")
async def edit_user(user: User):
    try:
        print("user::: ", user)
        # Validate the user ID
        if not ObjectId.is_valid(user.id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # Convert _id to ObjectId
        user_obj_id = ObjectId(user.id)

        # Convert the User model to a dictionary
        update_data = user.dict(by_alias=True)

        # W remove `_id` from the update_data dictionary since `_id` is the MongoDB identifier
        update_data.pop("_id", None)

        # Ensure there's data to update
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Update the user information
        collection = database[USER_COLLECTION]
        result = collection.update_one(
            {"_id": user_obj_id}, {"$set": update_data}
        )

        # Check if the user was found and updated
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "User updated successfully"}

    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in edit_user function: {e}")
        raise HTTPException(status_code=500, detail=f"edit_user: {e}")
    


# ------------------------------------------------------------------------------------------------------------------------------
@app.delete("/delete_user")
async def delete_user(user_id: str):
    try:
        # Ensure `user_id` is provided and valid
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Attempt to delete the user
        collection = database[USER_COLLECTION]
        result = collection.delete_one({"user_id": user_id})

        # Check if the user was found and deleted
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "User deleted successfully"}

    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in delete_user function: {e}")
        raise HTTPException(status_code=500, detail=f"delete_user: {e}")