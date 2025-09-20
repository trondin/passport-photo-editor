import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os

# Configurable parameters
TARGET_WIDTH = 500
TARGET_HEIGHT = 653
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 1000
FRAME_OFFSET_X = (WINDOW_WIDTH - TARGET_WIDTH) // 2
FRAME_OFFSET_Y = 50

LONG_HORIZ_WIDTH_PERCENT = 0.8
LONG_HORIZ_TOP_Y = FRAME_OFFSET_Y + 56
LONG_HORIZ_BOTTOM_Y = FRAME_OFFSET_Y + TARGET_HEIGHT - 96

SHORT_HORIZ_WIDTH_PERCENT = 0.6
SHORT_HORIZ_OFFSET = 28

VERT_LINES_GAP = 40
VERT_LINES_SHORTEN = 28

CONFIG_FILE = "last_dir.txt"
MAX_RENDER_SIZE = 1600  # Reduced for better performance without visible quality loss
HIGH_QUALITY_SIZE = 4000  # For final saving

class PhotoEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Passport Photo Editor")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        self.image = None
        self.original_image = None  # Keep original image for quality preservation
        self.display_image = None   # Image for display purposes
        self.tk_image = None
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.dragging = False
        self.start_x = 0
        self.start_y = 0
        self.rotation = 0
        self.last_render_size = (0, 0)  # Cache last render size
        self.filename = None  # Store the loaded filename

        # Canvas
        self.canvas = tk.Canvas(root, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Menu
        menubar = tk.Menu(root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open", command=self.load_image)
        filemenu.add_command(label="Save", command=self.save_image)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        imagemenu = tk.Menu(menubar, tearoff=0)
        imagemenu.add_command(label="Rotate Left", command=lambda: self.rotate(-90))
        imagemenu.add_command(label="Rotate Right", command=lambda: self.rotate(90))
        menubar.add_cascade(label="Image", menu=imagemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help", command=self.show_help)
        menubar.add_cascade(label="Help", menu=helpmenu)

        root.config(menu=menubar)

        # Bindings
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)
        # Cross-platform scroll bindings
        self.canvas.bind("<MouseWheel>", self.do_zoom)  # Windows
        self.canvas.bind("<Button-4>", lambda event: self.do_zoom(event, delta=120))  # Linux/macOS scroll up
        self.canvas.bind("<Button-5>", lambda event: self.do_zoom(event, delta=-120))  # Linux/macOS scroll down

        self.draw_frame()

    def show_help(self):
        help_text = (
            "Passport Photo Editor Help\n\n"
            "1. Open an image: Use 'File -> Open' to select an image (.jpg, .jpeg, .png, .bmp).\n"
            "2. Adjust the image:\n"
            "   - Drag the image with the left mouse button to reposition.\n"
            "   - Use the mouse wheel (or scroll up/down on touchpad) for smooth zoom.\n"
            "   - Hold Ctrl while using the mouse wheel for coarser zoom.\n"
            "   - Use 'Image -> Rotate Left/Right' to rotate the image.\n"
            "3. Save the image: Use 'File -> Save' to crop and save the image within the frame.\n"
            "4. The frame shows the target area for the passport photo (500x653 pixels).\n"
            "5. The saved image is stored with '_passi' appended to the original filename in the same directory."
        )
        messagebox.showinfo("Help", help_text)

    def get_last_dir(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return f.read().strip()
            except:
                return os.getcwd()
        return os.getcwd()

    def save_last_dir(self, path):
        try:
            with open(CONFIG_FILE, "w") as f:
                f.write(path)
        except:
            pass

    def load_image(self):
        initial_dir = self.get_last_dir()
        filename = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.bmp *.JPG *.JPEG *.PNG *.BMP"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.save_last_dir(os.path.dirname(filename))
            self.filename = filename  # Store the loaded filename
            # Load image without immediate processing
            self.original_image = Image.open(filename)
            self.image = self.original_image.copy()
            self.rotation = 0
            self.zoom = 1.0
            self.offset_x = 0
            self.offset_y = 0

            # Create display image with optimal size
            self._create_display_image()
            self.update_canvas()

    def _create_display_image(self):
        """Create optimized image for display purposes"""
        if not self.image:
            return
            
        w, h = self.image.size
        # Calculate scale to fit within MAX_RENDER_SIZE while maintaining aspect ratio
        scale = min(MAX_RENDER_SIZE / w, MAX_RENDER_SIZE / h, 1.0)
        new_size = (int(w * scale), int(h * scale))
        
        if new_size != self.last_render_size:
            self.display_image = self.image.resize(new_size, Image.LANCZOS)
            self.last_render_size = new_size

    def rotate(self, angle):
        if self.image and self.original_image:
            self.rotation = (self.rotation + angle) % 360
            # Rotate the original image for best quality
            self.image = self.original_image.rotate(self.rotation, expand=True)
            self._create_display_image()
            self.update_canvas()

    def start_drag(self, event):
        self.dragging = True
        self.start_x = event.x
        self.start_y = event.y

    def do_drag(self, event):
        if self.dragging and self.image:
            dx = event.x - self.start_x
            dy = event.y - self.start_y
            self.offset_x += dx
            self.offset_y += dy
            self.start_x = event.x
            self.start_y = event.y
            self.update_canvas()

    def stop_drag(self, event):
        self.dragging = False

    def do_zoom(self, event, delta=None):
        if not self.image:
            return
            
        # Determine delta
        if delta is None:
            delta = event.delta

        # Check if Ctrl is pressed
        ctrl_pressed = (event.state & 0x0004) != 0  # Control mask

        # Determine factor
        if delta > 0:
            factor = 1.1 if ctrl_pressed else 1.02
        else:
            factor = 0.9 if ctrl_pressed else 0.98

        old_zoom = self.zoom
        self.zoom = max(0.1, min(self.zoom * factor, 5.0))  # Reduced max zoom to 5.0

        # Adjust offset to zoom towards cursor position
        cursor_x = event.x - FRAME_OFFSET_X
        cursor_y = event.y - FRAME_OFFSET_Y
        
        # Calculate image position relative to cursor
        img_x = cursor_x - self.offset_x
        img_y = cursor_y - self.offset_y
        
        # Adjust offset based on zoom change
        self.offset_x = cursor_x - img_x * (self.zoom / old_zoom)
        self.offset_y = cursor_y - img_y * (self.zoom / old_zoom)

        self.update_canvas()

    def update_canvas(self):
        self.canvas.delete("all")
        if self.display_image:
            w, h = self.display_image.size
            # Only resize if necessary
            new_w, new_h = int(w * self.zoom), int(h * self.zoom)
            
            # Use faster resampling during interaction
            resample = Image.NEAREST if self.dragging else Image.LANCZOS
            resized = self.display_image.resize((new_w, new_h), resample)
            
            self.tk_image = ImageTk.PhotoImage(resized)
            self.canvas.create_image(
                FRAME_OFFSET_X + self.offset_x,
                FRAME_OFFSET_Y + self.offset_y,
                anchor="nw",
                image=self.tk_image
            )
        self.draw_frame()

    def draw_frame(self):
        # Frame
        self.canvas.create_rectangle(FRAME_OFFSET_X, FRAME_OFFSET_Y,
                                     FRAME_OFFSET_X + TARGET_WIDTH, FRAME_OFFSET_Y + TARGET_HEIGHT,
                                     outline="black")

        # Lines
        long_horiz_length = int(TARGET_WIDTH * LONG_HORIZ_WIDTH_PERCENT)
        long_horiz_top_x = FRAME_OFFSET_X + (TARGET_WIDTH - long_horiz_length) // 2
        long_horiz_bottom_x = long_horiz_top_x

        short_horiz_length = int(TARGET_WIDTH * SHORT_HORIZ_WIDTH_PERCENT)
        short_horiz_top_x = FRAME_OFFSET_X + (TARGET_WIDTH - short_horiz_length) // 2
        short_horiz_top_y = LONG_HORIZ_TOP_Y + SHORT_HORIZ_OFFSET
        short_horiz_bottom_x = short_horiz_top_x
        short_horiz_bottom_y = LONG_HORIZ_BOTTOM_Y - SHORT_HORIZ_OFFSET

        vert_left_x = FRAME_OFFSET_X + (TARGET_WIDTH - VERT_LINES_GAP) // 2
        vert_right_x = vert_left_x + VERT_LINES_GAP
        vert_top_y = short_horiz_top_y + VERT_LINES_SHORTEN
        vert_bottom_y = short_horiz_bottom_y - VERT_LINES_SHORTEN

        self.canvas.create_line(long_horiz_top_x, LONG_HORIZ_TOP_Y,
                                long_horiz_top_x + long_horiz_length, LONG_HORIZ_TOP_Y,
                                fill="red", width=2)
        self.canvas.create_line(long_horiz_bottom_x, LONG_HORIZ_BOTTOM_Y,
                                long_horiz_bottom_x + long_horiz_length, LONG_HORIZ_BOTTOM_Y,
                                fill="red", width=2)
        self.canvas.create_line(short_horiz_top_x, short_horiz_top_y,
                                short_horiz_top_x + short_horiz_length, short_horiz_top_y,
                                fill="red", width=2)
        self.canvas.create_line(short_horiz_bottom_x, short_horiz_bottom_y,
                                short_horiz_bottom_x + short_horiz_length, short_horiz_bottom_y,
                                fill="red", width=2)
        self.canvas.create_line(vert_left_x, vert_top_y,
                                vert_left_x, vert_bottom_y,
                                fill="red", width=2)
        self.canvas.create_line(vert_right_x, vert_top_y,
                                vert_right_x, vert_bottom_y,
                                fill="red", width=2)

    def save_image(self):
        if not self.image or not self.filename:
            messagebox.showerror("Error", "No image to save")
            return

        # Calculate crop coordinates based on original image size
        orig_w, orig_h = self.image.size
        disp_w, disp_h = self.display_image.size if self.display_image else (1, 1)
        
        # Calculate scale factor between original and display image
        scale_x = orig_w / disp_w
        scale_y = orig_h / disp_h
        
        # Calculate crop area in original image coordinates
        crop_x = max(0, (-self.offset_x / self.zoom) * scale_x)
        crop_y = max(0, (-self.offset_y / self.zoom) * scale_y)
        crop_width = (TARGET_WIDTH / self.zoom) * scale_x
        crop_height = (TARGET_HEIGHT / self.zoom) * scale_y
        
        crop_right = min(orig_w, crop_x + crop_width)
        crop_bottom = min(orig_h, crop_y + crop_height)

        if crop_x >= crop_right or crop_y >= crop_bottom:
            messagebox.showerror("Error", "Crop area is invalid")
            return

        try:
            # Crop from the rotated image (which is from original)
            cropped = self.image.crop((crop_x, crop_y, crop_right, crop_bottom))
            
            # Only resize if necessary to avoid quality loss
            if cropped.size != (TARGET_WIDTH, TARGET_HEIGHT):
                cropped = cropped.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS)
                
            # Generate output filename with '_passi' appended
            base, ext = os.path.splitext(self.filename)
            output_path = f"{base}_passi{ext}"
            
            cropped.save(output_path, "JPEG", quality=95)
            messagebox.showinfo("Saved", f"Photo saved as {output_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoEditor(root)
    root.mainloop()
