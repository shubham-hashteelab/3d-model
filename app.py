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
Hugging Face Spaces App for Depth Anything 3.

This app uses the @spaces.GPU decorator to dynamically allocate GPU resources
for model inference on Hugging Face Spaces.
"""

import os
import spaces
from depth_anything_3.app.gradio_app import DepthAnything3App
from depth_anything_3.app.modules.model_inference import ModelInference

# Monkey-patch the run_inference method to use @spaces.GPU decorator
# This allows dynamic GPU allocation on Hugging Face Spaces
original_run_inference = ModelInference.run_inference

@spaces.GPU(duration=120)  # Request GPU for up to 120 seconds per inference
def gpu_run_inference(self, *args, **kwargs):
    """
    GPU-accelerated inference with Spaces decorator.
    
    This function wraps the original run_inference method with @spaces.GPU,
    which ensures the model is moved to GPU when needed on HF Spaces.
    """
    return original_run_inference(self, *args, **kwargs)

# Replace the original method with the GPU-decorated version
ModelInference.run_inference = gpu_run_inference

# Initialize and launch the app
if __name__ == "__main__":
    # Configure directories for Hugging Face Spaces
    model_dir = os.environ.get("DA3_MODEL_DIR", "depth-anything/DA3NESTED-GIANT-LARGE")
    workspace_dir = os.environ.get("DA3_WORKSPACE_DIR", "workspace/gradio")
    gallery_dir = os.environ.get("DA3_GALLERY_DIR", "workspace/gallery")
    
    # Create directories if they don't exist
    os.makedirs(workspace_dir, exist_ok=True)
    os.makedirs(gallery_dir, exist_ok=True)
    
    # Initialize the app
    app = DepthAnything3App(
        model_dir=model_dir,
        workspace_dir=workspace_dir,
        gallery_dir=gallery_dir
    )
    
    # Launch with Spaces-friendly settings
    print("🚀 Launching Depth Anything 3 on Hugging Face Spaces...")
    print(f"📦 Model Directory: {model_dir}")
    print(f"📁 Workspace Directory: {workspace_dir}")
    print(f"🖼️  Gallery Directory: {gallery_dir}")
    
    app.launch(
        host="0.0.0.0",  # Required for Spaces
        port=7860,       # Standard Gradio port
        share=False,     # Not needed on Spaces
        debug=False
    )
