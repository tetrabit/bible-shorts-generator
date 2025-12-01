#!/bin/bash

# Bible Shorts Generator - Run Script

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Parse command
case "$1" in
    generate)
        # Generate N videos (default: 1)
        count=${2:-1}
        python3 src/main.py --generate $count
        ;;

    upload)
        # Upload video by ID
        if [ -z "$2" ]; then
            echo "ERROR: Video ID required"
            echo "Usage: ./run.sh upload <video_id>"
            exit 1
        fi
        python3 src/main.py --upload $2
        ;;

    schedule)
        # Start scheduler
        echo "Starting scheduler..."
        echo "Press Ctrl+C to stop"
        python3 src/main.py --schedule
        ;;

    stats)
        # Show statistics
        python3 src/main.py --stats
        ;;

    retry)
        # Retry failed videos
        python3 src/main.py --retry
        ;;

    mode)
        # Set processing mode
        if [ -z "$2" ]; then
            echo "ERROR: Mode required (random or sequential)"
            echo "Usage: ./run.sh mode <random|sequential>"
            exit 1
        fi
        python3 src/main.py --mode $2
        ;;

    progress)
        # Show current progress
        python3 src/main.py --progress
        ;;

    test)
        # Test components
        echo "Testing components..."
        echo ""

        echo "1. Testing configuration..."
        python3 -c "from src.config import config; print('✓ Config loaded')"

        echo "2. Testing database..."
        python3 -c "from src.modules.database import Database; db = Database(); print('✓ Database OK')"

        echo "3. Testing FFmpeg..."
        python3 -c "from src.utils.ffmpeg_utils import check_ffmpeg; print('✓ FFmpeg found' if check_ffmpeg() else '✗ FFmpeg not found')"

        echo "4. Testing Piper TTS..."
        python3 -c "from src.modules.tts_engine import TTSEngine; from src.config import config; tts = TTSEngine(config); print('✓ Piper available' if tts.test_installation() else '✗ Piper not found')"

        echo ""
        echo "Basic tests complete!"
        ;;

    logs)
        # Tail logs
        log_file=${2:-app.log}
        tail -f logs/$log_file
        ;;

    clean)
        # Clean generated files
        read -p "Delete all generated files? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf generated/{backgrounds,audio,timestamps,subtitles,final}/*
            echo "✓ Generated files cleaned"
        fi
        ;;

    db)
        # Database operations
        case "$2" in
            shell)
                sqlite3 data/database.db
                ;;
            stats)
                sqlite3 data/database.db "SELECT * FROM statistics ORDER BY date DESC LIMIT 7;"
                ;;
            videos)
                sqlite3 data/database.db "SELECT id, verse_id, status, created_at FROM videos ORDER BY created_at DESC LIMIT 10;"
                ;;
            ready)
                sqlite3 data/database.db "SELECT id, verse_id, created_at FROM videos WHERE status='ready' ORDER BY created_at ASC;"
                ;;
            *)
                echo "Database commands:"
                echo "  ./run.sh db shell   - Open database shell"
                echo "  ./run.sh db stats   - Show statistics"
                echo "  ./run.sh db videos  - List recent videos"
                echo "  ./run.sh db ready   - List videos ready to upload"
                ;;
        esac
        ;;

    auth)
        # Run authentication
        python3 auth.py
        ;;

    models)
        # Download models
        python3 download_models.py
        ;;

    --help|help|-h)
        echo "Bible Shorts Generator - Command Line Interface"
        echo ""
        echo "Usage: ./run.sh <command> [arguments]"
        echo ""
        echo "Commands:"
        echo "  generate <N>      Generate N videos (default: 1)"
        echo "  upload <ID>       Upload video by database ID"
        echo "  schedule          Start automated scheduler"
        echo "  stats             Show generation statistics"
        echo "  retry             Retry failed videos (up to 3 attempts)"
        echo "  mode <type>       Set mode (random or sequential)"
        echo "  progress          Show current progress (sequential mode)"
        echo "  test              Run component tests"
        echo "  logs [file]       Tail log files (default: app.log)"
        echo "  clean             Delete generated files"
        echo "  db <cmd>          Database operations"
        echo "  auth              Authenticate with YouTube"
        echo "  models            Download AI models"
        echo "  help              Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run.sh generate 3           # Generate 3 videos"
        echo "  ./run.sh upload 42            # Upload video ID 42"
        echo "  ./run.sh schedule             # Start scheduler"
        echo "  ./run.sh retry                # Retry failed videos"
        echo "  ./run.sh mode sequential      # Enable sequential mode"
        echo "  ./run.sh progress             # Check progress"
        echo "  ./run.sh logs upload.log      # View upload logs"
        echo ""
        ;;

    *)
        echo "Unknown command: $1"
        echo "Run './run.sh help' for usage information"
        exit 1
        ;;
esac
