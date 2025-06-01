import pandas as pd
import folium
import webbrowser
from tkinter import Tk, filedialog
import os

# Hide the root Tkinter window
root = Tk()
root.withdraw()

# Ask user to select the Excel file
file_path = filedialog.askopenfilename(
    title="Select Excel File",
    filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
)

if not file_path:
    print("No file selected. Exiting...")
    exit()

# Read the Excel file
try:
    df = pd.read_excel(file_path)
    required_columns = ['Customer ID', 'Latitude', 'Longitude']
    
    # Check if required columns exist
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        raise ValueError(f"Missing columns: {', '.join(missing)}")
        
    # Add data type validation and conversion
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    
    # Remove rows with invalid coordinates
    initial_count = len(df)
    df = df.dropna(subset=['Latitude', 'Longitude'])
    new_count = len(df)
    
    if new_count == 0:
        raise ValueError("No valid coordinate data remaining after cleaning")
        
    if initial_count != new_count:
        print(f"Removed {initial_count - new_count} rows with invalid coordinates")
except Exception as e:
    print(f"Error reading file: {e}")
    exit()

# Create map centered on the mean of all coordinates
map_center = [df['Latitude'].mean(), df['Longitude'].mean()]
customer_map = folium.Map(location=map_center, zoom_start=13)

# Add markers for each customer
for idx, row in df.iterrows():
    folium.Marker(
        location=[row['Latitude'], row['Longitude']],
        popup=f"Customer ID: {row['Customer ID']}",
        tooltip=f"ID: {row['Customer ID']}"
    ).add_to(customer_map)

# Add a heatmap layer
from folium.plugins import HeatMap
heat_data = df[['Latitude', 'Longitude']].values.tolist()
HeatMap(heat_data, radius=15).add_to(customer_map)

# Save HTML to desktop
# Modified file saving section with directory creation
desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
os.makedirs(desktop, exist_ok=True)  # Create desktop directory if it doesn't exist

html_path = os.path.join(desktop, 'customer_map.html')
customer_map.save(html_path)

print(f"Interactive map saved to your desktop: {html_path}")
webbrowser.open(html_path)

# Export as image (PNG)
try:
    from selenium import webdriver
    from PIL import Image
    import time
    
    print("Exporting as image...")
    
    # Set up headless browser
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,1024')  # Adjust as needed
    
    driver = webdriver.Chrome(options=options)
    driver.get(f'file://{html_path}')
    
    # Wait for map to load
    time.sleep(5)
    
    # Save screenshot
    img_path = os.path.join(desktop, 'customer_map.png')
    driver.save_screenshot(img_path)
    
    # Crop to map area (adjust these values as needed)
    img = Image.open(img_path)
    img = img.crop((300, 100, 900, 800))  # left, top, right, bottom
    img.save(img_path)
    
    print(f"Map image saved to your desktop: {img_path}")
    driver.quit()
    
except Exception as e:
    print(f"Couldn't save as image. Error: {e}")
    print("Note: You need ChromeDriver installed for image export.")
    print("You can still use the interactive HTML map.")