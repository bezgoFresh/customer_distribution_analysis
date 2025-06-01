import tkinter as tk
from tkinter import ttk, filedialog
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from io import BytesIO
from PIL import Image, ImageTk
import webbrowser
import os
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Constants
EARTH_RADIUS_KM = 6371

class CustomerMappingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Customer Mapping Analysis Tool")
        self.root.geometry("1200x800")
        
        # Data storage
        self.customer_df = None
        self.butcher_df = None
        self.distance_df = None
        
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
        
        # Export Map Button
        btn_export_map = ttk.Button(
            control_frame, 
            text="Export Map as Image", 
            command=self.export_map_image
        )
        btn_export_map.pack(side="left", padx=5)
        
        # Map Display
        self.map_display = tk.Canvas(map_frame, bg="white")
        self.map_display.pack(fill="both", expand=True)
        
        # Status Label
        self.status_label = ttk.Label(map_frame, text="Upload customer data to begin")
        self.status_label.pack(fill="x")
    
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
        self.insights_text = tk.Text(insights_frame, height=10)
        self.insights_text.pack(fill="x", pady=5)
    
    def load_customer_data(self):
        file_path = filedialog.askopenfilename(
            title="Select Customer Data File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.customer_df = pd.read_csv(file_path)
                else:
                    self.customer_df = pd.read_excel(file_path)
                
                # Clean column names (remove spaces, make lowercase)
                self.customer_df.columns = self.customer_df.columns.str.strip().str.lower()
                
                # Add numeric conversion and validation
                self.customer_df['latitude'] = pd.to_numeric(self.customer_df['latitude'], errors='coerce')
                self.customer_df['longitude'] = pd.to_numeric(self.customer_df['longitude'], errors='coerce')
                
                # Remove rows with invalid coordinates
                initial_count = len(self.customer_df)
                self.customer_df = self.customer_df.dropna(subset=['latitude', 'longitude'])
                new_count = len(self.customer_df)
                
                # Check required columns after cleaning
                required = ['customer id', 'latitude', 'longitude']
                missing = [col for col in required if col not in self.customer_df.columns]
                
                if missing:
                    self.status_label.config(text=f"Missing columns: {', '.join(missing)}")
                elif new_count == 0:
                    self.status_label.config(text="Error: No valid coordinate data found")
                else:
                    if initial_count != new_count:
                        self.status_label.config(text=f"Loaded {new_count} valid records (removed {initial_count - new_count} invalid rows)")
                    else:
                        self.status_label.config(text=f"Loaded {len(self.customer_df)} customer records")
                    self.plot_customer_map()
                    
            except Exception as e:
                self.status_label.config(text=f"Error loading file: {str(e)}")
    
    def load_butcher_data(self):
        file_path = filedialog.askopenfilename(
            title="Select Butcher Data File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.butcher_df = pd.read_csv(file_path)
                else:
                    self.butcher_df = pd.read_excel(file_path)
                
                # Clean column names
                self.butcher_df.columns = self.butcher_df.columns.str.strip().str.lower()
                
                # Check required columns
                required = ['butcher id', 'butcher name', 'latitude', 'longitude']
                missing = [col for col in required if col not in self.butcher_df.columns]
                
                if missing:
                    self.status_label.config(text=f"Missing columns: {', '.join(missing)}")
                else:
                    self.status_label.config(text=f"Loaded {len(self.butcher_df)} butcher records")
                    self.plot_customer_map()  # Update map with butchers
                    
            except Exception as e:
                self.status_label.config(text=f"Error loading file: {str(e)}")
    
    def plot_customer_map(self):
        if self.customer_df is None:
            return
            
        # Create map centered on mean of customer locations
        mean_lat = self.customer_df['latitude'].mean()
        mean_lon = self.customer_df['longitude'].mean()
        
        self.current_map = folium.Map(
            location=[mean_lat, mean_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Add geographical center marker (new code)
        folium.Marker(
            location=[mean_lat, mean_lon],
            popup=f'recommended hub : {mean_lat:.4f}°N, {mean_lon:.4f}°E',
            icon=folium.Icon(color='green', icon='star', prefix='fa')
        ).add_to(self.current_map)
        
        # Add customer markers with clustering
        customer_cluster = MarkerCluster(name="Customers").add_to(self.current_map)
        
        for idx, row in self.customer_df.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"Customer ID: {row['customer id']}",
                icon=folium.Icon(color='blue', icon='user')
            ).add_to(customer_cluster)
        
        # Add butcher markers and 5km radius circles if available
        if self.butcher_df is not None:
            butcher_cluster = MarkerCluster(name="Butchers").add_to(self.current_map)
            
            for idx, row in self.butcher_df.iterrows():
                # Add butcher marker
                butcher_name = row.get('butcher name', row['butcher id'])
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=f"Butcher: {butcher_name}",
                    icon=folium.Icon(color='red', icon='cutlery')
                ).add_to(butcher_cluster)
                
                # Add 5km radius circle (approximately 0.045 degrees at equator)
                # Convert 5km to degrees based on latitude (adjust for Earth's curvature)
                radius_deg = 5 / (111.32 * math.cos(math.radians(row['latitude'])))
                
                folium.Circle(
                    location=[row['latitude'], row['longitude']],
                    radius=5000,  # 5km in meters
                    popup=f"{butcher_name} - 5km service radius",
                    color='red',
                    fill=True,
                    fill_color='red',
                    fill_opacity=0.1
                ).add_to(self.current_map)
        
        # Add customer distribution perimeter (bounding box)
        min_lat = self.customer_df['latitude'].min()
        max_lat = self.customer_df['latitude'].max()
        min_lon = self.customer_df['longitude'].min()
        max_lon = self.customer_df['longitude'].max()
        
        folium.Rectangle(
            bounds=[[min_lat, min_lon], [max_lat, max_lon]],
            color='blue',
            weight=2,
            fill=True,
            fill_color='blue',
            fill_opacity=0.05,
            popup="Customer Distribution Area"
        ).add_to(self.current_map)
        
        # Add heatmap
        heat_data = [[row['latitude'], row['longitude']] for idx, row in self.customer_df.iterrows()]
        HeatMap(heat_data, name="Heatmap").add_to(self.current_map)
        
        # Add layer control
        folium.LayerControl().add_to(self.current_map)
        
        # Save to temporary HTML and display
        self.temp_html = "temp_map.html"
        self.current_map.save(self.temp_html)
        
        # Display in browser (alternative would be to embed in Tkinter)
        webbrowser.open('file://' + os.path.abspath(self.temp_html))
        
        self.status_label.config(text="Map generated and opened in browser")
    
    def calculate_distances(self):
        if self.customer_df is None or self.butcher_df is None:
            self.status_label.config(text="Please load both customer and butcher data first")
            return
            
        try:
            # Calculate haversine distances between all customers and butchers
            distances = []
            
            for _, cust in self.customer_df.iterrows():
                row = {'Customer ID': cust['customer id']}
                
                for _, butcher in self.butcher_df.iterrows():
                    # Haversine formula
                    lat1, lon1 = math.radians(cust['latitude']), math.radians(cust['longitude'])
                    lat2, lon2 = math.radians(butcher['latitude']), math.radians(butcher['longitude'])
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    
                    distance_km = EARTH_RADIUS_KM * c
                    
                    butcher_name = butcher.get('butcher name', butcher['butcher id'])
                    row[f"Dist to {butcher_name} (km)"] = round(distance_km, 2)
                
                distances.append(row)
            
            self.distance_df = pd.DataFrame(distances)
            
            # Display in Treeview
            self.display_distance_matrix()
            
            self.status_label.config(text=f"Calculated distances for {len(self.customer_df)} customers")
            
        except Exception as e:
            self.status_label.config(text=f"Error calculating distances: {str(e)}")
    
    def display_distance_matrix(self):
        # Clear existing tree
        for i in self.distance_tree.get_children():
            self.distance_tree.delete(i)
        
        # Set up columns
        columns = list(self.distance_df.columns)
        self.distance_tree["columns"] = columns
        self.distance_tree["show"] = "headings"
        
        # Add headers
        for col in columns:
            self.distance_tree.heading(col, text=col)
            self.distance_tree.column(col, width=100)
        
        # Add data rows
        for _, row in self.distance_df.iterrows():
            self.distance_tree.insert("", "end", values=list(row))
    
    def export_distance_matrix(self):
        if self.distance_df is None:
            self.status_label.config(text="No distance data to export")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Distance Matrix As"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.distance_df.to_csv(file_path, index=False)
                else:
                    self.distance_df.to_excel(file_path, index=False)
                
                self.status_label.config(text=f"Distance matrix saved to {file_path}")
            except Exception as e:
                self.status_label.config(text=f"Error saving file: {str(e)}")
    
    def export_map_image(self):
        if not hasattr(self, 'current_map'):
            self.status_label.config(text="No map to export")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="Save Map Image As"
        )
        
        if file_path:
            try:
                # Use selenium to capture the map (alternative methods could be used here)
                from selenium import webdriver
                from PIL import Image
                import time
                
                options = webdriver.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1200,800')
                
                driver = webdriver.Chrome(options=options)
                driver.get(f'file://{os.path.abspath(self.temp_html)}')
                time.sleep(3)  # Wait for map to load
                
                driver.save_screenshot(file_path)
                driver.quit()
                
                # Crop to map area
                img = Image.open(file_path)
                img = img.crop((100, 100, 1100, 700))  # Adjust as needed
                img.save(file_path)
                
                self.status_label.config(text=f"Map image saved to {file_path}")
                
            except Exception as e:
                self.status_label.config(text=f"Error saving image: {str(e)}. Make sure ChromeDriver is installed.")
    
    def generate_insights(self):
        if self.customer_df is None:
            self.status_label.config(text="No customer data to analyze")
            return
            
        try:
            # Clear previous content
            self.insights_text.delete(1.0, tk.END)
            self.insights_canvas.delete("all")
            
            # Basic statistics
            num_customers = len(self.customer_df)
            avg_lat = self.customer_df['latitude'].mean()
            avg_lon = self.customer_df['longitude'].mean()
            
            # Density analysis
            lat_range = self.customer_df['latitude'].max() - self.customer_df['latitude'].min()
            lon_range = self.customer_df['longitude'].max() - self.customer_df['longitude'].min()
            
            # Calculate customer distribution area
            min_lat = self.customer_df['latitude'].min()
            max_lat = self.customer_df['latitude'].max()
            min_lon = self.customer_df['longitude'].min()
            max_lon = self.customer_df['longitude'].max()
            
            # Calculate area in square kilometers (approximate)
            lat_dist = (max_lat - min_lat) * 111.32  # km per degree latitude
            lon_dist = (max_lon - min_lon) * 111.32 * math.cos(math.radians((min_lat + max_lat) / 2))  # km per degree longitude
            customer_area = lat_dist * lon_dist
            
            insights = [
                f"Customer Base Insights:",
                f"Total customers: {num_customers}",
                f"Geographic center: {avg_lat:.4f}°N, {avg_lon:.4f}°E",
                f"Customer distribution area: {customer_area:.2f} km²",
                f"Latitude range: {lat_range:.4f} degrees ({lat_dist:.2f} km)",
                f"Longitude range: {lon_range:.4f} degrees ({lon_dist:.2f} km)",
                "\nRecommendations:"
            ]
            
            if lat_range > 0.1 or lon_range > 0.1:
                insights.append("- Customer base is geographically dispersed")
                insights.append("- Consider regional service centers or multiple butchers")
            else:
                insights.append("- Customer base is geographically concentrated")
                insights.append("- Single service location may be sufficient")
            
            if self.butcher_df is not None:
                insights.append(f"\nButcher Coverage Analysis:")
                insights.append(f"Number of butchers: {len(self.butcher_df)}")
                
                # Calculate butcher coverage metrics
                total_coverage_area = 0
                butcher_coverage = []
                outside_coverage = []
                
                for _, butcher in self.butcher_df.iterrows():
                    butcher_name = butcher.get('butcher name', butcher['butcher id'])
                    
                    # Calculate 5km radius coverage area
                    coverage_area = math.pi * 5 * 5  # πr²
                    total_coverage_area += coverage_area
                    
                    # Check if butcher is inside or outside customer distribution area
                    is_inside = (
                        min_lat <= butcher['latitude'] <= max_lat and
                        min_lon <= butcher['longitude'] <= max_lon
                    )
                    
                    # Calculate distance to nearest edge of customer distribution
                    if is_inside:
                        edge_dist = min(
                            butcher['latitude'] - min_lat,
                            max_lat - butcher['latitude'],
                            butcher['longitude'] - min_lon,
                            max_lon - butcher['longitude']
                        ) * 111.32  # Convert to km
                        butcher_coverage.append(f"- {butcher_name}: Inside customer area (5km service radius, {edge_dist:.2f}km from edge)")
                    else:
                        # Calculate distance to nearest point of customer distribution
                        nearest_lat = max(min(butcher['latitude'], max_lat), min_lat)
                        nearest_lon = max(min(butcher['longitude'], max_lon), min_lon)
                        
                        dist = self.haversine(
                            butcher['latitude'], butcher['longitude'],
                            nearest_lat, nearest_lon
                        )
                        outside_coverage.append(f"- {butcher_name}: Outside customer area ({dist:.2f}km from nearest customer, 5km service radius)")
                
                # Calculate percentage of customer area covered by butchers
                coverage_percentage = min(100, (total_coverage_area / customer_area) * 100) if customer_area > 0 else 0
                
                insights.append(f"\nButcher Service Coverage:")
                insights.append(f"Total 5km service area: {total_coverage_area:.2f} km²")
                insights.append(f"Coverage of customer area: {coverage_percentage:.1f}%")
                
                if butcher_coverage:
                    insights.append("\nButchers inside customer distribution area:")
                    insights.extend(butcher_coverage)
                
                if outside_coverage:
                    insights.append("\nButchers outside customer distribution area:")
                    insights.extend(outside_coverage)
                
                if self.distance_df is not None:
                    avg_distances = self.distance_df.drop('Customer ID', axis=1).mean()
                    insights.append("\nAverage distances to butchers:")
                    for butcher, dist in avg_distances.items():
                        insights.append(f"- {butcher}: {dist:.2f} km")
                        
                    # Calculate percentage of customers within 5km of any butcher
                    customers_within_5km = 0
                    for _, row in self.distance_df.iterrows():
                        distances = [dist for col, dist in row.items() if col != 'Customer ID']
                        if any(d <= 5 for d in distances):
                            customers_within_5km += 1
                    
                    coverage_percent = (customers_within_5km / len(self.customer_df)) * 100 if len(self.customer_df) > 0 else 0
                    insights.append(f"\nCustomer coverage metrics:")
                    insights.append(f"Customers within 5km of any butcher: {customers_within_5km} ({coverage_percent:.1f}%)")
            
            self.insights_text.insert(tk.END, "\n".join(insights))
            
            # Create visualization plots
            self.create_coverage_visualization()
            
            self.status_label.config(text="Customer insights generated")
            
        except Exception as e:
            self.status_label.config(text=f"Error generating insights: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CustomerMappingApp(root)
    root.mainloop()

    def create_coverage_visualization(self):
        """Create visualization of butcher coverage"""
        if self.butcher_df is None or self.distance_df is None:
            # Create a simple customer distribution plot if no butcher data
            fig, ax = plt.subplots(figsize=(8, 4))
            self.customer_df['latitude'].hist(ax=ax, bins=15, alpha=0.7)
            ax.set_title('Customer Latitude Distribution')
            ax.set_xlabel('Latitude')
            ax.set_ylabel('Number of Customers')
        else:
            # Create a more detailed coverage analysis
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            fig.suptitle("Butcher Coverage Analysis")
            
            # Plot 1: Distance distribution
            distance_data = self.distance_df.drop('Customer ID', axis=1).min(axis=1)
            ax1.hist(distance_data, bins=20, color='skyblue', edgecolor='black')
            ax1.axvline(x=5, color='red', linestyle='--', label='5km service radius')
            ax1.set_title('Distance to Nearest Butcher')
            ax1.set_xlabel('Distance (km)')
            ax1.set_ylabel('Number of Customers')
            ax1.legend()
            
            # Plot 2: Coverage map (simplified)
            ax2.scatter(
                self.customer_df['longitude'], 
                self.customer_df['latitude'],
                alpha=0.5, s=10, c='blue', label='Customers'
            )
            
            # Plot butchers
            ax2.scatter(
                self.butcher_df['longitude'],
                self.butcher_df['latitude'],
                alpha=1, s=50, c='red', marker='*', label='Butchers'
            )
            
            # Plot customer distribution area
            min_lat = self.customer_df['latitude'].min()
            max_lat = self.customer_df['latitude'].max()
            min_lon = self.customer_df['longitude'].min()
            max_lon = self.customer_df['longitude'].max()
            
            ax2.add_patch(plt.Rectangle(
                (min_lon, min_lat),
                max_lon - min_lon,
                max_lat - min_lat,
                fill=False, edgecolor='blue', linestyle='-'
            ))
            
            ax2.set_title('Customer and Butcher Locations')
            ax2.set_xlabel('Longitude')
            ax2.set_ylabel('Latitude')
            ax2.legend()
            
        plt.tight_layout()
        
        # Embed plot in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.insights_canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def haversine(self, lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points in kilometers"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return EARTH_RADIUS_KM * c


