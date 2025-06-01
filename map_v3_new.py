import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QTabWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
import os
import math

class CustomerMappingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Customer Mapping Analysis Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Data storage
        self.customer_df = None
        self.butcher_df = None
        self.distance_df = None
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Setup tabs
        self.setup_map_tab()
        self.setup_distance_tab()
        self.setup_insights_tab()
    
    def setup_map_tab(self):
        map_tab = QWidget()
        layout = QVBoxLayout(map_tab)
        
        # Control panel
        button_layout = QVBoxLayout()
        
        # Upload Customer Data Button
        btn_upload_customers = QPushButton("Upload Customer Data")
        btn_upload_customers.clicked.connect(self.load_customer_data)
        button_layout.addWidget(btn_upload_customers)
        
        # Upload Butcher Data Button
        btn_upload_butchers = QPushButton("Upload Butcher Data")
        btn_upload_butchers.clicked.connect(self.load_butcher_data)
        button_layout.addWidget(btn_upload_butchers)
        
        # Export Map Button
        btn_export_map = QPushButton("Export Map as Image")
        btn_export_map.clicked.connect(self.export_map_image)
        button_layout.addWidget(btn_export_map)
        
        layout.addLayout(button_layout)
        
        # Map widget
        self.map_widget = QWebEngineView()
        layout.addWidget(self.map_widget)
        
        # Status label
        self.status_label = QLabel("Upload customer data to begin")
        layout.addWidget(self.status_label)
        
        self.tab_widget.addTab(map_tab, "Customer Map")
    
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
        
        # Save to temporary HTML and display in widget
        self.temp_html = os.path.join(os.path.dirname(__file__), "temp_map.html")
        self.current_map.save(self.temp_html)
        
        # Load the map in QWebEngineView
        self.map_widget.setUrl(QUrl.fromLocalFile(os.path.abspath(self.temp_html)))
        self.status_label.setText("Map generated and displayed")

# Main entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomerMappingApp()
    window.show()
    sys.exit(app.exec_())


