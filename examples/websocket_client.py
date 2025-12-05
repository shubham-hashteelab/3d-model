#!/usr/bin/env python3
"""
Example WebSocket client for real-time 3D reconstruction.

This script demonstrates how to:
1. Create a WebSocket session
2. Stream images to the server
3. Receive incremental point cloud updates
4. Save the final GLB file

Usage:
    python websocket_client.py --images path/to/images/*.png
    python websocket_client.py --video path/to/video.mp4 --num-frames 20
"""

import asyncio
import websockets
import json
import base64
import argparse
import os
from pathlib import Path
from typing import List
import requests
import cv2
from PIL import Image
import io


class ReconstructionClient:
    """WebSocket client for 3D reconstruction."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.session_id = None
        self.received_glb = None
        self.metadata = None
    
    def create_session(self, max_images: int = 100, **kwargs) -> str:
        """Create a new WebSocket session.
        
        Args:
            max_images: Maximum number of images to process
            **kwargs: Additional session configuration
            
        Returns:
            Session ID
        """
        response = requests.post(
            f"{self.base_url}/ws/session/create",
            params={
                "max_images": max_images,
                **kwargs
            }
        )
        response.raise_for_status()
        
        data = response.json()
        self.session_id = data["session_id"]
        print(f"✓ Created session: {self.session_id}")
        print(f"  Max images: {data['max_images']}")
        print(f"  Config: {data['config']}")
        
        return self.session_id
    
    def get_session_info(self, session_id: str = None) -> dict:
        """Get session information."""
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session ID provided")
        
        response = requests.get(f"{self.base_url}/ws/session/{sid}")
        response.raise_for_status()
        return response.json()
    
    def delete_session(self, session_id: str = None):
        """Delete a session."""
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session ID provided")
        
        response = requests.delete(f"{self.base_url}/ws/session/{sid}")
        response.raise_for_status()
        print(f"✓ Deleted session: {sid}")
    
    async def send_images_and_reconstruct(
        self,
        image_paths: List[str],
        incremental: bool = True,
        save_output: str = "output.glb"
    ):
        """Send images via WebSocket and receive 3D reconstruction.
        
        Args:
            image_paths: List of image file paths
            incremental: Whether to request incremental updates
            save_output: Path to save final GLB file
        """
        if not self.session_id:
            raise ValueError("No session created. Call create_session() first.")
        
        ws_endpoint = f"{self.ws_url}/ws/reconstruct/{self.session_id}"
        
        print(f"\n🔌 Connecting to WebSocket: {ws_endpoint}")
        
        async with websockets.connect(ws_endpoint) as websocket:
            # Wait for connection acknowledgment
            response = await websocket.recv()
            msg = json.loads(response)
            print(f"✓ Connected: {msg}")
            
            # Send images
            print(f"\n📤 Sending {len(image_paths)} images...")
            for i, image_path in enumerate(image_paths, 1):
                # Read and encode image
                with open(image_path, "rb") as f:
                    image_data = f.read()
                
                image_b64 = base64.b64encode(image_data).decode('utf-8')
                
                # Send image
                await websocket.send(json.dumps({
                    "type": "image",
                    "data": image_b64,
                    "filename": os.path.basename(image_path)
                }))
                
                # Wait for acknowledgment
                response = await websocket.recv()
                msg = json.loads(response)
                
                if msg["type"] == "ack":
                    print(f"  [{i}/{len(image_paths)}] ✓ {msg['image_path']}")
                elif msg["type"] == "error":
                    print(f"  [{i}/{len(image_paths)}] ✗ Error: {msg['message']}")
                    continue
            
            # Request generation
            print(f"\n🔨 Requesting 3D reconstruction...")
            await websocket.send(json.dumps({
                "type": "generate",
                "incremental": incremental
            }))
            
            # Receive updates
            while True:
                response = await websocket.recv()
                msg = json.loads(response)
                msg_type = msg["type"]
                
                if msg_type == "progress":
                    stage = msg.get("stage", "processing")
                    progress = msg.get("progress", 0) * 100
                    message = msg.get("message", "")
                    print(f"  [{stage}] {progress:.1f}% - {message}")
                
                elif msg_type == "delta":
                    image_count = msg.get("image_count", 0)
                    glb_data = msg.get("glb_base64", "")
                    metadata = msg.get("metadata", {})
                    glb_size = metadata.get("glb_size_bytes", 0)
                    
                    print(f"\n📊 Received delta update:")
                    print(f"  Images processed: {image_count}")
                    print(f"  GLB size: {glb_size / 1024:.1f} KB")
                    
                    # Decode and save intermediate result
                    if glb_data and save_output:
                        self.received_glb = base64.b64decode(glb_data)
                        intermediate_path = save_output.replace(".glb", f"_intermediate_{image_count}.glb")
                        with open(intermediate_path, "wb") as f:
                            f.write(self.received_glb)
                        print(f"  ✓ Saved intermediate: {intermediate_path}")
                
                elif msg_type == "complete":
                    image_count = msg.get("image_count", 0)
                    glb_data = msg.get("glb_base64", "")
                    self.metadata = msg.get("metadata", {})
                    glb_size = self.metadata.get("glb_size_bytes", 0)
                    
                    print(f"\n✅ Reconstruction complete!")
                    print(f"  Images processed: {image_count}")
                    print(f"  GLB size: {glb_size / 1024:.1f} KB")
                    
                    # Decode and save final result
                    if glb_data:
                        self.received_glb = base64.b64decode(glb_data)
                        if save_output:
                            with open(save_output, "wb") as f:
                                f.write(self.received_glb)
                            print(f"  ✓ Saved: {save_output}")
                    
                    # Show metadata
                    if "intrinsics" in self.metadata:
                        print(f"  Camera intrinsics available: {len(self.metadata['intrinsics'])} cameras")
                    if "extrinsics" in self.metadata:
                        print(f"  Camera extrinsics available: {len(self.metadata['extrinsics'])} cameras")
                    
                    break
                
                elif msg_type == "error":
                    print(f"\n❌ Error: {msg['message']}")
                    break
                
                else:
                    print(f"\n⚠️  Unknown message type: {msg_type}")
    
    async def finalize_session(self, save_output: str = "output.glb"):
        """Finalize session and get final reconstruction."""
        if not self.session_id:
            raise ValueError("No session created")
        
        ws_endpoint = f"{self.ws_url}/ws/reconstruct/{self.session_id}"
        
        async with websockets.connect(ws_endpoint) as websocket:
            # Wait for connection
            await websocket.recv()
            
            # Request finalization
            print(f"\n🏁 Finalizing session...")
            await websocket.send(json.dumps({
                "type": "finalize"
            }))
            
            # Receive final result
            while True:
                response = await websocket.recv()
                msg = json.loads(response)
                msg_type = msg["type"]
                
                if msg_type == "progress":
                    progress = msg.get("progress", 0) * 100
                    message = msg.get("message", "")
                    print(f"  {progress:.1f}% - {message}")
                
                elif msg_type == "complete":
                    glb_data = msg.get("glb_base64", "")
                    self.metadata = msg.get("metadata", {})
                    
                    print(f"\n✅ Session finalized!")
                    
                    if glb_data:
                        self.received_glb = base64.b64decode(glb_data)
                        if save_output:
                            with open(save_output, "wb") as f:
                                f.write(self.received_glb)
                            print(f"  ✓ Saved: {save_output}")
                    
                    break
                
                elif msg_type == "error":
                    print(f"\n❌ Error: {msg['message']}")
                    break


def extract_video_frames(video_path: str, num_frames: int = 10) -> List[str]:
    """Extract frames from video.
    
    Args:
        video_path: Path to video file
        num_frames: Number of frames to extract
        
    Returns:
        List of paths to extracted frames
    """
    import tempfile
    
    temp_dir = tempfile.mkdtemp(prefix="video_frames_")
    print(f"Extracting {num_frames} frames from {video_path}...")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_indices = [int(i * total_frames / num_frames) for i in range(num_frames)]
    
    frame_paths = []
    for i, frame_idx in enumerate(frame_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            print(f"  Warning: Failed to read frame {frame_idx}")
            continue
        
        frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
        cv2.imwrite(frame_path, frame)
        frame_paths.append(frame_path)
        print(f"  Extracted frame {i+1}/{num_frames}")
    
    cap.release()
    print(f"✓ Extracted {len(frame_paths)} frames to {temp_dir}")
    
    return frame_paths


async def main():
    parser = argparse.ArgumentParser(description="WebSocket client for 3D reconstruction")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the server")
    parser.add_argument("--images", nargs="+", help="Image files to process")
    parser.add_argument("--video", help="Video file to process")
    parser.add_argument("--num-frames", type=int, default=10, help="Number of frames to extract from video")
    parser.add_argument("--output", default="output.glb", help="Output GLB file path")
    parser.add_argument("--incremental", action="store_true", help="Request incremental updates")
    parser.add_argument("--max-images", type=int, default=100, help="Maximum images per session")
    parser.add_argument("--delete-session", action="store_true", help="Delete session after completion")
    
    args = parser.parse_args()
    
    # Get image paths
    image_paths = []
    if args.images:
        image_paths = args.images
    elif args.video:
        image_paths = extract_video_frames(args.video, args.num_frames)
    else:
        parser.error("Either --images or --video must be provided")
    
    if not image_paths:
        print("❌ No images to process")
        return
    
    # Create client
    client = ReconstructionClient(base_url=args.base_url)
    
    try:
        # Create session
        client.create_session(max_images=args.max_images)
        
        # Send images and reconstruct
        await client.send_images_and_reconstruct(
            image_paths=image_paths,
            incremental=args.incremental,
            save_output=args.output
        )
        
        # Get session info
        session_info = client.get_session_info()
        print(f"\n📊 Session info:")
        print(f"  Status: {session_info['status']}")
        print(f"  Images: {session_info['image_count']}/{session_info['max_images']}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if args.delete_session and client.session_id:
            client.delete_session()


if __name__ == "__main__":
    asyncio.run(main())

