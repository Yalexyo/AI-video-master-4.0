import os
from sentence_transformers import SentenceTransformer
from pathlib import Path

def cache_models():
    model_names = [
        'all-MiniLM-L6-v2',
        'paraphrase-multilingual-MiniLM-L12-v2'
    ]
    base_save_dir = Path("models/sentence_transformers")

    print("Starting model caching process...")

    for model_name in model_names:
        print(f"Attempting to download and cache model: {model_name}")
        try:
            # Load the model (this will download it if not cached by sentence-transformers locally)
            model = SentenceTransformer(model_name)

            # Define the specific save path for our application's structure
            # Replace '/' with '_' in model_name for directory naming if that was the original convention,
            # but the original paths were 'all-MiniLM-L6-v2', not 'all-MiniLM-L6-v2_'.
            # The convention used in your mapper.py is just the model name as the directory.
            model_save_path = base_save_dir / model_name
            
            print(f"Ensuring save directory exists: {model_save_path}")
            os.makedirs(model_save_path, exist_ok=True)

            print(f"Saving model to: {model_save_path}")
            model.save(str(model_save_path))
            print(f"Successfully cached model: {model_name} to {model_save_path}")

        except Exception as e:
            print(f"ERROR: Failed to cache model {model_name}. Error: {e}")
            print("Please check your internet connection and try again.")
            print("If the problem persists, the model might be temporarily unavailable or there could be other issues.")

    print("Model caching process finished.")

if __name__ == "__main__":
    # Create the base directory if it doesn't exist
    os.makedirs("models/sentence_transformers", exist_ok=True)
    # Create a dummy scripts directory if it doesn't exist, for placing the script
    os.makedirs("scripts", exist_ok=True)
    cache_models() 