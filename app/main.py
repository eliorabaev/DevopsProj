from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
from typing import Optional, List, Union
import os
import random

# Initialize FastAPI app
app = FastAPI(title="Fun Redis Word Service")

# Export app variable explicitly for Uvicorn
__all__ = ["app"]

# Connect to Redis
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = os.getenv("REDIS_PORT", 6379)
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

# Define data models
class Item(BaseModel):
    key: str
    value: str
    
class WordInput(BaseModel):
    word: str
    
class MultipleWordsInput(BaseModel):
    words: List[str]

# List of fun words to preload
WORDS = [
    "serendipity", "eloquent", "exuberant", "whimsical", "luminous", 
    "cacophony", "ebullient", "effervescent", "mellifluous", "resplendent",
    "quintessential", "ephemeral", "scrumptious", "dazzling", "jubilant",
    "phenomenal", "magnificent", "surreptitious", "persnickety", "vivacious",
    "flabbergasted", "bamboozled", "discombobulated", "shenanigan", "kerfuffle",
    "brouhaha", "flummoxed", "hullabaloo", "gobsmacked", "rigmarole",
    "taradiddle", "abracadabra", "bumfuzzle", "cattywampus", "widdershins",
    "lollygagging", "nincompoop", "scalawag", "ragamuffin", "rapscallion",
    "flibbertigibbet", "bodacious", "supercalifragilisticexpialidocious", "hippopotomonstrosesquippedaliophobia", "fantastic",
    "wonderful", "splendid", "marvelous", "brilliant", "stupendous",
    "miraculous", "spectacular", "extraordinary", "incredible", "unbelievable",
    "outstanding", "remarkable", "fabulous", "terrific", "awesome",
    "colossal", "tremendous", "gigantic", "enormous", "ginormous",
    "humongous", "gargantuan", "mammoth", "behemoth", "titanic",
    "leviathan", "herculean", "brobdingnagian", "astronomical", "cosmic",
    "interstellar", "galactic", "universal", "omnipotent", "omniscient",
    "omnipresent", "ethereal", "celestial", "sublime", "transcendent",
    "majestic", "regal", "imperial", "sovereign", "grandiose",
    "stately", "elegant", "luxurious", "opulent", "sumptuous",
    "lavish", "extravagant", "plush", "ritzy", "swanky",
    "posh", "fancy", "chic", "stylish", "sophisticated"
]

# Key prefix for Redis
WORD_KEY_PREFIX = "fun_word:"
WORD_INDEX_KEY = "current_word_index"
TOTAL_WORDS_KEY = "total_words"

@app.on_event("startup")
async def startup_event():
    """Preload words into Redis on application startup"""
    # Check if words are already loaded
    if not redis_client.exists(WORD_INDEX_KEY):
        # Initialize the index
        redis_client.set(WORD_INDEX_KEY, "0")
        
        # Set total words count
        redis_client.set(TOTAL_WORDS_KEY, str(len(WORDS)))
        
        # Load all words into Redis
        for i, word in enumerate(WORDS):
            redis_client.set(f"{WORD_KEY_PREFIX}{i}", word)
        
        print(f"Preloaded {len(WORDS)} words into Redis")

@app.get("/")
def read_root():
    """Return a new word each time the root endpoint is accessed"""
    try:
        # Get the total number of words from Redis
        total_words = int(redis_client.get(TOTAL_WORDS_KEY) or len(WORDS))
        
        # Get and increment the current index (with wrapping)
        current_index = int(redis_client.get(WORD_INDEX_KEY) or 0)
        next_index = (current_index + 1) % total_words
        redis_client.set(WORD_INDEX_KEY, str(next_index))
        
        # Get the word at the current index
        word = redis_client.get(f"{WORD_KEY_PREFIX}{current_index}")
        
        # If word is not found for some reason, get a random word
        if not word:
            random_index = random.randint(0, total_words - 1)
            word = WORDS[random_index % len(WORDS)]  # Fallback to the original list
            redis_client.set(f"{WORD_KEY_PREFIX}{random_index}", word)  # Restore it in Redis
        
        return {"word": word, "message": f"Your fun word is: {word}!"}
    except Exception as e:
        # Fallback in case of Redis errors
        random_word = random.choice(WORDS)
        return {"word": random_word, "message": f"Your fun word is: {random_word}! (Fallback mode)"}

@app.get("/data/{key}")
def get_item(key: str):
    value = redis_client.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": value}

@app.post("/data", status_code=201)
def create_item(item: Item):
    try:
        redis_client.set(item.key, item.value)
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/{key}")
def delete_item(key: str):
    result = redis_client.delete(key)
    if result == 0:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"message": "Key deleted successfully"}

@app.get("/words")
def get_all_words():
    """Get all available words"""
    words = []
    # Get total words from Redis
    total_words = int(redis_client.get(TOTAL_WORDS_KEY) or len(WORDS))
    
    for i in range(total_words):
        word = redis_client.get(f"{WORD_KEY_PREFIX}{i}")
        if word:
            words.append(word)
    return {"words": words, "count": len(words)}

@app.get("/words/reset")
def reset_word_index():
    """Reset the word index to start from the beginning"""
    redis_client.set(WORD_INDEX_KEY, "0")
    return {"message": "Word index reset successfully"}

# Add a new word to the database
@app.post("/words/add", status_code=201)
def add_word(word_input: WordInput):
    """Add a new word to the database"""
    try:
        # Get current total words count
        total_words = int(redis_client.get(TOTAL_WORDS_KEY) or len(WORDS))
        
        # Store the new word with the next available index
        new_index = total_words
        redis_client.set(f"{WORD_KEY_PREFIX}{new_index}", word_input.word)
        
        # Increment the total words counter
        redis_client.set(TOTAL_WORDS_KEY, str(total_words + 1))
        
        return {
            "message": f"Word '{word_input.word}' added successfully",
            "index": new_index,
            "total_words": total_words + 1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add multiple words at once
@app.post("/words/add-multiple", status_code=201)
def add_multiple_words(input_data: MultipleWordsInput):
    """Add multiple words to the database at once"""
    try:
        # Get current total words count
        total_words = int(redis_client.get(TOTAL_WORDS_KEY) or len(WORDS))
        
        # Store the new words
        added_words = []
        for i, word in enumerate(input_data.words):
            new_index = total_words + i
            redis_client.set(f"{WORD_KEY_PREFIX}{new_index}", word)
            added_words.append({"word": word, "index": new_index})
        
        # Update the total words counter
        new_total = total_words + len(input_data.words)
        redis_client.set(TOTAL_WORDS_KEY, str(new_total))
        
        return {
            "message": f"Added {len(input_data.words)} new words",
            "added_words": added_words,
            "total_words": new_total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
def health_check():
    try:
        # Check if Redis is responding
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}