# WebSocket API - Quick Start Guide

## Overview

The WebSocket API enables real-time 3D reconstruction by streaming images to the server and receiving incremental point cloud updates. This is ideal for:

- **Live camera streaming** from mobile/web apps
- **Progressive 3D reconstruction** with real-time preview
- **Batch processing** with progress updates
- **Interactive applications** requiring immediate feedback

## Installation

Ensure the WebSocket dependencies are installed:

```bash
pip install -r requirements.txt
```

Required packages:
- `websockets`
- `python-socketio`
- `python-multipart`

## Starting the Server

Start the backend server with WebSocket support:

```bash
python -m depth_anything_3.services.backend \
    --model-dir depth-anything/DA3NESTED-GIANT-LARGE \
    --host 0.0.0.0 \
    --port 8000
```

The server will expose:
- **HTTP API**: `http://localhost:8000`
- **WebSocket API**: `ws://localhost:8000/ws/reconstruct/{session_id}`
- **Dashboard**: `http://localhost:8000/dashboard`

## Quick Example (Python)

```python
import asyncio
import websockets
import json
import base64
import requests

# 1. Create a session
response = requests.post(
    "http://localhost:8000/ws/session/create",
    params={"max_images": 50, "process_res": 504}
)
session = response.json()
session_id = session["session_id"]

print(f"Created session: {session_id}")

# 2. Connect via WebSocket and send images
async def reconstruct():
    uri = f"ws://localhost:8000/ws/reconstruct/{session_id}"
    
    async with websockets.connect(uri) as ws:
        # Wait for connection
        msg = await ws.recv()
        print(f"Connected: {json.loads(msg)}")
        
        # Send images
        for image_path in ["img1.png", "img2.png", "img3.png"]:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            await ws.send(json.dumps({
                "type": "image",
                "data": image_data,
                "filename": image_path
            }))
            
            # Wait for ack
            ack = json.loads(await ws.recv())
            print(f"Uploaded: {ack['image_path']}")
        
        # Generate 3D model
        await ws.send(json.dumps({
            "type": "generate",
            "incremental": False
        }))
        
        # Receive progress and result
        while True:
            msg = json.loads(await ws.recv())
            
            if msg["type"] == "progress":
                print(f"Progress: {msg['progress'] * 100:.1f}% - {msg['message']}")
            
            elif msg["type"] == "complete":
                glb_data = base64.b64decode(msg["glb_base64"])
                with open("output.glb", "wb") as f:
                    f.write(glb_data)
                print(f"✓ Saved output.glb ({len(glb_data)} bytes)")
                break

asyncio.run(reconstruct())
```

## Quick Example (JavaScript/HTML)

```html
<!DOCTYPE html>
<html>
<body>
    <input type="file" id="images" multiple accept="image/*">
    <button onclick="process()">Process Images</button>
    <div id="status"></div>
    
    <script>
    let sessionId = null;
    
    async function createSession() {
        const response = await fetch('http://localhost:8000/ws/session/create', {
            method: 'POST'
        });
        const data = await response.json();
        sessionId = data.session_id;
        return sessionId;
    }
    
    async function process() {
        const files = document.getElementById('images').files;
        if (files.length === 0) return;
        
        // Create session
        await createSession();
        
        // Connect WebSocket
        const ws = new WebSocket(`ws://localhost:8000/ws/reconstruct/${sessionId}`);
        
        ws.onopen = async () => {
            // Send images
            for (const file of files) {
                const reader = new FileReader();
                reader.onload = async (e) => {
                    const base64 = e.target.result.split(',')[1];
                    ws.send(JSON.stringify({
                        type: 'image',
                        data: base64,
                        filename: file.name
                    }));
                };
                reader.readAsDataURL(file);
                await new Promise(r => setTimeout(r, 100)); // Throttle
            }
            
            // Generate model
            setTimeout(() => {
                ws.send(JSON.stringify({
                    type: 'generate',
                    incremental: false
                }));
            }, 1000);
        };
        
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            
            if (msg.type === 'complete') {
                const blob = base64ToBlob(msg.glb_base64, 'model/gltf-binary');
                const url = URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = 'model.glb';
                a.click();
                
                document.getElementById('status').textContent = '✓ Complete!';
            }
        };
    }
    
    function base64ToBlob(base64, mimeType) {
        const bytes = atob(base64);
        const array = new Uint8Array(bytes.length);
        for (let i = 0; i < bytes.length; i++) {
            array[i] = bytes.charCodeAt(i);
        }
        return new Blob([array], {type: mimeType});
    }
    </script>
</body>
</html>
```

## Using the Example Clients

### Python Client

Process images from command line:

```bash
# From images
python examples/websocket_client.py \
    --images path/to/img1.png path/to/img2.png \
    --output model.glb

