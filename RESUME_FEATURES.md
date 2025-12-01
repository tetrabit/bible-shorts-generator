# Resume & Retry Features

Your Bible Shorts Generator now has comprehensive resume and retry capabilities!

## ✅ What's New

### 1. **Auto-Retry for Failed Videos**
Videos that fail during generation are automatically retried up to 3 times.

### 2. **Sequential Verse Processing**
Process verses in order from start to finish with automatic progress tracking.

### 3. **Resume After Shutdown**
The system remembers where it left off and continues from that exact point.

## Features in Detail

### Auto-Retry System

**How it works:**
- Failed videos are marked with error message and retry count
- System automatically retries failed videos every 4 hours (when scheduler is running)
- Maximum 3 retry attempts per video
- After 3 failed attempts, video is marked as permanently failed

**Manual retry:**
```bash
./run.sh retry
```

**What you'll see:**
```
Retrying 5 failed videos...

Retrying: Psalms_23_4
Previous error: CUDA out of memory
Retry attempt: 1/3
✓ Retry successful!

Total retried: 5
Successful: 3
Still failed: 2
```

### Sequential Mode

**Enable sequential processing:**
```bash
./run.sh mode sequential
```

**How it works:**
1. Starts at first verse of first configured book
2. Processes verses in order: Chapter 1:1, 1:2, 1:3... 2:1, 2:2...
3. Skips verses that don't meet criteria (word count, duration)
4. Saves progress after each successful generation
5. Automatically resumes from last position after shutdown

**Check progress:**
```bash
./run.sh progress
```

**Output:**
```
Current Progress
==================================================
Mode: sequential
Current position: Psalms 45:12
Last updated: 2025-01-01 14:32:15

Total verses processed: 127
```

**Switch back to random:**
```bash
./run.sh mode random
```

### Resume Capability

**After computer shutdown/restart:**

1. **Random Mode:**
   - Skips already generated verses
   - Continues picking random verses that haven't been done
   - No duplicates

2. **Sequential Mode:**
   - Resumes from exact verse where it left off
   - Example: Was on Psalms 45:12, continues with Psalms 45:13
   - Perfect for processing entire books systematically

**Just restart the scheduler:**
```bash
./run.sh schedule
```

System automatically:
- Loads database
- Checks progress
- Resumes from where it stopped

## Database Tracking

All progress is saved in SQLite database (`data/database.db`):

**Tables:**
- `videos` - All generated videos with retry count and error messages
- `progress` - Current position for sequential mode
- `statistics` - Daily metrics

**View status:**
```bash
# Full statistics with retry info
./run.sh stats

# Just progress
./run.sh progress

# Database queries
./run.sh db videos    # Recent videos
./run.sh db ready     # Ready to upload
```

## Enhanced Statistics

**New stats command shows:**
```bash
./run.sh stats
```

Output:
```
Statistics (Last 7 Days)
==================================================
Date: 2025-01-01
  Generated: 15
  Uploaded: 12
  Errors: 3

Video Status Counts
==================================================
pending: 2
processing: 0
ready: 5
uploaded: 120
failed: 3

Processing Stats
==================================================
Total videos: 130
Failed (retryable): 2
Failed (permanent): 1

Current Mode
==================================================
Mode: sequential
Progress: Psalms 45:12
```

## Scheduler Integration

When scheduler is running (`./run.sh schedule`), it automatically:

**Every 2 hours:**
- Generates batch of new videos

**Every 4 hours:**
- Retries failed videos (up to 3 attempts)

**At scheduled times (9am, 3pm, 9pm):**
- Uploads ready videos

**Daily at 3am:**
- Cleans up old files
- Database maintenance

## Use Cases

### Use Case 1: Generate All Psalms in Order

```bash
# Set to sequential mode
./run.sh mode sequential

# Check starting point
./run.sh progress

# Start scheduler
./run.sh schedule
```

System will process:
- Psalms 1:1, 1:2, 1:3... → 2:1, 2:2... → all 150 chapters
- Automatically skip verses that are too long/short
- Save progress after each verse
- Resume if interrupted

### Use Case 2: Random Verses with Auto-Retry

```bash
# Ensure random mode
./run.sh mode random

# Start scheduler
./run.sh schedule
```

System will:
- Generate random verses
- Never repeat verses
- Auto-retry any failures
- Continue indefinitely

### Use Case 3: Recover from Failures

```bash
# Check what failed
./run.sh stats

# Manually retry all failures
./run.sh retry

# Or wait for automatic retry (every 4 hours)
```

## Technical Details

### Database Schema Changes

**New columns in `videos` table:**
- `retry_count` - Number of retry attempts
- `error_message` - Last error message

**New table:**
```sql
CREATE TABLE progress (
    id INTEGER PRIMARY KEY,
    current_book TEXT,
    current_chapter INTEGER,
    current_verse INTEGER,
    mode TEXT,  -- 'random' or 'sequential'
    updated_at TIMESTAMP
);
```

### New Methods

**Database (`database.py`):**
- `mark_video_failed(video_id, error)` - Track failures
- `get_failed_videos_for_retry(max_retry)` - Get retryable videos
- `reset_video_for_retry(video_id)` - Reset for retry
- `get_progress()` - Get current progress
- `set_progress(book, chapter, verse)` - Update progress
- `set_mode(mode)` - Change mode

**Main (`main.py`):**
- `retry_failed_videos()` - Retry all failed videos

**Verse Selector (`verse_selector.py`):**
- `_select_sequential_verse()` - Sequential verse selection

## Configuration

No configuration changes needed! Features work out of the box.

Optional: Adjust retry interval in `scheduler.py` (default: 4 hours)

## Monitoring

**Live logs:**
```bash
tail -f logs/app.log
```

**Database queries:**
```bash
# Failed videos with error messages
sqlite3 data/database.db "SELECT verse_id, retry_count, error_message FROM videos WHERE status='failed';"

# Current progress
sqlite3 data/database.db "SELECT * FROM progress;"

# Success rate
sqlite3 data/database.db "SELECT status, COUNT(*) as count FROM videos GROUP BY status;"
```

## Benefits

✅ **Never lose work** - All progress saved to database
✅ **Automatic recovery** - Retries handle temporary failures
✅ **Resume anytime** - Shutdown and restart without losing place
✅ **Sequential processing** - Process books in order if desired
✅ **Full visibility** - Track exactly what's happening
✅ **Zero maintenance** - Everything automatic

## Migration

**Existing installations:**

The database will automatically upgrade when you run:
```bash
./run.sh stats
# or any command that uses the database
```

New columns and tables are created automatically.

**No data loss** - Existing videos are preserved.

## Summary

Your Bible Shorts Generator is now even more robust:

- **Won't duplicate verses** - Tracks everything in database
- **Retries failures automatically** - Up to 3 attempts
- **Resumes after shutdown** - Exact position saved
- **Sequential mode available** - Process books in order
- **Full visibility** - Stats show retries, progress, everything

Just run `./run.sh schedule` and it handles everything! 🚀
