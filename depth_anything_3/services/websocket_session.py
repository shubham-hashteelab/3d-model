# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
WebSocket session manager for real-time 3D reconstruction.
Handles image streaming and incremental point cloud generation.
"""

import os
import time
import uuid
import tempfile
import shutil
import base64
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
from PIL import Image
import io

from ..utils.logger import logger


@dataclass
class WebSocketSession:
    """WebSocket session for incremental 3D reconstruction."""
    
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    temp_dir: Optional[str] = None
    image_paths: List[str] = field(default_factory=list)
    image_count: int = 0
    status: str = "active"  # active, processing, completed, error
    error_message: Optional[str] = None
    
    # Point cloud accumulation state
    accumulated_points: Optional[np.ndarray] = None
    accumulated_colors: Optional[np.ndarray] = None
    last_point_count: int = 0
    
    # Configuration
    max_images: int = 100
    process_res: int = 504
    process_res_method: str = "upper_bound_resize"
    conf_thresh_percentile: float = 10.0
    num_max_points: int = 10_000_000
    show_cameras: bool = True

    # Auto-generation settings
    auto_generate_after: int = 0  # 0 = disabled, N = generate after N images
    last_auto_generate_count: int = 0  # Track when we last auto-generated
    
    def __post_init__(self):
        """Initialize temporary directory."""
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix=f"ws_session_{self.session_id}_")
            logger.info(f"Created temp directory for session {self.session_id}: {self.temp_dir}")
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()
    
    def add_image(self, image_data: bytes, filename: Optional[str] = None) -> str:
        """Add image to session and save to disk.
        
        Args:
            image_data: Raw image bytes (PNG, JPEG, etc.)
            filename: Optional filename (generated if not provided)
            
        Returns:
            Path to saved image
        """
        self.update_activity()
        
        if self.image_count >= self.max_images:
            raise ValueError(f"Session has reached maximum image limit ({self.max_images})")
        
        if filename is None:
            filename = f"image_{self.image_count:04d}.png"
        
        # Save image to temp directory
        image_path = os.path.join(self.temp_dir, filename)
        
        # Decode and validate image
        try:
            img = Image.open(io.BytesIO(image_data))
            img.save(image_path)
            logger.info(f"Session {self.session_id}: Saved image {filename} ({img.size})")
        except Exception as e:
            logger.error(f"Session {self.session_id}: Failed to save image: {e}")
            raise ValueError(f"Invalid image data: {e}")
        
        self.image_paths.append(image_path)
        self.image_count += 1
        
        return image_path
    
    def cleanup(self):
        """Clean up session resources."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up session {self.session_id} temp directory")
            except Exception as e:
                logger.error(f"Failed to cleanup session {self.session_id}: {e}")
        
        self.status = "completed"
        self.accumulated_points = None
        self.accumulated_colors = None


class WebSocketSessionManager:
    """Manager for WebSocket sessions."""
    
    def __init__(self, max_sessions: int = 100, session_timeout: float = 3600.0):
        """Initialize session manager.
        
        Args:
            max_sessions: Maximum number of concurrent sessions
            session_timeout: Session timeout in seconds (default 1 hour)
        """
        self.sessions: Dict[str, WebSocketSession] = {}
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self._cleanup_task: Optional[asyncio.Task] = None
        logger.info(f"WebSocket session manager initialized (max_sessions={max_sessions}, timeout={session_timeout}s)")
    
    def create_session(self, **kwargs) -> WebSocketSession:
        """Create a new WebSocket session.
        
        Args:
            **kwargs: Session configuration parameters
            
        Returns:
            Created session
        """
        # Cleanup old sessions if at capacity
        if len(self.sessions) >= self.max_sessions:
            self._cleanup_old_sessions(force=True)
        
        if len(self.sessions) >= self.max_sessions:
            raise RuntimeError(f"Maximum number of sessions ({self.max_sessions}) reached")
        
        session_id = str(uuid.uuid4())
        session = WebSocketSession(session_id=session_id, **kwargs)
        self.sessions[session_id] = session
        
        logger.info(f"Created session {session_id} (total sessions: {len(self.sessions)})")
        return session
    
    def get_session(self, session_id: str) -> Optional[WebSocketSession]:
        """Get session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session or None if not found
        """
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session and cleanup resources.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if session was deleted, False if not found
        """
        session = self.sessions.pop(session_id, None)
        if session:
            session.cleanup()
            logger.info(f"Deleted session {session_id} (remaining sessions: {len(self.sessions)})")
            return True
        return False
    
    def _cleanup_old_sessions(self, force: bool = False):
        """Cleanup expired sessions.
        
        Args:
            force: If True, cleanup oldest sessions even if not expired
        """
        current_time = time.time()
        sessions_to_delete = []
        
        for session_id, session in self.sessions.items():
            age = current_time - session.last_activity
            if age > self.session_timeout:
                sessions_to_delete.append(session_id)
        
        # If force and still no sessions to delete, delete oldest
        if force and not sessions_to_delete and self.sessions:
            oldest_session = min(self.sessions.values(), key=lambda s: s.last_activity)
            sessions_to_delete.append(oldest_session.session_id)
        
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
        
        if sessions_to_delete:
            logger.info(f"Cleaned up {len(sessions_to_delete)} expired sessions")
    
    async def start_cleanup_task(self, interval: float = 300.0):
        """Start background cleanup task.
        
        Args:
            interval: Cleanup interval in seconds (default 5 minutes)
        """
        while True:
            await asyncio.sleep(interval)
            self._cleanup_old_sessions()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics.
        
        Returns:
            Statistics dictionary
        """
        active_sessions = sum(1 for s in self.sessions.values() if s.status == "active")
        processing_sessions = sum(1 for s in self.sessions.values() if s.status == "processing")
        total_images = sum(s.image_count for s in self.sessions.values())
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "processing_sessions": processing_sessions,
            "max_sessions": self.max_sessions,
            "total_images": total_images,
            "session_timeout": self.session_timeout,
        }


# Global session manager instance
_session_manager: Optional[WebSocketSessionManager] = None


def get_session_manager() -> WebSocketSessionManager:
    """Get global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = WebSocketSessionManager()
    return _session_manager

