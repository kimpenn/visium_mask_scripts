import geopandas as gpd
import json
from rasterio.features import rasterize
import numpy as np
import tifffile
import os
import glob
from pathlib import Path
import xml.etree.ElementTree as ET
import traceback

# Define directories
geojson_dir = './geojson'
# Example of the geojson files:
# -rw-r--r--@ 1 kuangda  staff   454K Apr 13 00:07 Visium_13_38_S1_b.geojson
# -rw-r--r--@ 1 kuangda  staff   452K Apr 13 00:08 Visium_13_38_S2_b.geojson
# -rw-r--r--@ 1 kuangda  staff   131K Apr 12 23:32 Visium_13_41_S1_b.geojson
# -rw-r--r--@ 1 kuangda  staff    64K Apr 13 00:11 Visium_13_44_S1_b.geojson
# -rw-r--r--@ 1 kuangda  staff   381K Sep 12  2024 Visium_9_RTAMP_4_S1_2slice.geojson
# -rw-r--r--@ 1 kuangda  staff   475K Apr 12 23:09 Visium_9_RTAMP_4_S2_2slice.geojson
# -rw-r--r--@ 1 kuangda  staff    83K Apr 13 00:10 Visium_9_RTINF_4_S2_2slice.geojson
# -rw-r--r--@ 1 kuangda  staff   316K Apr 12 23:37 Visium_9_RTIS_4_S2_2slice.geojson

raw_dir = './ome_tiff'
# Example of the raw images:
# -rw-r--r--  1 kuangda  staff   2.2G Apr 13 15:14 Visium_13_38_S1_b.ome.tiff
# -rw-r--r--  1 kuangda  staff   2.2G Apr 13 15:23 Visium_13_38_S2_b.ome.tiff
# -rw-r--r--  1 kuangda  staff   1.1G Apr 13 15:27 Visium_13_41_S1_b.ome.tiff
# -rw-r--r--  1 kuangda  staff   2.2G Apr 13 15:37 Visium_13_44_S1_b.ome.tiff
# -rw-r--r--  1 kuangda  staff   1.1G Apr 13 15:42 Visium_9_RTAMP_4_S1_2slice.ome.tiff
# -rw-r--r--  1 kuangda  staff   1.0G Apr 13 15:46 Visium_9_RTAMP_4_S2_2slice.ome.tiff
# -rw-r--r--@ 1 kuangda  staff   1.1G Apr 13 15:57 Visium_9_RTINF_4_S2_2slice.ome.tiff
# -rw-r--r--  1 kuangda  staff   1.1G Apr 13 15:50 Visium_9_RTIS_4_S2_2slice.ome.tiff

mask_output_dir = './ome_tiff_masks'
if not os.path.exists(mask_output_dir):
    os.makedirs(mask_output_dir)
mask_meta_json_dir = './mask_meta_json'
if not os.path.exists(mask_meta_json_dir):
    os.makedirs(mask_meta_json_dir)

def extract_metadata(image_path):
    """Extract metadata from a raw image file using OME-XML parsing."""
    print(f"image_path:{image_path}")
    try:
        with tifffile.TiffFile(image_path) as tif:
            ome_metadata = tif.ome_metadata
            if ome_metadata:
                # Parse the XML
                ns = {'ome': 'http://www.openmicroscopy.org/Schemas/OME/2016-06'}
                root = ET.fromstring(ome_metadata)
                
                # Find the Pixels element
                pixels = root.find('.//ome:Pixels', ns)
                
                # Extract physical size information
                physical_size_x = pixels.get('PhysicalSizeX', '0')
                physical_size_x_unit = pixels.get('PhysicalSizeXUnit', 'mm')
                physical_size_y = pixels.get('PhysicalSizeY', '0')
                physical_size_y_unit = pixels.get('PhysicalSizeYUnit', 'mm')
                physical_size_z = pixels.get('PhysicalSizeZ', '0')
                physical_size_z_unit = pixels.get('PhysicalSizeZUnit', 'mm')
                size_x = pixels.get('SizeX')
                size_y = pixels.get('SizeY')
                
                print(f"PhysicalSizeX=\"{physical_size_x}\"")
                print(f"PhysicalSizeXUnit=\"{physical_size_x_unit}\"")
                print(f"PhysicalSizeY=\"{physical_size_y}\"")
                print(f"PhysicalSizeYUnit=\"{physical_size_y_unit}\"")
                print(f"PhysicalSizeZ=\"{physical_size_z}\"")
                print(f"PhysicalSizeZUnit=\"{physical_size_z_unit}\"")
                print(f"SizeX=\"{size_x}\"")
                print(f"SizeY=\"{size_y}\"")
                
        return {
            'physical_size_x': float(physical_size_x) if physical_size_x else 0.0,
            'physical_size_x_unit': str(physical_size_x_unit),
            'physical_size_y': float(physical_size_y) if physical_size_y else 0.0,
            'physical_size_y_unit': str(physical_size_y_unit),
            'physical_size_z': float(physical_size_z) if physical_size_z else 0.0,
            'physical_size_z_unit': str(physical_size_z_unit),
            'size_x': int(float(size_x)) if size_x else 0,
            'size_y': int(float(size_y)) if size_y else 0,
        }
    except Exception as e:
        print(f"Error reading metadata from {image_path}: {str(e)}")

