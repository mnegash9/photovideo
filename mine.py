import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Optional, Tuple
from PIL import Image, ImageTk, ExifTags
from pillow_heif import register_heif_opener
import cv2


register_heif_opener()

directory = "C:/Users/himat/Lehigh University Dropbox/Matyas Negash/Apps/Google Download Your Data/Takeout/Google Photos"
current_image_path = None
images_to_iterate = []
image_index = 0
files_deleted, file_sizes = 0, 0
video_capture = None
stop_video = False

MAX_WIDTH, MAX_HEIGHT = 800, 600

# Function to read the tally from a file
def read_tally(filename='delete_tally.txt'):
    global files_deleted, file_sizes, current_image_path, image_index
    try:
        with open(filename, 'r') as file:
            files_deleted = int(file.readline().strip())
            file_sizes = float(file.readline().strip())
            current_image_path = file.readline().strip()  # Read the image path as a string
            
            # Ensure images_to_iterate contains valid paths
            if Path(current_image_path) in images_to_iterate:
                image_index = images_to_iterate.index(Path(current_image_path))  # Get the index of the current image
            else:
                image_index = 0

    except (FileNotFoundError, ValueError):
        files_deleted = 0  # If file doesn't exist or contains invalid data, start at 0
        file_sizes = 0
        image_index = 0

# Function to save the tally to a file
def save_tally(filename='delete_tally.txt'):
    global files_deleted, file_sizes, current_image_path
    with open(filename, 'w') as file:
        file.write(f"{files_deleted}\n")
        file.write(f"{file_sizes}\n")
        file.write(f"{str(current_image_path)}\n")


def load_image(image_path: str, max_width: int = MAX_WIDTH, max_height: int = MAX_HEIGHT) -> Optional[ImageTk.PhotoImage]:
    """
    Load and process an image file with EXIF orientation correction and aspect ratio preservation.
    
    Args:
        image_path: Path to the image file
        max_width: Maximum allowed width
        max_height: Maximum allowed height
    
    Returns:
        ImageTk.PhotoImage object or None if loading fails
    """
    try:
        img = Image.open(image_path)
        
        # Get orientation and dimensions in one pass through EXIF data
        orientation = None
        original_width, original_height = img.size
        
        if hasattr(img, "_getexif") and (exif := img._getexif()):
            # Get orientation tag if it exists
            for tag, tag_value in ExifTags.TAGS.items():
                if tag_value == 'Orientation':
                    orientation = exif.get(tag)
                    break
            
            # Apply rotation based on orientation
            rotation_map = {
                3: 180,
                6: 270,
                8: 90
            }
            if orientation in rotation_map:
                img = img.rotate(rotation_map[orientation], expand=True)
                # Update dimensions after rotation
                original_width, original_height = img.size

        # Calculate new dimensions maintaining aspect ratio
        new_width, new_height = calculate_new_dimensions(original_width, original_height)
        
        # Only resize if necessary
        if (new_width, new_height) != (original_width, original_height):
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
        return ImageTk.PhotoImage(img)
        
    except Exception as e:
        messagebox.showerror("Error", f"Could not load image: {e}")
        return None

def calculate_new_dimensions(width: int, height: int, max_width: int = MAX_WIDTH, max_height: int = MAX_HEIGHT) -> Tuple[int, int]:
    """
    Calculate new dimensions while maintaining aspect ratio.
    """
    if width <= max_width and height <= max_height:
        return width, height
        
    aspect_ratio = width / height
    if width > height:
        new_width = max_width
        new_height = int(max_width / aspect_ratio)
    else:
        new_height = max_height
        new_width = int(max_height * aspect_ratio)
        
    return new_width, new_height

def prepare_images(directory):
    global images_to_iterate, image_index
    try:
        # Define the image file extensions to match
        images_to_iterate = []
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.tiff", "*.heic", "*.mp4"]
        
        # Search for each extension and add them to our list
        for ext in image_extensions:
            images_to_iterate.extend(Path(directory).rglob(ext))
        image_index = 0
        
        if not images_to_iterate:
            messagebox.showinfo("No Media", "No images or videos found in the specified directory.")
    except Exception as e:
        messagebox.showerror("Error", f"Could not prepare media: {e}")
        
def show_prev(event=None):
    global current_image_path, image_index, video_capture, stop_video

    stop_video_playback()  # Stop any video currently playing

    if images_to_iterate:
        if image_index < len(images_to_iterate) and image_index > 0:
            image_index -= 1
            current_image_path = images_to_iterate[image_index]
            debug_label.config(text=f"File: {current_image_path}")
            if current_image_path.suffix.lower() == '.mp4':
                load_video(current_image_path)
            else:
                img = load_image(current_image_path)
                if img:
                    image_label.config(image=img)
                    image_label.image = img
            
            save_tally()
        else:
            messagebox.showinfo("End of Media", "No more images or videos to display.")
    else:
        messagebox.showwarning("No Media", "No images or videos loaded. Use the 'Prepare Images' button.")

