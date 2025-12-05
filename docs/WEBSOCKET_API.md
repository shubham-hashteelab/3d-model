# WebSocket API for Real-time 3D Reconstruction

This document describes the WebSocket API for streaming images and receiving incremental 3D point cloud updates.

## Overview

The WebSocket API allows clients to:

1. **Create a session** with specific reconstruction parameters
2. **Stream images** via WebSocket in real-time
3. **Receive incremental updates** as the point cloud is generated
4. **Get the final GLB model** with camera metadata

## Quick Start

### 1. Create a Session

First, create a WebSocket session via HTTP POST:

```bash
curl -X POST "http://localhost:8000/ws/session/create?max_images=100&process_res=504"
```

Response:
```json
{
  "success": true,
  "session_id": "abc123-...",
  "created_at": 1234567890.0,
  "max_images": 100,
  "config": {
    "process_res": 504,
    "process_res_method": "upper_bound_resize",
    "conf_thresh_percentile": 10.0,
    "num_max_points": 10000000,
    "show_cameras": true
  }
}
```

### 2. Connect via WebSocket

Connect to the WebSocket endpoint using the session ID:

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/reconstruct/{session_id}`);
```

### 3. Send Images

Send images as base64-encoded data:

```javascript
ws.send(JSON.stringify({
    type: "image",
    data: base64ImageData,
    filename: "image_001.png"
}));
```

### 4. Request Generation

Request point cloud generation:

```javascript
ws.send(JSON.stringify({
    type: "generate",
    incremental: true
}));
```

### 5. Receive Updates

Handle server messages:

```javascript
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    switch (msg.type) {
        case "progress":
            console.log(`Progress: ${msg.progress * 100}%`);
            break;
        case "delta":
            // Incremental update
            const glbData = atob(msg.glb_base64);
            break;
        case "complete":
            // Final result
            const finalGLB = atob(msg.glb_base64);
            break;
    }
};
```

## API Reference

### HTTP Endpoints

#### Create Session

**POST** `/ws/session/create`

Creates a new WebSocket session for 3D reconstruction.

**Query Parameters:**
- `max_images` (int, default=100): Maximum number of images
- `process_res` (int, default=504): Processing resolution
- `process_res_method` (str, default="upper_bound_resize"): Resolution method
- `conf_thresh_percentile` (float, default=10.0): Confidence threshold percentile
- `num_max_points` (int, default=10000000): Maximum points in point cloud
- `show_cameras` (bool, default=true): Include camera visualization

**Response:**
```json
{
  "success": true,
  "session_id": "string",
  "created_at": 1234567890.0,
  "max_images": 100,
  "config": { ... }
}
```

#### Get Session Info

**GET** `/ws/session/{session_id}`

Get information about a session.

**Response:**
```json
{
  "session_id": "string",
  "created_at": 1234567890.0,
  "last_activity": 1234567890.0,
  "status": "active",
  "image_count": 5,
  "max_images": 100,
  "error_message": null
}
```

#### Delete Session

**DELETE** `/ws/session/{session_id}`

Delete a session and cleanup resources.

**Response:**
```json
{
  "success": true,
  "message": "Session abc123 deleted"
}
```

#### List Sessions

**GET** `/ws/sessions`

List all active sessions and statistics.

**Response:**
```json
{
  "stats": {
    "total_sessions": 5,
    "active_sessions": 3,
    "processing_sessions": 2,
    "max_sessions": 100,
    "total_images": 150,
    "session_timeout": 3600.0
  },
  "sessions": [
    {
      "session_id": "abc123",
      "created_at": 1234567890.0,
      "last_activity": 1234567890.0,
      "status": "active",
      "image_count": 10
    }
  ]
}
```

### WebSocket Endpoint

**WS** `/ws/reconstruct/{session_id}`

WebSocket endpoint for real-time reconstruction.

### Message Protocol

#### Client → Server Messages

##### 1. Send Image

```json
{
  "type": "image",
  "data": "base64_encoded_image_data",
  "filename": "optional_filename.png"
}
```

Sends an image to be added to the reconstruction.

##### 2. Generate Point Cloud

```json
{
  "type": "generate",
  "incremental": true
}
```

Request point cloud generation. If `incremental` is true, sends delta updates.

##### 3. Finalize Session

```json
{
  "type": "finalize"
}
```

Generate final point cloud and mark session as completed.

##### 4. Keep-Alive Ping

```json
{
  "type": "ping"
}
```

Keep the connection alive.

#### Server → Client Messages

##### 1. Connection Acknowledgment

```json
{
  "type": "connected",
  "session_id": "abc123",
  "image_count": 0,
  "max_images": 100
}
```

Sent when WebSocket connection is established.

##### 2. Image Acknowledgment

```json
{
  "type": "ack",
  "image_count": 5,
  "session_id": "abc123",
  "image_path": "image_001.png"
}
```

Confirms image was received and saved.

##### 3. Progress Update

```json
{
  "type": "progress",
  "stage": "inference",
  "progress": 0.5,
  "message": "Processing frame 5/10"
}
```

Progress update during processing.

**Stages:**
- `loading_model`: Loading the AI model
- `inference`: Running inference on images
- `exporting`: Generating GLB file
- `finalizing`: Creating final output

##### 4. Delta Update

```json
{
  "type": "delta",
  "image_count": 5,
  "glb_base64": "...",
  "metadata": {
    "num_frames": 5,
    "session_id": "abc123",
    "glb_size_bytes": 1234567,
    "intrinsics": [[...]],
    "extrinsics": [[...]]
  }
}
```

