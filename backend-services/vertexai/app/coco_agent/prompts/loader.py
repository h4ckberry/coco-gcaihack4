import os

def load_prompt(prompt_name: str) -> str:
    """Loads a prompt from a markdown file in the same directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, f"{prompt_name}.md")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
