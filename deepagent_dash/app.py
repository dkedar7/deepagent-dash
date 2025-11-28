# -*- coding: utf-8 -*-
"""Simple Dash app for DeepAgents interface."""

import os
import sys
import json
import re
import ast
from pathlib import Path
from typing import Optional
import importlib.util

import dash
from dash import dcc, Input, Output, State
import dash_mantine_components as dmc


# Load configuration
def load_config(config_file="./config.py"):
    """Load configuration from config.py file."""
    config_path = Path(config_file).resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    spec = importlib.util.spec_from_file_location("config", config_path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)

    return config


def load_agent(agent_spec: str):
    """Load agent from module:object specification."""
    if ":" not in agent_spec:
        raise ValueError(f"Invalid agent spec: {agent_spec}. Expected format: 'path/to/file.py:object_name'")

    module_path, obj_name = agent_spec.split(":", 1)
    module_path = Path(module_path).resolve()

    if not module_path.exists():
        raise FileNotFoundError(f"Agent module not found: {module_path}")

    spec = importlib.util.spec_from_file_location("agent_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, obj_name):
        raise AttributeError(f"Object '{obj_name}' not found in {module_path}")

    return getattr(module, obj_name)


def parse_todos_from_tool_message(tool_content):
    """Parse todos from write_todos tool message content."""
    todos = None

    if isinstance(tool_content, str):
        # Look for array pattern first
        match = re.search(r'\[.*\]', tool_content, re.DOTALL)
        if match:
            array_str = match.group(0)
            try:
                todos = ast.literal_eval(array_str)
            except:
                try:
                    todos = json.loads(array_str)
                except:
                    pass
        else:
            try:
                parsed = json.loads(tool_content)
                if isinstance(parsed, dict):
                    todos = parsed.get('todos')
                    if isinstance(todos, str):
                        todos = json.loads(todos)
                elif isinstance(parsed, list):
                    todos = parsed
            except:
                pass
    elif isinstance(tool_content, dict):
        todos = tool_content.get('todos')
        if isinstance(todos, str):
            try:
                todos = json.loads(todos)
            except:
                pass
    elif isinstance(tool_content, list):
        todos = tool_content

    return todos if isinstance(todos, list) else None


def create_app(workspace: Path, agent, title: str = "DeepAgent Dash"):
    """Create and configure the Dash application."""
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    app.title = title

    # App layout
    app.layout = dmc.MantineProvider([
        dmc.Container([
            # Header
            dmc.Title(title, order=2, mb="md", mt="md"),

            # Main content - two column grid
            dmc.Grid([
                # Left column - Chat interface
                dmc.GridCol([
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Text("Chat", size="lg", fw=500),

                            # Messages container
                            dmc.ScrollArea(
                                id="chat-messages",
                                h=500,
                                style={
                                    "border": "1px solid #dee2e6",
                                    "borderRadius": "4px",
                                    "padding": "10px",
                                    "backgroundColor": "#f8f9fa"
                                },
                                children=[]
                            ),

                            # Thinking display
                            dmc.Paper(
                                id="thinking-display",
                                p="sm",
                                withBorder=True,
                                style={"display": "none", "backgroundColor": "#fff3cd"},
                                children=[]
                            ),

                            # Todo list display
                            dmc.Paper(
                                id="todo-display",
                                p="sm",
                                withBorder=True,
                                style={"display": "none"},
                                children=[]
                            ),

                            # Input area
                            dmc.Group([
                                dmc.TextInput(
                                    id="user-input",
                                    placeholder="Type your message...",
                                    style={"flex": 1},
                                    n_submit=0
                                ),
                                dmc.Button(
                                    "Send",
                                    id="send-button",
                                    n_clicks=0
                                )
                            ], gap="xs")
                        ], gap="md")
                    ], p="md", shadow="sm", withBorder=True),

                    # Streaming update interval
                    dcc.Interval(
                        id="stream-interval",
                        interval=100,  # 100ms
                        disabled=True
                    )
                ], span=6),

                # Right column - File browser / Canvas
                dmc.GridCol([
                    dmc.Paper([
                        dmc.Stack([
                            # Header with switch
                            dmc.Group([
                                dmc.Text("Workspace", size="lg", fw=500),
                                dmc.Switch(
                                    id="view-switch",
                                    label="Canvas",
                                    checked=False,
                                    size="md"
                                )
                            ], justify="space-between"),

                            # Content area
                            dmc.ScrollArea(
                                id="right-pane-content",
                                h=500,
                                style={"padding": "10px"}
                            )
                        ], gap="md")
                    ], p="md", shadow="sm", withBorder=True)
                ], span=6)
            ], gutter="md")
        ], fluid=True, size="xl"),

        # Hidden divs for state
        dcc.Store(id="chat-history", data=[]),
        dcc.Store(id="workspace-path", data=str(workspace)),
        dcc.Store(id="stream-state", data={"streaming": False, "buffer": []}),
        dcc.Store(id="current-todos", data=[]),
        dcc.Store(id="current-thinking", data="")
    ])

    # Streaming state (shared across callbacks)
    import threading
    from queue import Queue

    stream_queue = Queue()
    stream_thread = [None]  # [Thread object]

    def stream_worker(agent, user_message):
        """Worker thread that consumes the stream and puts results in queue."""
        try:
            agent_input = {"messages": [user_message]}
            for update in agent.stream(agent_input, stream_mode="updates"):
                stream_queue.put({"type": "update", "data": update})
            stream_queue.put({"type": "complete"})
        except Exception as e:
            stream_queue.put({"type": "error", "error": str(e)})

    # Callbacks
    @app.callback(
        Output("stream-state", "data"),
        Output("stream-interval", "disabled"),
        Output("chat-history", "data", allow_duplicate=True),
        Input("send-button", "n_clicks"),
        Input("user-input", "n_submit"),
        State("user-input", "value"),
        State("chat-history", "data"),
        State("stream-state", "data"),
        prevent_initial_call=True
    )
    def start_streaming(n_clicks, n_submit, user_message, chat_history, stream_state):
        """Start streaming agent response."""
        if not user_message or not user_message.strip():
            return dash.no_update, dash.no_update, dash.no_update

        # Don't start new stream if already streaming
        if stream_state.get("streaming"):
            return dash.no_update, dash.no_update, dash.no_update

        # Add user message to history
        chat_history = chat_history or []
        chat_history.append({"role": "user", "content": user_message})

        # Clear any old items from queue
        while not stream_queue.empty():
            try:
                stream_queue.get_nowait()
            except:
                break

        # Start streaming in background thread
        thread = threading.Thread(target=stream_worker, args=(agent, user_message))
        thread.daemon = True
        thread.start()
        stream_thread[0] = thread

        return {"streaming": True, "buffer": []}, False, chat_history

    @app.callback(
        Output("chat-messages", "children"),
        Output("thinking-display", "children"),
        Output("thinking-display", "style"),
        Output("todo-display", "children"),
        Output("todo-display", "style"),
        Output("stream-state", "data", allow_duplicate=True),
        Output("stream-interval", "disabled", allow_duplicate=True),
        Output("chat-history", "data", allow_duplicate=True),
        Output("current-todos", "data"),
        Output("current-thinking", "data"),
        Input("stream-interval", "n_intervals"),
        State("chat-history", "data"),
        State("stream-state", "data"),
        State("current-todos", "data"),
        State("current-thinking", "data"),
        prevent_initial_call=True
    )
    def update_stream(n_intervals, chat_history, stream_state, current_todos, current_thinking):
        """Update streaming content."""
        if not stream_state.get("streaming"):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, \
                   dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        try:
            # Get next item from queue (non-blocking)
            if stream_queue.empty():
                # No updates yet, keep polling
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, \
                       dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

            item = stream_queue.get_nowait()

            # Handle completion
            if item["type"] == "complete":
                stream_thread[0] = None
                messages = render_messages(chat_history)

                # Keep final state visible
                thinking_display = dmc.Stack([
                    dmc.Text("🤔 Thinking:", size="sm", fw=700, c="orange"),
                    dmc.Text(current_thinking, size="sm", c="dimmed")
                ], gap="xs") if current_thinking else []
                thinking_style = {"display": "block", "backgroundColor": "#fff3cd"} if current_thinking else {"display": "none"}

                todo_display = render_todos(current_todos) if current_todos else []
                todo_style = {"display": "block"} if current_todos else {"display": "none"}

                return messages, thinking_display, thinking_style, todo_display, todo_style, \
                       {"streaming": False, "buffer": []}, True, chat_history, current_todos, current_thinking

            # Handle error
            if item["type"] == "error":
                stream_thread[0] = None
                chat_history = chat_history or []
                chat_history.append({"role": "assistant", "content": f"Error: {item['error']}"})
                messages = render_messages(chat_history)

                return messages, [], {"display": "none"}, [], {"display": "none"}, \
                       {"streaming": False, "buffer": []}, True, chat_history, [], ""

            # Process update
            update = item["data"]

            # Process update
            agent_content = []
            new_todos = current_todos
            new_thinking = current_thinking

            if isinstance(update, dict):
                for node_name, state_data in update.items():
                    if isinstance(state_data, dict) and "messages" in state_data:
                        messages = state_data["messages"]
                        if messages:
                            last_message = messages[-1] if isinstance(messages, list) else messages
                            message_type = last_message.__class__.__name__ if hasattr(last_message, '__class__') else None

                            # Handle think_tool
                            if message_type == 'ToolMessage' and hasattr(last_message, 'name') and last_message.name == 'think_tool':
                                tool_content = last_message.content
                                if isinstance(tool_content, str):
                                    try:
                                        parsed = json.loads(tool_content)
                                        new_thinking = parsed.get('reflection', tool_content)
                                    except:
                                        new_thinking = tool_content
                                elif isinstance(tool_content, dict):
                                    new_thinking = tool_content.get('reflection', '')

                            # Handle write_todos
                            elif message_type == 'ToolMessage' and hasattr(last_message, 'name') and last_message.name == 'write_todos':
                                todos = parse_todos_from_tool_message(last_message.content)
                                if todos:
                                    new_todos = todos

                            # Handle regular messages
                            elif hasattr(last_message, 'content'):
                                content = last_message.content
                                if isinstance(content, str):
                                    content_str = content.strip()
                                    if content_str:
                                        agent_content.append(content_str)

            # Update chat history if we have new content
            if agent_content:
                # Check if last message is from assistant, if so append, otherwise create new
                if chat_history and chat_history[-1]["role"] == "assistant":
                    chat_history[-1]["content"] += " " + " ".join(agent_content)
                else:
                    chat_history.append({"role": "assistant", "content": " ".join(agent_content)})

            # Render messages
            messages = render_messages(chat_history)

            # Render thinking
            thinking_display = dmc.Stack([
                dmc.Text("🤔 Thinking:", size="sm", fw=700, c="orange"),
                dmc.Text(new_thinking, size="sm", c="dimmed")
            ], gap="xs") if new_thinking else []
            thinking_style = {"display": "block", "backgroundColor": "#fff3cd"} if new_thinking else {"display": "none"}

            # Render todos
            todo_display = render_todos(new_todos) if new_todos else []
            todo_style = {"display": "block"} if new_todos else {"display": "none"}

            return messages, thinking_display, thinking_style, todo_display, todo_style, \
                   stream_state, False, chat_history, new_todos, new_thinking

        except Exception as e:
            # Unexpected error in callback
            stream_thread[0] = None
            chat_history = chat_history or []
            chat_history.append({"role": "assistant", "content": f"Error: {str(e)}"})
            messages = render_messages(chat_history)

            return messages, [], {"display": "none"}, [], {"display": "none"}, \
                   {"streaming": False, "buffer": []}, True, chat_history, [], ""

    @app.callback(
        Output("user-input", "value"),
        Input("send-button", "n_clicks"),
        Input("user-input", "n_submit"),
        prevent_initial_call=True
    )
    def clear_input(n_clicks, n_submit):
        """Clear input after sending."""
        return ""

    @app.callback(
        Output("right-pane-content", "children"),
        Input("view-switch", "checked"),
        State("workspace-path", "data"),
        prevent_initial_call=False
    )
    def update_right_pane(show_canvas, workspace_path):
        """Toggle between file browser and canvas view."""
        try:
            if show_canvas:
                # Canvas view - render canvas.md
                canvas_file = Path(workspace_path) / "canvas.md"
                if canvas_file.exists():
                    content = canvas_file.read_text()
                    return dmc.TypographyStylesProvider(
                        dcc.Markdown(content),
                        style={"padding": "10px"}
                    )
                else:
                    return dmc.Text(
                        "Canvas is empty. The agent can populate canvas.md to use this as a whiteboard.",
                        c="dimmed",
                        size="sm"
                    )
            else:
                # File browser view
                workspace = Path(workspace_path)
                files = []

                try:
                    for item in sorted(workspace.rglob("*")):
                        if item.is_file():
                            rel_path = item.relative_to(workspace)
                            files.append(
                                dmc.Text(
                                    f"📄 {rel_path}",
                                    size="sm",
                                    ff="monospace",
                                    mb="xs"
                                )
                            )
                except Exception as e:
                    files.append(dmc.Text(f"Error reading workspace: {e}", c="red"))

                if not files:
                    files.append(dmc.Text("No files in workspace", c="dimmed", size="sm"))

                return dmc.Stack(files, gap="xs")

        except Exception as e:
            # Catch-all error handler
            return dmc.Text(f"Error updating view: {str(e)}", c="red", size="sm")

    return app


