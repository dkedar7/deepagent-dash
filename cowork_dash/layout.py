"""Layout components for DeepAgent Dash."""

from dash import html, dcc
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from .file_utils import build_file_tree, render_file_tree


def create_layout(workspace_root, app_title, app_subtitle, colors, styles, agent):
    """
    Create the app layout with current configuration.

    Args:
        workspace_root: Path to workspace directory
        app_title: Application title
        app_subtitle: Application subtitle
        colors: Color scheme dictionary
        styles: Styles dictionary
        agent: Agent instance (or None)

    Returns:
        Dash layout component
    """
    return dmc.MantineProvider(
        id="mantine-provider",
        forceColorScheme="light",
        children=[
            # State stores
            dcc.Store(id="chat-history", data=[{
                "role": "assistant",
                "content": f"""This is your AI-powered workspace. I can help you write code, analyze files, create visualizations, and more.

**Getting Started:**
- Type a message below to chat with me
- Browse files on the right (click to view, ↓ to download)
- Switch to **Canvas** tab to see charts and diagrams I create

Let's get started!"""
            }]),
            dcc.Store(id="pending-message", data=None),
            dcc.Store(id="expanded-folders", data=[]),
            dcc.Store(id="file-to-view", data=None),
            dcc.Store(id="file-click-tracker", data={}),
            dcc.Store(id="theme-store", data="light", storage_type="local"),
            dcc.Download(id="file-download"),

            # Interval for polling agent updates (disabled by default)
            dcc.Interval(id="poll-interval", interval=250, disabled=True),

            # File viewer modal
            dmc.Modal(
                id="file-modal",
                title="",
                size="xl",
                children=[
                    html.Div(id="modal-content"),
                    html.Div([
                        dmc.Button(
                            "Download",
                            id="modal-download-btn",
                            variant="outline",
                            color="blue",
                            style={"marginTop": "16px"}
                        )
                    ], style={"textAlign": "right"})
                ],
                opened=False,
            ),

            html.Div([
                # Header
                html.Header([
                    html.Div([
                        html.Div([
                            html.H1(app_title or "DeepAgent Dash", id="app-title", style={
                                "fontSize": "18px", "fontWeight": "600", "margin": "0",
                            }),
                            html.Span(app_subtitle or "AI-Powered Workspace", id="app-subtitle", style={
                                "fontSize": "12px", "color": "var(--mantine-color-dimmed)", "marginLeft": "12px",
                            })
                        ], style={"display": "flex", "alignItems": "baseline"}),
                        html.Div([
                            dmc.ActionIcon(
                                DashIconify(icon="radix-icons:moon", width=18),
                                id="theme-toggle-btn",
                                variant="outline",
                                color="gray",
                                size="lg",
                                radius="md",
                                style={"marginRight": "16px"},
                            ),
                            html.Div(style={
                                "width": "8px", "height": "8px",
                                "borderRadius": "50%",
                                "background": "var(--mantine-color-green-6)" if agent else "var(--mantine-color-red-6)",
                                "marginRight": "8px",
                            }, id="agent-status-indicator"),
                            dmc.Text("Ready" if agent else "No Agent", size="sm", c="dimmed", id="agent-status-text")
                        ], style={"display": "flex", "alignItems": "center"})
                    ], style={
                        "display": "flex", "justifyContent": "space-between",
                        "alignItems": "center", "maxWidth": "1600px",
                        "margin": "0 auto", "padding": "0 24px",
                    })
                ], id="header", style={
                    "background": "var(--mantine-color-body)",
                    "borderBottom": "1px solid var(--mantine-color-default-border)",
                    "padding": "16px 0",
                }),

            # Main content
            html.Main([
                # Chat panel
                html.Div([
                    html.Div([
                        dmc.Text("Chat", fw=600, size="sm", id="chat-header-text"),
                    ], id="chat-header", style={
                        "padding": "16px 20px",
                        "borderBottom": "1px solid var(--mantine-color-default-border)",
                        "background": "var(--mantine-color-body)",
                    }),

                    # Messages
                    html.Div(id="chat-messages", style={
                        "flex": "1", "overflowY": "auto", "padding": "20px",
                        "display": "flex", "flexDirection": "column", "gap": "16px",
                    }),

                    # Input
                    html.Div([
                        dcc.Upload(
                            id="file-upload",
                            children=dmc.ActionIcon(
                                DashIconify(icon="radix-icons:plus", width=20),
                                id="upload-plus",
                                variant="default",
                                size="lg",
                            ),
                            style={"cursor": "pointer"},
                            multiple=True
                        ),
                        dmc.TextInput(
                            id="chat-input",
                            placeholder="Type a message...",
                            className="chat-input",
                            style={"flex": "1"},
                            size="md",
                        ),
                        dmc.Button("Send", id="send-btn", className="send-btn", size="md"),
                    ], id="chat-input-area", style={
                        "display": "flex", "gap": "8px", "padding": "16px 20px",
                        "borderTop": "1px solid var(--mantine-color-default-border)",
                        "background": "var(--mantine-color-body)",
                    }),
                    dmc.Text(id="upload-status", size="xs", c="dimmed", style={
                        "padding": "0 20px 12px",
                    }),
                ], id="chat-panel", style={
                    "flex": "1", "display": "flex", "flexDirection": "column",
                    "background": "var(--mantine-color-gray-0)", "minWidth": "0",
                }),

                # Resize handle
                html.Div(id="resize-handle", className="resize-handle", style={
                    "width": "4px",
                    "cursor": "col-resize",
                    "background": "transparent",
                    "flexShrink": "0",
                }),

                # Sidebar (Files/Canvas toggle)
                html.Div([
                    # Header with toggle
                    html.Div([
                        dmc.SegmentedControl(
                            id="sidebar-view-toggle",
                            data=[
                                {"value": "files", "label": "Files"},
                                {"value": "canvas", "label": "Canvas"},
                            ],
                            value="files",
                            size="sm",
                        ),
                        dmc.Group([
                            dmc.ActionIcon(
                                DashIconify(icon="radix-icons:terminal", width=16),
                                id="open-terminal-btn",
                                variant="subtle",
                                color="gray",
                                size="md",
                            ),
                            dmc.ActionIcon(
                                DashIconify(icon="radix-icons:reload", width=16),
                                id="refresh-btn",
                                variant="subtle",
                                color="gray",
                                size="md",
                            ),
                        ], id="files-actions", gap="xs")
                    ], id="sidebar-header", style={
                        "display": "flex", "justifyContent": "space-between",
                        "alignItems": "center", "padding": "16px",
                        "borderBottom": "1px solid var(--mantine-color-default-border)",
                    }),

                    # Files view
                    html.Div([
                        html.Div(
                            id="file-tree",
                            children=render_file_tree(build_file_tree(workspace_root, workspace_root), colors, styles),
                            style={
                                "flex": "1",
                                "overflowY": "auto",
                                "minHeight": "0",
                                "paddingBottom": "15px"
                            }
                        ),
                    ], id="files-view", style={
                        "flex": "1",
                        "minHeight": "0",
                        "display": "flex",
                        "flexDirection": "column",
                        "paddingBottom": "5%"
                    }),

                    # Canvas view (hidden by default)
                    html.Div([
                        html.Div(id="canvas-content", style={
                            "flex": "1",
                            "minHeight": "0",
                            "overflowY": "auto",
                            "padding": "20px",
                            "background": "var(--mantine-color-body)",
                        }),
                        # Canvas action buttons (floating at bottom)
                        dmc.Group([
                            dmc.Button("Refresh", id="refresh-canvas-btn", size="sm"),
                            dmc.Button("Clear", id="clear-canvas-btn", size="sm", color="red"),
                        ], id="canvas-actions", justify="center", style={
                            "padding": "12px 20px",
                            "borderTop": "1px solid var(--mantine-color-default-border)",
                            "background": "var(--mantine-color-body)",
                        })
                    ], id="canvas-view", style={
                        "flex": "1",
                        "minHeight": "0",
                        "display": "none",
                        "flexDirection": "column",
                        "overflow": "hidden"
                    }),
                ], id="sidebar-panel", style={
                    "flex": "1",
                    "minWidth": "0",
                    "minHeight": "0",
                    "display": "flex",
                    "flexDirection": "column",
                    "background": "var(--mantine-color-body)",
                    "borderLeft": "1px solid var(--mantine-color-default-border)",
                }),
            ], id="main-container", style={"display": "flex", "flex": "1", "overflow": "hidden"}),
        ], id="app-container", style={"display": "flex", "flexDirection": "column", "height": "100vh"})
    ])
