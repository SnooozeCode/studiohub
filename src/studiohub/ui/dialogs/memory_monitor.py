"""Memory monitor dialog for debugging memory usage."""
from __future__ import annotations

import gc
import psutil
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any

import types
from collections import Counter

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QDialog, QProgressBar

from studiohub.style.typography.rules import apply_typography


class MemoryMonitorDialog(QDialog):
    """Dialog showing detailed memory usage statistics."""
    
    def __init__(self, parent=None, app_start_time=None):
        super().__init__(parent)
        self.setWindowTitle("Memory Monitor")
        self.setModal(False)
        self.setMinimumSize(600, 500)
        self.setObjectName("MemoryMonitorDialog")
        
        self._process = psutil.Process(os.getpid())
        self._history: list[float] = []
        self._max_history = 60

        if app_start_time:
            self._start_time = app_start_time
        else:
            self._start_time = time.time()
        
        self._setup_ui()
        self._setup_timer()
        self._refresh()
    
    def _setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Memory Usage Monitor")
        header.setObjectName("DialogTitle")
        apply_typography(header, "h2")
        layout.addWidget(header)
        
        # Runtime display
        runtime_layout = QHBoxLayout()
        runtime_layout.addWidget(QLabel("Runtime:"))
        self.runtime_label = QLabel("0:00:00")
        apply_typography(self.runtime_label, "h3")
        runtime_layout.addWidget(self.runtime_label)
        runtime_layout.addStretch()
        layout.addLayout(runtime_layout)
        
        # Current usage
        self.current_label = QLabel("Current: -- MB")
        apply_typography(self.current_label, "h3")
        layout.addWidget(self.current_label)
        
        # Progress bar for visual
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)  # 0-1000MB scale
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v MB")
        layout.addWidget(self.progress_bar)
        
        # Stats grid
        stats_widget = QtWidgets.QWidget()
        stats_layout = QtWidgets.QGridLayout(stats_widget)
        stats_layout.setSpacing(8)
        
        # Row 1
        stats_layout.addWidget(QLabel("Peak:"), 0, 0)
        self.peak_label = QLabel("-- MB")
        apply_typography(self.peak_label, "body-strong")
        stats_layout.addWidget(self.peak_label, 0, 1)
        
        stats_layout.addWidget(QLabel("Min:"), 0, 2)
        self.min_label = QLabel("-- MB")
        apply_typography(self.min_label, "body-strong")
        stats_layout.addWidget(self.min_label, 0, 3)
        
        # Row 2
        stats_layout.addWidget(QLabel("Growth rate:"), 1, 0)
        self.growth_label = QLabel("-- MB/hour")
        apply_typography(self.growth_label, "body-strong")
        stats_layout.addWidget(self.growth_label, 1, 1)
        
        stats_layout.addWidget(QLabel("Threads:"), 1, 2)
        self.threads_label = QLabel("--")
        apply_typography(self.threads_label, "body-strong")
        stats_layout.addWidget(self.threads_label, 1, 3)
        
        # Row 3
        stats_layout.addWidget(QLabel("Samples:"), 2, 0)
        self.samples_label = QLabel("0")
        apply_typography(self.samples_label, "body-strong")
        stats_layout.addWidget(self.samples_label, 2, 1)
        
        layout.addWidget(stats_widget)
        
        # Cache breakdown section
        cache_header = QLabel("Cache Breakdown")
        cache_header.setObjectName("SectionHeader")
        apply_typography(cache_header, "h4")
        layout.addWidget(cache_header)
        
        self.cache_text = QTextEdit()
        self.cache_text.setReadOnly(True)
        self.cache_text.setFont(QtGui.QFont("Courier New", 10))
        self.cache_text.setMinimumHeight(150)
        layout.addWidget(self.cache_text)
        
        # Object count section
        objects_header = QLabel("Object Counts")
        objects_header.setObjectName("SectionHeader")
        apply_typography(objects_header, "h4")
        layout.addWidget(objects_header)
        
        self.objects_text = QTextEdit()
        self.objects_text.setReadOnly(True)
        self.objects_text.setFont(QtGui.QFont("Courier New", 10))
        self.objects_text.setMinimumHeight(150)
        layout.addWidget(self.objects_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.clicked.connect(self._refresh)
        button_layout.addWidget(self.refresh_btn)
        
        self.gc_btn = QPushButton("Run Garbage Collection")
        self.gc_btn.clicked.connect(self._force_gc)
        button_layout.addWidget(self.gc_btn)
        
        self.clear_cache_btn = QPushButton("Clear Icon Cache")
        self.clear_cache_btn.clicked.connect(self._clear_icon_cache)
        button_layout.addWidget(self.clear_cache_btn)
        
        self.trace_btn = QPushButton("Trace Functions")
        self.trace_btn.clicked.connect(self._trace_new_functions)
        button_layout.addWidget(self.trace_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _setup_timer(self):
        """Setup auto-refresh timer."""
        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh)
        self._timer.start(5000)  # Refresh every 5 seconds
        
        # Timer for runtime updates
        self._runtime_timer = QTimer()
        self._runtime_timer.timeout.connect(self._update_runtime)
        self._runtime_timer.start(1000)  # Update every second
    
    def _update_runtime(self):
        """Update the runtime display."""
        elapsed = time.time() - self._start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        self.runtime_label.setText(f"{hours}:{minutes:02d}:{seconds:02d}")
    
    def _force_gc(self):
        """Force garbage collection."""
        before = self._process.memory_info().rss / 1024 / 1024
        collected = gc.collect()
        after = self._process.memory_info().rss / 1024 / 1024
        
        QtWidgets.QMessageBox.information(
            self,
            "Garbage Collection",
            f"Collected {collected} objects\n"
            f"Memory: {before:.1f}MB → {after:.1f}MB ({(before-after):.1f}MB freed)"
        )
        self._refresh()
    
    def _clear_icon_cache(self):
        """Clear the global icon cache."""
        try:
            from studiohub.ui.views.missing_files_view_qt import _ICON_CACHE
            size = len(_ICON_CACHE)
            _ICON_CACHE.clear()
            QtWidgets.QMessageBox.information(
                self,
                "Cache Cleared",
                f"Cleared {size} icons from cache"
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                f"Failed to clear icon cache: {e}"
            )
        self._refresh()
    
    def _refresh(self):
        """Update all displays."""
        try:
            # Basic process info
            mem_info = self._process.memory_info()
            rss_mb = mem_info.rss / 1024 / 1024
            vms_mb = mem_info.vms / 1024 / 1024
            
            # Update history
            self._history.append(rss_mb)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            
            # Current usage
            self.current_label.setText(f"Current: {rss_mb:.1f} MB (RSS) / {vms_mb:.1f} MB (VMS)")
            self.progress_bar.setValue(int(rss_mb))
            
            # Peak and min
            peak = max(self._history) if self._history else rss_mb
            minimum = min(self._history) if self._history else rss_mb
            self.peak_label.setText(f"{peak:.1f} MB")
            self.min_label.setText(f"{minimum:.1f} MB")
            
            # Samples count
            self.samples_label.setText(str(len(self._history)))
            
            # Growth rate (MB per hour) - using actual runtime
            if len(self._history) >= 2:
                elapsed_hours = (time.time() - self._start_time) / 3600
                if elapsed_hours > 0:
                    first = self._history[0]
                    last = self._history[-1]
                    growth = (last - first) / elapsed_hours
                    self.growth_label.setText(f"{growth:.1f} MB/hour")
            else:
                self.growth_label.setText("-- MB/hour")
            
            # Thread count
            self.threads_label.setText(str(len(self._process.threads())))
            
            # Cache breakdown
            self._update_cache_info()
            
            # Object counts
            self._update_object_counts()
            
        except Exception as e:
            self.cache_text.setText(f"Error refreshing: {e}")
    
    def _update_cache_info(self):
        """Get cache sizes from various modules."""
        lines = []
        
        # Icon cache
        try:
            from studiohub.ui.views.missing_files_view_qt import _ICON_CACHE
            lines.append(f"Icon cache: {len(_ICON_CACHE)} items")
            
            # Estimate size (rough)
            if hasattr(_ICON_CACHE, '__sizeof__'):
                size_bytes = _ICON_CACHE.__sizeof__()
                lines.append(f"  Approx size: {size_bytes / 1024 / 1024:.1f} MB")
        except:
            lines.append("Icon cache: N/A")
        
        # Print log cache
        try:
            parent = self.parent()
            if parent and hasattr(parent, '_deps'):
                print_log = parent._deps.print_log_state
                if print_log:
                    jobs = len(getattr(print_log, '_jobs', []))
                    lines.append(f"Print log: {jobs} jobs")
        except:
            pass
        
        # Notification cache
        try:
            if parent and hasattr(parent, '_deps'):
                notif = parent._deps.notification_service
                if notif:
                    notes = len(getattr(notif, '_notifications', []))
                    timers = len(getattr(notif, '_dismiss_timers', {}))
                    lines.append(f"Notifications: {notes} items, {timers} timers")
        except:
            pass
        
        # Decorator cache stats
        try:
            from studiohub.utils.logging.decorators import get_decorator_stats
            stats = get_decorator_stats()
            lines.append(f"Performance wrappers: {stats['performance_wrappers']}")
            lines.append(f"Critical wrappers: {stats['critical_wrappers']}")
        except:
            pass
        
        self.cache_text.setText("\n".join(lines))
    
    def _update_object_counts(self):
        """Count Python objects by type."""
        import collections
        
        # Get all objects
        objects = gc.get_objects()
        
        # Count by type
        type_counts = collections.Counter(type(obj).__name__ for obj in objects)
        
        # Get top 20
        top_types = type_counts.most_common(20)
        
        # Format as text
        lines = ["Top 20 object types:"]
        for type_name, count in top_types:
            lines.append(f"  {type_name}: {count}")
        
        # Add Qt-specific counts
        from PySide6.QtCore import QTimer, QThread, QObject
        from PySide6.QtGui import QPixmap, QIcon
        
        qt_counts = []
        qt_counts.append(f"QTimer: {sum(1 for obj in objects if isinstance(obj, QTimer))}")
        qt_counts.append(f"QThread: {sum(1 for obj in objects if isinstance(obj, QThread))}")
        qt_counts.append(f"QObject: {sum(1 for obj in objects if isinstance(obj, QObject))}")
        qt_counts.append(f"QPixmap: {sum(1 for obj in objects if isinstance(obj, QPixmap))}")
        qt_counts.append(f"QIcon: {sum(1 for obj in objects if isinstance(obj, QIcon))}")
        
        lines.append("\nQt Objects:")
        lines.extend(f"  {line}" for line in qt_counts)
        
        # Add function breakdown
        lines.append("\n" + self._update_function_breakdown())
        
        self.objects_text.setText("\n".join(lines))
    
    def _update_function_breakdown(self):
        """Analyze function objects."""
        # Get all function objects
        functions = [obj for obj in gc.get_objects() if isinstance(obj, types.FunctionType)]
        
        # Group by module and name
        func_names = Counter()
        for f in functions[-1000:]:  # Sample last 1000
            try:
                # Get the defining module
                module = getattr(f, '__module__', 'unknown')
                name = getattr(f, '__name__', 'anonymous')
                func_names[f"{module}.{name}"] += 1
            except:
                pass
        
        # Count lambdas specifically
        lambdas = sum(1 for f in functions if getattr(f, '__name__', '') == '<lambda>')
        
        # Count decorated functions (those with __wrapped__ attribute)
        decorated = sum(1 for f in functions if hasattr(f, '__wrapped__'))
        
        lines = []
        lines.append(f"Total functions: {len(functions)}")
        lines.append(f"  Lambdas: {lambdas}")
        lines.append(f"  Decorated: {decorated}")
        lines.append("")
        lines.append("Top 20 function types:")
        
        for name, count in func_names.most_common(20):
            lines.append(f"  {name}: {count}")
        
        return "\n".join(lines)
    
    def _trace_new_functions(self):
        """Trace newly created functions."""
        import gc
        import types
        from collections import Counter
        
        # Get current function count
        objects = gc.get_objects()
        current_funcs = [obj for obj in objects if isinstance(obj, types.FunctionType)]
        
        # Store for next time
        if not hasattr(self, '_last_funcs'):
            self._last_funcs = current_funcs
            QtWidgets.QMessageBox.information(
                self, 
                "Trace", 
                "Baseline captured. Click again to see new functions."
            )
            return
        
        # Find new functions
        new_funcs = [f for f in current_funcs if f not in self._last_funcs]
        
        # Group by name
        names = Counter()
        for f in new_funcs:
            try:
                names[f"{f.__module__}.{f.__name__}"] += 1
            except:
                names["unknown"] += 1
        
        # Show results
        lines = [f"New functions: {len(new_funcs)}"]
        for name, count in names.most_common(20):
            lines.append(f"  {name}: {count}")
        
        QtWidgets.QMessageBox.information(self, "New Functions", "\n".join(lines))
        
        self._last_funcs = current_funcs
    
    def closeEvent(self, event):
        """Clean up timer on close."""
        self._timer.stop()
        self._runtime_timer.stop()
        super().closeEvent(event)