def show_next(event=None):
    global current_image_path, image_index, video_capture, stop_video

    stop_video_playback()  # Stop any video currently playing

    if images_to_iterate:
        if image_index + 1 < len(images_to_iterate):
            image_index += 1
            current_image_path = images_to_iterate[image_index]
            debug_label.config(text=f"File: {current_image_path}")
            if current_image_path.suffix.lower() == '.mp4':
                load_video(current_image_path)
            else:
                img = load_image(current_image_path)
                if img:
                    image_label.config(image=img)
                    image_label.image = img
            
            save_tally()
        else:
            messagebox.showinfo("End of Media", "No more images or videos to display.")
    else:
        messagebox.showwarning("No Media", "No images or videos loaded. Use the 'Prepare Images' button.")

def delete_current_image(event):
    global current_image_path, files_deleted, file_sizes

    if current_image_path and current_image_path.exists():
        try:
            
            # Use resolved path for reliability
            resolved_path = current_image_path.resolve()

            if resolved_path.suffix.lower() == '.mp4' and video_capture:
                    video_capture.release()  # Release the video file before deletion

             # Add to sizes dashboard and save to tally
            file_sizes += resolved_path.stat().st_size
            files_deleted += 1
            files_deleted_label.config(text=f"Files deleted: {files_deleted} Space Saved: {file_sizes / (1024) :.2f} bytes, {file_sizes / (1024*1024*1024) :.2f}GB")
            save_tally()
            
            # Delete the file
            resolved_path.unlink()
            status_label.config(text=f"Deleted file: {resolved_path}")
            
            # Reset the current image
            current_image_path = None
            image_label.config(image="")
            image_label.image = None
            
            # Show next image or video
            show_next()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete file: {e}")
    else:
        messagebox.showwarning("No File", "No image or video is currently loaded or file does not exist.")

def load_video(video_path):
    global video_capture, stop_video
    try:
        stop_video = False
        video_capture = cv2.VideoCapture(video_path)
        play_video()
    except Exception as e:
        messagebox.showerror("Error", f"Could not load video: {e}")

def play_video():
    global video_capture, stop_video

    if stop_video or not video_capture or not video_capture.isOpened():
        return

    ret, frame = video_capture.read()
    if not ret:
        stop_video_playback()
        return
    
    # Get the original width and height of the frame and resize to fit our max with aspect ratio
    original_height, original_width = frame.shape[:2]
    new_width, new_height = calculate_new_dimensions(original_width, original_height)

    # Resize the frame
    frame = cv2.resize(frame, (new_width, new_height))

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.resize(frame, (new_width, new_height))
    img = ImageTk.PhotoImage(Image.fromarray(frame))
    image_label.config(image=img)
    image_label.image = img

    root.after(30, play_video)  # Schedule the next frame after 30ms

def stop_video_playback():
    global stop_video, video_capture
    stop_video = True
    if video_capture:
        video_capture.release()


# Create the main application window
root = tk.Tk()
root.title("PhotoandVideoDeletinator")

# Create input label and entry
input_label = ttk.Label(root, text="Press D to delete an image, or K to advance to the next image: ")
input_label.pack(pady=10)

# Prepare all images in directory and sub-directories
prepare_images(directory=directory)
read_tally()

# Label to display the image
image_label = ttk.Label(root)
image_label.pack(pady=20)

status_label = ttk.Label(root, text="File viewing.")
status_label.pack(pady=10)

debug_label = ttk.Label(root, text=f"File: {current_image_path}")
debug_label.pack(pady=10)

files_deleted_label = ttk.Label(root, text=f"Files deleted: {files_deleted} Space Saved: {file_sizes / (1024) :.2f} bytes, {file_sizes / (1024*1024*1024) :.2f}GB")
files_deleted_label.pack(pady=10)

copyright = ttk.Label(root, text="Copyright Matyas Negash - 2024.")
copyright.pack(pady=10)

# Show the next image
show_next()

# Bind the 'D' key to delete the current image
root.bind("<d>", delete_current_image)

# Bind the 'Right' key to show the next image
root.bind("<Right>", show_next)

# Bind the 'Right' key to show the next image
root.bind("<Left>", show_prev)

# Ensure video playback stops when the program exits
root.protocol("WM_DELETE_WINDOW", lambda: (stop_video_playback(), root.destroy()))

# Run the application
root.mainloop()
