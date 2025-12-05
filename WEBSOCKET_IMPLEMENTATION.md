# WebSocket Implementation Summary

## Overview

This document summarizes the WebSocket implementation for real-time 3D reconstruction in the Depth Anything 3 backend.

## What Was Implemented

### 1. Session Management System

**File**: `depth_anything_3/services/websocket_session.py`

A comprehensive session management system that:
- Creates and manages WebSocket sessions with unique IDs
- Stores uploaded images in temporary directories
- Tracks session state (active, processing, completed, error)
- Automatically cleans up old sessions (1-hour timeout by default)
- Limits concurrent sessions (100 by default)
- Supports incremental point cloud accumulation

**Key Classes**:
- `WebSocketSession`: Represents a single reconstruction session
- `WebSocketSessionManager`: Manages multiple sessions, cleanup, and statistics

### 2. WebSocket API Endpoints

**File**: `depth_anything_3/services/backend.py` (additions)

Added the following endpoints:

#### HTTP Endpoints

1. **POST /ws/session/create** - Create a new WebSocket session
   - Parameters: max_images, process_res, process_res_method, conf_thresh_percentile, etc.
   - Returns: session_id and configuration

2. **GET /ws/session/{session_id}** - Get session information
   - Returns: status, image count, timestamps, error messages

3. **DELETE /ws/session/{session_id}** - Delete a session
   - Cleans up temporary files and resources

4. **GET /ws/sessions** - List all sessions with statistics
   - Returns: session list and aggregate stats

#### WebSocket Endpoint

**WS /ws/reconstruct/{session_id}** - Main WebSocket endpoint

Supports the following message types:

**Client → Server**:
- `image`: Upload an image (base64 encoded)
- `generate`: Request point cloud generation (incremental or full)
- `finalize`: Finalize session and get final result
- `ping`: Keep-alive message

**Server → Client**:
- `connected`: Connection acknowledgment
- `ack`: Image upload acknowledgment
- `progress`: Processing progress updates
- `delta`: Incremental point cloud update (with GLB data)
- `complete`: Final reconstruction result (with GLB data)
- `error`: Error message
- `pong`: Keep-alive response

### 3. Background Cleanup Task

Implemented automatic session cleanup:
- Runs every 5 minutes
- Removes sessions inactive for more than 1 hour
- Enforces maximum session limits
- Cleans up temporary files

### 4. Example Clients

#### Python Client
**File**: `examples/websocket_client.py`

Full-featured command-line client that:
- Creates sessions via HTTP API
- Connects to WebSocket endpoint
- Uploads images (from files or video frames)
- Receives progress updates
- Saves GLB files
- Supports incremental updates
- Handles errors gracefully

Usage:
```bash
python examples/websocket_client.py --images img1.png img2.png
python examples/websocket_client.py --video video.mp4 --num-frames 20
```

#### HTML/JavaScript Client
**File**: `examples/websocket_client.html`

Interactive web-based client with:
- Modern, responsive UI
- Drag-and-drop image upload
- Real-time progress bar
- Preview of uploaded images
- Session management
- Download link for GLB files
- Error handling and status updates

### 5. Documentation

Created comprehensive documentation:

1. **WEBSOCKET_QUICKSTART.md** - Quick start guide with examples
2. **docs/WEBSOCKET_API.md** - Complete API reference
3. **WEBSOCKET_IMPLEMENTATION.md** - This file
4. **Updated README.md** - Added WebSocket feature overview

### 6. Testing

**File**: `tests/test_websocket.py`

Automated tests for:
- Session creation
- Session retrieval
- Session listing
- Session deletion
- Error handling (404 for non-existent sessions)

## Architecture

```
┌─────────────┐
│   Client    │
│ (Browser/   │
│  Python)    │
└──────┬──────┘
       │
       │ HTTP POST /ws/session/create
       │
       ▼
┌─────────────────────────────────┐
│   SessionManager                │
│   - Creates session             │
│   - Assigns session_id          │
│   - Creates temp directory      │
└──────┬──────────────────────────┘
       │
       │ Returns session_id
       │
       ▼
┌─────────────┐
│   Client    │
│  Connects   │
│  WebSocket  │
└──────┬──────┘
       │
       │ WS /ws/reconstruct/{session_id}
       │
       ▼
┌─────────────────────────────────┐
│   WebSocket Handler             │
│   - Receives images             │
│   - Stores to session temp_dir  │
│   - Sends ACKs                  │
└──────┬──────────────────────────┘
       │
       │ Client sends "generate"
       │
       ▼
┌─────────────────────────────────┐
│   Model Inference               │
│   - Loads model                 │
│   - Processes all images        │
│   - Generates depth maps        │
│   - Creates point cloud         │
└──────┬──────────────────────────┘
       │
       │ Exports GLB
       │
       ▼
┌─────────────────────────────────┐
│   GLB Export                    │
│   - Generates 3D mesh           │
│   - Encodes as base64           │
│   - Sends via WebSocket         │
└──────┬──────────────────────────┘
       │
       │ "complete" message
       │
       ▼
┌─────────────┐
│   Client    │
│   Receives  │
│   GLB data  │
└─────────────┘
```

## Data Flow

### Typical Session Flow

1. **Session Creation**
   ```
   Client → POST /ws/session/create
   Server → {"session_id": "abc123", ...}
   ```

2. **WebSocket Connection**
   ```
   Client → WS /ws/reconstruct/abc123
   Server → {"type": "connected", ...}
   ```

