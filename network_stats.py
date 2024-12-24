from datetime import datetime, timedelta
import pytz
from db import mongo_client
from config import DB_NAME, COLLECTION_NAME

# Get database collection
db = mongo_client.get_database(DB_NAME)
network_stats = db.get_collection(COLLECTION_NAME)
network_stats_logs = db.get_collection(f"{COLLECTION_NAME}_logs")

def log_network_stats_event(event_type, message, data=None):
    """Log network statistics event
    Args:
        event_type: Event type (e.g. 'skip', 'validation', 'error')
        message: Event description
        data: Related data (optional)
    """
    try:
        current_time = datetime.now(pytz.UTC)
        
        # Calculate current period's start time
        current_weekday = current_time.weekday()
        days_since_wednesday = (current_weekday - 2) % 7
        period_start = current_time - timedelta(days=days_since_wednesday)
        period_start = period_start.replace(hour=12, minute=0, second=0, microsecond=0)
        
        if current_time < period_start:
            period_start -= timedelta(days=7)
            
        # Check if old logs need to be cleaned up
        last_log = network_stats_logs.find_one(sort=[('timestamp', -1)])
        if last_log and last_log.get('period_start'):
            latest_period_start = last_log['period_start']
            if latest_period_start.tzinfo is None:
                latest_period_start = pytz.UTC.localize(latest_period_start)
            if period_start > latest_period_start:
                old_logs = network_stats_logs.delete_many({
                    'timestamp': {'$lt': latest_period_start}
                })
                print(f"Cleaned up {old_logs.deleted_count} old log entries")
        
        # Create log entry
        log_entry = {
            'timestamp': current_time,
            'period_start': period_start,
            'event_type': event_type,
            'message': message
        }
        
        if data:
            log_entry['data'] = data
            
        network_stats_logs.insert_one(log_entry)
        
    except Exception as e:
        print(f"Error logging network stats event: {str(e)}")

def is_valid_hashrate(current_value, previous_values, threshold=0.5):
    """Check if hashrate value is valid
    Args:
        current_value: Current hashrate value
        previous_values: List of previous hashrate values
        threshold: Maximum allowed change ratio (default 50%)
    """
    if not previous_values:
        return True
    
    # If only one historical value, compare directly
    if len(previous_values) == 1:
        prev_value = previous_values[0]
        if prev_value == 0:
            return True
        change_ratio = abs(current_value - prev_value) / prev_value
        return change_ratio <= threshold
    
    # Calculate moving average, excluding outliers
    sorted_values = sorted(previous_values)
    if len(sorted_values) >= 3:
        # Remove highest and lowest values
        values_for_avg = sorted_values[1:-1]
    else:
        values_for_avg = sorted_values
    
    avg = sum(values_for_avg) / len(values_for_avg)
    if avg == 0:
        return True
    
    # Calculate change ratio
    change_ratio = abs(current_value - avg) / avg
    return change_ratio <= threshold