# From video
python examples/websocket_client.py \
    --video path/to/video.mp4 \
    --num-frames 30 \
    --output model.glb \
    --incremental
```

### HTML Client

Open the example HTML client:

```bash
# Serve the example
cd examples
python -m http.server 8080

# Open in browser
open http://localhost:8080/websocket_client.html
```

Then:
1. Configure server URL (default: `http://localhost:8000`)
2. Select images to upload
3. Click "Create Session"
4. Click "Send Images"
5. Click "Generate 3D Model"
6. Download the resulting GLB file

## API Endpoints

### Create Session
```bash
POST /ws/session/create?max_images=100&process_res=504
```

### Connect WebSocket
```
WS /ws/reconstruct/{session_id}
```

### Get Session Info
```bash
GET /ws/session/{session_id}
```

### List Sessions
```bash
GET /ws/sessions
```

### Delete Session
```bash
DELETE /ws/session/{session_id}
```

## Message Types

### Client → Server

**Upload Image:**
```json
{
  "type": "image",
  "data": "base64_encoded_image",
  "filename": "image.png"
}
```

**Generate Point Cloud:**
```json
{
  "type": "generate",
  "incremental": true
}
```

**Finalize Session:**
```json
{
  "type": "finalize"
}
```

### Server → Client

**Progress Update:**
```json
{
  "type": "progress",
  "progress": 0.5,
  "message": "Processing..."
}
```

**Complete:**
```json
{
  "type": "complete",
  "glb_base64": "...",
  "metadata": {
    "num_frames": 10,
    "glb_size_bytes": 1234567
  }
}
```

**Error:**
```json
{
  "type": "error",
  "message": "Error description"
}
```

## Common Use Cases

### 1. Mobile App Integration

Stream images from a mobile device camera:

```javascript
// React Native / Mobile Web
const uploadFrame = async (imageUri) => {
    const base64 = await convertToBase64(imageUri);
    ws.send(JSON.stringify({
        type: 'image',
        data: base64
    }));
};

// Capture and upload every N frames
camera.onFrame((frame) => {
    if (frameCount % 5 === 0) {
        uploadFrame(frame);
    }
});
```

### 2. Batch Processing with Progress

Process a large batch of images with progress tracking:

```python
async def process_batch(images):
    # Send all images
    for img in images:
        await send_image(ws, img)
    
    # Generate with progress
    await ws.send(json.dumps({"type": "generate"}))
    
    # Track progress
    while True:
        msg = json.loads(await ws.recv())
        if msg["type"] == "progress":
            update_progress_bar(msg["progress"])
        elif msg["type"] == "complete":
            return msg["glb_base64"]
```

### 3. Incremental Preview

Show real-time preview as more images are added:

```javascript
let previewModel = null;

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    if (msg.type === 'delta') {
        // Update 3D viewer with new point cloud
        previewModel = loadGLB(msg.glb_base64);
        viewer.updateModel(previewModel);
    }
};

// Request incremental updates after each batch
const uploadBatch = async (batch) => {
    for (const img of batch) {
        await sendImage(img);
    }
    ws.send(JSON.stringify({
        type: 'generate',
        incremental: true
    }));
};
```

## Performance Optimization

1. **Adjust Resolution**: Lower `process_res` for faster processing
   ```bash
   POST /ws/session/create?process_res=256  # Faster
   POST /ws/session/create?process_res=1024 # Higher quality
   ```

2. **Limit Points**: Reduce point cloud size
   ```bash
   POST /ws/session/create?num_max_points=1000000  # Smaller file
   ```

3. **Batch Images**: Send images in groups rather than one-by-one

4. **Connection Reuse**: Keep WebSocket connection open for multiple operations

## Troubleshooting

**Session not found:**
- Session may have timed out (default: 1 hour)
- Create a new session

**WebSocket connection failed:**
- Check server is running
- Verify URL format: `ws://` not `http://`
- Check firewall/network settings

**Out of memory:**
- Reduce `process_res`
- Reduce `num_max_points`
- Process fewer images per session

**Slow processing:**
- Lower resolution
- Use GPU if available
- Reduce number of images

## Next Steps

- Read the full [WebSocket API Documentation](docs/WEBSOCKET_API.md)
- Explore the [Python client example](examples/websocket_client.py)
- Try the [HTML client example](examples/websocket_client.html)
- Check the [API Reference](docs/WEBSOCKET_API.md#api-reference)

## Support

For issues or questions:
- Check server logs for errors
- Review the [troubleshooting guide](docs/WEBSOCKET_API.md#troubleshooting)
- Monitor session status: `GET /ws/session/{session_id}`
- Check dashboard: `http://localhost:8000/dashboard`

