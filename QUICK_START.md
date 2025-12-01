# Quick Start Guide

Get your Bible Shorts Generator running in 30 minutes!

## Prerequisites

- Ubuntu/Debian Linux (or similar)
- NVIDIA GPU with 12GB+ VRAM
- 100GB free disk space
- Internet connection

## Step-by-Step Setup

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3.10 python3-pip python3-venv ffmpeg git
```

### 2. Clone & Setup

```bash
# Clone repository
cd ~
git clone <your-repo-url> bible-shorts-generator
cd bible-shorts-generator

# Run setup script
./setup.sh
```

**Note:** Setup will ask if you want to download AI models (~15GB). Say yes if you have time and bandwidth. Otherwise, download later with `./run.sh models`.

### 3. Get YouTube API Credentials

1. Go to https://console.cloud.google.com/
2. Create new project: "Bible Shorts"
3. Enable API: "YouTube Data API v3"
4. Create credentials: OAuth 2.0 Client ID (Desktop app)
5. Download JSON file
6. Save as `client_secrets.json` in project directory

### 4. Authenticate with YouTube

```bash
./run.sh auth
```

- Browser will open
- Log in to Google account
- Grant permissions
- Credentials automatically saved

### 5. Generate First Video

```bash
./run.sh generate 1
```

**First run will be slow** (downloading models if not done earlier). Subsequent runs are much faster.

Output: `generated/final/<verse_id>.mp4`

### 6. Upload to YouTube

```bash
# Get video ID from previous output or database
./run.sh db ready

# Upload video
./run.sh upload <video_id>
```

## Configuration Tips

### Adjust Video Settings

Edit `config.yaml`:

```yaml
bible:
  books: ["Psalms", "Proverbs", "John"]  # Choose your favorite books
  max_words: 18  # Increase for slightly longer verses

youtube:
  privacy: "private"  # Start with private for testing
  upload_schedule:
    times: ["10:00", "14:00", "18:00"]  # Your preferred times
```

### Test Before Automating

```bash
# Generate 3 test videos
./run.sh generate 3

# Check output
ls -lh generated/final/

# View statistics
./run.sh stats
```

### Start Automated Scheduler

Once you're happy with the output:

```bash
./run.sh schedule
```

This runs indefinitely:
- Generates videos every 2 hours
- Uploads at scheduled times
- Handles cleanup automatically

**Run in background:**

```bash
# Option 1: screen
screen -S bible-shorts
./run.sh schedule
# Press Ctrl+A then D to detach

# Option 2: tmux
tmux new -s bible-shorts
./run.sh schedule
# Press Ctrl+B then D to detach

# Option 3: systemd (recommended for production)
# See README.md for systemd setup
```

## Common First-Time Issues

### Issue: CUDA Out of Memory

```yaml
# config.yaml - Reduce memory usage
models:
  sdxl:
    num_inference_steps: 20  # Down from 25
```

Or use CPU mode (slower):

```yaml
models:
  sdxl:
    device: "cpu"
    dtype: "float32"
```

### Issue: No Suitable Verses Found

```yaml
# config.yaml - Allow more words
bible:
  max_words: 22  # Up from 18
```

### Issue: YouTube Quota Exceeded

You hit daily limit (6 videos/day default). Solutions:
1. Wait until next day
2. Request quota increase from Google
3. Reduce upload frequency in config

### Issue: Piper TTS Fails

```bash
pip install --upgrade piper-tts
```

## Testing Components

```bash
./run.sh test
```

Should show all green checkmarks:
- ✓ Config loaded
- ✓ Database OK
- ✓ FFmpeg found
- ✓ Piper available

## Monitoring

### View Logs

```bash
# Application logs
./run.sh logs

# Upload logs
./run.sh logs upload.log

# Follow logs in real-time
tail -f logs/app.log
```

### Database Status

```bash
# List recent videos
./run.sh db videos

# Show ready to upload
./run.sh db ready

# View statistics
./run.sh db stats
```

## Performance Expectations

**With RTX 4070:**
- First video: ~5-10 min (model loading)
- Subsequent videos: ~2-4 min each
- Batch of 10: ~25-40 min total

**Storage per video:**
- Intermediate files: ~500MB
- Final video only: ~30-50MB
- Enable cleanup to save space

## Next Steps

1. ✓ Generate test videos
2. ✓ Verify quality
3. ✓ Upload test video
4. ✓ Configure preferences
5. ✓ Start scheduler
6. 📊 Monitor statistics
7. 📈 Scale up (increase batch size)

## Getting Help

```bash
# Show all commands
./run.sh help

# Test specific component
python3 -c "from src.modules.tts_engine import TTSEngine; print('TTS OK')"

# Check logs
./run.sh logs
```

## Production Checklist

Before running 24/7:

- [ ] Test generated 10+ videos successfully
- [ ] Verified video quality (resolution, audio, subtitles)
- [ ] Uploaded test video to YouTube
- [ ] Configured upload schedule
- [ ] Set up monitoring (logs, database)
- [ ] Enabled automatic cleanup
- [ ] (Optional) Set up systemd service
- [ ] (Optional) Set up disk space alerts

## Congratulations!

Your Bible Shorts Generator is now running. The system will:

- ✅ Generate high-quality videos automatically
- ✅ Upload to YouTube on schedule
- ✅ Track everything in database
- ✅ Clean up files automatically
- ✅ Log all activities

Enjoy your automated Bible Shorts channel!