def calculate_network_stats(tool_data):
    """Calculate and store network statistics data
    Args:
        tool_data: Data from /api/qubic/tool
    """
    try:
        current_time = datetime.now(pytz.UTC)
        print(f"\n=== Starting network stats calculation at {current_time} ===")
        
        # Get latest record
        last_record = network_stats.find_one(sort=[('timestamp', -1)])
        
        # Check record interval (at least 5 minutes)
        if last_record:
            last_time = last_record.get('timestamp')
            # Ensure last_time has timezone info
            if last_time.tzinfo is None:
                last_time = pytz.UTC.localize(last_time)
            time_diff = (current_time - last_time).total_seconds()
            
            if time_diff < 300:  # 5 minutes
                log_network_stats_event('skip', f"Only {time_diff:.1f} seconds since last record")
                print(f"Only {time_diff:.1f} seconds since last record, skipping")
                return
        
        # Get idle status
        is_idle = tool_data.get('data', {}).get('idle', False)
        print(f"Current idle status: {is_idle}")
        
        # If current is idle, skip
        if is_idle:
            log_network_stats_event('skip', f"Mining is idle at {current_time}")
            print(f"Mining is idle at {current_time}, skipping record")
            return
            
        # If recovering from idle, check recovery time
        if last_record and last_record.get('was_idle', False):
            recovery_time = (current_time - last_time).total_seconds()
            required_wait_time = 300  # Wait 5 minutes
            if recovery_time < required_wait_time:
                log_network_stats_event('skip', f"Only {recovery_time:.1f} seconds since idle recovery")
                print(f"Only {recovery_time:.1f} seconds since idle recovery, waiting for {required_wait_time} seconds")
                return
            print(f"Waited {recovery_time:.1f} seconds after idle recovery, proceeding")
        
        # Get hashrate data from tool_data
        pool_hashrate = tool_data.get('data', {}).get('pool_hashrate', {})
        current_hashrates = pool_hashrate.get('current', {})
        
        # Get corrected hashrate data
        apool_data = tool_data.get('data', {}).get('apool', {})
        solutions_data = tool_data.get('data', {}).get('solutions', {})
        minerlab_data = tool_data.get('data', {}).get('minerlab', {})
        
        estimated_its = float(current_hashrates.get('qli_hashrate', 0))
        apool_hashrate = float(apool_data.get('corrected_hashrate', 0))
        solutions_hashrate = float(solutions_data.get('corrected_hashrate', 0))
        minerlab_hashrate = float(minerlab_data.get('corrected_hashrate', 0))
        
        hashrate_data = {
            'qli': estimated_its,
            'apool': apool_hashrate,
            'solutions': solutions_hashrate,
            'minerlab': minerlab_hashrate
        }
        
        # Validate hashrate data
        validation_results = {
            'qli': True,
            'apool': True,
            'solutions': True,
            'minerlab': True
        }
        
        # Check QLI hashrate
        if estimated_its <= 0:
            log_network_stats_event('warning', "QLI hashrate is non-positive")
            print("Warning: QLI hashrate is non-positive")
            validation_results['qli'] = False
            
            # Use historical QLI hashrate
            recent_records = list(network_stats.find(
                {'qli_hashrate': {'$gt': 0}},
                {'qli_hashrate': 1}
            ).sort('timestamp', -1).limit(5))
            
            if recent_records:
                estimated_its = sum(r['qli_hashrate'] for r in recent_records) / len(recent_records)
                log_network_stats_event('info', f"Using average of last {len(recent_records)} records for QLI")
                print(f"Using average of last {len(recent_records)} records for QLI: {estimated_its}")
                validation_results['qli'] = True
        
        # Check pool hashrate
        if apool_hashrate <= 0 or solutions_hashrate <= 0 or minerlab_hashrate <= 0:
            log_network_stats_event('warning', "Some pool hashrate is non-positive", hashrate_data)
            print(f"Warning: Some pool hashrate is non-positive: {hashrate_data}")
            if apool_hashrate <= 0:
                validation_results['apool'] = False
            if solutions_hashrate <= 0:
                validation_results['solutions'] = False
            if minerlab_hashrate <= 0:
                validation_results['minerlab'] = False
        
        # If any validation fails, skip record
        if not all(validation_results.values()):
            log_network_stats_event('validation', "Skipping record with abnormal values", {
                'hashrates': hashrate_data,
                'validation_results': validation_results
            })
            print("Skipping record due to validation failures")
            return
        
        # Calculate current period's start time
        current_weekday = current_time.weekday()
        days_since_wednesday = (current_weekday - 2) % 7
        period_start = current_time - timedelta(days=days_since_wednesday)
        period_start = period_start.replace(hour=12, minute=0, second=0, microsecond=0)
        
        if current_time < period_start:
            period_start -= timedelta(days=7)
            
        # Check if old records need to be cleaned up
        if last_record and last_record.get('period_start'):
            latest_period_start = last_record['period_start']
            if latest_period_start.tzinfo is None:
                latest_period_start = pytz.UTC.localize(latest_period_start)
            
            if period_start > latest_period_start:
                # New period started, clean up old records
                old_records = network_stats.delete_many({
                    'timestamp': {'$lt': latest_period_start}
                })
                print(f"New period started, deleted {old_records.deleted_count} old records")
        
        # Save record
        record = {
            'timestamp': current_time,
            'period_start': period_start,
            'qli_hashrate': estimated_its,
            'apool_hashrate': apool_hashrate,
            'solutions_hashrate': solutions_hashrate,
            'minerlab_hashrate': minerlab_hashrate,
            'was_idle': is_idle
        }
        
        network_stats.insert_one(record)
        log_network_stats_event('success', "Successfully recorded network stats", {
            'hashrates': hashrate_data,
            'validation_results': validation_results
        })
        print(f"\nSuccessfully recorded network stats with values:")
        print(f"qli={estimated_its}, apool={apool_hashrate}, solutions={solutions_hashrate}, minerlab={minerlab_hashrate}")
        
        # New code
        print("New code:")
        print("Record saved successfully, calculating averages...")
        
    except Exception as e:
        error_msg = f"Error calculating network stats: {str(e)}"
        log_network_stats_event('error', error_msg)
        print(error_msg)

