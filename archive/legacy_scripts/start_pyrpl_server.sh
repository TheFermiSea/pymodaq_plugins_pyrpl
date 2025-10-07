#!/bin/bash
# Start PyRPL TCP Server for PyMoDAQ integration
#
# This server runs PyRPL and exposes it via TCP to PyMoDAQ clients.
# Run this BEFORE launching the PyMoDAQ dashboard.
#
# Usage:
#   ./start_pyrpl_server.sh              # Real hardware
#   ./start_pyrpl_server.sh --mock       # Mock mode (no hardware)

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Default settings
HOSTNAME="100.107.106.75"
CONFIG="pymodaq"
PORT=6341

echo "=========================================="
echo "Starting PyRPL TCP Server"
echo "=========================================="
echo "Red Pitaya IP: $HOSTNAME"
echo "Config: $CONFIG"
echo "Port: $PORT"
echo ""
echo "PyMoDAQ clients should connect to:"
echo "  Server IP: localhost"
echo "  Server Port: $PORT"
echo ""
echo "Press Ctrl+C to stop server"
echo "=========================================="
echo ""

# Start server
python -m pymodaq_plugins_pyrpl.utils.pyrpl_tcp_server \
    --hostname "$HOSTNAME" \
    --config "$CONFIG" \
    --port "$PORT" \
    "$@"
