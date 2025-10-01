# ROAM Client

Python client library for **R**un **O**n **A**nother **M**achine remote execution.

## Features

🔥 **Real-time SSE streaming** - Get results as they happen  
⚡ **Persistent workers** - No container startup overhead  
🎯 **Simple decorators** - Just add `@env.fn` to any function  
🔄 **Async/sync support** - Works in both contexts  
🛡️ **Error handling** - Proper exception propagation  

## Architecture

```
@env.fn → Job Queue → Persistent Workers → SSE Stream → Result
```

## Usage

```python
from remote_env import Env

env = Env(base_url="http://roam.localtest.me")

@env.fn  
def get_system_info():
    import subprocess
    return subprocess.check_output("uname -a", shell=True, text=True)

# Sync usage
result = get_system_info.sync()

# Async usage  
result = await get_system_info()
```

## Configuration

```python
env = Env(
    base_url="http://your-roam-server.com",
    should_run_locally=lambda: os.getenv("IS_LOCAL") == "1"
)
```