def process_geojson(geojson_path):
    """Process a single GeoJSON file and create corresponding mask."""
    try:
        base_name = os.path.splitext(os.path.basename(geojson_path))[0]        
        
        # Step 1: Extract metadata from the raw image
        raw_image_pattern = os.path.join(raw_dir, f"{base_name}*")
        raw_images = glob.glob(raw_image_pattern)
        if raw_images:
            print(f"\nProcessing raw image for {base_name}:")
            metadata = extract_metadata(raw_images[0])
        else:
            print(f"No corresponding raw image found for {base_name}")
        
        # Step 2: Initialize a multi-channel mask (4 channels, one for each annotation)
        channel_names = [
            'antimesosalpinx epithelium',
            'antimesosalpinx muscularus', 
            'mesosalpinx epithelium', 
            'mesosalpinx muscularus', 
            ]
        channel_values = [1, 2, 3, 4]
        num_channels = len(channel_values)
        # Define the output raster resolution
        width = metadata['size_x']
        height = metadata['size_y']        
        masks = np.zeros((num_channels, height, width), dtype=np.uint8)
        
        # Step 3: Extract the 'Value' from the 'measurements' field and rasterize each into a separate channel
        # Load GeoJSON
        gdf = gpd.read_file(geojson_path)        
        # Rasterize each channel
        for idx, value in enumerate(channel_values):
            print(f"Processing channel {idx} with value {value}")
            parsed_measurements = gdf['measurements'].apply(json.loads)
            shapes = [(geom, 1) for geom, measurement in zip(gdf['geometry'], parsed_measurements) 
                     if measurement.get('Value') == value]
            print(f"shapes: {shapes}")
            if shapes:
                # Rasterize the shapes into the respective mask channel
                masks[idx] = rasterize(shapes, out_shape=(height, width), fill=0, dtype=np.uint8)
        
        # Step 4: Save the multi-channel OME-TIFF        
        # Prepare OME metadata including channel names
        ome_metadata = {
            'axes': 'CYX',
            'Channel': [{'Name': name} for name in channel_names],
            'PhysicalSizeX': float(metadata['physical_size_x']),
            'PhysicalSizeXUnit': metadata['physical_size_x_unit'],
            'PhysicalSizeY': float(metadata['physical_size_y']),
            'PhysicalSizeYUnit': metadata['physical_size_y_unit'],
            'PhysicalSizeZ': float(metadata['physical_size_z']),
            'PhysicalSizeZUnit': metadata['physical_size_z_unit'],
            'SizeC': int(num_channels),
            'SizeX': int(width),
            'SizeY': int(height),
            'SizeZ': 1,
        }
        print(f"ome_metadata: {ome_metadata}")
        # Save the multi-channel OME-TIFF
        output_path = f"{mask_output_dir}/{base_name}-mask.ome.tiff"
        tifffile.imwrite(
            output_path,
            masks,
            photometric='minisblack',
            metadata=ome_metadata,
            ome=True
        )
        
        print(f"OME-TIFF saved as {output_path}")
        
        output_meta_path = f"{mask_meta_json_dir}/{base_name}-mask.json"
        with open(output_meta_path, 'w') as f:
            json.dump(ome_metadata, f)
            
    except Exception as e:
        print(f"Error processing {geojson_path}: {str(e)}")
        print("\nDetailed traceback:")
        traceback.print_exc()
        exit()

def main():
    try:
        # Process all GeoJSON files in the directory
        geojson_files = glob.glob(os.path.join(geojson_dir, "*.geojson"))
        
        if not geojson_files:
            print(f"No GeoJSON files found in {geojson_dir}")
            return
            
        for geojson_file in geojson_files:
            print(f"\n====== Processing {geojson_file}")
            process_geojson(geojson_file)
            # exit() # for testing
    except Exception as e:
        print(f"Error in main: {str(e)}")
        print("\nDetailed traceback:")
        traceback.print_exc()
        exit()

if __name__ == "__main__":
    main()
