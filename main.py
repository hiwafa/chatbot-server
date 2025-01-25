from fastapi import FastAPI, HTTPException
from database import database 
from pydantic import BaseModel
from bson import ObjectId
import logging
import random


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
@app.get("/random_answer")
async def get_random_answer(question_text: str):
    try:
        # Fetch the question document based on question_text
        collection = database[COLLECTION_NAME]
        question = collection.find_one({"question_text": question_text})

        # Check if the question exists
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Get the answers and pick a random one
        answers = question.get("question_answers", [])
        if not answers:
            raise HTTPException(status_code=404, detail="No answers found for the question")

        random_answer = random.choice(answers)
        return {"random_answer": random_answer}

    except Exception as e:
        # Log unexpected errors
        logger.error(f"An error occurred in get_random_answer function: {e}")
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
