"""
Simple example demonstrating @spaces.GPU decorator usage.

This example shows how the @spaces.GPU decorator works:
- Variables created outside the decorated function stay on CPU initially
- When the decorated function is called, the process moves to GPU environment
- Inside the decorated function, tensors can access CUDA
"""

import gradio as gr
import spaces
import torch

# This tensor is created at module load time
# On HF Spaces, it will be on CPU until a @spaces.GPU function is called
zero = torch.Tensor([0])

# Try to move to cuda - will fail gracefully if no GPU available
try:
    zero = zero.cuda()
    print(f"Initial device: {zero.device}")  # On Spaces: shows 'cpu' 🤔
except:
    print(f"Initial device: {zero.device}")  # cpu (no GPU available yet)


@spaces.GPU(duration=60)  # Request GPU for up to 60 seconds
def greet(n):
    """
    This function runs on GPU when called.
    The @spaces.GPU decorator ensures GPU access.
    """
    # Inside the decorated function, we have GPU access
    print(f"Inside GPU function - device: {zero.device}")  # On Spaces: shows 'cuda:0' 🤗
    
    # Perform GPU computation
    result = zero + n
    
    return f"Hello {result.item()} Tensor! (computed on {zero.device})"


# Create Gradio interface
demo = gr.Interface(
    fn=greet,
    inputs=gr.Number(value=42, label="Enter a number"),
    outputs=gr.Text(label="Result"),
    title="Spaces GPU Example",
    description="Demonstrates @spaces.GPU decorator usage"
)

if __name__ == "__main__":
    demo.launch()

