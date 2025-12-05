# Getting Started with WebSocket API

This guide will help you start using the WebSocket API for real-time 3D reconstruction in just a few minutes.

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Download Model** (if not already done)
   ```bash
   # Model will be downloaded automatically on first run
   # Or download manually from Hugging Face
   ```

## Step 1: Start the Server

Start the backend server with WebSocket support:

```bash
python -m depth_anything_3.services.backend \
    --model-dir depth-anything/DA3NESTED-GIANT-LARGE \
    --host 0.0.0.0 \
    --port 8000
```

You should see:
```
Starting Depth Anything 3 Backend...
Model directory: depth-anything/DA3NESTED-GIANT-LARGE
Device: cuda
Server: http://0.0.0.0:8000
Dashboard: http://0.0.0.0:8000/dashboard
...
```

## Step 2: Verify Server is Running

Open your browser and visit:
- **Dashboard**: http://localhost:8000/dashboard
- **API Docs**: http://localhost:8000/docs

You should see the server status and available endpoints.

## Step 3: Choose Your Client

### Option A: Use the HTML Client (Easiest)

1. Open the HTML client:
   ```bash
   cd examples
   python -m http.server 8080
   ```

2. Open http://localhost:8080/websocket_client.html in your browser

3. Follow the UI:
   - Click "Create Session"
   - Select images to upload
   - Click "Send Images"
   - Click "Generate 3D Model"
   - Download the GLB file when ready

### Option B: Use the Python Client

1. Prepare some images in a folder:
   ```bash
   mkdir test_images
   # Copy some images to test_images/
   ```

2. Run the client:
   ```bash
   python examples/websocket_client.py \
       --images test_images/*.png \
       --output my_model.glb
   ```

3. Wait for processing to complete

4. View the GLB file in a 3D viewer

### Option C: Write Your Own Client

Here's a minimal example:

```python
import asyncio
import websockets
import requests
import json
import base64

async def generate_3d_model(image_paths):
    # 1. Create session
    response = requests.post("http://localhost:8000/ws/session/create")
    session_id = response.json()["session_id"]
    print(f"Session: {session_id}")
    
    # 2. Connect WebSocket
    uri = f"ws://localhost:8000/ws/reconstruct/{session_id}"
    async with websockets.connect(uri) as ws:
        # Wait for connection
        await ws.recv()
        
        # 3. Send images
        for img_path in image_paths:
            with open(img_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            
            await ws.send(json.dumps({
                "type": "image",
                "data": img_data
            }))
            
            # Wait for ack
            await ws.recv()
            print(f"Uploaded: {img_path}")
        
        # 4. Generate model
        await ws.send(json.dumps({"type": "generate"}))
        
        # 5. Wait for result
        while True:
            msg = json.loads(await ws.recv())
            
            if msg["type"] == "progress":
                print(f"Progress: {msg['progress']*100:.1f}%")
            
            elif msg["type"] == "complete":
                # Save GLB
                glb_data = base64.b64decode(msg["glb_base64"])
                with open("output.glb", "wb") as f:
                    f.write(glb_data)
                print("✓ Saved output.glb")
                break

# Run it
asyncio.run(generate_3d_model([
    "image1.png",
    "image2.png",
    "image3.png"
]))
```

Save this as `my_client.py` and run:
```bash
python my_client.py
```

## Step 4: View Your 3D Model

You can view the generated GLB file using:

1. **Online Viewers**:
   - https://gltf-viewer.donmccurdy.com/
   - https://3dviewer.net/
   - https://modelviewer.dev/

2. **Desktop Software**:
   - Blender (free, open-source)
   - MeshLab (free, open-source)
   - 3D Viewer (Windows built-in)

3. **In Web Apps**:
   ```html
   <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
   <model-viewer src="output.glb" auto-rotate camera-controls></model-viewer>
   ```

## Common Workflows

### Workflow 1: Process Photos from Phone

1. Take photos on your phone of an object/scene
2. Transfer to computer
3. Run Python client: 
   ```bash
   python examples/websocket_client.py --images photos/*.jpg
   ```
4. Download and view GLB model

### Workflow 2: Process Video

1. Record a video walking around an object
2. Run client with video:
   ```bash
   python examples/websocket_client.py \
       --video myvideo.mp4 \
       --num-frames 30
   ```
3. Get 3D reconstruction

### Workflow 3: Real-time Streaming

1. Use the HTML client
2. Upload images one at a time or in batches
3. Click "Generate 3D Model" after each batch
4. See progressive updates
5. Click "Finalize" for final high-quality model

## Tips for Best Results

### 1. Image Quality
- Use high-resolution images (but not too large)
- Good lighting
- Minimal motion blur
- Overlapping views (50%+ overlap between consecutive images)

### 2. Number of Images
- Minimum: 3-5 images
- Recommended: 10-30 images
- More images = better coverage but slower processing

### 3. Camera Movement
- Smooth, steady movement
- Maintain consistent distance from object
- Cover all angles
- Avoid rapid movements

### 4. Processing Settings

For faster processing:
```python
# Lower resolution
POST /ws/session/create?process_res=256

# Fewer points
POST /ws/session/create?num_max_points=1000000
```

For better quality:
```python
# Higher resolution
POST /ws/session/create?process_res=1024

# More points
POST /ws/session/create?num_max_points=50000000
```

## Troubleshooting

### Server Won't Start

**Problem**: `CUDA out of memory`
- **Solution**: Use CPU mode: add `--device cpu` to server start command
- Or reduce batch size/resolution

**Problem**: `Model not found`
- **Solution**: Check model directory path, ensure model is downloaded

### Images Not Uploading

**Problem**: WebSocket connection fails
- **Solution**: Check server is running on correct port
- Verify firewall isn't blocking WebSocket connections

**Problem**: "Session not found"
- **Solution**: Session may have timed out, create a new one

### Poor Quality Results

**Problem**: Sparse point cloud
- **Solution**: 
  - Use more images
  - Increase `num_max_points`
  - Lower `conf_thresh_percentile`

**Problem**: Noisy reconstruction
- **Solution**: 
  - Use better quality images
  - Increase `conf_thresh_percentile`
  - Improve lighting conditions

## Next Steps

1. **Read Full Documentation**
   - [WebSocket API Reference](docs/WEBSOCKET_API.md)
   - [Quick Start Guide](WEBSOCKET_QUICKSTART.md)

2. **Explore Examples**
   - Python client: `examples/websocket_client.py`
   - HTML client: `examples/websocket_client.html`

3. **Run Tests**
   ```bash
   python tests/test_websocket.py
   ```

4. **Monitor Performance**
   - Visit dashboard: http://localhost:8000/dashboard
   - Check GPU usage
   - Monitor session stats

5. **Optimize for Your Use Case**
   - Adjust resolution settings
   - Configure point cloud density
   - Tune confidence thresholds

## Getting Help

If you encounter issues:

1. Check the server logs for error messages
2. Visit the dashboard to see task status
3. Review the troubleshooting section in [WEBSOCKET_API.md](docs/WEBSOCKET_API.md)
4. Check session info: `GET /ws/session/{session_id}`

## Summary

You now have a working WebSocket API for real-time 3D reconstruction! The basic workflow is:

1. **Start server** → `python -m depth_anything_3.services.backend ...`
2. **Create session** → `POST /ws/session/create`
3. **Connect WebSocket** → `ws://localhost:8000/ws/reconstruct/{session_id}`
4. **Upload images** → Send `image` messages
5. **Generate model** → Send `generate` message
6. **Download GLB** → Receive `complete` message with base64 GLB data

Happy 3D reconstructing! 🎨✨