def render_messages(chat_history):
    """Render chat messages."""
    messages = []
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(
                dmc.Group([
                    dmc.Text("You:", fw=700, c="blue"),
                    dmc.Text(msg["content"])
                ], gap="xs", mb="sm", align="flex-start")
            )
        else:
            messages.append(
                dmc.Group([
                    dmc.Text("Agent:", fw=700, c="green"),
                    dmc.Text(msg["content"])
                ], gap="xs", mb="sm", align="flex-start")
            )
    return messages


def render_todos(todos):
    """Render todo list."""
    if not todos:
        return []

    todo_items = []
    todo_items.append(dmc.Text("📋 Todo List:", size="sm", fw=700, mb="xs"))

    for todo in todos:
        status = todo.get("status", "pending")
        content = todo.get("content", "")

        # Status icon and color
        if status == "completed":
            icon = "✅"
            color = "green"
        elif status == "in_progress":
            icon = "🔄"
            color = "blue"
        else:
            icon = "⭕"
            color = "gray"

        todo_items.append(
            dmc.Group([
                dmc.Text(icon, size="sm"),
                dmc.Text(content, size="sm", c=color)
            ], gap="xs", mb="xs")
        )

    return dmc.Stack(todo_items, gap="xs")


def run_app(
    workspace: Optional[str] = None,
    agent_spec: Optional[str] = None,
    port: Optional[int] = None,
    host: Optional[str] = None,
    debug: Optional[bool] = None,
    title: Optional[str] = None,
    config_file: str = "./config.py"
):
    """Run the Dash application."""
    # Load config
    config = load_config(config_file)

    # Override config with CLI arguments
    workspace = Path(workspace) if workspace else config.WORKSPACE_ROOT
    agent_spec = agent_spec or config.AGENT_SPEC
    port = port if port is not None else config.PORT
    host = host or config.HOST
    debug = debug if debug is not None else config.DEBUG
    title = title or config.APP_TITLE

    # Ensure workspace exists
    workspace.mkdir(exist_ok=True, parents=True)

    # Load agent
    print(f"Loading agent from: {agent_spec}")
    agent = load_agent(agent_spec)

    # Create and run app
    print(f"Starting {title}...")
    print(f"Workspace: {workspace}")
    print(f"Running on http://{host}:{port}")

    app = create_app(workspace, agent, title)
    app.run(host=host, port=port, debug=debug)

    return 0


if __name__ == "__main__":
    run_app(debug=True)
