"""Utility for cleaning up old log files."""

import shutil
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger


def cleanup_old_logs(logs_dir: str = "logs", days_to_keep: int = 7, dry_run: bool = False) -> dict:
    """Remove log files and directories older than specified days.
    
    Args:
        logs_dir: Path to the logs directory (default: "logs")
        days_to_keep: Number of days to keep (default: 7)
        dry_run: If True, only report what would be deleted without actually deleting
        
    Returns:
        Dictionary with cleanup statistics
    """
    logs_path = Path(logs_dir)
    
    if not logs_path.exists():
        logger.warning(f"Logs directory does not exist: {logs_path}")
        return {"error": "Directory not found", "deleted_files": 0, "deleted_dirs": 0, "freed_bytes": 0}
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    logger.info(f"Cleaning up logs older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    stats = {
        "deleted_files": 0,
        "deleted_dirs": 0,
        "freed_bytes": 0,
        "errors": []
    }
    
    # Find all date-based directories (format: YYYY/YYYY MM/YYYY MM DD/)
    for year_dir in sorted(logs_path.glob("*")):
        if not year_dir.is_dir():
            continue
            
        for month_dir in sorted(year_dir.glob("*")):
            if not month_dir.is_dir():
                continue
                
            for day_dir in sorted(month_dir.glob("*")):
                if not day_dir.is_dir():
                    continue
                
                # Parse directory name to get date
                try:
                    # Format is "YYYY MM DD"
                    dir_date = datetime.strptime(day_dir.name, "%Y %m %d")
                    
                    if dir_date < cutoff_date:
                        # Calculate size before deletion
                        dir_size = sum(f.stat().st_size for f in day_dir.rglob("*") if f.is_file())
                        
                        if dry_run:
                            logger.info(f"[DRY RUN] Would delete: {day_dir} ({dir_size / 1024 / 1024:.2f} MB)")
                            stats["deleted_dirs"] += 1
                            stats["freed_bytes"] += dir_size
                        else:
                            try:
                                shutil.rmtree(day_dir)
                                logger.info(f"Deleted: {day_dir} ({dir_size / 1024 / 1024:.2f} MB)")
                                stats["deleted_dirs"] += 1
                                stats["freed_bytes"] += dir_size
                            except Exception as e:
                                error_msg = f"Failed to delete {day_dir}: {e}"
                                logger.error(error_msg)
                                stats["errors"].append(error_msg)
                                
                except ValueError:
                    # Not a date directory, skip
                    continue
            
            # Clean up empty month directories after processing all day dirs
            if month_dir.exists() and not any(month_dir.iterdir()):
                if dry_run:
                    logger.info(f"[DRY RUN] Would delete empty month dir: {month_dir}")
                else:
                    try:
                        month_dir.rmdir()
                        logger.info(f"Deleted empty month directory: {month_dir}")
                    except Exception as e:
                        logger.warning(f"Could not delete empty month dir {month_dir}: {e}")
        
        # Clean up empty year directories after processing all month dirs
        if year_dir.exists() and not any(year_dir.iterdir()):
            if dry_run:
                logger.info(f"[DRY RUN] Would delete empty year dir: {year_dir}")
            else:
                try:
                    year_dir.rmdir()
                    logger.info(f"Deleted empty year directory: {year_dir}")
                except Exception as e:
                    logger.warning(f"Could not delete empty year dir {year_dir}: {e}")
    
    # Summary
    freed_mb = stats["freed_bytes"] / 1024 / 1024
    action = "Would free" if dry_run else "Freed"
    logger.info(
        f"Cleanup {'simulation' if dry_run else 'complete'}: "
        f"{stats['deleted_dirs']} directories, {action} {freed_mb:.2f} MB"
    )
    
    if stats["errors"]:
        logger.warning(f"Encountered {len(stats['errors'])} errors during cleanup")
    
    return stats


def cleanup_old_log_files(logs_dir: str = "logs", days_to_keep: int = 7, dry_run: bool = False) -> dict:
    """Remove individual log files older than specified days (for flat log structures).
    
    This is an alternative approach for log directories without date-based folder structure.
    
    Args:
        logs_dir: Path to the logs directory (default: "logs")
        days_to_keep: Number of days to keep (default: 7)
        dry_run: If True, only report what would be deleted without actually deleting
        
    Returns:
        Dictionary with cleanup statistics
    """
    logs_path = Path(logs_dir)
    
    if not logs_path.exists():
        logger.warning(f"Logs directory does not exist: {logs_path}")
        return {"error": "Directory not found", "deleted_files": 0, "freed_bytes": 0}
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cutoff_timestamp = cutoff_date.timestamp()
    
    logger.info(f"Cleaning up log files older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    stats = {
        "deleted_files": 0,
        "freed_bytes": 0,
        "errors": []
    }
    
    # Find all log files recursively
    for log_file in logs_path.rglob("*.log*"):  # Matches .log, .log.zip, etc.
        if not log_file.is_file():
            continue
        
        try:
            # Check file modification time
            file_mtime = log_file.stat().st_mtime
            
            if file_mtime < cutoff_timestamp:
                file_size = log_file.stat().st_size
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would delete: {log_file} ({file_size / 1024:.2f} KB)")
                    stats["deleted_files"] += 1
                    stats["freed_bytes"] += file_size
                else:
                    try:
                        log_file.unlink()
                        logger.info(f"Deleted: {log_file} ({file_size / 1024:.2f} KB)")
                        stats["deleted_files"] += 1
                        stats["freed_bytes"] += file_size
                    except Exception as e:
                        error_msg = f"Failed to delete {log_file}: {e}"
                        logger.error(error_msg)
                        stats["errors"].append(error_msg)
                        
        except Exception as e:
            error_msg = f"Error processing {log_file}: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
    
    # Summary
    freed_mb = stats["freed_bytes"] / 1024 / 1024
    action = "Would free" if dry_run else "Freed"
    logger.info(
        f"Cleanup {'simulation' if dry_run else 'complete'}: "
        f"{stats['deleted_files']} files, {action} {freed_mb:.2f} MB"
    )
    
    if stats["errors"]:
        logger.warning(f"Encountered {len(stats['errors'])} errors during cleanup")
    
    return stats


if __name__ == "__main__":
    import sys
    
    # Simple CLI interface
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    days = 7
    
    # Check for custom days argument
    for arg in sys.argv:
        if arg.startswith("--days="):
            try:
                days = int(arg.split("=")[1])
            except ValueError:
                print(f"Invalid days value: {arg}")
                sys.exit(1)
    
    print(f"Log Cleanup Utility")
    print(f"Mode: {'DRY RUN (no files will be deleted)' if dry_run else 'LIVE (files will be deleted)'}")
    print(f"Keeping logs from the last {days} days\n")
    
    # Run cleanup for date-based directory structure
    stats = cleanup_old_logs(days_to_keep=days, dry_run=dry_run)
    
    print(f"\nResults:")
    print(f"  Directories processed: {stats['deleted_dirs']}")
    print(f"  Space freed: {stats['freed_bytes'] / 1024 / 1024:.2f} MB")
    if stats["errors"]:
        print(f"  Errors: {len(stats['errors'])}")
