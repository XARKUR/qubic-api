# Qubic API Service

This is an API service for collecting and providing Qubic network data. The service periodically collects data from multiple sources, including the official Qubic API, various mining pools, and provides a unified interface for access.

## Features

- Real-time Qubic network status
- Collect and integrate data from multiple mining pools
- Periodically calculate and store network statistics
- Provide voting information query
- Support cross-domain requests (CORS)
- Cache mechanism to optimize response speed

## API Endpoints

### 1. Get Comprehensive Data
```
GET /api/qubic/tool
```
Returns comprehensive data containing:
- Current epoch information
- Qubic price
- Network hashrate estimate
- Status of each mining pool
- Voting information
- Exchange rate data

### 2. Network Statistics
```
GET /api/network-stats/data
```
Returns network statistics data, including:
- Hashrate data for each mining pool
- Historical average values
- Record count

### 3. Update Network Statistics
```
POST /api/network-stats/update
```
Manually trigger network statistics data update

### 4. Get Logs
```
GET /api/network-stats/logs
```
Get recent network statistics logs

## Deployment Requirements

- Python 3.8+
- MongoDB
- Dependency packages (see requirements.txt)

## Environment Variables

The following environment variables need to be configured:
- `MONGODB_URI`: MongoDB connection string
- `DB_NAME`: Database name
- `COLLECTION_NAME`: Collection name
- `QUBIC_API_KEY`: Qubic API key (optional)

## Local Development