Incremental point cloud update.

##### 5. Complete

```json
{
  "type": "complete",
  "image_count": 10,
  "glb_base64": "...",
  "metadata": {
    "num_frames": 10,
    "session_id": "abc123",
    "glb_size_bytes": 2345678,
    "intrinsics": [[...]],
    "extrinsics": [[...]]
  }
}
```

Final reconstruction result.

##### 6. Error

```json
{
  "type": "error",
  "message": "Error description"
}
```

Error occurred during processing.

##### 7. Keep-Alive Pong

```json
{
  "type": "pong",
  "session_id": "abc123"
}
```

Response to ping message.

## Metadata

The `metadata` object in `delta` and `complete` messages contains:

- `num_frames` (int): Number of frames processed
- `session_id` (str): Session identifier
- `glb_size_bytes` (int): Size of GLB data in bytes
- `intrinsics` (array, optional): Camera intrinsic matrices (3×3 per camera)
- `extrinsics` (array, optional): Camera extrinsic matrices (world-to-camera, 4×4 per camera)

## Example Workflows

### Workflow 1: Batch Upload

1. Create session
2. Connect to WebSocket
3. Upload all images sequentially
4. Request generation once
5. Receive final GLB

```python
# Create session
session_id = create_session()

# Connect
ws = connect(session_id)

# Upload images
for image in images:
    ws.send({"type": "image", "data": encode(image)})

# Generate
ws.send({"type": "generate", "incremental": false})

# Receive result
result = ws.receive()
save_glb(result["glb_base64"])
```

### Workflow 2: Incremental Updates

1. Create session
2. Connect to WebSocket
3. Upload images in batches
4. Request generation after each batch
5. Receive incremental updates
6. Finalize for final result

```python
# Create session
session_id = create_session()
ws = connect(session_id)

# Process in batches
for batch in image_batches:
    # Upload batch
    for image in batch:
        ws.send({"type": "image", "data": encode(image)})
    
    # Generate incremental update
    ws.send({"type": "generate", "incremental": true})
    
    # Receive delta
    delta = ws.receive()
    update_preview(delta["glb_base64"])

# Finalize
ws.send({"type": "finalize"})
final = ws.receive()
save_glb(final["glb_base64"])
```

### Workflow 3: Live Streaming

1. Create session
2. Connect to WebSocket
3. Stream images from camera
4. Request generation periodically
5. Show live preview

```python
session_id = create_session()
ws = connect(session_id)

while capturing:
    # Capture frame
    frame = camera.read()
    ws.send({"type": "image", "data": encode(frame)})
    
    # Generate every N frames
    if frame_count % 10 == 0:
        ws.send({"type": "generate", "incremental": true})
        delta = ws.receive()
        show_preview(delta["glb_base64"])
```

## Client Examples

### Python Client

See `examples/websocket_client.py` for a complete Python client implementation.

```bash
# Process images
python examples/websocket_client.py --images img1.png img2.png img3.png

# Process video
python examples/websocket_client.py --video video.mp4 --num-frames 20
```

### JavaScript/HTML Client

See `examples/websocket_client.html` for a web-based client.

```bash
# Serve the HTML file
python -m http.server 8080

# Open in browser
open http://localhost:8080/examples/websocket_client.html
```

## Session Management

### Session Lifecycle

1. **Created**: Session is created and ready to receive images
2. **Active**: Receiving images and/or generating point clouds
3. **Processing**: Currently running inference
4. **Completed**: Finalized and ready for cleanup
5. **Error**: An error occurred

### Automatic Cleanup

Sessions are automatically cleaned up after:
- **1 hour** of inactivity (default timeout)
- **Manual deletion** via DELETE endpoint
- **Server shutdown**

### Session Limits

- **Max concurrent sessions**: 100 (default)
- **Max images per session**: Configurable (default: 100)
- **Session timeout**: 3600 seconds (1 hour)

## Error Handling

Common errors and solutions:

### "Session not found"
- Session may have expired
- Check session ID is correct
- Create a new session

### "Session has reached maximum image limit"
- Finalize current session
- Create a new session for more images

### "Out of memory"
- Reduce `process_res` parameter
- Reduce `num_max_points` parameter
- Process fewer images per session

### "WebSocket disconnected"
- Network interruption
- Reconnect to same session
- Session data is preserved

## Performance Tips

1. **Batch images**: Send images in groups for better efficiency
2. **Optimize resolution**: Lower `process_res` for faster processing
3. **Incremental updates**: Use for real-time preview
4. **Cleanup sessions**: Delete completed sessions to free resources
5. **Connection pooling**: Reuse WebSocket connections when possible

## Security Considerations

1. **Authentication**: Add authentication to session creation endpoint
2. **Rate limiting**: Implement rate limits on session creation
3. **Resource limits**: Configure max sessions and images per session
4. **CORS**: Configure appropriate CORS policies
5. **Encryption**: Use WSS (WebSocket Secure) in production

## Troubleshooting

### Enable Debug Logging

Set environment variable:
```bash
export LOG_LEVEL=DEBUG
```

### Check Session Status

```bash
curl http://localhost:8000/ws/session/{session_id}
```

### List All Sessions

```bash
curl http://localhost:8000/ws/sessions
```

### Monitor Server Logs

Check server console output for detailed error messages.

## API Versioning

Current version: **v1.0.0**

Future versions will maintain backward compatibility where possible.

