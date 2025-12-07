# Maigret Optimization Guide

This document outlines potential optimizations for the Maigret tool to improve performance.

## Current Performance Bottlenecks

### 1. Network Request Handling

- **HTTP Request Processing**: The program spends most of its time waiting for HTTP responses from thousands of sites.
- **Connection Pool Management**: Current implementation using `TCPConnector` with individual session creation isn't optimized.
- **SSL Verification**: Every request performs SSL verification, which adds overhead.

### 2. Concurrency Implementation

- **Executors**: Multiple deprecated executor classes are still in the codebase.
- **Worker Management**: The `AsyncioProgressbarQueueExecutor` creates workers but could be more efficient with task distribution.
- **Progress Tracking**: Progress updates are potentially expensive, involving `asyncio.sleep(0)` calls.

### 3. Data Processing

- **JSON Processing**: Large `data.json` file with thousands of site definitions adds initialization overhead.
- **String Operations**: Multiple string comparisons and manipulations in site detection logic.
- **Regular Expression Matching**: Regular expressions are compiled and used frequently.

## Optimization Recommendations

### 1. HTTP Request Optimization

```python
# Optimize connection pooling
async def optimize_session_creation():
    # Create a single shared connector with optimized settings
    connector = TCPConnector(
        ssl=False,
        limit=100,  # Increase connection limit
        ttl_dns_cache=300,  # Cache DNS results longer
        enable_cleanup_closed=True  # Clean up closed connections
    )
    
    # Create a session factory that reuses the connector
    async def get_session(proxy=None):
        if proxy:
            from aiohttp_socks import ProxyConnector
            proxy_connector = ProxyConnector.from_url(proxy)
            return ClientSession(connector=proxy_connector, trust_env=True)
        else:
            return ClientSession(connector=connector, trust_env=True)
    
    return get_session
```

### 2. Concurrency Improvements

```python
# Optimize AsyncioProgressbarQueueExecutor
class OptimizedQueueExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Increase default worker count based on available resources
        self.workers_count = kwargs.get('in_parallel', min(32, os.cpu_count() * 4))
        self.queue = asyncio.Queue(self.workers_count * 2)  # Double queue size for buffer
        self.timeout = kwargs.get('timeout')
        # Use simple progress tracking by default
        self.progress_func = kwargs.get('progress_func', lambda x, **kw: _SimpleProgressBar(x))
        self.progress = None
        self.results = []

    # Simplified worker implementation
    async def worker(self):
        while True:
            try:
                task = await self.queue.get()
                f, args, kwargs = task
                
                # Process batch of tasks when possible
                task_result = await f(*args, **kwargs)
                self.results.append(task_result)
                
                # Simple progress update that avoids additional awaits when possible
                if self.progress and not asyncio.iscoroutinefunction(self.progress):
                    self.progress(1)
                
                self.queue.task_done()
            except asyncio.QueueEmpty:
                return
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                self.queue.task_done()
```

### 3. Initialization Optimizations

```python
# Optimize site data loading
class OptimizedMaigretDatabase(MaigretDatabase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache for URL patterns to avoid recompilation
        self._url_pattern_cache = {}
        # Index sites by domain for faster lookup
        self._domain_index = {}
        
    def load_sites_from_json(self, json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            site_data = json.load(f)
            
        # Process sites in batches
        sites = site_data.get("sites", {})
        batch_size = 100
        site_items = list(sites.items())
        
        for i in range(0, len(site_items), batch_size):
            batch = site_items[i:i+batch_size]
            for site_name, site_info in batch:
                site = MaigretSite(site_name, site_info)
                self.add_site(site)
                
                # Index by domain for faster lookups
                domain = self._extract_domain(site.url_main)
                if domain:
                    if domain not in self._domain_index:
                        self._domain_index[domain] = []
                    self._domain_index[domain].append(site)
```

### 4. Memory Management

```python
# Optimize memory usage
def optimize_memory_usage():
    # Use slots for common classes to reduce memory footprint
    class OptimizedMaigretSite(MaigretSite):
        __slots__ = (
            'name', 'url_main', 'url', 'engine', 'tags', 'check_type', 
            'presense_strs', 'absence_strs', 'headers', 'alexa_rank'
        )
        
    # Implement lazy loading for large data structures
    class LazyLoadDatabase:
        def __init__(self, json_file):
            self.json_file = json_file
            self._loaded = False
            self._sites = {}
            
        def get_site(self, site_name):
            if not self._loaded:
                self._load_site(site_name)
            return self._sites.get(site_name)
            
        def _load_site(self, site_name):
            # Load only the specific site data
            with open(self.json_file, 'r', encoding='utf-8') as f:
                site_data = json.load(f)
                site_info = site_data.get("sites", {}).get(site_name)
                if site_info:
                    self._sites[site_name] = MaigretSite(site_name, site_info)
```

### 5. Performance Profiling and Monitoring

```python
# Add performance monitoring
async def profile_execution(coro, label=""):
    import time
    start = time.time()
    result = await coro
    duration = time.time() - start
    logging.debug(f"Performance {label}: {duration:.4f}s")
    return result
```

## Implementation Priority

1. Optimize HTTP connection pooling first (biggest impact)
2. Improve worker management and task distribution
3. Implement memory optimizations for large site database
4. Add caching mechanisms for repeated operations
5. Use lazy loading for site data

## Measurement

After implementing these optimizations, measure performance using the following metrics:

1. Total execution time for a standard search query
2. Memory usage during execution
3. CPU utilization
4. Number of successful site checks per second

These improvements should significantly enhance Maigret's performance while maintaining its core functionality.