1. Clone the repository
```bash
git clone <repository-url>
cd qubic-api
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure environment variables
```bash
export MONGODB_URI="your-mongodb-uri"
export DB_NAME="your-db-name"
export COLLECTION_NAME="your-collection-name"
```

4. Run the service
```bash
python app.py
```

## Production Deployment

The service supports deployment on Vercel, with configuration files in `vercel.json`.

## Data Update Mechanism

- The service updates data immediately upon startup
- Then updates data every 5 minutes automatically
- The update mechanism includes a validation process to ensure data quality
- Automatically cleans up expired data

## CORS Configuration

Supports cross-domain requests from the following domains:
- https://tool.qubic.site
- https://qubic-tools.vercel.app
- Local development environment (localhost)

## Error Handling

- All API requests have proper error handling
- Error responses contain detailed error information
- Critical operations are logged

## Cache Mechanism

- Uses decorators to implement caching
- Cache duration can be configured
- Automatic update mechanism ensures data freshness

## Automation Mechanism

### Token Auto-update

The service implements an automatic Qubic API Token update mechanism:

1. **Initialization**
   - Automatically obtains a new Token upon service startup
   - Stores the Token in memory to avoid frequent I/O
   - Uses decorators to ensure Token validity during API calls

2. **Auto Refresh**
   - Automatically updates the Token before expiration
   - Uses background tasks to periodically check Token status
   - Retry mechanism for update failures

3. **Configuration**
   ```python
   # Configure in config.py
   QUBIC_API_KEY = "your-api-key"  # API key
   TOKEN_REFRESH_INTERVAL = 3600    # Token refresh interval (seconds)
   TOKEN_RETRY_ATTEMPTS = 3         # Retry attempts
   ```

4. **Usage**
   ```python
   from utils import get_qubic_headers
   
   # Automatic Token handling
   headers = get_qubic_headers()
   response = requests.get(url, headers=headers)
   ```

### Data Auto-update

1. **Scheduled Tasks**
   - Uses APScheduler for task management
   - Supports cron expression configuration
   - Automatic retry for failed tasks

2. **Configuration Example**
   ```python
   # Configure scheduled tasks in app.py
   scheduler.add_job(
       update_network_stats,
       'cron',
       minute='*/5',  # Execute every 5 minutes
       id='update_network_stats'
   )
   ```

3. **Monitoring**
   - Records each update status
   - Supports manual update trigger
   - Automatic notification for exceptions

### Error Retry

1. **Network Request Retry**
   ```python
   # Retry mechanism in utils.py
   @retry(stop_max_attempt_number=3, wait_fixed=2000)
   def safe_request(url, **kwargs):
       response = requests.get(url, **kwargs)
       response.raise_for_status()
       return response.json()
   ```

2. **Data Validation**
   - Checks data integrity
   - Validates value ranges
   - Automatic repair of abnormal data

### Logging

1. **Auto-log Key Events**
   - Token update status
   - Data retrieval results
   - Errors and exceptions

2. **Log Cleanup**
   - Automatic cleanup of expired logs
   - Retains important error records
   - Configurable retention period

### Monitoring & Alerts

1. **Health Check**
   - Regular service status checks
   - Monitors data update status
   - Checks database connections

2. **Exception Handling**
   - Automatic retry of failed operations
   - Records detailed error information
   - Supports configurable alert thresholds

## Hashrate Statistics Mechanism

### Data Collection

1. **Data Sources**
   - QubicLi API (estimatedIts)
   - Apool Pool Data
   - Solutions Pool Data
   - Minerlab Pool Data

2. **Collection Frequency**
   - Every 5 minutes
   - Immediate collection on service startup
   - Supports manual collection trigger

### Hashrate Calculation

1. **Raw Hashrate**
   ```python
   {
       "qli_hashrate": estimatedIts,            # QubicLi estimated hashrate
       "apool_hashrate": pool_hash,             # Apool raw hashrate
       "solutions_hashrate": iterrate,          # Solutions raw hashrate
       "minerlab_hashrate": currentIts          # Minerlab raw hashrate
   }
   ```

2. **Corrected Hashrate**
   ```python
   # Hashrate correction based on solution count
   corrected_hashrate = pool_hash / accepted_solution * total_solutions
   ```
   - Considers pool solution ratio
   - Automatic hashrate correction
   - Handles zero and abnormal values

### Average Calculation

1. **Time Period**
   - Starts every Wednesday 12:00 UTC
   - Ends next Wednesday 12:00 UTC
   - Automatic period transition

2. **Data Validation**
   ```python
   def is_valid_hashrate(current_value, previous_values, threshold=0.5):
       """Validate if hashrate is within reasonable range"""
       if not previous_values:
           return True
       avg = sum(previous_values) / len(previous_values)
       max_change = avg * threshold
       return abs(current_value - avg) <= max_change
   ```

3. **Exception Handling**
   - Skip abnormal data points
   - Use historical data for补充
   - Log validation failures

### Data Storage

1. **Record Structure**
   ```python
   {
       'timestamp': current_time,          # Record time
       'period_start': period_start,       # Period start time
       'qli_hashrate': estimated_its,      # QLI hashrate
       'apool_hashrate': apool_hashrate,   # Apool hashrate
       'solutions_hashrate': solutions_hashrate,  # Solutions hashrate
       'minerlab_hashrate': minerlab_hashrate,   # Minerlab hashrate
       'was_idle': is_idle                 # Idle status
   }
   ```

2. **Data Cleanup**
   - Automatic cleanup of old period data
   - Retain all records for current period
   - Log cleanup operations

### Statistical Metrics

1. **Basic Metrics**
   - Current hashrate for each pool
   - Average hashrate within period
   - Valid record count

2. **Calculation Rules**
   - Exclude idle status records
   - Validate data validity
   - Handle data intervals (≥5 minutes)

3. **Output Format**
   ```json
   {
       "current": {
           "qli_hashrate": 123456,
           "apool_hashrate": 234567,
           "solutions_hashrate": 345678,
           "minerlab_hashrate": 456789
       },
       "average": {
           "average_qli_hashrate": 123000,
           "average_apool_hashrate": 234000,
           "average_solutions_hashrate": 345000,
           "average_minerlab_hashrate": 456000,
           "record_count": 1440
       }
   }
   ```