3. **Image Upload**
   ```
   Client → {"type": "image", "data": "base64...", "filename": "img1.png"}
   Server → {"type": "ack", "image_count": 1, ...}
   Client → {"type": "image", "data": "base64...", "filename": "img2.png"}
   Server → {"type": "ack", "image_count": 2, ...}
   ```

4. **Generation Request**
   ```
   Client → {"type": "generate", "incremental": true}
   Server → {"type": "progress", "progress": 0.1, "message": "Loading model..."}
   Server → {"type": "progress", "progress": 0.3, "message": "Processing..."}
   Server → {"type": "progress", "progress": 0.7, "message": "Exporting..."}
   Server → {"type": "complete", "glb_base64": "...", "metadata": {...}}
   ```

5. **Session Cleanup** (optional)
   ```
   Client → DELETE /ws/session/abc123
   Server → {"success": true}
   ```

## Key Features

### 1. Incremental Updates

The system supports incremental point cloud generation:
- Client can request `"incremental": true`
- Server sends `delta` messages with partial results
- Useful for real-time preview as images are added

### 2. Session Persistence

Sessions persist across WebSocket disconnections:
- Images remain in temporary storage
- Client can reconnect to same session
- Session state is maintained

### 3. Progress Tracking

Detailed progress updates through multiple stages:
- `loading_model`: Model initialization
- `inference`: Processing images
- `exporting`: Generating GLB file
- `finalizing`: Creating final output

### 4. Metadata Extraction

The system extracts and returns:
- Camera intrinsics (3×3 matrices per camera)
- Camera extrinsics (4×4 world-to-camera transforms)
- Depth statistics
- Confidence information
- Point cloud dimensions

### 5. Resource Management

Efficient resource handling:
- Temporary directories for each session
- Automatic cleanup of old sessions
- GPU memory cleanup after inference
- Session limits to prevent overload

## Dependencies

Added to `requirements.txt`:
- `websockets`: WebSocket client/server library
- `python-socketio`: Socket.IO support (future use)
- `python-multipart`: Multipart form data handling

## Configuration

### Session Manager

```python
WebSocketSessionManager(
    max_sessions=100,        # Maximum concurrent sessions
    session_timeout=3600.0   # Session timeout in seconds
)
```

### Session

```python
WebSocketSession(
    max_images=100,                           # Max images per session
    process_res=504,                          # Processing resolution
    process_res_method="upper_bound_resize",  # Resolution method
    conf_thresh_percentile=10.0,              # Confidence threshold
    num_max_points=10_000_000,                # Max points in cloud
    show_cameras=True                         # Show camera wireframes
)
```

## Error Handling

The implementation handles:
- Invalid session IDs (404 errors)
- Session capacity limits (500 errors)
- Invalid image data (error messages via WebSocket)
- Network disconnections (graceful cleanup)
- OOM errors (cleanup and informative messages)
- Timeout handling (automatic session cleanup)

## Security Considerations

Current implementation:
- ✅ CORS configured for all origins (development)
- ✅ Session ID validation
- ✅ Resource limits (max sessions, max images)
- ✅ Automatic cleanup of old sessions
- ❌ No authentication (should be added for production)
- ❌ No rate limiting (should be added for production)
- ❌ No WSS/TLS (should use WSS in production)

For production deployment, add:
1. Authentication middleware
2. Rate limiting per IP/user
3. WSS (WebSocket Secure) with TLS
4. Input validation and sanitization
5. Request size limits
6. DDoS protection

## Performance

### Memory Management

- Each session uses a temporary directory
- Images are stored as files, not in memory
- GPU memory is cleaned up after each inference
- Old sessions are automatically removed

### Scalability

Current limits:
- 100 concurrent sessions (configurable)
- 100 images per session (configurable)
- 10M points per cloud (configurable)

For higher scale:
- Use Redis for session storage
- Implement session queuing
- Add horizontal scaling with load balancer
- Use distributed file storage

## Future Enhancements

Potential improvements:

1. **Streaming Point Clouds**
   - Send point cloud data in chunks
   - Progressive rendering on client side

2. **Advanced Caching**
   - Cache model in memory
   - Reuse partial computations

3. **Multi-GPU Support**
   - Distribute sessions across GPUs
   - Load balancing

4. **Advanced Session Features**
   - Session persistence to disk/database
   - Session sharing between users
   - Session snapshots/checkpoints

5. **Enhanced Metadata**
   - Mesh quality metrics
   - Processing statistics
   - Optimization suggestions

6. **Client SDKs**
   - JavaScript/TypeScript SDK
   - Python SDK
   - Mobile SDKs (iOS/Android)

## Testing

Run the test suite:

```bash
# Start server
python -m depth_anything_3.services.backend --model-dir MODEL_DIR --port 8000

# Run tests
python tests/test_websocket.py --base-url http://localhost:8000
```

## Troubleshooting

Common issues and solutions:

1. **Connection refused**
   - Ensure server is running
   - Check port is not blocked by firewall

2. **Session timeout**
   - Increase timeout in SessionManager
   - Keep connection alive with ping messages

3. **Out of memory**
   - Reduce process_res
   - Reduce num_max_points
   - Process fewer images per session

4. **Slow processing**
   - Ensure GPU is being used
   - Lower resolution/quality settings
   - Check GPU memory availability

## Conclusion

The WebSocket implementation provides a robust, real-time API for 3D reconstruction with:

- ✅ Session-based architecture
- ✅ Real-time image streaming
- ✅ Incremental updates
- ✅ Progress tracking
- ✅ Comprehensive error handling
- ✅ Automatic resource cleanup
- ✅ Full documentation and examples
- ✅ Test coverage

The system is production-ready with some security enhancements needed for public deployment.

