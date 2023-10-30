import psutil

disk_usage = psutil.disk_usage("/")
print(disk_usage.percent)
print(disk_usage.free)