#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
System monitoring utilities for batch processing.

Provides disk space monitoring, process management, and health checks
for reliable long-running batch operations.
"""

import os
import shutil
import subprocess
import signal
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime

from fintel.core.logging import get_logger

logger = get_logger(__name__)


class DiskMonitor:
    """
    Monitor disk space for batch processing operations.

    Ensures sufficient disk space is available for downloading and
    storing SEC filings during long-running batch operations.
    """

    # Estimated sizes in MB
    ESTIMATED_PDF_SIZE_MB = 15  # Average 10-K PDF size
    ESTIMATED_RESULT_SIZE_MB = 0.1  # Average analysis result size

    # Minimum free space thresholds
    MIN_FREE_SPACE_GB = 5  # Minimum free space to continue processing
    WARNING_FREE_SPACE_GB = 10  # Warn when below this threshold

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize disk monitor.

        Args:
            data_dir: Data directory to monitor (default: ./data)
        """
        self.data_dir = data_dir or Path("./data")
        self.logger = get_logger(f"{__name__}.DiskMonitor")

    def get_disk_space(self) -> Dict[str, float]:
        """
        Get current disk space information.

        Returns:
            Dictionary with total_gb, used_gb, free_gb, percent_used
        """
        try:
            # Get the mount point for the data directory
            path = self.data_dir if self.data_dir.exists() else Path(".")
            usage = shutil.disk_usage(path)

            return {
                'total_gb': usage.total / (1024 ** 3),
                'used_gb': usage.used / (1024 ** 3),
                'free_gb': usage.free / (1024 ** 3),
                'percent_used': (usage.used / usage.total) * 100,
                'path': str(path.absolute())
            }

        except Exception as e:
            self.logger.error(f"Failed to get disk space: {e}")
            return {
                'total_gb': 0,
                'used_gb': 0,
                'free_gb': 0,
                'percent_used': 0,
                'path': str(self.data_dir),
                'error': str(e)
            }

    def estimate_space_needed(self, num_tickers: int, num_years: int) -> float:
        """
        Estimate disk space needed for a batch job.

        Args:
            num_tickers: Number of companies to process
            num_years: Years per company

        Returns:
            Estimated GB needed
        """
        total_filings = num_tickers * num_years

        # PDF storage (may be cached/reused)
        pdf_space_mb = total_filings * self.ESTIMATED_PDF_SIZE_MB

        # Result storage
        result_space_mb = total_filings * self.ESTIMATED_RESULT_SIZE_MB

        # Add 20% buffer for temporary files and database growth
        total_mb = (pdf_space_mb + result_space_mb) * 1.2

        return total_mb / 1024  # Convert to GB

    def check_space_available(
        self,
        num_tickers: int = 0,
        num_years: int = 0
    ) -> Tuple[bool, str]:
        """
        Check if sufficient disk space is available.

        Args:
            num_tickers: Number of companies (optional, for estimation)
            num_years: Years per company (optional, for estimation)

        Returns:
            Tuple of (is_ok, message)
        """
        space = self.get_disk_space()
        free_gb = space.get('free_gb', 0)

        if 'error' in space:
            return False, f"Unable to check disk space: {space['error']}"

        # Estimate needed space if parameters provided
        if num_tickers > 0 and num_years > 0:
            estimated_gb = self.estimate_space_needed(num_tickers, num_years)

            if free_gb < estimated_gb + self.MIN_FREE_SPACE_GB:
                return False, (
                    f"Insufficient disk space. Free: {free_gb:.1f}GB, "
                    f"Estimated needed: {estimated_gb:.1f}GB + "
                    f"{self.MIN_FREE_SPACE_GB}GB reserve"
                )

        # Check minimum threshold
        if free_gb < self.MIN_FREE_SPACE_GB:
            return False, (
                f"Critical: Only {free_gb:.1f}GB free. "
                f"Minimum required: {self.MIN_FREE_SPACE_GB}GB"
            )

        # Check warning threshold
        if free_gb < self.WARNING_FREE_SPACE_GB:
            return True, (
                f"Warning: Low disk space ({free_gb:.1f}GB free). "
                f"Recommended: >{self.WARNING_FREE_SPACE_GB}GB"
            )

        return True, f"Disk space OK: {free_gb:.1f}GB free"

    def should_pause_batch(self) -> bool:
        """
        Check if batch processing should pause due to low disk space.

        Returns:
            True if disk space is critically low
        """
        space = self.get_disk_space()
        free_gb = space.get('free_gb', 0)

        if free_gb < self.MIN_FREE_SPACE_GB:
            self.logger.warning(
                f"Disk space critically low: {free_gb:.1f}GB free. "
                "Batch should pause."
            )
            return True

        return False


