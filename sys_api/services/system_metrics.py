import time

from sys_api.utils import run_command


def get_disk_metrics(min_usage: int, top_n: int | None = None):
    output = run_command(["df", "-h"])
    lines = output.splitlines()
    results = []

    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 6:
            filesystem = parts[0]
            total = parts[1]
            used = parts[2]
            available = parts[3]
            used_percent = parts[4]
            mount_point = parts[5]

            if filesystem in ["none", "tmpfs", "rootfs"]:
                continue

            percent_num = int(used_percent.strip("%"))
            if percent_num < min_usage:
                continue

            results.append(
                {
                    "filesystem": filesystem,
                    "total": total,
                    "used": used,
                    "available": available,
                    "used_percent": percent_num,
                    "mount_point": mount_point,
                }
            )

    results.sort(key=lambda x: x["used_percent"], reverse=True)

    if top_n:
        results = results[:top_n]

    return results


def get_memory_metrics():
    output = run_command(["free", "-h"])
    lines = output.splitlines()

    for line in lines:
        if line.startswith("Mem:"):
            parts = line.split()
            return {
                "total": parts[1],
                "used": parts[2],
                "free": parts[3],
            }

    return {}


def parse_cpu_line(line: str):
    parts = line.split()
    values = list(map(int, parts[1:]))

    idle = values[3] + values[4]  # idle + iowait
    total = sum(values)

    return idle, total


def get_cpu_metrics():
    output1 = run_command(["cat", "/proc/stat"])
    cpu_line1 = output1.splitlines()[0]
    idle1, total1 = parse_cpu_line(cpu_line1)

    time.sleep(1)

    output2 = run_command(["cat", "/proc/stat"])
    cpu_line2 = output2.splitlines()[0]
    idle2, total2 = parse_cpu_line(cpu_line2)

    idle_delta = idle2 - idle1
    total_delta = total2 - total1

    usage = 0
    if total_delta != 0:
        usage = (1 - idle_delta / total_delta) * 100

    return {
        "cpu_usage_percent": round(usage, 2),
    }


def get_uptime_metrics():
    output = run_command(["cat", "/proc/uptime"])
    first_value = output.split()[0]
    total_seconds = int(float(first_value))

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    return {
        "uptime_seconds": total_seconds,
        "uptime_readable": f"{days} days, {hours} hours, {minutes} minutes"
    }
