
import os
import sys
import time
from PIL import Image
from io import BytesIO

# Add execution dir
sys.path.append(os.path.join(os.getcwd(), 'execution'))

# Import the modified functions
from series_processor import resize_bytes_to_jpeg

# Test Image
TEST_IMG = "debug_download_test.png"

def create_dummy_image():
    print("Creating dummy 4k image...")
    img = Image.new('RGB', (4000, 3000), color = 'red')
    img.save("dummy_4k.png")
    return "dummy_4k.png"

def test_resizing():
    if os.path.exists(TEST_IMG):
        target_img = TEST_IMG
    else:
        target_img = create_dummy_image()
        
    print(f"Testing with {target_img}...")
    original_size = os.path.getsize(target_img)
    print(f"Original File Size: {original_size / 1024 / 1024:.2f} MB")
    
    with open(target_img, "rb") as f:
        raw_bytes = f.read()
        
    start_time = time.time()
    resized_bytes = resize_bytes_to_jpeg(raw_bytes, max_size=1024)
    end_time = time.time()
    
    new_size = len(resized_bytes)
    print(f"Resized File Size: {new_size / 1024 / 1024:.2f} MB")
    print(f"Reduction: {(1 - new_size/original_size)*100:.1f}%")
    print(f"Time Taken: {end_time - start_time:.4f}s")
    
    # Verify Dimensions
    img = Image.open(BytesIO(resized_bytes))
    print(f"New Dimensions: {img.size}")
    if max(img.size) <= 1024:
        print("✅ SUCCESS: Dimensions are within 1024px")
    else:
        print("❌ FAIL: Dimensions too large")
        
    # Clean up dummy
    if target_img == "dummy_4k.png":
        os.remove("dummy_4k.png")

if __name__ == "__main__":
    try:
        test_resizing()
    except ImportError:
        print("Could not import resize_bytes_to_jpeg. Use view_file to check indentation.")
    except Exception as e:
        print(f"Error: {e}")
