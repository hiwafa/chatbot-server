import logging

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def divide_numbers(a: float, b: float):
    try:
        # Attempt division
        result = a / b
        return {"result": result}
    except ZeroDivisionError as e:
        # Log the error
        logger.error(f"Division error: {e}")
        
        # Raise a user-friendly error
        # raise ValueError("Cannot divide by zero.") from e
        #  print("err$$$$$$$$$$$$1 ", e)
    except Exception as e:
        # Log unexpected errors
        # logger.error(f"Unexpected error: {e}")
        print("err$$$$$$$$$$$$2 ", e)
        
        # Raise a generic error
        # raise RuntimeError("An unexpected error occurred.") from e

# Testing the function
try:
    print(divide_numbers(10, 0))  # Division by zero
except Exception as e:
    print(f"Handled Error: {e}")

try:
    print(divide_numbers(10, "five"))  # Invalid input
except Exception as e:
    print(f"Handled Error: {e}")
