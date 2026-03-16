#!/bin/bash

# Get the absolute path to the workflow directory
WORKFLOW_DIR="$HOME/Desktop/AI Cnntent Creator workflow"

echo "💤 Cleaning up old processes..."
pkill -f "webui"
pkill -f "start_painter"
pkill -f "streamlit"
# Give them a moment to die
sleep 2

echo "🔧 Verifying patches..."
python3 "$WORKFLOW_DIR/force_fix.py"

echo "🚀 Launching Stable Diffusion Server..."
# Use AppleScript to open a new terminal window for the server
osascript -e "tell application \"Terminal\" to do script \"cd ~ && bash \\\"$WORKFLOW_DIR/start_painter.sh\\\"\""

echo "✨ Launching AI Content App..."
# Use AppleScript to open a new terminal window for the app
osascript -e "tell application \"Terminal\" to do script \"cd \\\"$WORKFLOW_DIR\\\" && python3 -m streamlit run app.py\""

echo "✅ DONE! Look for the two new Terminal windows that just popped up."
