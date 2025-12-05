---
title: Depth Anything 3
emoji: 🏢
colorFrom: indigo
colorTo: pink
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
python_version: 3.11
pinned: false
license: cc-by-nc-4.0
---

# Depth Anything 3 - 3D Model Generation

High-quality 3D model generation from images and videos using Depth Anything 3.

## Features

- 🎨 **Web Interface**: Easy-to-use Gradio interface for uploading images/videos
- 🚀 **FastAPI Backend**: High-performance REST API for batch processing
- 📡 **WebSocket API**: Real-time streaming and incremental 3D reconstruction
- 🎯 **Multiple Export Formats**: GLB, PLY, NPZ with camera metadata
- 📊 **Dashboard**: Monitor processing tasks and system status
- 🖼️ **Gallery**: Browse and visualize generated 3D models

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Run Gradio Interface

```bash
python app.py
```

Open http://localhost:7860 in your browser.

### Run Backend Server

```bash
python -m depth_anything_3.services.backend \
    --model-dir depth-anything/DA3NESTED-GIANT-LARGE \
    --host 0.0.0.0 \
    --port 8000
```

Access:
- Dashboard: http://localhost:8000/dashboard
- API Docs: http://localhost:8000/docs
- Gallery: http://localhost:8000/gallery

## API Usage

### REST API

Process images via REST API:

```python
import requests

# Upload images
files = [
    ('files', open('image1.png', 'rb')),
    ('files', open('image2.png', 'rb'))
]

response = requests.post(
    'http://localhost:8000/process-files',
    files=files,
    data={'num_frames': 10, 'output_format': 'glb'}
)

# Save GLB file
with open('output.glb', 'wb') as f:
    f.write(response.content)
```

### WebSocket API

Stream images in real-time:

```python
import asyncio
import websockets
import json
import base64

async def reconstruct():
    # Create session
    session_id = create_session()
    
    # Connect WebSocket
    uri = f"ws://localhost:8000/ws/reconstruct/{session_id}"
    async with websockets.connect(uri) as ws:
        # Send images
        for img_path in image_paths:
            with open(img_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode()
            
            await ws.send(json.dumps({
                "type": "image",
                "data": data
            }))
        
        # Generate 3D model
        await ws.send(json.dumps({
            "type": "generate",
            "incremental": True
        }))
        
        # Receive updates
        while True:
            msg = json.loads(await ws.recv())
            if msg["type"] == "complete":
                glb_data = base64.b64decode(msg["glb_base64"])
                break

asyncio.run(reconstruct())
```

See [WEBSOCKET_QUICKSTART.md](WEBSOCKET_QUICKSTART.md) for more details.

## Examples

### Python Client

```bash
# Process images
python examples/websocket_client.py --images img1.png img2.png img3.png

# Process video
python examples/websocket_client.py --video video.mp4 --num-frames 30
```

### HTML Client

```bash
# Serve example
cd examples
python -m http.server 8080

# Open http://localhost:8080/websocket_client.html
```

## Documentation

- [WebSocket API Quick Start](WEBSOCKET_QUICKSTART.md)
- [WebSocket API Reference](docs/WEBSOCKET_API.md)
- [Python Client Example](examples/websocket_client.py)
- [HTML Client Example](examples/websocket_client.html)

## Configuration

Key parameters:

- `process_res`: Processing resolution (default: 504)
- `num_max_points`: Maximum points in point cloud (default: 10M)
- `conf_thresh_percentile`: Confidence threshold percentile (default: 10.0)
- `show_cameras`: Include camera visualization (default: true)

## System Requirements

- Python 3.10+
- CUDA-capable GPU (recommended)
- 8GB+ GPU memory for high-resolution processing

## License

CC-BY-NC-4.0

## Reference

Check out the [Hugging Face Spaces configuration reference](https://huggingface.co/docs/hub/spaces-config-reference)