class ProcessMonitor:
    """
    Monitor and manage system processes for batch operations.

    Handles Chrome process cleanup and process health monitoring.
    """

    def __init__(self):
        """Initialize process monitor."""
        self.logger = get_logger(f"{__name__}.ProcessMonitor")

    def should_cleanup_chrome(self, memory_threshold_pct: float = 80.0) -> bool:
        """
        Check if Chrome cleanup should be triggered based on memory usage.

        Instead of cleaning up on a fixed schedule (every N companies),
        this checks actual memory pressure and triggers cleanup when needed.

        Args:
            memory_threshold_pct: Trigger cleanup when memory usage exceeds this %

        Returns:
            True if cleanup should be performed
        """
        memory = self.get_memory_usage()
        if 'error' in memory:
            return False
        used_pct = memory.get('percent_used', 0)
        if used_pct >= memory_threshold_pct:
            self.logger.info(
                f"Memory usage {used_pct:.1f}% exceeds threshold {memory_threshold_pct}%. "
                "Chrome cleanup recommended."
            )
            return True
        return False

    def cleanup_chrome_processes(self, max_age_minutes: int = 60) -> int:
        """
        Clean up orphaned Chrome/Chromium processes.

        During batch processing, Selenium may leave behind Chrome processes
        that consume memory. This method finds and terminates old Chrome
        processes that are likely orphaned.

        Args:
            max_age_minutes: Only kill processes older than this

        Returns:
            Number of processes cleaned up
        """
        cleaned = 0

        try:
            import psutil
        except ImportError:
            self.logger.warning("psutil not installed, cannot cleanup Chrome processes")
            return 0

        current_time = datetime.now().timestamp()

        try:
            for proc in psutil.process_iter(['pid', 'name', 'create_time', 'cmdline']):
                try:
                    pinfo = proc.info
                    name = pinfo.get('name', '').lower()

                    # Check if it's a Chrome-related process
                    if not any(x in name for x in ['chrome', 'chromium', 'chromedriver']):
                        continue

                    # Check process age
                    create_time = pinfo.get('create_time', current_time)
                    age_minutes = (current_time - create_time) / 60

                    if age_minutes < max_age_minutes:
                        continue

                    # Check if it looks like a headless/automation process
                    cmdline = pinfo.get('cmdline', [])
                    cmdline_str = ' '.join(cmdline) if cmdline else ''

                    is_headless = any(x in cmdline_str for x in [
                        '--headless', '--disable-gpu', '--no-sandbox',
                        'chromedriver', '--remote-debugging'
                    ])

                    if is_headless:
                        self.logger.info(
                            f"Terminating orphaned Chrome process: "
                            f"PID {pinfo['pid']}, age {age_minutes:.0f}m"
                        )
                        proc.terminate()
                        cleaned += 1

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            self.logger.error(f"Error during Chrome cleanup: {e}")

        if cleaned > 0:
            self.logger.info(f"Cleaned up {cleaned} orphaned Chrome processes")

        return cleaned

    def is_process_alive(self, pid: int) -> bool:
        """
        Check if a process with given PID is still running.

        Args:
            pid: Process ID to check

        Returns:
            True if process is running
        """
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage information.

        Returns:
            Dictionary with total_gb, used_gb, available_gb, percent_used
        """
        try:
            import psutil
            mem = psutil.virtual_memory()

            return {
                'total_gb': mem.total / (1024 ** 3),
                'used_gb': mem.used / (1024 ** 3),
                'available_gb': mem.available / (1024 ** 3),
                'percent_used': mem.percent
            }

        except ImportError:
            return {
                'error': 'psutil not installed'
            }
        except Exception as e:
            return {
                'error': str(e)
            }


class HealthChecker:
    """
    Comprehensive health check for batch processing systems.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize health checker.

        Args:
            data_dir: Data directory to monitor
        """
        self.disk_monitor = DiskMonitor(data_dir)
        self.process_monitor = ProcessMonitor()
        self.logger = get_logger(f"{__name__}.HealthChecker")

    def run_health_check(self) -> Dict:
        """
        Run comprehensive health check.

        Returns:
            Dictionary with health check results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'healthy': True,
            'warnings': [],
            'errors': []
        }

        # Check disk space
        disk_ok, disk_msg = self.disk_monitor.check_space_available()
        results['disk'] = self.disk_monitor.get_disk_space()

        if not disk_ok:
            results['healthy'] = False
            results['errors'].append(disk_msg)
        elif 'Warning' in disk_msg:
            results['warnings'].append(disk_msg)

        # Check memory
        memory = self.process_monitor.get_memory_usage()
        results['memory'] = memory

        if 'error' not in memory:
            if memory.get('percent_used', 0) > 90:
                results['warnings'].append(
                    f"High memory usage: {memory['percent_used']:.1f}%"
                )

        return results

    def is_healthy(self) -> bool:
        """
        Quick health check - returns True if system is healthy.

        Returns:
            True if all critical checks pass
        """
        check = self.run_health_check()
        return check['healthy']


# Convenience function for quick disk space check
def check_disk_space(data_dir: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Quick check if sufficient disk space is available.

    Args:
        data_dir: Data directory to check

    Returns:
        Tuple of (is_ok, message)
    """
    monitor = DiskMonitor(data_dir)
    return monitor.check_space_available()


# Convenience function for Chrome cleanup
def cleanup_orphaned_chrome(max_age_minutes: int = 60) -> int:
    """
    Clean up orphaned Chrome processes.

    Args:
        max_age_minutes: Only kill processes older than this

    Returns:
        Number of processes cleaned up
    """
    monitor = ProcessMonitor()
    return monitor.cleanup_chrome_processes(max_age_minutes)
