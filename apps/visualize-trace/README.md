# Trace Analysis Web Demo

An interactive web interface for analyzing and visualizing trace JSON files.

## Features

- 🔍 **Interactive Analysis**: Intuitive web interface for easily browsing and analyzing trace data
- 📊 **Execution Flow Visualization**: Clear display of main agent and browser agent execution flows
- 🛠️ **Tool Call Tracking**: Detailed display of MCP tool call information and parameters
- 📱 **Responsive Design**: Supports desktop and mobile device access
- 💾 **File Management**: Supports dynamic loading and switching between different trace files

## Project Structure

```
web_demo/
├── app.py              # Flask backend application
├── trace_analyzer.py   # Core analysis logic
├── run.py              # Startup script
├── requirements.txt    # Python dependencies
├── README.md          # Documentation
├── templates/
│   └── index.html     # Main page template
└── static/
    ├── css/
    │   └── style.css  # Style file
    └── js/
        └── script.js  # Frontend interaction logic
```

## Installation and Running

### Method 1: Using Python (Recommended)

```bash
pip install -r requirements.txt
python run.py
```

The startup script will automatically check and install dependencies, then start the web application. Visit `http://127.0.0.1:5000`

### Method 2: Using uv

```bash
uv run run.py
```

## Usage

1. **Start the Application**: After running, visit `http://127.0.0.1:5000` in your browser

2. **Load Files**: 
   - Select the trace JSON file to analyze from the dropdown menu in the top navigation bar
   - Click the "Load" button to load the file

3. **View Analysis Results**:
   - **Left Panel**: Displays basic information, execution summary, and performance statistics
   - **Right Panel**: Shows detailed execution flow
   - **Bottom Panel**: Displays spans statistics and step logs statistics

4. **Interactive Operations**:
   - Click on execution steps to expand/collapse detailed information
   - Use "Expand All"/"Collapse All" buttons to control all steps
   - Click "View Details" button to see complete message content

## Interface Description

### Execution Flow View

- **User Messages**: Blue background, representing user input
- **Assistant Messages**: Purple background, representing AI assistant replies
- **Browser Agent**: Green/orange background, representing browser agent operations
- **Tool Calls**: Yellow background, displaying tool call information
- **Browser Sessions**: Gray background, showing detailed browser agent conversations

### Color Coding

- 🔵 **Blue**: Main Agent user messages
- 🟣 **Purple**: Main Agent assistant messages
- 🟢 **Green**: Browser Agent user messages
- 🟠 **Orange**: Browser Agent assistant messages
- 🟡 **Yellow**: Tool calls
- 🟢 **Green Tags**: Browser session identifiers

## Data Structure

This tool supports analyzing JSON files containing the following structure:

- `main_agent_message_history`: Main agent conversation history
- `browser_agent_message_history_sessions`: Browser agent session history
- `trace_data.spans`: Execution trace data
- `step_logs`: Step logs
- `performance_summary`: Performance summary information

## API Interfaces

The backend provides the following API interfaces:

- `GET /`: Main page
- `GET /api/list_files`: Get available JSON file list
- `POST /api/load_trace`: Load specified trace file
- `GET /api/basic_info`: Get basic information
- `GET /api/execution_flow`: Get execution flow
- `GET /api/execution_summary`: Get execution summary
- `GET /api/performance_summary`: Get performance summary
- `GET /api/spans_summary`: Get spans statistics
- `GET /api/step_logs_summary`: Get step logs statistics

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI Framework**: Bootstrap 5
- **Icons**: Font Awesome
- **Data Processing**: JSON, Regular expressions

## Development Guide

### Adding New Features

1. **Backend**: Add new API endpoints in `app.py`
2. **Data Analysis**: Add new analysis methods in `trace_analyzer.py`
3. **Frontend**: Add corresponding API calls and interface update logic in `script.js`
4. **Styling**: Add corresponding style definitions in `style.css`