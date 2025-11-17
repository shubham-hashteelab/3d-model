# flake8: noqa: E501

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
CSS and HTML content for the Depth Anything 3 Gradio application.
This module contains all the CSS styles and HTML content blocks
used in the Gradio interface.
"""

# CSS Styles for the Gradio interface
GRADIO_CSS = """
/* Minimal, clean design */
.link-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    text-decoration: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 500;
    transition: all 0.2s ease;
}

/* Dark mode minimal theme */
@media (prefers-color-scheme: dark) {
    html, body {
        background: #1a1a1a;
        color: #e0e0e0;
    }

    .gradio-container {
        background: #1a1a1a;
        color: #e0e0e0;
    }

    .link-btn {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .link-btn:hover {
        background: rgba(255, 255, 255, 0.15);
    }

    .gradio-container .panel,
    .gradio-container .block,
    .gradio-container .form {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
    }

    .gradio-container * {
        color: #e0e0e0;
    }

    .gradio-container label {
        color: #d0d0d0;
    }

    .gradio-container .markdown {
        color: #d0d0d0;
    }
}

/* Light mode minimal theme */
@media (prefers-color-scheme: light) {
    html, body {
        background: #ffffff;
        color: #333333;
    }

    .gradio-container {
        background: #ffffff;
        color: #333333;
    }

    .link-btn {
        background: rgba(0, 0, 0, 0.05);
        color: #333333;
        border: 1px solid rgba(0, 0, 0, 0.1);
    }

    .link-btn:hover {
        background: rgba(0, 0, 0, 0.1);
    }

    .gradio-container .panel,
    .gradio-container .block,
    .gradio-container .form {
        background: rgba(0, 0, 0, 0.02);
        border: 1px solid rgba(0, 0, 0, 0.1);
        border-radius: 8px;
    }
}

/* Align navigation buttons with dropdown bottom */
.navigation-row {
    display: flex !important;
    align-items: flex-end !important;
    gap: 8px !important;
}

.navigation-row > div:nth-child(1),
.navigation-row > div:nth-child(3) {
    align-self: flex-end !important;
}

.navigation-row > div:nth-child(2) {
    flex: 1 !important;
}

/* Make thumbnails clickable with pointer cursor */
.clickable-thumbnail img {
    cursor: pointer !important;
}

.clickable-thumbnail:hover img {
    cursor: pointer !important;
    opacity: 0.85;
    transition: opacity 0.2s ease;
}

/* Make thumbnail containers narrower horizontally */
.clickable-thumbnail {
    padding: 5px 2px !important;
    margin: 0 2px !important;
}

.clickable-thumbnail .image-container {
    margin: 0 !important;
    padding: 0 !important;
}

.scene-info {
    text-align: center !important;
    padding: 5px 2px !important;
    margin: 0 !important;
}
"""


def get_header_html(logo_base64=None):
    """
    Generate the main header HTML with logo and title.

    Args:
        logo_base64 (str, optional): Base64 encoded logo image

    Returns:
        str: HTML string for the header
    """
    return """
    <div style="text-align: center; margin-bottom: 20px; padding: 30px 20px;">
        <h1 style="margin: 0; font-size: 2.5em; font-weight: 600; color: #333; letter-spacing: 1px;">
            Hashtee Lab 3D Modeling
        </h1>
    </div>

    <style>
        @media (prefers-color-scheme: dark) {
            h1 {
                color: #e0e0e0 !important;
            }
        }
    </style>
    """


def get_description_html():
    """
    Generate the main description and getting started HTML.

    Returns:
        str: HTML string for the description
    """
    return """
    """


def get_acknowledgements_html():
    """
    Generate the acknowledgements section HTML.

    Returns:
        str: HTML string for the acknowledgements
    """
    return """
    """


def get_gradio_theme():
    """
    Get the configured Gradio theme with minimal, clean design.

    Returns:
        gr.themes.Base: Configured Gradio theme
    """
    import gradio as gr

    return gr.themes.Base(
        primary_hue=gr.themes.Color(
            c50="#f5f5f5",
            c100="#e5e5e5",
            c200="#d4d4d4",
            c300="#a3a3a3",
            c400="#737373",
            c500="#525252",
            c600="#404040",
            c700="#262626",
            c800="#171717",
            c900="#0a0a0a",
            c950="#000000",
        ),
        secondary_hue=gr.themes.Color(
            c50="#fafafa",
            c100="#f4f4f5",
            c200="#e4e4e7",
            c300="#d4d4d8",
            c400="#a1a1aa",
            c500="#71717a",
            c600="#52525b",
            c700="#3f3f46",
            c800="#27272a",
            c900="#18181b",
            c950="#09090b",
        ),
        neutral_hue=gr.themes.Color(
            c50="#fafafa",
            c100="#f5f5f5",
            c200="#e5e5e5",
            c300="#d4d4d4",
            c400="#a3a3a3",
            c500="#737373",
            c600="#525252",
            c700="#404040",
            c800="#262626",
            c900="#171717",
            c950="#0a0a0a",
        ),
    )


# Measure tab instructions HTML
MEASURE_INSTRUCTIONS_HTML = """
### Click two points on the image to measure distance.
> **Note:** Measurements may be less accurate on aerial/drone images.
"""
