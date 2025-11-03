"""
Collect data from Windows Performance Counters.
"""
from typing import Dict, List, Any
from datetime import datetime
import platform

error_message = None

# Only import WMI on Windows systems
if platform.system() == "Windows":
    try:
        import wmi
        import pythoncom
    except ImportError:
        error_message = "WMI module must be installed to use Windows counters collector!"
        wmi = None
        pythoncom = None
else:
    wmi = None
    pythoncom = None


def init():
    """Initialize the data collector."""
    if platform.system() != "Windows":
        global error_message
        error_message = "Windows counters collector can only be used on Windows systems!"


def collect(config: Dict[str, Any], persistent_state: object, last_execution_time: datetime) -> List[Dict[str, Any]]:
    """
    Collect data from Windows Performance Counters.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary for the data collector
        persistent_state (object): Persistent state object to store collector state between runs and server executions
        last_execution_time (datetime): The last time the collector was executed

    Returns:
        List[Dict[str, Any]]: List of event dictionaries collected from the data source
    """
    
    if platform.system() != "Windows":
        return []
    
    if wmi is None:
        return []
    
    events = []

    global error_message
    
    try:
        # Initialize COM for this thread
        if pythoncom is not None:
            pythoncom.CoInitialize()
        
        # Connect to WMI
        c = wmi.WMI()
        
        # 1. Processor Queue Length (shows CPU bottlenecks)
        try:
            processor_queue = c.Win32_PerfRawData_PerfOS_System()[0]
            events.append({
                "name": "perf_counters",
                "value": int(processor_queue.ProcessorQueueLength),
                "tag": "processor_queue_length"
            })
        except Exception as e:
            error_message = f"Error getting processor queue length: {e}"
            raise
        
        # 2. Available Memory (MB)
        try:
            memory_info = c.Win32_PerfRawData_PerfOS_Memory()[0]
            available_mb = int(memory_info.AvailableMBytes)
            events.append({
                "name": "perf_counters", 
                "value": available_mb,
                "tag": "available_memory_mb"
            })
        except Exception as e:
            error_message = f"Error getting available memory: {e}"
            raise

        # 3. Pages/sec (memory pressure indicator)
        try:
            memory_info = c.Win32_PerfRawData_PerfOS_Memory()[0]
            events.append({
                "name": "perf_counters",
                "value": int(memory_info.PagesPersec),
                "tag": "pages_per_sec"
            })
        except Exception as e:
            error_message = f"Error getting pages per sec: {e}"
            raise

        # 4. Context Switches/sec (system activity)
        try:
            system_info = c.Win32_PerfRawData_PerfOS_System()[0]
            events.append({
                "name": "perf_counters",
                "value": int(system_info.ContextSwitchesPersec),
                "tag": "context_switches_per_sec"
            })
        except Exception as e:
            error_message = f"Error getting context switches: {e}"  
            raise

        # 5. Process Count
        try:
            system_info = c.Win32_PerfRawData_PerfOS_System()[0]
            events.append({
                "name": "perf_counters",
                "value": int(system_info.Processes),
                "tag": "process_count"
            })
        except Exception as e:
            error_message = f"Error getting process count: {e}"
            raise

        # 6. Thread Count
        try:
            system_info = c.Win32_PerfRawData_PerfOS_System()[0]
            events.append({
                "name": "perf_counters",
                "value": int(system_info.Threads),
                "tag": "thread_count"
            })
        except Exception as e:
            error_message = f"Error getting thread count: {e}"
            raise

        # 7. System Up Time (seconds)
        try:
            system_info = c.Win32_PerfRawData_PerfOS_System()[0]
            events.append({
                "name": "perf_counters",
                "value": int(system_info.SystemUpTime),
                "tag": "system_uptime_sec"
            })
        except Exception as e:
            error_message = f"Error getting system uptime: {e}" 
            raise

        # 8. Disk Queue Length (for first physical disk)
        try:
            disk_info = c.Win32_PerfRawData_PerfDisk_PhysicalDisk()
            for disk in disk_info:
                if disk.Name and "_Total" not in disk.Name and "HarddiskVolume" not in disk.Name:
                    events.append({
                        "name": "perf_counters",
                        "value": int(disk.CurrentDiskQueueLength),
                        "tag": f"disk_queue_length,disk:{disk.Name}"
                    })
                    break  # Only get first physical disk
        except Exception as e:
            error_message = f"Error getting disk queue length: {e}"
            raise

        # 9. Handle Count
        try:
            # Use Process object to get total handles across all processes
            processes = c.Win32_Process()
            total_handles = sum(int(proc.HandleCount or 0) for proc in processes if proc.HandleCount is not None)
            events.append({
                "name": "perf_counters",
                "value": total_handles,
                "tag": "handle_count"
            })
        except Exception as e:
            error_message = f"Error getting handle count: {e}"
            raise

        # 10. Network Interface Bytes Total/sec (for first active network interface)
        try:
            network_adapters = c.Win32_PerfRawData_Tcpip_NetworkInterface()
            for adapter in network_adapters:
                if adapter.Name and "Loopback" not in adapter.Name and "_Total" not in adapter.Name and "Teredo" not in adapter.Name:
                    if int(adapter.BytesTotalPersec or 0) > 0:  # Only active interfaces
                        events.append({
                            "name": "perf_counters", 
                            "value": int(adapter.BytesTotalPersec),
                            "tag": f"network_bytes_per_sec,interface:{adapter.Name}"
                        })
                        events.append({
                            "name": "perf_counters",
                            "value": int(adapter.PacketsPersec or 0), 
                            "tag": f"network_packets_per_sec,interface:{adapter.Name}"
                        })
                        break  # Only get first active interface
        except Exception as e:
            error_message = f"Error getting network interface stats: {e}"
            raise

        # 11. Paging File Usage %
        try:
            paging_file = c.Win32_PerfRawData_PerfOS_PagingFile()
            for pf in paging_file:
                if pf.Name and "_Total" in pf.Name:
                    usage_percent = int(pf.PercentUsage or 0)
                    events.append({
                        "name": "perf_counters",
                        "value": usage_percent,
                        "tag": "paging_file_usage_percent"
                    })
                    break
        except Exception as e:
            error_message = f"Error getting paging file usage: {e}"
            raise

        # 12. Cache Bytes
        try:
            memory_info = c.Win32_PerfRawData_PerfOS_Memory()[0]
            cache_bytes = int(memory_info.CacheBytes or 0)
            events.append({
                "name": "perf_counters",
                "value": cache_bytes // (1024 * 1024),  # Convert to MB
                "tag": "cache_bytes_mb"
            })
        except Exception as e:
            error_message = f"Error getting cache bytes: {e}"
            raise

        # 13. Committed Bytes
        try:
            memory_info = c.Win32_PerfRawData_PerfOS_Memory()[0]
            committed_bytes = int(memory_info.CommittedBytes or 0)
            events.append({
                "name": "perf_counters",
                "value": committed_bytes // (1024 * 1024),  # Convert to MB
                "tag": "committed_bytes_mb"
            })
        except Exception as e:
            error_message = f"Error getting committed bytes: {e}"
            raise

        # 14. Pool Paged Bytes
        try:
            memory_info = c.Win32_PerfRawData_PerfOS_Memory()[0]
            pool_paged = int(memory_info.PoolPagedBytes or 0)
            events.append({
                "name": "perf_counters",
                "value": pool_paged // (1024 * 1024),  # Convert to MB
                "tag": "pool_paged_bytes_mb"
            })
        except Exception as e:
            error_message = f"Error getting pool paged bytes: {e}"
            raise

        # 15. Pool Non-paged Bytes
        try:
            memory_info = c.Win32_PerfRawData_PerfOS_Memory()[0]
            pool_nonpaged = int(memory_info.PoolNonpagedBytes or 0)
            events.append({
                "name": "perf_counters",
                "value": pool_nonpaged // (1024 * 1024),  # Convert to MB
                "tag": "pool_nonpaged_bytes_mb"
            })
        except Exception as e:
            error_message = f"Error getting pool non-paged bytes: {e}"
            raise

        # 16. System Calls/sec
        try:
            system_info = c.Win32_PerfRawData_PerfOS_System()[0]
            syscalls = int(system_info.SystemCallsPersec or 0)
            events.append({
                "name": "perf_counters",
                "value": syscalls,
                "tag": "system_calls_per_sec"
            })
        except Exception as e:
            error_message = f"Error getting system calls: {e}"
            raise

        # 17. File Read Operations/sec and File Write Operations/sec
        try:
            system_info = c.Win32_PerfRawData_PerfOS_System()[0]
            file_reads = int(system_info.FileReadOperationsPersec or 0)
            file_writes = int(system_info.FileWriteOperationsPersec or 0)
            events.append({
                "name": "perf_counters",
                "value": file_reads,
                "tag": "file_read_ops_per_sec"
            })
            events.append({
                "name": "perf_counters", 
                "value": file_writes,
                "tag": "file_write_ops_per_sec"
            })
        except Exception as e:
            error_message = f"Error getting file operations: {e}"
            raise

        # 18. Registry Quota In Use %
        try:
            system_info = c.Win32_PerfRawData_PerfOS_System()[0]
            registry_quota = int(system_info.PercentRegistryQuotaInUse or 0)
            events.append({
                "name": "perf_counters",
                "value": registry_quota,
                "tag": "registry_quota_percent"
            })
        except Exception as e:
            error_message = f"Error getting registry quota: {e}"
            raise

        # 19. Processor Time % (for first processor)
        try:
            processors = c.Win32_PerfRawData_PerfOS_Processor()
            for proc in processors:
                if proc.Name == "_Total":
                    cpu_usage = 100 - int(proc.PercentIdleTime or 0)  # Invert idle time to get usage
                    events.append({
                        "name": "perf_counters",
                        "value": max(0, min(100, cpu_usage)),  # Clamp to 0-100
                        "tag": "cpu_usage_percent"
                    })
                    break
        except Exception as e:
            error_message = f"Error getting CPU usage: {e}"
            raise

        # 20. Disk Read/Write Bytes per sec (for first physical disk)
        try:
            disk_info = c.Win32_PerfRawData_PerfDisk_PhysicalDisk()
            for disk in disk_info:
                if disk.Name and "_Total" not in disk.Name and "HarddiskVolume" not in disk.Name:
                    read_bytes = int(disk.DiskReadBytesPersec or 0)
                    write_bytes = int(disk.DiskWriteBytesPersec or 0)
                    events.append({
                        "name": "perf_counters",
                        "value": read_bytes,
                        "tag": f"disk_read_bytes_per_sec,disk:{disk.Name}"
                    })
                    events.append({
                        "name": "perf_counters",
                        "value": write_bytes,
                        "tag": f"disk_write_bytes_per_sec,disk:{disk.Name}"
                    })
                    break  # Only get first physical disk
        except Exception as e:
            error_message = f"Error getting disk read/write bytes: {e}"
            raise

    except Exception as e:
        error_message = f"Error connecting to WMI: {e}"
        raise

    finally:
        # Clean up COM initialization
        try:
            if pythoncom is not None:
                pythoncom.CoUninitialize()
        except:
            pass
    
    error_message = None
    return events


def get_retention_rules(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get retention rules for the data collector.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary for the data collector
        
    Returns:
        List[Dict[str, Any]]: List of retention rule dictionaries
    """
    rules = [
        {
            "event_name": "perf_counters",
            "max_age_days": config.get('retention_days', 7)
        }
    ]
    return rules