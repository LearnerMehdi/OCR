"""
Advanced OCR Result Viewer using Tkinter
Professional GUI with search, filter, and export capabilities
Enhanced with RGB/Grayscale image support
"""

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import argparse


class OCRViewerTkinter:
    def __init__(self, master, image_path, json_path, model: str = "paddle"):
        """Initialize the Tkinter OCR viewer"""
        self.model = model
        
        self.master = master
        self.master.title("OCR Result Viewer - Advanced")
        self.master.geometry("1400x900")
        
        # Load data
        self.image_path = image_path
        original_loaded = Image.open(image_path)
        
        # Detect and handle image mode (RGB/Grayscale flexibility)
        self.original_mode = original_loaded.mode
        self.is_grayscale_source = self.original_mode in ('L', 'LA')
        
        # Normalize to RGB for consistent processing
        if self.original_mode != 'RGB':
            print(f"[INFO] Converting image from {self.original_mode} to RGB mode")
            self.original_image = original_loaded.convert('RGB')
            self.converted = True
        else:
            self.original_image = original_loaded
            self.converted = False
        
        self.display_image = self.original_image.copy()
        
        with open(json_path, 'r', encoding='utf-8') as f:
            self.ocr_data = json.load(f)[0]

        if model == "paddle":
            self.dt_polys = self.ocr_data['dt_polys']
            self.rec_texts = self.ocr_data['rec_texts']

        elif model == "structure":
            self.dt_polys = self.ocr_data["overall_ocr_res"]["dt_polys"]
            self.rec_texts = self.ocr_data["overall_ocr_res"]["rec_texts"]

        
        # State variables
        self.zoom_level = 1.0
        self.show_boxes = tk.BooleanVar(value=True)
        self.show_text = tk.BooleanVar(value=False)
        self.current_hover_idx = None
        self.hidden_boxes = set()
        self.search_results = []
        self.current_search_idx = 0
        
        # Colors for boxes
        self.colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788'
        ]
        
        self._create_ui()
        self._update_display()
    
    def _create_ui(self):
        """Create the user interface"""
        # Main container
        main_container = ttk.Frame(self.master)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Controls
        left_panel = ttk.Frame(main_container, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        # Right panel - Image display
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # === LEFT PANEL CONTENTS ===
        
        # Title
        title_label = ttk.Label(left_panel, text="OCR Analysis Tools", 
                               font=('Helvetica', 14, 'bold'))
        title_label.pack(pady=10)
        
        # Image info frame
        info_frame = ttk.LabelFrame(left_panel, text="Image Information", padding=10)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text=f"Original Mode: {self.original_mode}",
                 font=('Helvetica', 9)).pack(anchor=tk.W)
        
        if self.converted:
            ttk.Label(info_frame, text="✓ Converted to RGB",
                     font=('Helvetica', 9), foreground='green').pack(anchor=tk.W)
        
        ttk.Label(info_frame, text=f"Size: {self.original_image.size}",
                 font=('Helvetica', 9)).pack(anchor=tk.W)
        
        # Statistics
        stats_frame = ttk.LabelFrame(left_panel, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(stats_frame, text=f"Total Boxes: {len(self.dt_polys)}",
                 font=('Helvetica', 10, 'bold')).pack(anchor=tk.W)
        
        # Display options
        display_frame = ttk.LabelFrame(left_panel, text="Display Options", padding=10)
        display_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(display_frame, text="Show Bounding Boxes", 
                       variable=self.show_boxes,
                       command=self._update_display).pack(anchor=tk.W)
        
        ttk.Checkbutton(display_frame, text="Show Text on Image", 
                       variable=self.show_text,
                       command=self._update_display).pack(anchor=tk.W)
        
        # Zoom controls
        zoom_frame = ttk.LabelFrame(left_panel, text="Zoom", padding=10)
        zoom_frame.pack(fill=tk.X, pady=5)
        
        zoom_buttons = ttk.Frame(zoom_frame)
        zoom_buttons.pack(fill=tk.X)
        
        ttk.Button(zoom_buttons, text="−", width=3,
                  command=lambda: self._zoom(0.8)).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_buttons, text="+", width=3,
                  command=lambda: self._zoom(1.25)).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_buttons, text="Reset", width=8,
                  command=lambda: self._zoom(1.0, reset=True)).pack(side=tk.LEFT, padx=2)
        
        self.zoom_label = ttk.Label(zoom_frame, text=f"Zoom: {self.zoom_level:.0%}")
        self.zoom_label.pack(pady=5)
        
        # Search functionality
        search_frame = ttk.LabelFrame(left_panel, text="Search Text", padding=10)
        search_frame.pack(fill=tk.X, pady=5)
        
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(fill=tk.X, pady=(0, 5))
        self.search_entry.bind('<Return>', lambda e: self._search_text())
        
        search_buttons = ttk.Frame(search_frame)
        search_buttons.pack(fill=tk.X)
        
        ttk.Button(search_buttons, text="Search", 
                  command=self._search_text).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_buttons, text="Next", 
                  command=self._next_search).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_buttons, text="Clear", 
                  command=self._clear_search).pack(side=tk.LEFT, padx=2)
        
        self.search_result_label = ttk.Label(search_frame, text="")
        self.search_result_label.pack(pady=5)
        
        # Text list box
        list_frame = ttk.LabelFrame(left_panel, text="Recognized Texts", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox
        self.text_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                       font=('Courier', 9))
        self.text_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_listbox.yview)
        
        # Populate listbox
        for idx, text in enumerate(self.rec_texts, 1):
            self.text_listbox.insert(tk.END, f"{idx:3d}. {text[:50]}")
        
        self.text_listbox.bind('<<ListboxSelect>>', self._on_listbox_select)
        
        # Action buttons
        action_frame = ttk.Frame(left_panel)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="Export Text List",
                  command=self._export_text).pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text="Reset View",
                  command=self._reset_view).pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text="Save Image",
                  command=self._save_image).pack(fill=tk.X, pady=2)
        
        # === RIGHT PANEL CONTENTS ===
        
        # Canvas with scrollbars
        canvas_frame = ttk.Frame(right_panel)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbars
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas
        self.canvas = tk.Canvas(canvas_frame, 
                               xscrollcommand=h_scrollbar.set,
                               yscrollcommand=v_scrollbar.set,
                               bg='gray80')
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        h_scrollbar.config(command=self.canvas.xview)
        v_scrollbar.config(command=self.canvas.yview)
        
        # Bind mouse events
        self.canvas.bind('<Motion>', self._on_canvas_motion)
        self.canvas.bind('<Button-1>', self._on_canvas_click)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        
        # Tooltip label
        self.tooltip = tk.Label(self.master, text="", bg='yellow', 
                               relief=tk.SOLID, borderwidth=1,
                               font=('Helvetica', 10, 'bold'), padx=5, pady=5)
        self.tooltip.place_forget()
    
    def _update_display(self):
        """Update the image display with current settings"""
        # Create a fresh copy
        img = self.original_image.copy()
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Try to load a font, fallback to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        if self.show_boxes.get():
            for idx, poly in enumerate(self.dt_polys):
                if idx in self.hidden_boxes:
                    continue
                
                # Get color
                color = self.colors[idx % len(self.colors)]
                
                # Highlight if searching
                if idx in self.search_results:
                    color = '#FFD700'  # Gold for search results
                    line_width = 4
                else:
                    line_width = 2
                
                # Convert hex to RGB with alpha
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                
                # Draw filled polygon
                draw.polygon(poly, fill=(r, g, b, 50), outline=(r, g, b, 200), width=line_width)
                
                # Draw text if enabled
                if self.show_text.get():
                    # Calculate center of polygon
                    xs = [p[0] for p in poly]
                    ys = [p[1] for p in poly]
                    center_x = sum(xs) / len(xs)
                    center_y = sum(ys) / len(ys)
                    
                    text = self.rec_texts[idx][:20]  # Limit text length
                    draw.text((center_x, center_y), text, fill='red', font=font)
        
        # Apply zoom
        if self.zoom_level != 1.0:
            new_size = (int(img.width * self.zoom_level), 
                       int(img.height * self.zoom_level))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(img)
        
        # Update canvas
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        
        self.display_image = img
    
    def _zoom(self, factor, reset=False):
        """Zoom in or out"""
        if reset:
            self.zoom_level = 1.0
        else:
            self.zoom_level *= factor
            self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        
        self.zoom_label.config(text=f"Zoom: {self.zoom_level:.0%}")
        self._update_display()
    
    def _on_canvas_motion(self, event):
        """Handle mouse motion on canvas"""
        # Get canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert to image coordinates
        img_x = canvas_x / self.zoom_level
        img_y = canvas_y / self.zoom_level
        
        # Check if mouse is over any polygon
        hover_idx = None
        for idx, poly in enumerate(self.dt_polys):
            if idx in self.hidden_boxes:
                continue
            
            if self._point_in_polygon(img_x, img_y, poly):
                hover_idx = idx
                break
        
        if hover_idx is not None:
            # Show tooltip with text when over a text region
            text = self.rec_texts[hover_idx]
            self.tooltip.config(text=f"Box {hover_idx + 1}: {text}")
            
            # Position tooltip near cursor
            x = event.x_root + 20
            y = event.y_root + 10
            self.tooltip.place(x=x - self.master.winfo_rootx(), 
                             y=y - self.master.winfo_rooty())
            
            # Highlight in listbox
            self.text_listbox.selection_clear(0, tk.END)
            self.text_listbox.selection_set(hover_idx)
            self.text_listbox.see(hover_idx)
            
            self.current_hover_idx = hover_idx
        else:
            # Show coordinates when outside text regions
            # Convert to integer coordinates for display
            coord_x = int(img_x)
            coord_y = int(img_y)
            self.tooltip.config(text=f"x: {coord_x}, y: {coord_y}")
            
            # Position tooltip near cursor
            x = event.x_root + 20
            y = event.y_root + 10
            self.tooltip.place(x=x - self.master.winfo_rootx(), 
                             y=y - self.master.winfo_rooty())
            
            # Clear listbox selection when outside text regions
            if self.current_hover_idx is not None:
                self.text_listbox.selection_clear(0, tk.END)
                self.current_hover_idx = None
    
    def _on_canvas_click(self, event):
        """Handle mouse click on canvas"""
        # Get image coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = canvas_x / self.zoom_level
        img_y = canvas_y / self.zoom_level
        
        # Check which box was clicked
        for idx, poly in enumerate(self.dt_polys):
            if self._point_in_polygon(img_x, img_y, poly):
                # Toggle box visibility
                if idx in self.hidden_boxes:
                    self.hidden_boxes.remove(idx)
                else:
                    self.hidden_boxes.add(idx)
                self._update_display()
                break
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel for zooming"""
        if event.delta > 0:
            self._zoom(1.1)
        else:
            self._zoom(0.9)
    
    def _point_in_polygon(self, x, y, polygon):
        """Check if point (x, y) is inside polygon"""
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _on_listbox_select(self, event):
        """Handle listbox selection"""
        selection = self.text_listbox.curselection()
        if selection:
            idx = selection[0]
            # You could highlight this box or zoom to it
            # For now, just show it in tooltip
            text = self.rec_texts[idx]
            messagebox.showinfo("Box Content", f"Box {idx + 1}:\n\n{text}")
    
    def _search_text(self):
        """Search for text in recognized texts"""
        query = self.search_entry.get().lower().strip()
        if not query:
            return
        
        self.search_results = []
        for idx, text in enumerate(self.rec_texts):
            if query in text.lower():
                self.search_results.append(idx)
        
        self.current_search_idx = 0
        
        if self.search_results:
            self.search_result_label.config(
                text=f"Found {len(self.search_results)} match(es)")
            self._highlight_search_result()
        else:
            self.search_result_label.config(text="No matches found")
        
        self._update_display()
    
    def _next_search(self):
        """Go to next search result"""
        if not self.search_results:
            return
        
        self.current_search_idx = (self.current_search_idx + 1) % len(self.search_results)
        self._highlight_search_result()
    
    def _highlight_search_result(self):
        """Highlight current search result"""
        if not self.search_results:
            return
        
        idx = self.search_results[self.current_search_idx]
        
        # Update listbox
        self.text_listbox.selection_clear(0, tk.END)
        self.text_listbox.selection_set(idx)
        self.text_listbox.see(idx)
        
        # Update label
        self.search_result_label.config(
            text=f"Match {self.current_search_idx + 1} of {len(self.search_results)}")
    
    def _clear_search(self):
        """Clear search results"""
        self.search_results = []
        self.current_search_idx = 0
        self.search_entry.delete(0, tk.END)
        self.search_result_label.config(text="")
        self._update_display()
    
    def _reset_view(self):
        """Reset all view settings"""
        self.zoom_level = 1.0
        self.hidden_boxes.clear()
        self.search_results = []
        self.show_boxes.set(True)
        self.show_text.set(False)
        self.zoom_label.config(text=f"Zoom: {self.zoom_level:.0%}")
        self._update_display()
        messagebox.showinfo("Reset", "View has been reset")
    
    def _export_text(self):
        """Export text list to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="ocr_text_list.txt"
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("OCR Recognition Results\n")
                f.write("=" * 80 + "\n")
                f.write(f"Source Image: {self.image_path}\n")
                f.write(f"Image Mode: {self.original_mode}\n")
                if self.converted:
                    f.write("Note: Image was converted from {} to RGB for processing\n".format(self.original_mode))
                f.write("=" * 80 + "\n\n")
                for idx, text in enumerate(self.rec_texts, 1):
                    f.write(f"Box {idx:4d}: {text}\n")
            messagebox.showinfo("Export", f"Text list exported to:\n{filename}")
    
    def _save_image(self):
        """Save current view as image"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            initialfile="ocr_annotated.png"
        )
        
        if filename:
            # Optionally convert back to original mode before saving
            save_img = self.display_image
            
            # If user wants to preserve original grayscale format
            if self.is_grayscale_source and filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                # Ask user preference
                result = messagebox.askyesno(
                    "Save Format",
                    f"Original image was grayscale ({self.original_mode}).\n\n"
                    "Save as RGB (with colored annotations)?\n"
                    "Click 'No' to convert back to grayscale."
                )
                if not result:
                    # Convert back to grayscale
                    save_img = save_img.convert('L')
            
            save_img.save(filename)
            messagebox.showinfo("Save", f"Image saved to:\n{filename}")


def main():
    parser = argparse.ArgumentParser(description='Advanced OCR Result Viewer (Tkinter) - Enhanced with RGB/Grayscale support')
    parser.add_argument('--image', '-i', required=True, help='Path to the image file (RGB or Grayscale)')
    parser.add_argument('--json', '-j', required=True, help='Path to the OCR JSON results file')
    parser.add_argument('--model', '-m', default='paddle', help='model to select')
    args = parser.parse_args()
    
    root = tk.Tk()
    app = OCRViewerTkinter(root, args.image, args.json, args.model)
    root.mainloop()


if __name__ == '__main__':
    main()