def get_network_stats_data():
    """Get network statistics data"""
    try:
        # Get current period's start time
        current_time = datetime.now(pytz.UTC)
        current_weekday = current_time.weekday()
        days_since_wednesday = (current_weekday - 2) % 7
        period_start = current_time - timedelta(days=days_since_wednesday)
        period_start = period_start.replace(hour=12, minute=0, second=0, microsecond=0)
        
        if current_time < period_start:
            period_start -= timedelta(days=7)
        
        print(f"\nCalculating averages for period starting from: {period_start}")
        
        # Get current period's records
        records = list(network_stats.find({
            'timestamp': {'$gte': period_start}
        }).sort('timestamp', 1))
        
        if not records:
            print("No records found in the current period")
            return None
        
        # Use sliding window for data validation
        window_size = 5
        valid_records = []
        
        for i, record in enumerate(records):
            if i < window_size - 1:
                valid_records.append(record)
                continue
            
            # Get previous records for validation
            window = records[i-window_size+1:i+1]
            
            # Check each pool's hashrate
            qli_values = [r['qli_hashrate'] for r in window]
            apool_values = [r['apool_hashrate'] for r in window]
            solutions_values = [r['solutions_hashrate'] for r in window]
            minerlab_values = [r['minerlab_hashrate'] for r in window]
            
            # If all values pass validation, add to valid records
            if (is_valid_hashrate(record['qli_hashrate'], qli_values[:-1]) and
                is_valid_hashrate(record['apool_hashrate'], apool_values[:-1]) and
                is_valid_hashrate(record['solutions_hashrate'], solutions_values[:-1]) and
                is_valid_hashrate(record['minerlab_hashrate'], minerlab_values[:-1])):
                valid_records.append(record)
        
        if not valid_records:
            print("No valid records found after validation")
            return None
        
        # Calculate averages
        total_qli = sum(record['qli_hashrate'] for record in valid_records)
        total_apool = sum(record['apool_hashrate'] for record in valid_records)
        total_solutions = sum(record['solutions_hashrate'] for record in valid_records)
        total_minerlab = sum(record['minerlab_hashrate'] for record in valid_records)
        record_count = len(valid_records)
        
        averages = {
            'average_qli_hashrate': total_qli / record_count if record_count > 0 else 0,
            'average_apool_hashrate': total_apool / record_count if record_count > 0 else 0,
            'average_solutions_hashrate': total_solutions / record_count if record_count > 0 else 0,
            'average_minerlab_hashrate': total_minerlab / record_count if record_count > 0 else 0
        }
        
        print(f"Calculated averages from {record_count} valid records")
        
        return {
            'averages': averages,
            'record_count': record_count,  # Add record count
            'period_start': period_start.isoformat()
        }
        
    except Exception as e:
        print(f"Error in get_network_stats_data: {str(e)}")
        return None

def get_network_stats_logs(limit=100):
    """Get recent network statistics logs"""
    try:
        db = mongo_client[DB_NAME]
        collection = db[f"{COLLECTION_NAME}_logs"]
        
        # Get recent logs
        logs = list(collection.find(
            {},
            {'_id': 0}  # Do not return _id field
        ).sort('timestamp', -1).limit(limit))
        
        # Convert timestamps to ISO format strings
        for log in logs:
            if 'timestamp' in log:
                log['timestamp'] = log['timestamp'].isoformat()
            if 'period_start' in log:
                log['period_start'] = log['period_start'].isoformat()
                
        return logs
    except Exception as e:
        print(f"Error getting logs: {str(e)}")
        return []

def check_db_connection():
    """Check database connection status"""
    try:
        # Try to ping database
        mongo_client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        return True
    except Exception as e:
        error_msg = f"Failed to connect to MongoDB: {str(e)}"
        print(error_msg)
        return False