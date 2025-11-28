from typing import Any, Dict
from pathlib import Path
from .config import WORKSPACE_ROOT
from .canvas import parse_canvas_object, load_canvas_from_markdown, export_canvas_to_markdown


def add_to_canvas(content: Any) -> Dict[str, Any]:
    """Add an item to the canvas for visualization. Canvas is like a note-taking tool where
    you can store charts, dataframes, images, and markdown text for the user to see.

    Args:
        content: Can be a pandas DataFrame, matplotlib Figure, plotly Figure,
                PIL Image, dictionary (for Plotly JSON), or string (for Markdown)

    Returns:
        Dictionary with the parsed canvas object and status

    Examples:
        # Add a DataFrame
        import pandas as pd
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        add_to_canvas(df)

        # Add a Matplotlib chart
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        add_to_canvas(fig)

        # Add Markdown text
        add_to_canvas("## Key Findings\\n- Point 1\\n- Point 2")
    """
    try:
        print(f"[add_to_canvas] WORKSPACE_ROOT: {WORKSPACE_ROOT}")
        print(f"[add_to_canvas] Content type: {type(content)}")

        # Parse the content into canvas format
        parsed = parse_canvas_object(content, workspace_root=WORKSPACE_ROOT)
        print(f"[add_to_canvas] Parsed type: {parsed.get('type')}")

        # Load existing canvas items
        canvas_path = WORKSPACE_ROOT / "canvas.md"
        print(f"[add_to_canvas] Canvas path: {canvas_path}")

        existing_items = load_canvas_from_markdown(WORKSPACE_ROOT, canvas_path) if canvas_path.exists() else []
        print(f"[add_to_canvas] Existing items: {len(existing_items)}")

        # Append new item
        existing_items.append(parsed)

        # Export to canvas.md
        result_path = export_canvas_to_markdown(existing_items, WORKSPACE_ROOT, canvas_path)
        print(f"[add_to_canvas] Exported to: {result_path}")
        print(f"[add_to_canvas] File exists: {Path(result_path).exists()}")

        return {
            "status": "success",
            "message": f"Added {parsed['type']} to canvas at {canvas_path}",
            "item": parsed,
            "canvas_path": str(canvas_path)
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[add_to_canvas] ERROR: {error_trace}")
        return {
            "status": "error",
            "message": f"Failed to add to canvas: {str(e)}",
            "error": str(e),
            "traceback": error_trace
        }
