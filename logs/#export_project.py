import os

def save_python_files(src_dir: str, log_dir: str):
    """Saves all Python files in src_dir into a single text file (logs/all.txt)."""
    os.makedirs(log_dir, exist_ok=True)  # Ensure logs/ directory exists
    output_file = os.path.join(log_dir, "all.txt")
    
    with open(output_file, "w", encoding="utf-8") as out_file:
        for root, _, files in os.walk(src_dir):
            for file in sorted(files):  # Sort to maintain order
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    out_file.write(f"# {file} #\n")  # Header
                    with open(file_path, "r", encoding="utf-8") as f:
                        out_file.write(f.read() + "\n\n")  # Append content
    print(f"✅ Saved all Python files to {output_file}")

def save_directory_structure(base_dir: str, log_dir: str):
    """Saves the directory structure of base_dir into logs/vzs.txt."""
    os.makedirs(log_dir, exist_ok=True)  # Ensure logs/ directory exists
    output_file = os.path.join(log_dir, "vzs.txt")

    with open(output_file, "w", encoding="utf-8") as out_file:
        for root, dirs, files in os.walk(base_dir):
            if ".git" in root:
                continue  # Skip the .git folder
            level = root.replace(base_dir, "").count(os.sep)
            indent = "│   " * level + "├───" if level > 0 else ""
            out_file.write(f"{indent}{os.path.basename(root)}/\n")
            for file in sorted(files):  # Sort to maintain order
                out_file.write(f"{'│   ' * (level + 1)}{file}\n")
    print(f"✅ Saved directory structure to {output_file}")

if __name__ == "__main__":
    src_dir = "src"  # Change if needed
    project_root = os.getcwd()
    log_dir = os.path.join(project_root, "logs")  # Store logs in logs/

    save_python_files(src_dir, log_dir)
    save_directory_structure(project_root, log_dir)

    print("🚀 Export complete! Logs saved in /logs/")
