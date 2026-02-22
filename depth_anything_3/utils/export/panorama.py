"""
Panorama export module for Depth Anything 3.

Generates a flattened 2D panoramic image by:
1. Back-projecting all frame pixels into 3D world space using depth + camera params
2. Computing the optimal viewing direction from the camera trajectory
3. Orthographically projecting the colored 3D point cloud onto a 2D plane
4. Rendering the result as a clean 2D image

This avoids per-frame warping artifacts and produces a coherent single-viewpoint render.
"""

from __future__ import annotations

import os
from typing import Tuple

import cv2
import numpy as np


def _as_homogeneous44(ext: np.ndarray) -> np.ndarray:
    """Accept (4,4) or (3,4) extrinsic, return (4,4) homogeneous matrix."""
    if ext.shape == (4, 4):
        return ext.astype(np.float64)
    if ext.shape == (3, 4):
        H = np.eye(4, dtype=np.float64)
        H[:3, :4] = ext
        return H
    raise ValueError(f"extrinsic must be (4,4) or (3,4), got {ext.shape}")


def _backproject_to_world(
    images: np.ndarray,
    depths: np.ndarray,
    intrinsics: np.ndarray,
    extrinsics: np.ndarray,
    subsample: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Back-project all pixels from all frames into 3D world coordinates.

    Args:
        images: (N, H, W, 3) uint8 RGB
        depths: (N, H, W) float depth maps
        intrinsics: (N, 3, 3) camera intrinsics
        extrinsics: (N, 4, 4) world-to-camera transforms
        subsample: Take every Nth pixel to reduce memory (1 = all pixels)

    Returns:
        points_world: (M, 3) float64 world coordinates
        colors: (M, 3) uint8 RGB colors
    """
    N, H, W = depths.shape

    # Build pixel grid (optionally subsampled)
    us, vs = np.meshgrid(np.arange(0, W, subsample), np.arange(0, H, subsample))
    ones = np.ones_like(us)
    pix = np.stack([us, vs, ones], axis=-1).reshape(-1, 3).astype(np.float64)  # (P, 3)

    all_pts = []
    all_cols = []

    for i in range(N):
        d = depths[i]
        img = images[i]

        # Get depth values at subsampled positions
        d_sub = d[::subsample, ::subsample].reshape(-1)
        img_sub = img[::subsample, ::subsample].reshape(-1, 3)

        # Valid mask
        valid = np.isfinite(d_sub) & (d_sub > 0)
        valid_idx = np.flatnonzero(valid)

        if len(valid_idx) == 0:
            continue

        K_inv = np.linalg.inv(intrinsics[i].astype(np.float64))
        c2w = np.linalg.inv(_as_homogeneous44(extrinsics[i]))

        # Back-project: pixel -> camera coords -> world coords
        rays = (K_inv @ pix[valid_idx].T)  # (3, M)
        Xc = rays * d_sub[valid_idx][None, :]  # (3, M)
        Xc_h = np.vstack([Xc, np.ones((1, Xc.shape[1]))])  # (4, M)
        Xw = (c2w @ Xc_h)[:3].T.astype(np.float64)  # (M, 3)

        cols = img_sub[valid_idx].astype(np.uint8)

        all_pts.append(Xw)
        all_cols.append(cols)

    if len(all_pts) == 0:
        return np.zeros((0, 3), dtype=np.float64), np.zeros((0, 3), dtype=np.uint8)

    return np.concatenate(all_pts, 0), np.concatenate(all_cols, 0)


def _compute_viewing_direction(
    extrinsics: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute the optimal viewing direction from camera trajectory.

    For a linear camera sweep (e.g. scanning a cabinet), the average
    forward direction of all cameras gives the best projection angle.

    Also computes the "up" and "right" vectors for the projection plane.

    Args:
        extrinsics: (N, 4, 4) world-to-camera transforms

    Returns:
        forward: (3,) average camera forward direction (pointing into the scene)
        right: (3,) right direction on the projection plane
        up: (3,) up direction on the projection plane
    """
    N = extrinsics.shape[0]

    forwards = []
    ups = []
    positions = []

    for i in range(N):
        c2w = np.linalg.inv(_as_homogeneous44(extrinsics[i]))
        # Camera forward is -Z in camera frame, which is the 3rd column of rotation negated,
        # but in c2w, column 2 (Z-axis) points backward, so forward = -c2w[:3, 2]
        fwd = -c2w[:3, 2]
        fwd = fwd / (np.linalg.norm(fwd) + 1e-12)
        forwards.append(fwd)

        # Camera up is Y in camera frame = c2w[:3, 1]
        # But in CV convention Y points down, so up = -c2w[:3, 1]
        up = -c2w[:3, 1]
        up = up / (np.linalg.norm(up) + 1e-12)
        ups.append(up)

        # Camera position
        positions.append(c2w[:3, 3])

    forwards = np.array(forwards)
    ups = np.array(ups)
    positions = np.array(positions)

    # Average forward direction
    avg_forward = np.mean(forwards, axis=0)
    avg_forward = avg_forward / (np.linalg.norm(avg_forward) + 1e-12)

    # Average up direction
    avg_up = np.mean(ups, axis=0)

    # Make up perpendicular to forward
    avg_up = avg_up - np.dot(avg_up, avg_forward) * avg_forward
    avg_up = avg_up / (np.linalg.norm(avg_up) + 1e-12)

    # Right = forward x up
    avg_right = np.cross(avg_forward, avg_up)
    avg_right = avg_right / (np.linalg.norm(avg_right) + 1e-12)

    # Ensure right-handed coordinate system
    avg_up = np.cross(avg_right, avg_forward)
    avg_up = avg_up / (np.linalg.norm(avg_up) + 1e-12)

    print(f"[Panorama] Camera positions span: {positions.ptp(axis=0)}")
    print(f"[Panorama] Avg forward: {avg_forward}")
    print(f"[Panorama] Avg up: {avg_up}")
    print(f"[Panorama] Avg right: {avg_right}")

    return avg_forward, avg_right, avg_up


def _render_orthographic(
    points: np.ndarray,
    colors: np.ndarray,
    forward: np.ndarray,
    right: np.ndarray,
    up: np.ndarray,
    pixels_per_meter: float = 0,
    max_resolution: int = 4096,
) -> np.ndarray:
    """
    Render the point cloud via orthographic projection along the given viewing direction.

    Projects all points onto a plane defined by (right, up) axes,
    then rasterizes into a 2D image.

    Args:
        points: (M, 3) world coordinates
        colors: (M, 3) uint8 RGB
        forward: (3,) viewing direction
        right: (3,) right axis of projection plane
        up: (3,) up axis of projection plane
        pixels_per_meter: Resolution (0 = auto-compute)
        max_resolution: Max image dimension in pixels

    Returns:
        panorama: (H, W, 3) uint8 RGB image
    """
    if len(points) == 0:
        return np.zeros((100, 100, 3), dtype=np.uint8)

    # Project points onto the 2D plane
    # u = dot(point, right)   -> horizontal position
    # v = dot(point, up)      -> vertical position (will be flipped for image coords)
    # d = dot(point, forward) -> depth along viewing direction (for z-buffering)
    u_coords = points @ right  # (M,)
    v_coords = points @ up  # (M,)
    d_coords = points @ forward  # (M,) depth for z-buffering

    # Remove outliers (use percentile to be robust)
    u_lo, u_hi = np.percentile(u_coords, 0.5), np.percentile(u_coords, 99.5)
    v_lo, v_hi = np.percentile(v_coords, 0.5), np.percentile(v_coords, 99.5)

    # Filter to inliers
    inlier_mask = (
        (u_coords >= u_lo)
        & (u_coords <= u_hi)
        & (v_coords >= v_lo)
        & (v_coords <= v_hi)
    )
    u_coords = u_coords[inlier_mask]
    v_coords = v_coords[inlier_mask]
    d_coords = d_coords[inlier_mask]
    colors = colors[inlier_mask]

    if len(u_coords) == 0:
        return np.zeros((100, 100, 3), dtype=np.uint8)

    # Compute spans
    u_span = u_hi - u_lo
    v_span = v_hi - v_lo

    if u_span < 1e-6 or v_span < 1e-6:
        return np.zeros((100, 100, 3), dtype=np.uint8)

    # Auto-compute resolution if not specified
    if pixels_per_meter <= 0:
        # Aim for max_resolution on the longest side
        pixels_per_meter = max_resolution / max(u_span, v_span)

    img_W = int(np.ceil(u_span * pixels_per_meter))
    img_H = int(np.ceil(v_span * pixels_per_meter))

    # Clamp to max resolution
    if img_W > max_resolution or img_H > max_resolution:
        scale = max_resolution / max(img_W, img_H)
        img_W = int(img_W * scale)
        img_H = int(img_H * scale)
        pixels_per_meter *= scale

    # Ensure minimum size
    img_W = max(img_W, 10)
    img_H = max(img_H, 10)

    print(f"[Panorama] Rendering {img_W}x{img_H} image ({pixels_per_meter:.1f} px/m)")

    # Convert world coordinates to pixel coordinates
    px = ((u_coords - u_lo) * pixels_per_meter).astype(np.int32)
    # Flip v because image y-axis is top-down
    py = ((v_hi - v_coords) * pixels_per_meter).astype(np.int32)

    # Clamp to image bounds
    px = np.clip(px, 0, img_W - 1)
    py = np.clip(py, 0, img_H - 1)

    # Rasterize with z-buffering and accumulation for anti-aliasing
    canvas_color = np.zeros((img_H, img_W, 3), dtype=np.float64)
    canvas_count = np.zeros((img_H, img_W), dtype=np.float64)
    canvas_depth = np.full((img_H, img_W), np.inf, dtype=np.float64)

    # Sort by depth (farthest first so closer points overwrite)
    depth_order = np.argsort(-d_coords)
    px = px[depth_order]
    py = py[depth_order]
    colors_sorted = colors[depth_order]
    d_sorted = d_coords[depth_order]

    # First pass: find the closest depth at each pixel
    np.minimum.at(canvas_depth, (py, px), d_sorted)

    # Compute depth tolerance for accumulation
    # Points within this tolerance of the closest are averaged together
    d_range = np.percentile(d_sorted, 95) - np.percentile(d_sorted, 5)
    depth_tolerance = max(d_range * 0.05, 0.01)  # 5% of depth range or 1cm

    # Second pass: accumulate colors for points near the closest surface
    closest_at_pixel = canvas_depth[py, px]
    depth_ok = (d_sorted - closest_at_pixel) < depth_tolerance

    px_ok = px[depth_ok]
    py_ok = py[depth_ok]
    colors_ok = colors_sorted[depth_ok].astype(np.float64)

    np.add.at(canvas_color, (py_ok, px_ok), colors_ok.reshape(-1, 3))
    np.add.at(canvas_count, (py_ok, px_ok), 1.0)

    # Normalize
    valid = canvas_count > 0
    for c in range(3):
        canvas_color[:, :, c][valid] /= canvas_count[valid]

    panorama = np.clip(canvas_color, 0, 255).astype(np.uint8)

    # Fill small holes via inpainting
    hole_mask = (~valid).astype(np.uint8) * 255

    # Crop to content first
    rows_with_content = np.any(valid, axis=1)
    cols_with_content = np.any(valid, axis=0)

    if np.any(rows_with_content) and np.any(cols_with_content):
        r0 = np.argmax(rows_with_content)
        r1 = len(rows_with_content) - np.argmax(rows_with_content[::-1])
        c0 = np.argmax(cols_with_content)
        c1 = len(cols_with_content) - np.argmax(cols_with_content[::-1])

        # Add small padding
        pad = 5
        r0 = max(0, r0 - pad)
        r1 = min(img_H, r1 + pad)
        c0 = max(0, c0 - pad)
        c1 = min(img_W, c1 + pad)

        panorama = panorama[r0:r1, c0:c1]
        hole_mask = hole_mask[r0:r1, c0:c1]

    # Inpaint remaining holes
    if np.any(hole_mask > 0):
        panorama = cv2.inpaint(
            panorama, hole_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA
        )

    return panorama


def export_to_panorama(
    images: np.ndarray,
    depths: np.ndarray,
    intrinsics: np.ndarray,
    extrinsics: np.ndarray,
    export_dir: str,
    ref_frame: str = "middle",
    fill_holes: bool = True,
    max_resolution: int = 4096,
) -> str:
    """
    Generate a panoramic 2D image by projecting the 3D point cloud orthographically.

    Pipeline:
    1. Back-project all pixels from all frames into 3D world space
    2. Compute optimal viewing direction from camera trajectory
    3. Orthographically project colored point cloud onto 2D plane
    4. Render and save

    Args:
        images: RGB images (N, H, W, 3) uint8
        depths: Depth maps (N, H, W) float
        intrinsics: Camera intrinsic matrices (N, 3, 3)
        extrinsics: World-to-camera extrinsic matrices (N, 4, 4) or (N, 3, 4)
        export_dir: Directory to save output
        ref_frame: Unused (kept for API compat)
        fill_holes: Whether to inpaint small holes in the result
        max_resolution: Maximum output image dimension

    Returns:
        Path to the saved panorama image
    """
    N, H, W, _ = images.shape
    print(f"[Panorama] Generating panorama from {N} frames ({W}x{H})")
    print(f"[Panorama] Total pixels: {N * H * W:,}")

    # Determine subsample factor based on total pixel count
    total_pixels = N * H * W
    if total_pixels > 20_000_000:
        subsample = max(2, int(np.sqrt(total_pixels / 10_000_000)))
        print(f"[Panorama] Subsampling every {subsample} pixels to manage memory")
    else:
        subsample = 1

    # Step 1: Back-project all pixels to 3D
    print("[Panorama] Step 1: Back-projecting pixels to 3D world space...")
    points, colors = _backproject_to_world(
        images, depths, intrinsics, extrinsics, subsample=subsample
    )
    print(f"[Panorama] Got {len(points):,} 3D points")

    if len(points) == 0:
        raise ValueError("No valid 3D points could be generated from the reconstruction.")

    # Remove NaN/Inf points
    finite_mask = np.isfinite(points).all(axis=1)
    points = points[finite_mask]
    colors = colors[finite_mask]

    # Step 2: Compute optimal viewing direction
    print("[Panorama] Step 2: Computing optimal viewing direction from camera poses...")
    forward, right, up = _compute_viewing_direction(extrinsics)

    # Step 3: Orthographic projection and rendering
    print("[Panorama] Step 3: Rendering orthographic projection...")
    panorama = _render_orthographic(
        points, colors, forward, right, up, max_resolution=max_resolution
    )

    # Step 4: Save
    os.makedirs(export_dir, exist_ok=True)
    out_path = os.path.join(export_dir, "panorama.png")
    cv2.imwrite(out_path, cv2.cvtColor(panorama, cv2.COLOR_RGB2BGR))
    print(f"[Panorama] Saved to {out_path} ({panorama.shape[1]}x{panorama.shape[0]})")

    return out_path
