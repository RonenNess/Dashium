from pathlib import Path


DATA_COLLECTORS = [
    {
        "module": "example_data_collector", 
        "collect_interval_in_minutes": 1, 
        "config": {}
    },
    {
        "module": "cpu_usage", 
        "collect_interval_in_minutes": 5, 
        "config": {"retention_days": 60, "collect_when_server_starts": True}
    },
    {
        "module": "memory_usage", 
        "collect_interval_in_minutes": 5, 
        "config": {"retention_days": 60, "collect_when_server_starts": True}
    },
    {
        "module": "network_usage", 
        "collect_interval_in_minutes": 5, 
        "config": {"retention_days": 60, "collect_when_server_starts": True}
    },
    {
        "module": "io_operations", 
        "collect_interval_in_minutes": 5, 
        "config": {"retention_days": 60, "collect_when_server_starts": True}
    },
    {
        "module": "processes_count", 
        "collect_interval_in_minutes": 5, 
        "config": {"retention_days": 60, "collect_when_server_starts": True}
    },
    {
        "module": "windows_counters", 
        "collect_interval_in_minutes": 5, 
        "config": {"retention_days": 7, "collect_when_server_starts": True}
    },
    {
        "module": "disk_usage", 
        "collect_interval_in_minutes": 10, 
        "unique_id": "root",
        "config": {
            "retention_days": 60,
            "path": "/",
            "collect_when_server_starts": True
        }
    },
    {
        "module": "logs_collector", 
        "collect_interval_in_minutes": 1, 
        "config": {
            "log_file_path": str(Path(__file__).parent / 'logs' / 'app.log'),
            "log_pattern": r'^(\w+)\s*\|\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s*\|\s*([^|]+)\s*\|\s*(.+)$',
            "timestamp_format": '%Y-%m-%d %H:%M:%S,%f',
            "timestamp_group_index": 2,
            "severity_group_index": 1,
            "content_group_index": 4,
            "retention_days": 60
        }
    }
]