import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from folium.vector_layers import PolyLine
import io
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import sys
import tempfile
import webbrowser
from tkinterhtml import HtmlFrame  # Alternative approach

# Constants
EARTH_RADIUS_KM = 6371
MAP_TYPES = {
    "Default Markers": "markers",
    "Heatmap": "heatmap",
    "Connected Wireframe": "wireframe",
    "Cluster Markers": "clusters"
}

class CustomerMappingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Customer Mapping Tool")
        self.root.geometry("1200x800")
        
        # Data storage
        self.customer_df = None
        self.butcher_df = None
        self.distance_df = None
        self.current_map = None
        self.temp_html = tempfile.NamedTemporaryFile(suffix=".html", delete=False).name
        self.current_map_type = "markers"
        
        # Create tabs
        self.tab_control = ttk.Notebook(root)
        
        # Customer Map Tab
        self.tab_map = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_map, text='Customer Map')
        
        # Butcher Distance Tab
        self.tab_distance = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_distance, text='Butcher Distances')
        
        # Insights Tab
        self.tab_insights = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_insights, text='Customer Insights')
        
        self.tab_control.pack(expand=1, fill="both")
        
        # Initialize tabs
        self.setup_map_tab()
        self.setup_distance_tab()
        self.setup_insights_tab()
    
    def setup_map_tab(self):
        # Map Frame
        map_frame = ttk.LabelFrame(self.tab_map, text="Customer Location Mapping")
        map_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Control Panel
        control_frame = ttk.Frame(map_frame)
        control_frame.pack(fill="x", pady=5)
        
        # Upload Customer Data Button
        btn_upload_customers = ttk.Button(
            control_frame, 
            text="Upload Customer Data", 
            command=self.load_customer_data
        )
        btn_upload_customers.pack(side="left", padx=5)
        
        # Upload Butcher Data Button
        btn_upload_butchers = ttk.Button(
            control_frame, 
            text="Upload Butcher Data", 
            command=self.load_butcher_data
        )
        btn_upload_butchers.pack(side="left", padx=5)
        
        # Map Type Dropdown
        self.map_type_var = tk.StringVar(value="Default Markers")
        map_type_menu = ttk.OptionMenu(
            control_frame,
            self.map_type_var,
            "Default Markers",
            *MAP_TYPES.keys(),
            command=self.change_map_type
        )
        map_type_menu.pack(side="left", padx=5)
        
        # Export Map Button
        btn_export_map = ttk.Button(
            control_frame, 
            text="Export Map as Image", 
            command=self.export_map_image
        )
        btn_export_map.pack(side="left", padx=5)
        
        # Open in Browser Button
        btn_open_browser = ttk.Button(
            control_frame,
            text="Open in Browser",
            command=self.open_in_browser
        )
        btn_open_browser.pack(side="left", padx=5)
        
        # Map Display Frame
        self.map_display_frame = ttk.Frame(map_frame)
        self.map_display_frame.pack(fill="both", expand=True)
        
        # Create HTML frame for map display
        self.html_frame = HtmlFrame(self.map_display_frame)
        self.html_frame.pack(fill="both", expand=True)
        
        # Status Label
        self.status_label = ttk.Label(map_frame, text="Upload customer data to begin")
        self.status_label.pack(fill="x")
    
    def open_in_browser(self):
        if hasattr(self, 'temp_html') and self.temp_html:
            webbrowser.open('file://' + os.path.abspath(self.temp_html))
    
    def change_map_type(self, *args):
        self.current_map_type = MAP_TYPES[self.map_type_var.get()]
        if self.customer_df is not None:
            self.plot_customer_map()
    
    def setup_distance_tab(self):
        # Distance Analysis Frame
        distance_frame = ttk.LabelFrame(self.tab_distance, text="Customer-Butcher Distance Analysis")
        distance_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Calculate Button
        btn_calculate = ttk.Button(
            distance_frame, 
            text="Calculate Distances", 
            command=self.calculate_distances
        )
        btn_calculate.pack(pady=5)
        
        # Export Button
        btn_export_distances = ttk.Button(
            distance_frame, 
            text="Export Distance Matrix", 
            command=self.export_distance_matrix
        )
        btn_export_distances.pack(pady=5)
        
        # Treeview for displaying distances
        self.distance_tree = ttk.Treeview(distance_frame)
        self.distance_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add scrollbars
        y_scroll = ttk.Scrollbar(distance_frame, orient="vertical", command=self.distance_tree.yview)
        y_scroll.pack(side="right", fill="y")
        x_scroll = ttk.Scrollbar(distance_frame, orient="horizontal", command=self.distance_tree.xview)
        x_scroll.pack(side="bottom", fill="x")
        
        self.distance_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
    
    def setup_insights_tab(self):
        # Insights Frame
        insights_frame = ttk.LabelFrame(self.tab_insights, text="Customer Base Insights")
        insights_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Generate Insights Button
        btn_generate = ttk.Button(
            insights_frame, 
            text="Generate Insights", 
            command=self.generate_insights
        )
        btn_generate.pack(pady=5)
        
        # Canvas for plots
        self.insights_canvas = tk.Canvas(insights_frame, bg="white")
        self.insights_canvas.pack(fill="both", expand=True)
        
        # Text widget for insights
        self.insights_text = tk.Text(insights_frame, height=10, wrap=tk.WORD)
        self.insights_text.pack(fill="x", pady=5)
    
    def safe_convert(self, value):
        """Safely convert values to float, handling various edge cases"""
        if pd.isna(value):
            return None
        try:
            # Handle percentage signs, commas, etc.
            if isinstance(value, str):
                value = value.replace('%', '').replace(',', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def load_customer_data(self):
        file_path = filedialog.askopenfilename(
            title="Select Customer Data File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            # Read file
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Check required columns
            required = {'customer_id', 'latitude', 'longitude'}
            missing = required - set(df.columns)
            
            if missing:
                messagebox.showerror(
                    "Missing Columns",
                    f"These required columns are missing: {', '.join(missing)}\n"
                    f"Available columns: {', '.join(df.columns)}"
                )
                return
            
            # Convert coordinates
            df['latitude'] = df['latitude'].apply(self.safe_convert)
            df['longitude'] = df['longitude'].apply(self.safe_convert)
            
            # Remove invalid rows
            initial_count = len(df)
            df = df.dropna(subset=['latitude', 'longitude'])
            final_count = len(df)
            
            if final_count == 0:
                messagebox.showerror(
                    "No Valid Data",
                    "No rows with valid latitude/longitude values found"
                )
                return
            
            self.customer_df = df
            
            # Update status
            msg = f"Loaded {final_count} customer records"
            if final_count < initial_count:
                msg += f" (dropped {initial_count-final_count} invalid records)"
            self.status_label.config(text=msg)
            
            self.plot_customer_map()
            
        except Exception as e:
            messagebox.showerror(
                "Loading Error",
                f"Could not load file:\n{str(e)}"
            )
            self.status_label.config(text="Error loading customer data")
    
    def load_butcher_data(self):
        file_path = filedialog.askopenfilename(
            title="Select Butcher Data File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            # Read file
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Check required columns
            required = {'butcher_id', 'latitude', 'longitude'}
            missing = required - set(df.columns)
            
            if missing:
                messagebox.showerror(
                    "Missing Columns",
                    f"These required columns are missing: {', '.join(missing)}\n"
                    f"Available columns: {', '.join(df.columns)}"
                )
                return
            
            # Convert coordinates
            df['latitude'] = df['latitude'].apply(self.safe_convert)
            df['longitude'] = df['longitude'].apply(self.safe_convert)
            
            # Remove invalid rows
            initial_count = len(df)
            df = df.dropna(subset=['latitude', 'longitude'])
            final_count = len(df)
            
            if final_count == 0:
                messagebox.showerror(
                    "No Valid Data",
                    "No rows with valid latitude/longitude values found"
                )
                return
            
            self.butcher_df = df
            
            # Update status
            msg = f"Loaded {final_count} butcher records"
            if final_count < initial_count:
                msg += f" (dropped {initial_count-final_count} invalid records)"
            self.status_label.config(text=msg)
            
            self.plot_customer_map()
            
        except Exception as e:
            messagebox.showerror(
                "Loading Error",
                f"Could not load file:\n{str(e)}"
            )
            self.status_label.config(text="Error loading butcher data")
    
    def plot_customer_map(self):
        if self.customer_df is None:
            return
            
        try:
            # Create map centered on mean of customer locations
            mean_lat = self.customer_df['latitude'].mean()
            mean_lon = self.customer_df['longitude'].mean()
            
            self.current_map = folium.Map(
                location=[mean_lat, mean_lon],
                zoom_start=13,
                tiles='OpenStreetMap',
                control_scale=True
            )
            
            # Add different visualization types based on selection
            if self.current_map_type == "markers":
                self._add_markers()
            elif self.current_map_type == "heatmap":
                self._add_heatmap()
            elif self.current_map_type == "wireframe":
                self._add_wireframe()
            elif self.current_map_type == "clusters":
                self._add_clusters()
            
            # Add butcher markers if available (regardless of visualization type)
            if self.butcher_df is not None:
                self._add_butcher_markers()
            
            # Save to temporary HTML
            self.current_map.save(self.temp_html)
            
            # Display in the HTML frame
            with open(self.temp_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.html_frame.set_content(html_content)
            
            self.status_label.config(text=f"Map generated ({self.map_type_var.get()})")
            
        except Exception as e:
            messagebox.showerror(
                "Mapping Error",
                f"Could not generate map:\n{str(e)}"
            )
            self.status_label.config(text="Error generating map")
    
    def _add_markers(self):
        """Add individual markers for each customer"""
        for idx, row in self.customer_df.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"Customer ID: {row['customer_id']}",
                icon=folium.Icon(color='blue', icon='user')
            ).add_to(self.current_map)
    
    def _add_heatmap(self):
        """Add heatmap visualization"""
        heat_data = [[row['latitude'], row['longitude']] for _, row in self.customer_df.iterrows()]
        HeatMap(heat_data, name="Customer Density", radius=15).add_to(self.current_map)
    
    def _add_wireframe(self):
        """Add connected lines between customer locations"""
        locations = [[row['latitude'], row['longitude']] for _, row in self.customer_df.iterrows()]
        
        # Connect all points in sequence
        PolyLine(
            locations=locations,
            color='blue',
            weight=2,
            opacity=0.7,
            tooltip="Customer Connections"
        ).add_to(self.current_map)
        
        # Add markers at each point
        for idx, row in self.customer_df.iterrows():
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=5,
                color='blue',
                fill=True,
                fill_color='blue',
                popup=f"Customer ID: {row['customer_id']}"
            ).add_to(self.current_map)
    
    def _add_clusters(self):
        """Add clustered markers"""
        customer_cluster = MarkerCluster(name="Customers").add_to(self.current_map)
        
        for idx, row in self.customer_df.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"Customer ID: {row['customer_id']}",
                icon=folium.Icon(color='blue', icon='user')
            ).add_to(customer_cluster)
    
    def _add_butcher_markers(self):
        """Add butcher markers to the map"""
        for idx, row in self.butcher_df.iterrows():
            butcher_name = row.get('butcher_name', row['butcher_id'])
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"Butcher: {butcher_name}",
                icon=folium.Icon(color='red', icon='cutlery')
            ).add_to(self.current_map)
    
    def calculate_distances(self):
        if self.customer_df is None or self.butcher_df is None:
            messagebox.showwarning(
                "Missing Data",
                "Please load both customer and butcher data first"
            )
            return
            
        try:
            # Calculate haversine distances between all customers and butchers
            distances = []
            
            for _, cust in self.customer_df.iterrows():
                row = {'customer_id': cust['customer_id']}
                
                for _, butcher in self.butcher_df.iterrows():
                    # Haversine formula
                    lat1, lon1 = math.radians(cust['latitude']), math.radians(cust['longitude'])
                    lat2, lon2 = math.radians(butcher['latitude']), math.radians(butcher['longitude'])
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    
                    distance_km = EARTH_RADIUS_KM * c
                    
                    butcher_name = butcher.get('butcher_name', butcher['butcher_id'])
                    row[f"dist_to_{butcher_name}"] = round(distance_km, 2)
                
                distances.append(row)
            
            self.distance_df = pd.DataFrame(distances)
            
            # Display in Treeview
            self.display_distance_matrix()
            
            self.status_label.config(text=f"Calculated distances for {len(self.customer_df)} customers")
            
        except Exception as e:
            messagebox.showerror(
                "Distance Calculation Error",
                f"Could not calculate distances:\n{str(e)}"
            )
            self.status_label.config(text="Error calculating distances")
    
    def display_distance_matrix(self):
        # Clear existing tree
        for i in self.distance_tree.get_children():
            self.distance_tree.delete(i)
        
        if self.distance_df is None or self.distance_df.empty:
            return
        
        # Set up columns
        columns = list(self.distance_df.columns)
        self.distance_tree["columns"] = columns
        self.distance_tree["show"] = "headings"
        
        # Add headers
        for col in columns:
            self.distance_tree.heading(col, text=col.replace('_', ' ').title())
            self.distance_tree.column(col, width=120, anchor=tk.CENTER)
        
        # Add data rows
        for _, row in self.distance_df.iterrows():
            self.distance_tree.insert("", "end", values=list(row))
    
    def export_distance_matrix(self):
        if self.distance_df is None:
            messagebox.showwarning(
                "No Data",
                "No distance data to export"
            )
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Distance Matrix As"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                self.distance_df.to_csv(file_path, index=False)
            else:
                self.distance_df.to_excel(file_path, index=False)
            
            self.status_label.config(text=f"Distance matrix saved to {os.path.basename(file_path)}")
            messagebox.showinfo(
                "Export Successful",
                f"Distance matrix saved successfully to:\n{file_path}"
            )
        except Exception as e:
            messagebox.showerror(
                "Export Error",
                f"Could not save file:\n{str(e)}"
            )
            self.status_label.config(text="Error saving distance matrix")
    
    def export_map_image(self):
        if not hasattr(self, 'current_map') or self.current_map is None:
            messagebox.showwarning(
                "No Map",
                "No map available to export. Please generate a map first."
            )
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="Save Map Image As"
        )
        
        if not file_path:
            return
            
        try:
            # Use html2image as an alternative to selenium
            from html2image import Html2Image
            hti = Html2Image()
            
            # Save screenshot (fix missing closing parenthesis)
            hti.screenshot(
                html_file=self.temp_html,
                save_as=file_path,
                size=(1200, 800)
            )  # Added closing parenthesis here
            
            self.status_label.config(text=f"Map image saved to {os.path.basename(file_path)}")
            messagebox.showinfo(
                "Export Successful",
                f"Map image saved successfully to:\n{file_path}"
            )
            
        except Exception as e:
            messagebox.showerror(
                "Export Error",
                f"Could not save map image:\n{str(e)}\n\n"
                "Please ensure you have html2image installed (pip install html2image)"
            )
            self.status_label.config(text="Error saving map image")
    
    def generate_insights(self):
        if self.customer_df is None:
            messagebox.showwarning(
                "No Data",
                "No customer data available for insights"
            )
            return
            
        try:
            # Clear previous content
            self.insights_text.delete(1.0, tk.END)
            for widget in self.insights_canvas.winfo_children():
                widget.destroy()
            
            # Basic statistics
            num_customers = len(self.customer_df)
            avg_lat = self.customer_df['latitude'].mean()
            avg_lon = self.customer_df['longitude'].mean()
            
            # Geographic spread
            lat_range = self.customer_df['latitude'].max() - self.customer_df['latitude'].min()
            lon_range = self.customer_df['longitude'].max() - self.customer_df['longitude'].min()
            
            # Prepare insights text
            insights = [
                "CUSTOMER BASE INSIGHTS",
                "="*40,
                f"Total customers: {num_customers}",
                f"\nGEOGRAPHIC DISTRIBUTION:",
                f"Geographic center: {avg_lat:.6f}°N, {avg_lon:.6f}°E",
                f"Latitude range: {lat_range:.6f} degrees (~{lat_range*111:.2f} km)",
                f"Longitude range: {lon_range:.6f} degrees (~{lon_range*111:.2f} km at equator)",
            ]
            
            # Add butcher-related insights if available
            if self.butcher_df is not None:
                insights.extend([
                    f"\nBUTCHER COVERAGE:",
                    f"Number of butchers: {len(self.butcher_df)}"
                ])
                
                if self.distance_df is not None:
                    # Calculate average distances
                    dist_cols = [col for col in self.distance_df.columns if col.startswith('dist_to_')]
                    avg_distances = self.distance_df[dist_cols].mean()
                    
                    insights.append("\nAVERAGE DISTANCES TO BUTCHERS:")
                    for col, dist in avg_distances.items():
                        butcher_name = col.replace('dist_to_', '').replace('_', ' ')
                        insights.append(f"- {butcher_name.title()}: {dist:.2f} km")
            
            # Add recommendations based on visualization type
            insights.extend([
                "\nRECOMMENDATIONS:",
                f"- Current visualization: {self.map_type_var.get()}",
                "- Consider opening new butcher shops in areas with high customer density",
                "- Analyze customer distribution patterns for targeted marketing",
                "- Use distance matrix to optimize delivery routes"
            ])
            
            # Display insights
            self.insights_text.insert(tk.END, "\n".join(insights))
            
            # Create visualizations
            self.create_visualizations()
            
            self.status_label.config(text="Customer insights generated")
            
        except Exception as e:
            messagebox.showerror(
                "Insights Error",
                f"Could not generate insights:\n{str(e)}"
            )
            self.status_label.config(text="Error generating insights")
    
    def create_visualizations(self):
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle("Customer Distribution Analysis")
        
        # Histogram of latitudes
        ax1.hist(self.customer_df['latitude'], bins=15, color='skyblue', edgecolor='black')
        ax1.set_title('Latitude Distribution')
        ax1.set_xlabel('Latitude')
        ax1.set_ylabel('Number of Customers')
        
        # Histogram of longitudes
        ax2.hist(self.customer_df['longitude'], bins=15, color='lightgreen', edgecolor='black')
        ax2.set_title('Longitude Distribution')
        ax2.set_xlabel('Longitude')
        ax2.set_ylabel('Number of Customers')
        
        plt.tight_layout()
        
        # Embed plot in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.insights_canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        # Install tkinterhtml if not available
        try:
            from tkinterhtml import HtmlFrame
        except ImportError:
            messagebox.showwarning(
                "Package Required",
                "The tkinterhtml package is required for embedded map display.\n"
                "Install it with: pip install tkinterhtml"
            )
            sys.exit(1)
        
        app = CustomerMappingApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror(
            "Fatal Error",
            f"The application encountered an unexpected error:\n\n{str(e)}\n\n"
            "Please report this issue."
        )
        sys.exit(1)