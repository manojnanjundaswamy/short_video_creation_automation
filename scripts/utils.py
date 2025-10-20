import logging
import os
import time
import psutil


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/scripts/app_metrics.log"),
        logging.StreamHandler()
    ]
)

start_time_main = time.time()
# 🧮 Helper: Measure execution time
def measure_execution_time(func):
    """Decorator to measure and log execution time of a function"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / (1024 * 1024)  # MB
        
        logging.info(f"▶️ Starting '{func.__name__}' ... Memory: {memory_before:.2f} MB")
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            logging.error(f"❌ Error occurred in '{func.__name__}': {e}", exc_info=True)
            raise

        end_time = time.time()
        elapsed = end_time - start_time
        memory_after = process.memory_info().rss / (1024 * 1024)

        logging.info(
            f"✅ Finished '{func.__name__}' | Time: {elapsed:.2f}s | "
            f"Memory Change: {memory_after - memory_before:.2f} MB | Total Memory: {memory_after:.2f} MB"
        )
        return result
    return wrapper
