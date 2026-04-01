#!/bin/bash

# ==========================================
# Cybergarden Orchestrator
# ==========================================

APP_DIR=$(pwd)
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
PID_DIR="$APP_DIR/pids"

# Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Explicit paths to the virtual environment binaries
PYTHON="$VENV_DIR/bin/python"
UVICORN="$VENV_DIR/bin/uvicorn"

# --- HELPER FUNCTIONS ---

start_service() {
    local name=$1
    local cmd=$2
    local pid_file="$PID_DIR/$name.pid"
    local log_file="$LOG_DIR/$name.log"

    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        echo "🌿 [ALREADY RUNNING] $name (PID: $(cat $pid_file))"
    else
        echo "🚀 [STARTING] $name..."
        # Run command in the background, redirect output to log, and save the PID
        nohup $cmd > "$log_file" 2>&1 &
        echo $! > "$pid_file"
        echo "✅ [STARTED] $name (PID: $(cat $pid_file))"
    fi
}

stop_service() {
    local name=$1
    local pid_file="$PID_DIR/$name.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo "🛑 [STOPPING] $name (PID: $pid)..."
            kill $pid
            # Wait for process to actually die
            while kill -0 $pid 2>/dev/null; do sleep 0.5; done
            echo "✅ [STOPPED] $name"
        else
            echo "⚠️ [CLEANUP] $name was not running, but PID file existed."
        fi
        rm -f "$pid_file"
    else
        echo "ℹ️  [NOT RUNNING] $name"
    fi
}

status_service() {
    local name=$1
    local pid_file="$PID_DIR/$name.pid"

    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        echo "🟢 $name is RUNNING (PID: $(cat $pid_file))"
    else
        echo "🔴 $name is STOPPED"
    fi
}

# --- MAIN COMMANDS ---

setup() {
    echo "📦 Setting up Cybergarden Virtual Environment..."
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        echo "✅ Virtual environment created."
    fi
    $PYTHON -m pip install --upgrade pip
    # Assuming you have a requirements.txt in the root and in stm32 folder
    $PYTHON -m pip install -r requirements.txt
    $PYTHON -m pip install fastapi uvicorn requests
    echo "✅ Dependencies installed."
}

start_all() {
    echo "🌱 Powering up Cybergarden..."
    start_service "web" "$UVICORN backend.app:app --host 0.0.0.0 --port 8000"
    start_service "receiver" "$UVICORN receiver.receiver:app --host 0.0.0.0 --port 8001"
    
    # Give the receiver a second to boot before the STM32 script tries to connect
    sleep 2 
    start_service "stm32" "$PYTHON -u stm32/stm.py"
}

stop_all() {
    echo "🍂 Shutting down Cybergarden..."
    stop_service "stm32"
    stop_service "receiver"
    stop_service "web"
}

status_all() {
    echo "📊 Cybergarden System Status:"
    status_service "web"
    status_service "receiver"
    status_service "stm32"
}

# --- CLI ROUTING ---

case "$1" in
    setup)
        setup
        ;;
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_all
        ;;
    status)
        status_all
        ;;
    *)
        echo "Usage: $0 {setup|start|stop|restart|status}"
        exit 1
esac